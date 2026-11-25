"""El dashboard operacional del personal (docs/11, UI-002; docs/04, RF-093 a RF-096).

Lo ven Técnico, Supervisor y Administrador. Reúne lo que necesita quien atiende: cuántos
tickets hay abiertos, sin asignar, críticos, fuera de SLA, próximos a vencer y en espera; los
tickets abiertos más prioritarios; una carga de trabajo compacta; y la actividad reciente. El
Técnico suma «Mi trabajo» y el Administrador un bloque de administración.

**Cada contador coincide con el total del listado al que enlaza** (igual que en la carga de
trabajo, de la que toma sus definiciones y sus cifras: `workload_overview`). Un único instante
(`now`) decide todo el SLA de la pantalla.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from sqlalchemy import func

from ..extensions import db
from ..formatting import start_of_local_day
from ..models import (
    Estado,
    PoliticaSla,
    Prioridad,
    Role,
    Ticket,
    TicketHistory,
    User,
)
from ..models.estado import ON_HOLD_STATE_CODE
from ..models.ticket_history import TicketEvent
from ..security import RoleCode, can_view_workload
from ..sla import periods as sla_periods
from ..sla.evaluation import SlaSnapshot, evaluate_tickets_sla
from ..sla.work_calendar import resolve_work_calendar
from ..tickets.queries import (
    SORT_PRIORITY_SLA,
    TAB_OPEN,
    TicketFilters,
    active_state_condition,
    list_tickets,
    visible_tickets_condition,
)
from ..tickets.service import CLOSED_STATE_CODE, visible_history_condition
from ..workload import TechnicianLoad, WorkloadOverview, workload_overview
from .requester import local_today

PRIORITY_TICKETS = 8
COMPACT_TECHNICIANS = 5
RECENT_ACTIVITY = 10
# «Resueltos» de Mi trabajo: los de los últimos 7 días (día local de hoy incluido).
RESOLVED_WINDOW_DAYS = 7


@dataclass(frozen=True)
class ActivityItem:
    """Un evento reciente: qué pasó, quién lo hizo y en qué ticket (sin su contenido)."""

    entry: TicketHistory
    ticket_number: str
    ticket_title: str


@dataclass(frozen=True)
class MyWork:
    """Lo del Técnico que consulta (`row` es su fila de la carga de trabajo)."""

    row: TechnicianLoad | None
    resolved_recently: int
    resolved_since: date


@dataclass(frozen=True)
class AdminBlock:
    users_by_role: list[tuple[str, int]]
    calendar_configured: bool
    calendar_version: int | None
    policies_defined: int
    priorities_total: int


@dataclass(frozen=True)
class StaffDashboard:
    open: int
    overview: WorkloadOverview
    in_progress_state_id: int | None
    on_hold_state_id: int | None
    critical_priority_id: int | None
    # Tickets activos por prioridad, de mayor a menor nivel: (prioridad, cuántos).
    by_priority: list[tuple[Prioridad, int]]
    priority_tickets: list[Ticket]
    slas: dict[int, SlaSnapshot | None]
    top_technicians: list[TechnicianLoad]
    activity: list[ActivityItem]
    my_work: MyWork | None = None
    admin: AdminBlock | None = None
    now: datetime = field(default=None)  # type: ignore[assignment]


def staff_dashboard(user, now: datetime | None = None) -> StaffDashboard:
    """El dashboard del personal. `PermissionError` si `user` no es del personal."""
    if not can_view_workload(user):
        raise PermissionError("El dashboard operacional es solo del personal.")

    now = now or sla_periods.current_time()
    overview = workload_overview(user, now=now)

    open_count = db.session.scalar(
        db.select(func.count(Ticket.id))
        .join(Ticket.estado)
        .where(visible_tickets_condition(user), Estado.codigo != CLOSED_STATE_CODE)
    )

    page = list_tickets(
        user,
        TicketFilters(active_only=True),
        tab=TAB_OPEN,
        sort=SORT_PRIORITY_SLA,
        per_page=PRIORITY_TICKETS,
        now=now,
    )
    slas = evaluate_tickets_sla([ticket.id for ticket in page.items], now)

    state_ids = dict(db.session.execute(db.select(Estado.codigo, Estado.id)).all())
    critical_id = next(
        (p.id for p in overview.priorities if p.codigo == "CRITICA"), None
    )

    return StaffDashboard(
        open=open_count,
        overview=overview,
        in_progress_state_id=state_ids.get("EN_PROGRESO"),
        on_hold_state_id=state_ids.get(ON_HOLD_STATE_CODE),
        critical_priority_id=critical_id,
        by_priority=_by_priority(user, overview.priorities),
        priority_tickets=list(page.items),
        slas=slas,
        top_technicians=sorted(
            (row for row in overview.technicians if row.active),
            key=lambda row: (-row.active, row.user.apellido.casefold()),
        )[:COMPACT_TECHNICIANS],
        activity=recent_activity(user),
        my_work=_my_work(user, overview, now) if _is_technician(user) else None,
        admin=_admin_block() if _is_administrator(user) else None,
        now=now,
    )


def recent_activity(user, limit: int = RECENT_ACTIVITY) -> list[ActivityItem]:
    """Los últimos eventos de los tickets que `user` puede ver, con la misma regla de
    visibilidad del historial (`visible_history_condition`). Solo trae quién, qué y en qué
    ticket: nunca copia el contenido de un comentario ni de una nota."""
    rows = db.session.execute(
        db.select(TicketHistory, Ticket.public_id, Ticket.titulo)
        .join(Ticket, Ticket.id == TicketHistory.ticket_id)
        .where(visible_tickets_condition(user), visible_history_condition(user))
        .options(db.joinedload(TicketHistory.actor))
        .order_by(TicketHistory.fecha_hora.desc(), TicketHistory.id.desc())
        .limit(limit)
    ).all()

    return [ActivityItem(entry, number, title) for entry, number, title in rows]


def _by_priority(user, priorities: list[Prioridad]) -> list[tuple[Prioridad, int]]:
    """Los tickets en trabajo de cada prioridad (RF-095), de mayor a menor nivel. Una
    prioridad desactivada solo aparece si aún tiene tickets."""
    counts = dict(
        db.session.execute(
            db.select(Ticket.prioridad_id, func.count(Ticket.id))
            .join(Ticket.estado)
            .where(visible_tickets_condition(user), active_state_condition())
            .group_by(Ticket.prioridad_id)
        ).all()
    )

    return [
        (priority, counts.get(priority.id, 0))
        for priority in sorted(priorities, key=lambda p: -p.nivel)
        if priority.activo or counts.get(priority.id)
    ]


def _is_technician(user) -> bool:
    return user.rol.codigo == RoleCode.TECNICO


def _is_administrator(user) -> bool:
    return user.rol.codigo == RoleCode.ADMINISTRADOR


def _my_work(user, overview: WorkloadOverview, now: datetime) -> MyWork:
    since = local_today(now) - timedelta(days=RESOLVED_WINDOW_DAYS)
    row = next((r for r in overview.technicians if r.user.id == user.id), None)

    resolved = db.session.scalar(
        db.select(func.count(TicketHistory.id)).where(
            TicketHistory.actor_usuario_id == user.id,
            TicketHistory.tipo_evento == TicketEvent.TICKET_RESUELTO.value,
            TicketHistory.fecha_hora >= start_of_local_day(since),
        )
    )

    return MyWork(row=row, resolved_recently=resolved, resolved_since=since)


def _admin_block() -> AdminBlock:
    by_role = db.session.execute(
        db.select(Role.nombre, func.count(User.id))
        .join(User, User.rol_id == Role.id)
        .where(User.activo.is_(True))
        .group_by(Role.id)
        .order_by(Role.id)
    ).all()
    calendar = resolve_work_calendar()
    policies = db.session.scalar(
        db.select(func.count(PoliticaSla.id)).where(PoliticaSla.activo.is_(True))
    )
    priorities = db.session.scalar(db.select(func.count(Prioridad.id)))

    return AdminBlock(
        users_by_role=[(name, total) for name, total in by_role],
        calendar_configured=calendar.record is not None,
        calendar_version=calendar.record.version if calendar.record else None,
        policies_defined=policies,
        priorities_total=priorities,
    )
