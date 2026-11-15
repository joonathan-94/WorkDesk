from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import false, func, true
from sqlalchemy.orm import contains_eager, joinedload, selectinload

from ..catalogs.service import list_categories
from ..extensions import db
from ..formatting import start_of_local_day
from ..models import (
    Categoria,
    Estado,
    Prioridad,
    Role,
    Ticket,
    TicketEvent,
    TicketHistory,
    TicketRequester,
    Ubicacion,
    User,
)
from ..models.admin_audit_log import ActorType
from ..models.categoria import FALLBACK_CATEGORY_CODE
from ..models.ticket import MAX_DESCRIPTION_LENGTH, MAX_TITLE_LENGTH
from ..search import escape_like
from ..security import STAFF_ROLES, RoleCode, has_any_role

INITIAL_STATE_CODE = "NUEVO"
CLOSED_STATE_CODE = "CERRADO"

# Listado (docs/11, UI-003).
PAGE_SIZE = 20
MAX_SEARCH_LENGTH = 100

# Pestañas. "Abiertos" son todos los tickets que no están Cerrados: uno
# Resuelto sigue abierto porque espera la validación del solicitante y puede
# reabrirse (docs/08).
TAB_ALL = "todos"
TAB_OPEN = "abiertos"
TAB_CLOSED = "cerrados"
VALID_TABS = (TAB_ALL, TAB_OPEN, TAB_CLOSED)
DEFAULT_TAB = TAB_OPEN

SORT_RECENT = "recientes"
SORT_OLDEST = "antiguos"
SORT_PRIORITY = "prioridad"
SORT_UPDATED = "actualizados"
DEFAULT_SORT = SORT_RECENT

# Nombre visible de cada orden, en el orden en que se ofrecen.
SORT_LABELS = {
    SORT_RECENT: "Más recientes",
    SORT_OLDEST: "Más antiguos",
    SORT_PRIORITY: "Mayor prioridad primero",
    SORT_UPDATED: "Recién actualizados",
}

_ORDERINGS = {
    SORT_RECENT: (Ticket.fecha_creacion.desc(), Ticket.id.desc()),
    SORT_OLDEST: (Ticket.fecha_creacion.asc(), Ticket.id.asc()),
    SORT_PRIORITY: (
        Prioridad.nivel.desc(),
        Ticket.fecha_creacion.desc(),
        Ticket.id.desc(),
    ),
    SORT_UPDATED: (
        func.coalesce(Ticket.fecha_modificacion, Ticket.fecha_creacion).desc(),
        Ticket.id.desc(),
    ),
}


@dataclass(frozen=True)
class TicketFilters:
    """Búsqueda y filtros del listado (todos opcionales y combinables)."""

    query_text: str = ""
    state_id: int | None = None
    priority_id: int | None = None
    category_id: int | None = None
    location_id: int | None = None
    created_from: date | None = None
    created_to: date | None = None


class TicketRuleError(ValueError):
    """Un dato del ticket incumple una regla de negocio.

    El mensaje está pensado para mostrarse al usuario.
    """


def clean_title_and_description(title: str, description: str) -> tuple[str, str]:
    """Recorta y valida el título y la descripción de un ticket.

    Son las mismas reglas al crear y al editar: ambos obligatorios y con su
    longitud máxima. Lanza `TicketRuleError` con un mensaje para el usuario.
    """
    title = title.strip()
    description = description.strip()

    if not title:
        raise TicketRuleError("El título es obligatorio.")

    if len(title) > MAX_TITLE_LENGTH:
        raise TicketRuleError(
            f"El título no puede superar los {MAX_TITLE_LENGTH} caracteres."
        )

    if not description:
        raise TicketRuleError("La descripción es obligatoria.")

    if len(description) > MAX_DESCRIPTION_LENGTH:
        raise TicketRuleError(
            "La descripción no puede superar los "
            f"{MAX_DESCRIPTION_LENGTH} caracteres."
        )

    return title, description


