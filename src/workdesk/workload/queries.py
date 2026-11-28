"""La carga de trabajo del equipo (docs/12, fase 6; docs/06, RN-24 a RN-30 y RN-87).

Responde cuántos tickets activos tiene cada técnico y cada grupo, cuántos hay sin
asignar y cómo está el SLA de todo eso. Es información de **todo el equipo**, así que es
solo del personal (`can_view_workload`).

Definiciones (una sola vez, aquí):

- **Activo:** ni `Resuelto` ni `Cerrado` (`active_state_condition`). Un resuelto espera la
  validación del solicitante y ya no es trabajo del técnico.
- **Asignado a un técnico:** tiene una asignación vigente (sin `fecha_desasignacion`).
- **Sin asignar:** activo y sin ningún técnico vigente.
- **Crítico:** su prioridad es la de código `CRITICA`.
- **SLA en riesgo:** próximo a vencer o vencido (`SlaFilter.RIESGO`); aquí se cuentan por
  separado y la suma de ambos es el «en riesgo».
- **Sin actividad reciente:** en trabajo y sin ninguna acción del personal en los últimos
  `INACTIVE_TICKET_DAYS` días (`inactive_condition`, RN-27); 0 lo desactiva.

**Cada cifra coincide con el total del listado al que enlaza** (los filtros `tecnico`,
`grupo`, `activos`, `sla`, `sin_actividad`, `prioridad` y `estado` del listado): un test lo comprueba para
cada técnico y cada grupo. Un ticket con varios técnicos cuenta en cada uno de ellos y una
sola vez en los totales, así que la suma por técnico puede superar al total.

Todo se calcula en PostgreSQL con un número fijo de consultas, sin una por técnico.
"""

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import false, func

from .. import settings
from ..configuration import value_of
from ..extensions import db
from ..models import (
    Estado,
    Grupo,
    Prioridad,
    Role,
    Ticket,
    TicketTechnician,
    User,
)
from ..models.estado import IN_PROGRESS_STATE_CODE, ON_HOLD_STATE_CODE
from ..models.prioridad import CRITICAL_PRIORITY_CODE
from ..security import RESOLVED_STATE, RoleCode, can_view_workload
from ..sla import periods as sla_periods
from ..sla.queries import SlaFilter, sla_condition
from ..tickets.queries import (
    active_state_condition,
    has_current_technician,
    inactive_condition,
)
from ..tickets.service import CLOSED_STATE_CODE


@dataclass(frozen=True)
class WorkloadFilters:
    """Restringen los tickets que se cuentan (todos opcionales y combinables)."""

    group_id: int | None = None
    priority_id: int | None = None
    state_id: int | None = None


@dataclass(frozen=True)
class TechnicianLoad:
    """La carga de un técnico. `by_priority` va de id de prioridad a tickets activos."""

    user: User
    active: int
    in_progress: int
    on_hold: int
    critical: int
    near_due: int
    overdue: int
    resolved: int
    by_priority: dict[int, int] = field(default_factory=dict)
    high: bool = False
    inactive: int = 0

    @property
    def at_risk(self) -> int:
        return self.near_due + self.overdue


@dataclass(frozen=True)
class GroupLoad:
    """La carga de un grupo; `group` es None para los tickets sin grupo."""

    group: Grupo | None
    active: int
    unassigned: int
    critical: int
    near_due: int
    overdue: int
    inactive: int = 0

    @property
    def at_risk(self) -> int:
        return self.near_due + self.overdue


@dataclass(frozen=True)
class WorkloadSummary:
    """Los totales, con tickets únicos (no la suma por técnico)."""

    active: int
    unassigned: int
    critical: int
    near_due: int
    overdue: int
    in_progress: int
    on_hold: int
    unassigned_critical: int
    # Técnicos con trabajo activo y cuántos de ellos están en «carga alta».
    technicians_with_work: int
    high_load_technicians: int
    inactive: int = 0

    @property
    def assigned(self) -> int:
        return self.active - self.unassigned

    @property
    def at_risk(self) -> int:
        return self.near_due + self.overdue


@dataclass(frozen=True)
class WorkloadOverview:
    summary: WorkloadSummary
    technicians: list[TechnicianLoad]
    groups: list[GroupLoad]
    priorities: list[Prioridad]
    # El umbral con el que se marcó la carga alta (0 = la marca está desactivada).
    high_threshold: int
    # Los días de «sin actividad reciente» (0 = la marca está desactivada).
    inactive_days: int = 0


