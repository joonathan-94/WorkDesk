"""Cómo está el SLA de un ticket en un momento dado (docs/10, 28.1; docs/06, RN-169).

Es la mitad de **lectura** del SLA: mira los períodos que `periods.py` va guardando y
dice si cada ticket está dentro de plazo, próximo a vencer, vencido o pausado. No
escribe nada. Su equivalente en SQL, para filtrar y ordenar el listado, está en
`queries.py`: si se cambia uno hay que cambiar el otro.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from ..extensions import db
from ..models import Estado, PeriodoSla, Ticket
from . import periods
from .periods import STOPPING_STATES, ClockCache, first_responses


class SlaStatus(StrEnum):
    """Dónde está un ticket respecto de su SLA (docs/10, sección 82)."""

    DENTRO = "DENTRO"
    PROXIMO_A_VENCER = "PROXIMO_A_VENCER"
    VENCIDO = "VENCIDO"
    PAUSADO = "PAUSADO"


# Nombre visible de cada estado del SLA.
SLA_STATUS_LABELS = {
    SlaStatus.DENTRO: "Dentro de SLA",
    SlaStatus.PROXIMO_A_VENCER: "Próximo a vencer",
    SlaStatus.VENCIDO: "Vencido",
    SlaStatus.PAUSADO: "Pausado",
}


@dataclass(frozen=True)
class SlaSnapshot:
    """Cómo está el SLA de un ticket en un momento dado."""

    status: SlaStatus
    period: PeriodoSla
    consumed_seconds: int
    objective_seconds: int
    percent: int
    due_at: datetime | None
    response_due_at: datetime | None
    responded_at: datetime | None
    response_overdue: bool
    breached: bool
    closed: bool

    @property
    def remaining_seconds(self) -> int:
        return max(self.objective_seconds - self.consumed_seconds, 0)

    @property
    def overdue_seconds(self) -> int:
        """Lo que el consumo pasa del objetivo (0 si todavía no lo alcanza)."""
        return max(self.consumed_seconds - self.objective_seconds, 0)


def evaluate_ticket_sla(
    ticket_id: int, now: datetime | None = None
) -> SlaSnapshot | None:
    """Cómo está el SLA del ticket en `now` (por defecto, ahora), o None si nunca
    tuvo SLA. Ver `evaluate_tickets_sla`, que hace lo mismo para varios a la vez."""
    return evaluate_tickets_sla([ticket_id], now).get(ticket_id)


def evaluate_tickets_sla(
    ticket_ids: Iterable[int], now: datetime | None = None
) -> dict[int, SlaSnapshot | None]:
    """Cómo está el SLA de cada ticket en `now` (por defecto, ahora), con un número
    fijo de consultas: no una por ticket (es lo que usa el listado).

    Devuelve una entrada por cada ticket pedido: su `SlaSnapshot`, o None si no tiene
    SLA (nunca tuvo períodos o su prioridad no tiene política). Mira el período más
    reciente: vigente (corriendo o pausado) o, si el ticket se resolvió o cerró, el
    último que tuvo. El consumo suma el de los períodos anteriores. Un incumplimiento
    ya ocurrido no se borra: si algún período venció, el ticket sigue vencido aunque
    después baje de prioridad (RN-88).
    """
    ids = list(dict.fromkeys(ticket_ids))

    if not ids:
        return {}

    if not periods.sla_enabled():
        return dict.fromkeys(ids)

    now = now or periods.current_time()
    rows_by_ticket = _periods_by_ticket(ids)
    # Un ticket cuyo último período está cerrado solo tiene SLA si terminó (resuelto o
    # cerrado). Si no, es que su prioridad no tiene política.
    finished = [
        tid for tid, rows in rows_by_ticket.items() if rows[-1].fecha_fin is not None
    ]
    stopped = _stopped_among(finished)
    answered = first_responses(rows_by_ticket)
    clocks = ClockCache()

    return {
        ticket_id: (
            _snapshot(
                rows_by_ticket[ticket_id],
                now,
                answered.get(ticket_id),
                clocks,
                stopped=ticket_id in stopped,
            )
            if ticket_id in rows_by_ticket
            else None
        )
        for ticket_id in ids
    }


def _periods_by_ticket(ticket_ids: list[int]) -> dict[int, list[PeriodoSla]]:
    grouped: dict[int, list[PeriodoSla]] = defaultdict(list)

    for period in db.session.scalars(
        db.select(PeriodoSla)
        .where(PeriodoSla.ticket_id.in_(ticket_ids))
        .order_by(PeriodoSla.ticket_id, PeriodoSla.fecha_inicio, PeriodoSla.id)
    ):
        grouped[period.ticket_id].append(period)

    return dict(grouped)


def _stopped_among(ticket_ids: list[int]) -> set[int]:
    """Cuáles de estos tickets están resueltos o cerrados."""
    if not ticket_ids:
        return set()

    return set(
        db.session.scalars(
            db.select(Ticket.id)
            .join(Estado, Estado.id == Ticket.estado_id)
            .where(Ticket.id.in_(ticket_ids), Estado.codigo.in_(sorted(STOPPING_STATES)))
        )
    )


def _snapshot(
    rows: list[PeriodoSla],
    now: datetime,
    responded_at: datetime | None,
    clocks: "ClockCache",
    *,
    stopped: bool,
) -> SlaSnapshot | None:
    period = rows[-1]

    if period.fecha_fin is not None and not stopped:
        return None

    earlier = rows[:-1]
    running = period.segundos_consumidos

    if period.esta_vigente and not period.esta_pausado:
        running = clocks.of(period).business_seconds_between(
            period.fecha_inicio, max(now, period.fecha_inicio)
        )

    consumed = sum(p.segundos_consumidos for p in earlier) + running
    objective = period.tiempo_objetivo_resolucion_minutos * 60
    percent = consumed * 100 // objective
    breached = consumed >= objective or any(
        p.fecha_vencimiento_resolucion is not None
        and p.fecha_vencimiento_resolucion <= p.fecha_fin
        for p in earlier
    )
    closed = period.fecha_fin is not None

    if breached:
        status = SlaStatus.VENCIDO
    elif period.esta_pausado:
        status = SlaStatus.PAUSADO
    elif not closed and _warning_reached(period, now):
        status = SlaStatus.PROXIMO_A_VENCER
    else:
        status = SlaStatus.DENTRO

    return SlaSnapshot(
        status=status,
        period=period,
        consumed_seconds=consumed,
        objective_seconds=objective,
        percent=percent,
        due_at=period.fecha_vencimiento_resolucion,
        response_due_at=period.fecha_vencimiento_respuesta,
        responded_at=responded_at,
        response_overdue=_response_overdue(period, responded_at, now),
        breached=breached,
        closed=closed,
    )


def _warning_reached(period: PeriodoSla, now: datetime) -> bool:
    """Si ya llegó la fecha de aviso del período (guardada al abrirlo; sin ella, que es
    lo que tienen los períodos anteriores a esta fecha hasta `sla-rebuild`, no hay
    aviso)."""
    return period.fecha_umbral_aviso is not None and now >= period.fecha_umbral_aviso


def _response_overdue(
    period: PeriodoSla, responded_at: datetime | None, now: datetime
) -> bool:
    due = period.fecha_vencimiento_respuesta

    if due is None:
        return False

    if responded_at is None:
        return now >= due

    return responded_at > due
