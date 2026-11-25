"""Posibles tickets duplicados al crear uno (RF-061; docs/06, RN-175; docs/10, sección 92).

La advertencia nunca impide crear: solo muestra tickets **abiertos y recientes** de la misma
categoría cuyo título comparte palabras con el nuevo. Se compara con la búsqueda en español
(`search.py`), así que «impresoras» encuentra «impresora» y da igual escribir sin tildes.

**Cada persona solo ve tickets que ya puede ver** (`visible_tickets_condition`): un
Solicitante nunca descubre tickets ajenos por esta vía.

La sensibilidad es configuración del Administrador: cuántos días atrás se mira (0 desactiva
la advertencia) y cuántas palabras deben coincidir.
"""

import re
from datetime import datetime, timedelta

from sqlalchemy import case
from sqlalchemy.orm import contains_eager

from .. import settings
from ..configuration import value_of
from ..extensions import db
from ..models import Categoria, Estado, Ticket
from ..models.categoria import FALLBACK_CATEGORY_CODE
from ..search import search_vector, text_search_query, without_accents
from ..sla import periods as sla_periods
from .queries import visible_tickets_condition
from .service import CLOSED_STATE_CODE

SIMILAR_LIMIT = 5
MAX_WORDS = 8
MIN_WORD_LENGTH = 3

# Palabras que aparecen en casi cualquier título y no distinguen un problema de otro
# (sin tildes, como se comparan).
_STOPWORDS = frozenset(
    (
        "ayuda", "buenas", "como", "con", "cuando", "del", "desde", "dias", "donde", "esa",
        "ese", "eso", "esta", "estan", "este", "favor", "hay", "las", "les", "los", "mas",
        "mis", "muy", "necesito", "nos", "para", "pero", "por", "porque", "problema",
        "puede", "puedo", "que", "sin", "sobre", "solicitud", "sus", "tengo", "tiene",
        "todo", "una", "uno", "urgente",
    )
)


def significant_words(title: str) -> list[str]:
    """Las palabras de `title` que sirven para compararlo, sin repetir."""
    words: dict[str, str] = {}

    for word in re.findall(r"\w+", (title or "").lower()):
        plain = without_accents(word)

        if len(plain) >= MIN_WORD_LENGTH and plain not in _STOPWORDS:
            words.setdefault(plain, word)

    return list(words.values())[:MAX_WORDS]


def find_similar_tickets(
    user,
    *,
    title: str,
    category_id: int,
    now: datetime | None = None,
    limit: int = SIMILAR_LIMIT,
) -> list[Ticket]:
    """Los tickets que `user` puede ver y que parecen tratar de lo mismo, primero los que
    comparten más palabras. Lista vacía si la advertencia está desactivada o el título no
    tiene palabras que comparar."""
    window_days = value_of(settings.DUPLICATE_WINDOW_DAYS)
    words = significant_words(title)

    if window_days <= 0 or not words:
        return []

    # Con un título de una sola palabra no se puede exigir que coincidan dos.
    required = min(value_of(settings.DUPLICATE_MIN_WORDS), len(words))
    since = (now or sla_periods.current_time()) - timedelta(days=window_days)
    conditions = [
        visible_tickets_condition(user),
        Estado.codigo != CLOSED_STATE_CODE,
        Ticket.fecha_creacion >= since,
    ]
    category = db.session.get(Categoria, category_id)

    # Quien no sabe clasificar usa «Sin clasificar»: entonces se mira en todas; con una
    # categoría concreta, en ella y en lo que quedó sin clasificar.
    if category is not None and category.codigo != FALLBACK_CATEGORY_CODE:
        fallback = db.select(Categoria.id).where(Categoria.codigo == FALLBACK_CATEGORY_CODE)
        conditions.append(
            (Ticket.categoria_id == category.id) | Ticket.categoria_id.in_(fallback)
        )

    # El vector de cada título se calcula una sola vez (`MATERIALIZED`): sin eso PostgreSQL
    # lo repite por cada palabra y, con 20 000 candidatos, la consulta tarda 2,5 veces más.
    candidates = (
        db.select(
            Ticket.id.label("ticket_id"), search_vector(Ticket.titulo).label("vector")
        )
        .join(Estado, Estado.id == Ticket.estado_id)
        .where(*conditions)
        .cte("candidatos")
        .prefix_with("MATERIALIZED")
    )
    shared = sum(
        case((candidates.c.vector.op("@@")(text_search_query(word)), 1), else_=0)
        for word in words
    )

    return list(
        db.session.scalars(
            db.select(Ticket)
            .join(candidates, candidates.c.ticket_id == Ticket.id)
            .join(Estado, Estado.id == Ticket.estado_id)
            .options(contains_eager(Ticket.estado))
            .where(shared >= required)
            .order_by(shared.desc(), Ticket.id.desc())
            .limit(limit)
        )
    )