def is_high_load(active: int, threshold: int) -> bool:
    """Carga alta: `threshold` tickets activos o más (0 desactiva la marca). Solo informa:
    nunca bloquea una asignación (RN-26)."""
    return threshold > 0 and active >= threshold


def workload_overview(
    user, filters: WorkloadFilters | None = None, now: datetime | None = None
) -> WorkloadOverview:
    """La carga de trabajo del equipo. Solo la ve el personal (`PermissionError` si no)."""
    if not can_view_workload(user):
        raise PermissionError("Solo el personal puede ver la carga de trabajo.")

    filters = filters or WorkloadFilters()
    now = now or sla_periods.current_time()
    threshold = value_of(settings.WORKLOAD_HIGH_ACTIVE_TICKETS)

    technicians = _technician_loads(filters, now, threshold)
    by_group = _group_rows(filters, now)
    groups = _group_loads(by_group)
    summary = _summary(by_group, technicians)

    priorities = list(db.session.scalars(db.select(Prioridad).order_by(Prioridad.nivel)))

    return WorkloadOverview(
        summary,
        technicians,
        groups,
        priorities,
        threshold,
        value_of(settings.INACTIVE_TICKET_DAYS),
    )


# --- Piezas -----------------------------------------------------------------------


def _ticket_filters(filters: WorkloadFilters) -> list:
    conditions = []

    if filters.group_id is not None:
        conditions.append(Ticket.grupo_id == filters.group_id)

    if filters.priority_id is not None:
        conditions.append(Ticket.prioridad_id == filters.priority_id)

    if filters.state_id is not None:
        conditions.append(Ticket.estado_id == filters.state_id)

    return conditions


def _counts(now: datetime) -> dict:
    """Los contadores comunes, como expresiones `COUNT ... FILTER`. Necesitan `Ticket`,
    `Estado` y `Prioridad` en el `FROM` (con `JOIN` externo, un ticket ausente no cuenta)."""
    active = active_state_condition()
    # Con el SLA apagado ninguna cifra de SLA cuenta nada (y la pantalla no las muestra).
    enabled = sla_periods.sla_enabled()
    near_due = sla_condition(SlaFilter.PROXIMO, now) if enabled else false()
    overdue = sla_condition(SlaFilter.VENCIDO, now) if enabled else false()

    return {
        "active": func.count(Ticket.id).filter(active),
        "in_progress": func.count(Ticket.id).filter(Estado.codigo == IN_PROGRESS_STATE_CODE),
        "on_hold": func.count(Ticket.id).filter(Estado.codigo == ON_HOLD_STATE_CODE),
        "critical": func.count(Ticket.id).filter(
            active, Prioridad.codigo == CRITICAL_PRIORITY_CODE
        ),
        "near_due": func.count(Ticket.id).filter(active, near_due),
        "overdue": func.count(Ticket.id).filter(active, overdue),
        # Ya incluye «en trabajo». Va al final: es una subconsulta por ticket.
        "inactive": func.count(Ticket.id).filter(inactive_condition(now)),
    }


def _technician_loads(filters, now, threshold) -> list[TechnicianLoad]:
    counts = _counts(now)
    not_closed = Ticket.estado_id.in_(
        db.select(Estado.id).where(Estado.codigo != CLOSED_STATE_CODE)
    )

    # Cada técnico, con sus asignaciones vigentes y los tickets sin cerrar de ellas (los
    # `JOIN` externos mantienen al que no tiene ninguno: carga cero). Aparecen los
    # técnicos activos y, aunque estén desactivados, los que aún conservan trabajo
    # activo: son los candidatos naturales a una reasignación.
    rows = db.session.execute(
        db.select(
            User,
            *(expression.label(name) for name, expression in counts.items()),
            func.count(Ticket.id).filter(Estado.codigo == RESOLVED_STATE).label("resolved"),
        )
        .select_from(User)
        .join(Role, User.rol_id == Role.id)
        .outerjoin(
            TicketTechnician,
            db.and_(
                TicketTechnician.tecnico_id == User.id,
                TicketTechnician.fecha_desasignacion.is_(None),
            ),
        )
        .outerjoin(
            Ticket,
            db.and_(
                Ticket.id == TicketTechnician.ticket_id,
                not_closed,
                *_ticket_filters(filters),
            ),
        )
        .outerjoin(Estado, Estado.id == Ticket.estado_id)
        .outerjoin(Prioridad, Prioridad.id == Ticket.prioridad_id)
        .group_by(User.id, Role.id)
        .having(
            db.or_(
                db.and_(User.activo.is_(True), Role.codigo == RoleCode.TECNICO),
                counts["active"] > 0,
            )
        )
        .order_by(func.lower(User.apellido), func.lower(User.nombre), User.id)
    ).all()

    distribution = _priority_distribution(
        [row.User.id for row in rows], filters
    )

    return [
        TechnicianLoad(
            user=row.User,
            active=row.active,
            in_progress=row.in_progress,
            on_hold=row.on_hold,
            critical=row.critical,
            near_due=row.near_due,
            overdue=row.overdue,
            resolved=row.resolved,
            inactive=row.inactive,
            by_priority=distribution.get(row.User.id, {}),
            high=is_high_load(row.active, threshold),
        )
        for row in rows
    ]


