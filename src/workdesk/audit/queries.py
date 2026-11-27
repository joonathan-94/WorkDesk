"""Las consultas de la pantalla de auditoría (RF-108, RF-109 y UI-027).

Tres registros de solo añadir, cada uno en su pestaña:

- **Administrativa** (`auditoria_administrativa`): las decisiones de quien administra.
- **Accesos** (`eventos_autenticacion`): cada intento de entrar y cada salida.
- **Tickets** (`historial_ticket`): lo que pasó en cada ticket, incluidas las notas y los
  eventos internos (el Administrador ve todo).

Quién puede consultarlas lo decide la ruta (`can_view_audit`, solo el Administrador). Aquí
se arma cada consulta con sus filtros y se pagina en PostgreSQL. Las personas y los tickets
que aparecen en una página se cargan en lote (`page_context`): la página cuesta lo mismo con
una fila que con cincuenta.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

from sqlalchemy import func, or_, select

from ..extensions import db
from ..formatting import start_of_local_day
from ..models import AdminAuditLog, AuthEvent, Ticket, TicketHistory, User
from ..search import escape_like

PAGE_SIZE = 50
MAX_PERSON_LENGTH = 100


class AuditView(StrEnum):
    ADMINISTRATIVA = "administrativa"
    ACCESOS = "accesos"
    TICKETS = "tickets"


VIEW_LABELS = {
    AuditView.ADMINISTRATIVA: "Administrativa",
    AuditView.ACCESOS: "Accesos",
    AuditView.TICKETS: "Tickets",
}


@dataclass(frozen=True)
class AuditFilters:
    """Los filtros de la URL ya validados. Cada pestaña usa los suyos."""

    since: date | None = None
    until: date | None = None
    # Nombre, apellido o usuario de quien actuó (o de lo escrito, en Accesos).
    person: str = ""
    # Acción administrativa o tipo de evento, según la pestaña.
    kind: str | None = None
    entity_type: str | None = None
    entity_id: int | None = None
    result: str | None = None
    ip: str | None = None
    ticket: str | None = None


def audit_statement(view: AuditView, filters: AuditFilters):
    """La consulta de la pestaña `view` con `filters`, de lo más reciente a lo más antiguo
    y sin paginar: la comparten la pantalla y la exportación."""
    model = _MODEL[view]

    return select(model).where(*_conditions(view, filters)).order_by(
        model.fecha_hora.desc(), model.id.desc()
    )


def count_audit_rows(view: AuditView, filters: AuditFilters) -> int:
    model = _MODEL[view]

    return db.session.scalar(
        select(func.count(model.id)).where(*_conditions(view, filters))
    )


def audit_page(view: AuditView, filters: AuditFilters, page: int = 1):
    """Una página de la pestaña `view` con `filters`, de lo más reciente a lo más antiguo."""
    return db.paginate(
        audit_statement(view, filters),
        page=page,
        per_page=PAGE_SIZE,
        max_per_page=PAGE_SIZE,
        error_out=False,
    )


@dataclass(frozen=True)
class PageContext:
    """Lo que una página necesita para mostrarse, cargado en lote."""

    users: dict[int, User]
    tickets: dict[int, str]


def page_context(view: AuditView, rows) -> PageContext:
    """Las personas (quién actuó y, en la auditoría, el usuario afectado) y los números de
    ticket de las filas, en a lo sumo dos consultas."""
    user_ids: set[int] = set()
    ticket_ids: set[int] = set()

    for row in rows:
        if view is AuditView.ACCESOS:
            user_ids.add(row.usuario_id)
            continue

        user_ids.add(row.actor_usuario_id)

        if view is AuditView.TICKETS:
            ticket_ids.add(row.ticket_id)
        elif row.entidad_tipo == "usuario":
            user_ids.add(row.entidad_id)
        elif row.entidad_tipo == "ticket":
            ticket_ids.add(row.entidad_id)

    user_ids.discard(None)
    ticket_ids.discard(None)

    users = (
        {u.id: u for u in db.session.scalars(select(User).where(User.id.in_(user_ids)))}
        if user_ids
        else {}
    )
    tickets = (
        dict(db.session.execute(select(Ticket.id, Ticket.public_id).where(Ticket.id.in_(ticket_ids))).all())
        if ticket_ids
        else {}
    )

    return PageContext(users=users, tickets=tickets)


def entity_types() -> list[str]:
    """Los tipos de entidad que aparecen en la auditoría (para el filtro)."""
    return list(
        db.session.scalars(
            select(AdminAuditLog.entidad_tipo)
            .where(AdminAuditLog.entidad_tipo.is_not(None))
            .distinct()
            .order_by(AdminAuditLog.entidad_tipo)
        )
    )


# --- Condiciones ------------------------------------------------------------------------

_MODEL = {
    AuditView.ADMINISTRATIVA: AdminAuditLog,
    AuditView.ACCESOS: AuthEvent,
    AuditView.TICKETS: TicketHistory,
}


def _conditions(view: AuditView, filters: AuditFilters) -> list:
    model = _MODEL[view]
    conditions = _date_conditions(model, filters)

    if view is AuditView.ADMINISTRATIVA:
        conditions += _administrative_conditions(filters)
    elif view is AuditView.ACCESOS:
        conditions += _access_conditions(filters)
    else:
        conditions += _ticket_conditions(filters)

    return conditions


def _date_conditions(model, filters: AuditFilters) -> list:
    """Días locales (`APP_TIMEZONE`): «hasta» incluye el día entero."""
    conditions = []

    if filters.since is not None:
        conditions.append(model.fecha_hora >= start_of_local_day(filters.since))

    if filters.until is not None:
        conditions.append(
            model.fecha_hora < start_of_local_day(filters.until + timedelta(days=1))
        )

    return conditions


def _person_condition(user_column, text: str):
    """Que `user_column` sea alguien cuyo nombre, apellido, nombre completo o usuario
    contenga `text` (sin distinguir mayúsculas; los comodines se buscan literalmente)."""
    pattern = f"%{escape_like(text)}%"
    full_name = User.nombre + " " + User.apellido
    matching = select(User.id).where(
        or_(
            User.username.ilike(pattern, escape="\\"),
            User.nombre.ilike(pattern, escape="\\"),
            User.apellido.ilike(pattern, escape="\\"),
            full_name.ilike(pattern, escape="\\"),
        )
    )

    return user_column.in_(matching)


def _administrative_conditions(filters: AuditFilters) -> list:
    conditions = []

    if filters.person:
        conditions.append(_person_condition(AdminAuditLog.actor_usuario_id, filters.person))

    if filters.kind:
        conditions.append(AdminAuditLog.accion == filters.kind)

    if filters.entity_type:
        conditions.append(AdminAuditLog.entidad_tipo == filters.entity_type)

    if filters.entity_id is not None:
        conditions.append(AdminAuditLog.entidad_id == filters.entity_id)

    if filters.result:
        conditions.append(AdminAuditLog.resultado == filters.result)

    return conditions


def _access_conditions(filters: AuditFilters) -> list:
    conditions = []

    if filters.person:
        # La cuenta, o lo que se escribió cuando no correspondía a ninguna.
        pattern = f"%{escape_like(filters.person)}%"
        conditions.append(
            or_(
                _person_condition(AuthEvent.usuario_id, filters.person),
                AuthEvent.identificador_intentado.ilike(pattern, escape="\\"),
            )
        )

    if filters.kind:
        conditions.append(AuthEvent.tipo_evento == filters.kind)

    if filters.result:
        conditions.append(AuthEvent.resultado == filters.result)

    if filters.ip:
        conditions.append(AuthEvent.ip_origen == filters.ip)

    return conditions


def _ticket_conditions(filters: AuditFilters) -> list:
    conditions = []

    if filters.person:
        conditions.append(_person_condition(TicketHistory.actor_usuario_id, filters.person))

    if filters.kind:
        conditions.append(TicketHistory.tipo_evento == filters.kind)

    if filters.ticket:
        conditions.append(
            TicketHistory.ticket_id.in_(
                select(Ticket.id).where(Ticket.public_id == filters.ticket)
            )
        )

    return conditions
