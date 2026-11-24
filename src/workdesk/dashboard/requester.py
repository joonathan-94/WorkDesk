"""El dashboard del Solicitante (docs/11, UI-002; docs/04, RF-097).

Reúne lo que necesita una persona que pide soporte: cuántas solicitudes tiene abiertas, en
qué van, cuáles esperan su revisión, qué se cerró hace poco, sus tickets recientes y sus
notificaciones. **No** incluye SLA, grupos, carga de técnicos ni métricas globales (RN-169 y
UI-002): quien lo consulta solo ve lo suyo.

Todo sale de la base de datos con la visibilidad del Solicitante (`visible_tickets_condition`,
la misma del listado) y cada contador enlaza con el listado que lo explica: la cifra y el total
de ese listado deben coincidir (un test lo comprueba con los tickets de demostración).
"""

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import func

from ..extensions import db
from ..formatting import app_zone, start_of_local_day
from ..models import Estado, Notificacion, Ticket
from ..models.estado import IN_PROGRESS_STATE_CODE
from ..notifications.service import list_notifications
from ..security import RESOLVED_STATE
from ..sla import periods as sla_periods
from ..tickets.queries import (
    SORT_UPDATED,
    TAB_ALL,
    list_tickets,
    pending_review_condition,
    visible_tickets_condition,
)
from ..tickets.service import CLOSED_STATE_CODE

# «Cerrados recientemente»: los de los últimos 7 días (más el día de hoy).
CLOSED_WINDOW_DAYS = 7
RECENT_TICKETS = 5
RECENT_NOTIFICATIONS = 5


@dataclass(frozen=True)
class RequesterDashboard:
    open: int
    in_progress: int
    pending_review: int
    recently_closed: int
    updated_today: int
    # Desde cuándo cuentan los cerrados recientes: el enlace usa el mismo día.
    closed_since: date
    # El ticket resuelto que espera su revisión desde hace menos tiempo.
    pending_ticket: Ticket | None
    # Los de la lista de recientes que esperan su revisión (para marcarlos).
    pending_ids: frozenset[int]
    # Para enlazar «En progreso» con el listado filtrado por ese estado.
    in_progress_state_id: int | None
    recent_tickets: list[Ticket]
    notifications: list[Notificacion]


def local_today(now=None) -> date:
    """El día de hoy en la zona horaria de la aplicación."""
    return (now or sla_periods.current_time()).astimezone(app_zone()).date()


def requester_dashboard(user, now=None) -> RequesterDashboard:
    today = local_today(now)
    closed_since = today - timedelta(days=CLOSED_WINDOW_DAYS)
    is_open = Estado.codigo != CLOSED_STATE_CODE

    # Cinco contadores en una sola consulta (`COUNT ... FILTER`), sobre los tickets visibles.
    counts = db.session.execute(
        db.select(
            func.count(Ticket.id).filter(is_open),
            func.count(Ticket.id).filter(Estado.codigo == IN_PROGRESS_STATE_CODE),
            func.count(Ticket.id).filter(pending_review_condition(user)),
            func.count(Ticket.id).filter(
                Estado.codigo == CLOSED_STATE_CODE,
                Ticket.fecha_cierre >= start_of_local_day(closed_since),
            ),
            func.count(Ticket.id).filter(
                is_open,
                func.coalesce(Ticket.fecha_modificacion, Ticket.fecha_creacion)
                >= start_of_local_day(today),
            ),
        )
        .select_from(Ticket)
        .join(Ticket.estado)
        .where(visible_tickets_condition(user))
    ).one()

    pending_ticket = db.session.scalar(
        db.select(Ticket)
        .join(Ticket.estado)
        .where(visible_tickets_condition(user), pending_review_condition(user))
        .order_by(Ticket.fecha_resolucion.desc(), Ticket.id.desc())
        .limit(1)
    )

    recent = list_tickets(
        user,
        tab=TAB_ALL,
        sort=SORT_UPDATED,
        per_page=RECENT_TICKETS,
        load_technicians=True,
    )

    in_progress_state_id = db.session.scalar(
        db.select(Estado.id).where(Estado.codigo == IN_PROGRESS_STATE_CODE)
    )
    pending_ids = frozenset(
        ticket.id
        for ticket in recent.items
        if ticket.estado.codigo == RESOLVED_STATE
        and any(link.solicitante_id == user.id for link in ticket.solicitantes_vigentes)
    )

    return RequesterDashboard(
        open=counts[0],
        in_progress=counts[1],
        pending_review=counts[2],
        recently_closed=counts[3],
        updated_today=counts[4],
        closed_since=closed_since,
        pending_ticket=pending_ticket,
        pending_ids=pending_ids,
        in_progress_state_id=in_progress_state_id,
        recent_tickets=list(recent.items),
        notifications=list(
            list_notifications(user, per_page=RECENT_NOTIFICATIONS).items
        ),
    )