def create_ticket(
    *,
    actor: User,
    title: str,
    description: str,
    category_id: int,
    priority_id: int,
    location_id: int | None = None,
    requester_ids: Iterable[int] = (),
) -> Ticket:
    """Crea un ticket en estado Nuevo y registra su evento de creación.

    - La categoría, la prioridad y la ubicación deben estar activas
      (un valor desactivado ya no puede elegirse en tickets nuevos).
    - Los solicitantes son opcionales (0..N): deben ser usuarios activos con
      rol Solicitante. El creador no se convierte en solicitante por sí
      mismo; quien llama decide quiénes lo son.
    - `creado_por_usuario_id` queda fijado con el actor y no cambia nunca.

    Lanza `TicketRuleError` sin dejar nada pendiente en la sesión. No hace
    commit: el ticket y su historial se confirman juntos, quien llama
    confirma la transacción.

    Quién puede crear tickets a nombre de otras personas lo decide la capa de
    rutas; este servicio solo asocia a los solicitantes que recibe.
    """
    title, description = clean_title_and_description(title, description)

    if not actor.is_active:
        raise TicketRuleError("El usuario no está activo.")

    category = _get_active(Categoria, category_id, "La categoría")
    priority = _get_active(Prioridad, priority_id, "La prioridad")
    location = (
        None
        if location_id is None
        else _get_active(Ubicacion, location_id, "La ubicación")
    )
    requesters = _load_requesters(requester_ids)
    state = _initial_state()

    ticket = Ticket(
        titulo=title,
        descripcion=description,
        creado_por_usuario_id=actor.id,
        categoria_id=category.id,
        prioridad_id=priority.id,
        estado_id=state.id,
        ubicacion_id=None if location is None else location.id,
    )
    db.session.add(ticket)
    db.session.flush()

    for requester in requesters:
        db.session.add(
            TicketRequester(
                ticket_id=ticket.id,
                solicitante_id=requester.id,
                asociado_por_usuario_id=actor.id,
            )
        )

    record_ticket_event(
        ticket,
        TicketEvent.TICKET_CREADO,
        actor=actor,
        detail="Ticket creado.",
        new_state=state,
        new_value={
            "titulo": ticket.titulo,
            "categoria": category.nombre,
            "prioridad": priority.nombre,
            "ubicacion": None if location is None else location.nombre,
            "solicitantes": [
                {"id": r.id, "username": r.username} for r in requesters
            ],
        },
    )

    db.session.refresh(ticket)

    return ticket


def visible_tickets_condition(user):
    """Condición SQL con los tickets que `user` puede ver.

    Es el mismo criterio que `can_view_ticket`, expresado para la consulta del
    listado: así cada rol recibe solo lo autorizado desde la base de datos, sin
    cargar tickets ajenos para descartarlos después. Los tests comprueban que
    ambos coinciden.

    - Personal: todos.
    - Solicitante: los que creó y aquellos donde es solicitante vigente.
    - Cualquier otro caso (inactivo, anónimo): ninguno.
    """
    if has_any_role(user, *STAFF_ROLES):
        return true()

    if not has_any_role(user, RoleCode.SOLICITANTE):
        return false()

    is_current_requester = (
        db.select(TicketRequester.id)
        .where(
            TicketRequester.ticket_id == Ticket.id,
            TicketRequester.solicitante_id == user.id,
            TicketRequester.fecha_retiro.is_(None),
        )
        .exists()
    )

    return db.or_(Ticket.creado_por_usuario_id == user.id, is_current_requester)


def list_tickets(
    user,
    filters: TicketFilters | None = None,
    *,
    tab: str = DEFAULT_TAB,
    sort: str = DEFAULT_SORT,
    page: int = 1,
):
    """Devuelve una página de los tickets que `user` puede ver.

    Aplica la visibilidad, la búsqueda y los filtros en PostgreSQL y pagina
    ahí mismo. Estado y prioridad se cargan con el mismo JOIN del filtro y
    la categoría y los solicitantes con consultas por lote, así que mostrar
    una fila no genera consultas adicionales.
    """
    filters = filters or TicketFilters()

    statement = (
        db.select(Ticket)
        .join(Ticket.estado)
        .join(Ticket.prioridad)
        .options(
            contains_eager(Ticket.estado),
            contains_eager(Ticket.prioridad),
            joinedload(Ticket.categoria),
            selectinload(Ticket.solicitantes).joinedload(
                TicketRequester.solicitante
            ),
        )
        .where(*_listing_conditions(user, filters))
        .order_by(*_ORDERINGS.get(sort, _ORDERINGS[DEFAULT_SORT]))
    )

    if tab == TAB_OPEN:
        statement = statement.where(Estado.codigo != CLOSED_STATE_CODE)
    elif tab == TAB_CLOSED:
        statement = statement.where(Estado.codigo == CLOSED_STATE_CODE)

    return db.paginate(
        statement,
        page=page,
        per_page=PAGE_SIZE,
        max_per_page=PAGE_SIZE,
        error_out=False,
    )