def _priority_distribution(technician_ids, filters) -> dict[int, dict[int, int]]:
    """Tickets activos de cada técnico por prioridad (una consulta para todos)."""
    if not technician_ids:
        return {}

    result: dict[int, dict[int, int]] = {}

    for technician_id, priority_id, total in db.session.execute(
        db.select(TicketTechnician.tecnico_id, Ticket.prioridad_id, func.count(Ticket.id))
        .join(Ticket, Ticket.id == TicketTechnician.ticket_id)
        .join(Estado, Estado.id == Ticket.estado_id)
        .where(
            TicketTechnician.fecha_desasignacion.is_(None),
            TicketTechnician.tecnico_id.in_(technician_ids),
            active_state_condition(),
            *_ticket_filters(filters),
        )
        .group_by(TicketTechnician.tecnico_id, Ticket.prioridad_id)
    ):
        result.setdefault(technician_id, {})[priority_id] = total

    return result


def _active_tickets_query(columns, filters):
    """`SELECT columns FROM tickets` con estado y prioridad, solo los activos."""
    return (
        db.select(*columns)
        .select_from(Ticket)
        .join(Estado, Estado.id == Ticket.estado_id)
        .join(Prioridad, Prioridad.id == Ticket.prioridad_id)
        .where(active_state_condition(), *_ticket_filters(filters))
    )


def _group_rows(filters, now) -> dict:
    """Una fila por grupo (la clave `None` es «sin grupo») con los contadores de sus tickets
    activos. Como todo ticket activo está en exactamente un grupo, la suma de las filas son
    los totales (`_summary`): se calculan una sola vez, con un solo recorrido de SLA."""
    counts = _counts(now)
    unassigned = ~has_current_technician()
    critical = Prioridad.codigo == CRITICAL_PRIORITY_CODE

    return {
        row.grupo_id: row
        for row in db.session.execute(
            _active_tickets_query(
                [
                    Ticket.grupo_id,
                    *(expression.label(name) for name, expression in counts.items()),
                    func.count(Ticket.id).filter(unassigned).label("unassigned"),
                    func.count(Ticket.id)
                    .filter(unassigned, critical)
                    .label("unassigned_critical"),
                ],
                filters,
            ).group_by(Ticket.grupo_id)
        )
    }


def _group_loads(by_group: dict) -> list[GroupLoad]:
    def load(group, row):
        if row is None:
            return GroupLoad(group, 0, 0, 0, 0, 0, 0)

        return GroupLoad(
            group,
            row.active,
            row.unassigned,
            row.critical,
            row.near_due,
            row.overdue,
            row.inactive,
        )

    # Los grupos activos aparecen aunque no tengan trabajo; uno desactivado solo si aún
    # conserva tickets activos. «Sin grupo» solo si hay tickets sin grupo.
    groups = list(db.session.scalars(db.select(Grupo).order_by(func.lower(Grupo.nombre))))
    loads = [
        load(group, by_group.get(group.id))
        for group in groups
        if group.activo or group.id in by_group
    ]

    if None in by_group:
        loads.append(load(None, by_group[None]))

    return loads


def _summary(by_group: dict, technicians) -> WorkloadSummary:
    def total(name: str) -> int:
        return sum(getattr(row, name) for row in by_group.values())

    return WorkloadSummary(
        active=total("active"),
        unassigned=total("unassigned"),
        critical=total("critical"),
        near_due=total("near_due"),
        overdue=total("overdue"),
        in_progress=total("in_progress"),
        on_hold=total("on_hold"),
        unassigned_critical=total("unassigned_critical"),
        technicians_with_work=sum(1 for t in technicians if t.active > 0),
        high_load_technicians=sum(1 for t in technicians if t.high),
        inactive=total("inactive"),
    )
