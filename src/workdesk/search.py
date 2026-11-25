"""Utilidades compartidas por las búsquedas.

**Búsqueda por palabras en español** (base de conocimiento, y la advertencia de tickets
parecidos). PostgreSQL entiende el español («impresoras» encuentra «impresora»), pero no
perdona las tildes: «configuración» se indexa como «configur» y quien escribe
«configuracion» no la encontraría. Por eso se indexa y se consulta dos veces, sin ninguna
extensión: con el diccionario español y, además, con las palabras sin tildes (`simple` sobre
el texto pasado por `translate`). Una coincidencia en cualquiera de las dos vale.
"""

from sqlalchemy import cast, func, literal
from sqlalchemy.dialects.postgresql import REGCONFIG

ACCENTED = "áàäâéèëêíìïîóòöôúùüûñ"
UNACCENTED = "aaaaeeeeiiiioooouuuun"

_ACCENT_TABLE = str.maketrans(ACCENTED, UNACCENTED)


def escape_like(text: str) -> str:
    """Escapa `%`, `_` y `\\` para que se busquen literalmente en un `ILIKE`.

    Se usa junto con `escape="\\\\"` en la comparación.
    """
    return (
        text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )


def without_accents(text: str) -> str:
    """El texto en minúsculas y sin tildes ni eñes."""
    return text.lower().translate(_ACCENT_TABLE)


def indexed_text_sql(column: str, weight: str) -> str:
    """La expresión SQL que indexa `column` con el peso `weight` (`A` a `D`).

    Es texto porque define una columna generada: `column` y `weight` los escribe el código,
    nunca una persona. Todas sus funciones son inmutables, como exige PostgreSQL.
    """
    plain = f"translate(lower({column}), '{ACCENTED}', '{UNACCENTED}')"

    return (
        f"setweight(to_tsvector('spanish'::regconfig, {column}), '{weight}') || "
        f"setweight(to_tsvector('simple'::regconfig, {plain}), '{weight}')"
    )


def search_vector(column):
    """El `tsvector` de una columna calculado en la consulta (para columnas sin uno
    guardado, como el título de un ticket). Equivale a `indexed_text_sql`."""
    plain = func.translate(func.lower(column), ACCENTED, UNACCENTED)

    return func.to_tsvector(cast(literal("spanish"), REGCONFIG), column).op("||")(
        func.to_tsvector(cast(literal("simple"), REGCONFIG), plain)
    )


def text_search_query(text: str):
    """La consulta (`tsquery`) para lo que escribió una persona, contra `indexed_text_sql`.

    Usa `websearch_to_tsquery`, que no falla con ninguna entrada: admite comillas para una
    frase, `-` para excluir y `or`. Todas las palabras deben aparecer.
    """
    spanish = func.websearch_to_tsquery(cast(literal("spanish"), REGCONFIG), text)
    plain = func.websearch_to_tsquery(
        cast(literal("simple"), REGCONFIG), without_accents(text)
    )

    return spanish.op("||")(plain)