def count_tickets_by_tab(
    user,
    filters: TicketFilters | None = None,
) -> dict[str, int]:
    """Cuántos tickets hay en cada pestaña, con la búsqueda y los filtros
    aplicados (la pestaña en sí no se aplica) y solo entre los visibles.
    """
    closed = Estado.codigo == CLOSED_STATE_CODE

    row = db.session.execute(
        db.select(
            func.count(Ticket.id),
            func.count(Ticket.id).filter(~closed),
            func.count(Ticket.id).filter(closed),
        )
        .select_from(Ticket)
        .join(Ticket.estado)
        .where(*_listing_conditions(user, filters or TicketFilters()))
    ).one()

    return {TAB_ALL: row[0], TAB_OPEN: row[1], TAB_CLOSED: row[2]}


def list_states() -> list[Estado]:
    """Los estados en su orden visual, para el filtro del listado."""
    return list(db.session.scalars(db.select(Estado).order_by(Estado.orden)))


def _listing_conditions(user, filters: TicketFilters) -> list:
    conditions = [visible_tickets_condition(user)]

    query_text = filters.query_text.strip()[:MAX_SEARCH_LENGTH]

    if query_text:
        conditions.append(_search_condition(user, query_text))

    if filters.state_id is not None:
        conditions.append(Ticket.estado_id == filters.state_id)

    if filters.priority_id is not None:
        conditions.append(Ticket.prioridad_id == filters.priority_id)

    if filters.category_id is not None:
        conditions.append(Ticket.categoria_id == filters.category_id)

    if filters.location_id is not None:
        conditions.append(Ticket.ubicacion_id == filters.location_id)

    # Las fechas son días de la zona horaria de la aplicación: "hasta" incluye
    # el día completo.
    if filters.created_from is not None:
        conditions.append(
            Ticket.fecha_creacion >= start_of_local_day(filters.created_from)
        )

    if filters.created_to is not None:
        conditions.append(
            Ticket.fecha_creacion
            < start_of_local_day(filters.created_to + timedelta(days=1))
        )

    return conditions


def _search_condition(user, query_text: str):
    """Número exacto, o texto en título y descripción (sin distinguir
    mayúsculas). El personal también busca por nombre del solicitante.
    """
    pattern = f"%{escape_like(query_text)}%"

    clauses = [
        Ticket.titulo.ilike(pattern, escape="\\"),
        Ticket.descripcion.ilike(pattern, escape="\\"),
    ]

    # "12" y "#12" localizan el ticket número 12.
    number = query_text.removeprefix("#").strip()

    if number.isascii() and number.isdecimal():
        clauses.append(Ticket.public_id == number)

    if has_any_role(user, *STAFF_ROLES):
        clauses.append(
            db.select(TicketRequester.id)
            .join(User, TicketRequester.solicitante_id == User.id)
            .where(
                TicketRequester.ticket_id == Ticket.id,
                TicketRequester.fecha_retiro.is_(None),
                db.or_(
                    User.nombre.ilike(pattern, escape="\\"),
                    User.apellido.ilike(pattern, escape="\\"),
                    (User.nombre + " " + User.apellido).ilike(
                        pattern,
                        escape="\\",
                    ),
                    User.username.ilike(pattern, escape="\\"),
                ),
            )
            .exists()
        )

    return db.or_(*clauses)


def get_ticket_by_public_id(public_id: str) -> Ticket | None:
    """Busca un ticket por su identificador público.

    Carga de una vez lo que muestra el detalle (estado, prioridad, categoría,
    ubicación, creador y solicitantes) para no hacer una consulta por cada uno.
    No comprueba permisos: quien llama debe aplicar `can_view_ticket`.
    """
    return db.session.scalar(
        db.select(Ticket)
        .where(Ticket.public_id == public_id)
        .options(
            joinedload(Ticket.estado),
            joinedload(Ticket.prioridad),
            joinedload(Ticket.categoria),
            joinedload(Ticket.ubicacion),
            joinedload(Ticket.creado_por),
            selectinload(Ticket.solicitantes).joinedload(
                TicketRequester.solicitante
            ),
        )
    )


