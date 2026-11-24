"""Consultas de tickets: quién ve qué y el listado con búsqueda, filtros y orden.

Reglas en `docs/06` (RN-154). Es la pieza que comparten el listado, los dashboards, la
carga de trabajo y la reasignación: cada pantalla recibe solo lo que su rol puede ver,
porque la visibilidad se aplica en la propia consulta y no en la plantilla.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import false, func, true
from sqlalchemy.orm import contains_eager, joinedload, selectinload

from ..extensions import db
from ..formatting import start_of_local_day
from ..models import (
    Estado,
    Grupo,
    Prioridad,
    Role,
    Ticket,
    TicketRequester,
    TicketTechnician,
    User,
)
from ..search import escape_like
from ..security import RESOLVED_STATE, STAFF_ROLES, RoleCode, has_any_role
from ..sla import periods as sla_periods
from ..sla.periods import STOPPING_STATES
from ..sla.queries import SlaFilter, sla_condition, sla_urgency_order
from .service import CLOSED_STATE_CODE

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
# Solo el personal ve y usa el SLA (docs/06, RN-169).
SORT_SLA = "sla"
DEFAULT_SORT = SORT_RECENT

# Nombre visible de cada orden, en el orden en que se ofrecen.
SORT_LABELS = {
    SORT_RECENT: "Más recientes",
    SORT_OLDEST: "Más antiguos",
    SORT_PRIORITY: "Mayor prioridad primero",
    SORT_UPDATED: "Recién actualizados",
}

SORT_SLA_LABEL = "SLA más urgente"

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
    # Solo el personal puede filtrar por SLA: para un Solicitante se ignora.
    sla: SlaFilter | None = None
    # Los tres siguientes son solo del personal (el grupo es un dato interno: un
    # Solicitante que probara el filtro podría deducirlo): para un Solicitante se
    # ignoran. `unassigned` y `technician_id` no se combinan con sentido.
    technician_id: int | None = None
    unassigned: bool = False
    group_id: int | None = None
    # «En trabajo»: ni resuelto ni cerrado (la carga de trabajo, docs/12 fase 6).
    active_only: bool = False
    # Los resueltos que están esperando la validación de quien consulta (solo para un
    # Solicitante: el creador que no figura como solicitante no puede validar).
    pending_review: bool = False
    # Cerrados desde ese día (día local, incluido).
    closed_from: date | None = None


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
    now=None,
):
    """Devuelve una página de los tickets que `user` puede ver.

    Aplica la visibilidad, la búsqueda y los filtros en PostgreSQL y pagina
    ahí mismo. Estado y prioridad se cargan con el mismo JOIN del filtro y
    la categoría y los solicitantes con consultas por lote, así que mostrar
    una fila no genera consultas adicionales.

    El filtro y el orden por SLA son solo para el personal (para un Solicitante se
    ignoran) y usan `now` (por defecto, ahora) para decidir quién está vencido o
    próximo a vencer: la pantalla pasa el mismo que usa para mostrar las insignias.
    """
    filters = filters or TicketFilters()
    staff = has_any_role(user, *STAFF_ROLES)

    if sort == SORT_SLA and not staff:
        sort = DEFAULT_SORT

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
        .where(*listing_conditions(user, filters, now))
        .order_by(
            *(
                sla_urgency_order()
                if sort == SORT_SLA
                else _ORDERINGS.get(sort, _ORDERINGS[DEFAULT_SORT])
            )
        )
    )

    if staff:
        # Las columnas Técnico(s) y Grupo: una consulta por lote, no una por fila.
        statement = statement.options(
            joinedload(Ticket.grupo),
            selectinload(Ticket.tecnicos).joinedload(TicketTechnician.tecnico),
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
    now=None,
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
        .where(*listing_conditions(user, filters or TicketFilters(), now))
    ).one()

    return {TAB_ALL: row[0], TAB_OPEN: row[1], TAB_CLOSED: row[2]}


def list_technician_options() -> list[User]:
    """Todos los técnicos, también los desactivados (conservan tickets asignados), por
    apellido y nombre: las opciones del filtro «Técnico»."""
    return list(
        db.session.scalars(
            db.select(User)
            .join(Role, User.rol_id == Role.id)
            .where(Role.codigo == RoleCode.TECNICO)
            .order_by(func.lower(User.apellido), func.lower(User.nombre))
        )
    )


def list_group_options() -> list[Grupo]:
    """Todos los grupos, también los desactivados, por nombre: las opciones del filtro."""
    return list(db.session.scalars(db.select(Grupo).order_by(func.lower(Grupo.nombre))))


def list_states() -> list[Estado]:
    """Los estados en su orden visual, para el filtro del listado."""
    return list(db.session.scalars(db.select(Estado).order_by(Estado.orden)))


def listing_conditions(user, filters: TicketFilters, now=None) -> list:
    conditions = [visible_tickets_condition(user)]

    query_text = filters.query_text.strip()[:MAX_SEARCH_LENGTH]

    if query_text:
        conditions.append(_search_condition(user, query_text))

    if filters.sla is not None and has_any_role(user, *STAFF_ROLES):
        conditions.append(sla_condition(filters.sla, now or sla_periods.current_time()))

    conditions += _assignment_conditions(user, filters)

    if filters.active_only:
        conditions.append(active_state_condition())

    if filters.pending_review and has_any_role(user, RoleCode.SOLICITANTE):
        conditions.append(pending_review_condition(user))

    if filters.closed_from is not None:
        conditions.append(
            Ticket.fecha_cierre >= start_of_local_day(filters.closed_from)
        )

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


def _assignment_conditions(user, filters: TicketFilters) -> list:
    """Técnico, «sin asignar» y grupo: solo para el personal."""
    if not has_any_role(user, *STAFF_ROLES):
        return []

    conditions = []

    if filters.technician_id is not None:
        conditions.append(has_current_technician(filters.technician_id))

    if filters.unassigned:
        conditions.append(~has_current_technician())

    if filters.group_id is not None:
        conditions.append(Ticket.grupo_id == filters.group_id)

    return conditions


def has_current_technician(technician_id: int | None = None):
    """«El ticket tiene un técnico asignado ahora» (o ese técnico en concreto).

    Usa las asignaciones vigentes (sin `fecha_desasignacion`), que es lo que cuenta la
    carga de trabajo y lo que enlazan los dashboards."""
    conditions = [
        TicketTechnician.ticket_id == Ticket.id,
        TicketTechnician.fecha_desasignacion.is_(None),
    ]

    if technician_id is not None:
        conditions.append(TicketTechnician.tecnico_id == technician_id)

    return db.select(TicketTechnician.id).where(*conditions).exists()


def active_state_condition():
    """Estado en trabajo: ni `Resuelto` ni `Cerrado`. Necesita `Estado` en el JOIN."""
    return Estado.codigo.not_in(sorted(STOPPING_STATES))


def pending_review_condition(user):
    """Resuelto y con `user` como solicitante vigente (quien puede validarlo)."""
    return db.and_(
        Estado.codigo == RESOLVED_STATE,
        db.select(TicketRequester.id)
        .where(
            TicketRequester.ticket_id == Ticket.id,
            TicketRequester.solicitante_id == user.id,
            TicketRequester.fecha_retiro.is_(None),
        )
        .exists(),
    )


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
