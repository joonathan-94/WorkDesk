"""Mantenimiento de los períodos de SLA ya existentes (comando `sla-rebuild`).

Recalcula períodos desde el historial (tickets anteriores al SLA y datos de
demostración) y completa las fechas de aviso que falten. Usa las mismas reglas que
los cambios en vivo (`periods.py`). Ninguna función hace commit.
"""

from dataclasses import dataclass

from ..extensions import db
from ..models import Estado, PeriodoSla, Ticket, TicketHistory
from ..models.ticket_history import TicketEvent
from .periods import (
    INITIAL_STATE_CODE,
    ClockCache,
    accumulated_seconds,
    list_periods,
    reconcile,
    warning_seconds,
)


def fill_missing_warning_dates() -> int:
    """Calcula la fecha de aviso de los períodos en marcha que todavía no la tienen.

    Son los que abrió una versión anterior a la fecha de aviso: la migración les copió
    el umbral de su política, pero el momento en que el consumo lo alcanza se calcula
    en tiempo laboral, con el calendario del propio período. Es idempotente y no toca
    los períodos cerrados ni los pausados. Devuelve cuántos completó. No hace commit.
    """
    pending = db.session.scalars(
        db.select(PeriodoSla).where(
            PeriodoSla.fecha_fin.is_(None),
            PeriodoSla.fecha_vencimiento_resolucion.is_not(None),
            PeriodoSla.umbral_aviso_porcentaje.is_not(None),
            PeriodoSla.fecha_umbral_aviso.is_(None),
        )
    ).all()
    clocks = ClockCache()

    for period in pending:
        warning = warning_seconds(
            period.tiempo_objetivo_resolucion_minutos * 60,
            period.umbral_aviso_porcentaje,
        )
        consumed = accumulated_seconds(period.ticket_id)
        period.fecha_umbral_aviso = clocks.of(period).add_business_seconds(
            period.fecha_inicio, max(warning - consumed, 0)
        )

    db.session.flush()

    return len(pending)


def rebuild_ticket_periods(ticket: Ticket) -> int:
    """Recalcula los períodos del ticket repasando su historial. Devuelve cuántos.

    Sirve para los tickets que existían antes de que hubiera SLA y para los datos de
    demostración, cuyo historial se reescribe con fechas pasadas. Repite, con las
    fechas de cada evento (la creación, los cambios de prioridad y los de estado),
    lo que `reconcile_sla` hizo o habría hecho en vivo.

    Es una aproximación: usa la política y el calendario **vigentes hoy**, porque el
    historial no guarda cuáles eran entonces. Por eso no se ejecuta sobre tickets que
    ya tienen períodos reales salvo que se pida expresamente.
    """
    db.session.execute(
        db.delete(PeriodoSla).where(PeriodoSla.ticket_id == ticket.id)
    )
    db.session.flush()

    state_codes = dict(db.session.execute(db.select(Estado.id, Estado.codigo)).all())
    events = db.session.scalars(
        db.select(TicketHistory)
        .where(TicketHistory.ticket_id == ticket.id)
        .order_by(TicketHistory.fecha_hora, TicketHistory.id)
    ).all()

    priority_id = _initial_priority(ticket, events)
    state_code = INITIAL_STATE_CODE

    created = next(
        (e for e in events if e.tipo_evento == TicketEvent.TICKET_CREADO.value), None
    )
    last_time = created.fecha_hora if created is not None else ticket.fecha_creacion

    reconcile(
        ticket.id, priority_id, state_code, last_time, actor_id=None, reason=None
    )

    for event in events:
        if event.tipo_evento == TicketEvent.TICKET_CREADO.value:
            continue

        reason = None

        if event.tipo_evento == TicketEvent.PRIORIDAD_CAMBIADA.value:
            priority_id = event.valor_nuevo["prioridad_id"]
            reason = (event.contexto or {}).get("motivo")
        elif event.estado_nuevo_id is not None:
            state_code = state_codes[event.estado_nuevo_id]
        else:
            continue

        last_time = event.fecha_hora
        reconcile(
            ticket.id,
            priority_id,
            state_code,
            last_time,
            actor_id=event.actor_usuario_id,
            reason=reason,
        )

    # Si el historial no explicara el estado actual (datos tocados a mano), el
    # ticket manda: así nunca queda un reloj que contradiga su estado.
    final_state = state_codes[ticket.estado_id]
    reconcile(
        ticket.id, ticket.prioridad_id, final_state, last_time, actor_id=None, reason=None
    )

    return len(list_periods(ticket.id))


@dataclass(frozen=True)
class RebuildResult:
    tickets: int
    periods: int


def rebuild_periods(
    *, only_missing: bool = True, public_id: str | None = None
) -> RebuildResult:
    """Recalcula los períodos de varios tickets (lo usa el comando `sla-rebuild`).

    Por defecto solo toca los tickets que no tienen ningún período (los anteriores
    al SLA): los que ya los tienen son el cálculo en vivo y no se reescriben.
    `only_missing=False` recalcula todos; `public_id` limita a un ticket.
    """
    statement = db.select(Ticket).order_by(Ticket.id)

    if public_id is not None:
        statement = statement.where(Ticket.public_id == public_id)

    if only_missing:
        statement = statement.where(
            ~db.exists().where(PeriodoSla.ticket_id == Ticket.id)
        )

    tickets = db.session.scalars(statement).all()
    periods = sum(rebuild_ticket_periods(ticket) for ticket in tickets)

    return RebuildResult(tickets=len(tickets), periods=periods)


def _initial_priority(ticket: Ticket, events) -> int:
    """La prioridad con que se creó el ticket: la anterior al primer cambio."""
    for event in events:
        if event.tipo_evento == TicketEvent.PRIORIDAD_CAMBIADA.value:
            return event.valor_anterior["prioridad_id"]

    return ticket.prioridad_id