def list_ticket_history(ticket: Ticket) -> list[TicketHistory]:
    """Eventos del ticket, del más antiguo al más reciente."""
    return list(
        db.session.scalars(
            db.select(TicketHistory)
            .where(TicketHistory.ticket_id == ticket.id)
            .options(joinedload(TicketHistory.actor))
            .order_by(TicketHistory.fecha_hora, TicketHistory.id)
        )
    )


def list_requester_candidates() -> list[User]:
    """Usuarios que pueden figurar como solicitantes: activos y con rol
    Solicitante, ordenados por apellido y nombre.
    """
    return list(
        db.session.scalars(
            db.select(User)
            .join(Role, User.rol_id == Role.id)
            .where(
                User.activo.is_(True),
                Role.codigo == RoleCode.SOLICITANTE,
            )
            .order_by(db.func.lower(User.apellido), db.func.lower(User.nombre))
        )
    )


def categories_for_selection() -> list[Categoria]:
    """Categorías activas para el desplegable del formulario.

    Van por orden y nombre, pero la categoría de respaldo `Sin clasificar`
    siempre queda al final: es la salida para quien no sabe cuál elegir, no
    la opción por defecto.
    """
    categories = list_categories("activo")

    return [
        category
        for category in categories
        if category.codigo != FALLBACK_CATEGORY_CODE
    ] + [
        category
        for category in categories
        if category.codigo == FALLBACK_CATEGORY_CODE
    ]


def record_ticket_event(
    ticket: Ticket,
    event: TicketEvent,
    *,
    actor: User | None,
    detail: str | None = None,
    old_state: Estado | None = None,
    new_state: Estado | None = None,
    old_value: dict | None = None,
    new_value: dict | None = None,
    context: dict | None = None,
) -> TicketHistory:
    """Añade un evento al historial del ticket en la sesión actual.

    No hace commit: el evento se confirma o se revierte junto con la
    operación que lo origina. `actor=None` identifica una acción del sistema.
    """
    entry = TicketHistory(
        ticket_id=ticket.id,
        actor_usuario_id=None if actor is None else actor.id,
        actor_tipo=(
            ActorType.SISTEMA if actor is None else ActorType.USUARIO
        ).value,
        tipo_evento=TicketEvent(event).value,
        estado_anterior_id=None if old_state is None else old_state.id,
        estado_nuevo_id=None if new_state is None else new_state.id,
        detalle=detail,
        valor_anterior=old_value,
        valor_nuevo=new_value,
        contexto=context,
    )

    db.session.add(entry)
    db.session.flush()

    return entry


def _get_active(model, record_id: int, label: str):
    record = db.session.get(model, record_id)

    if record is None or not record.activo:
        raise TicketRuleError(f"{label} seleccionada no está disponible.")

    return record


def _load_requesters(requester_ids: Iterable[int]) -> list[User]:
    # Sin duplicados y en el orden recibido.
    unique_ids = list(dict.fromkeys(requester_ids))

    if not unique_ids:
        return []

    users = db.session.scalars(
        db.select(User)
        .join(Role, User.rol_id == Role.id)
        .where(
            User.id.in_(unique_ids),
            User.activo.is_(True),
            Role.codigo == RoleCode.SOLICITANTE,
        )
    ).all()

    if len(users) != len(unique_ids):
        raise TicketRuleError(
            "Alguno de los solicitantes no existe, no está activo o no "
            "tiene el rol Solicitante."
        )

    by_id = {user.id: user for user in users}

    return [by_id[user_id] for user_id in unique_ids]


def _initial_state() -> Estado:
    state = db.session.scalar(
        db.select(Estado).where(Estado.codigo == INITIAL_STATE_CODE)
    )

    if state is None:
        raise TicketRuleError(
            "No existe el estado inicial. Ejecuta el comando seed-catalogs."
        )

    return state
