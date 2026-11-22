"""Períodos de SLA de los tickets (docs/09, 20.3; docs/06, RN-166).

Un ticket va acumulando **períodos de SLA**: tramos de su vida bajo unas mismas
condiciones (la política de su prioridad, corriendo o en pausa). Cuando esas
condiciones cambian se cierra el período vigente y se abre otro. Estas son las
reglas que lo gobiernan:

- **El reloj mide tiempo laboral** (`worktime.py`) con el calendario vigente al
  abrir cada período, que el período anota.
- **Un cambio nunca reinicia el reloj.** Al cerrar un período se guarda lo que
  consumió; el consumo del ticket es la suma de todos y el vencimiento del período
  siguiente es el momento del cambio más lo que queda del objetivo (si ya se
  consumió todo, nace vencido). Un vencimiento ya incumplido no se borra por un
  cambio posterior (RN-88).
- **El reloj corre mientras el ticket está en trabajo.** Se detiene al pasar a
  `Resuelto` (la espera de la validación del solicitante no cuenta contra el
  técnico) o a `Cerrado`, y sigue donde iba si el ticket se reabre.
- **La pausa** (RN-89): si la política pausa en espera, mientras el ticket está en
  `En espera` hay un período vigente **sin vencimiento**, que no consume tiempo.
  No hay una columna de pausa: ese vacío ya lo dice.
- **Las condiciones se heredan.** Mientras la prioridad no cambie, los períodos
  nuevos (al reanudar una pausa o reabrir) copian los objetivos del anterior: editar
  después la política no altera el SLA que un ticket ya tiene en curso. Solo un
  cambio de prioridad toma la política vigente de la prioridad nueva. Una
  prioridad sin política activa no tiene SLA.
- **El aviso de «próximo a vencer»** también se calcula al abrir el período: se copia
  el umbral de la política y se guarda el momento (en tiempo laboral) en que el consumo
  lo alcanza, igual que el vencimiento. Así el estado del SLA se puede filtrar y
  ordenar en la base de datos (`queries.py`) y se evalúa por lotes sin una consulta por
  ticket (`evaluate_tickets_sla`).
- **Primera respuesta** es el primer comentario público del personal.

`reconcile_sla` es el único punto de entrada de los cambios en vivo: la creación
del ticket, el cambio de prioridad y el cambio de estado la llaman al terminar.
Mira cómo está el ticket y deja los períodos como deben estar, así que es
idempotente. Ninguna función hace commit: los períodos se confirman o se revierten
junto con la operación que los provocó.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sqlalchemy import func

from ..extensions import db
from ..formatting import app_zone
from ..models import (
    CalendarioLaboral,
    Comment,
    Estado,
    PeriodoSla,
    PoliticaSla,
    Role,
    Ticket,
    TicketHistory,
    User,
)
from ..models.comment import CommentType
from ..models.estado import ON_HOLD_STATE_CODE
from ..models.ticket_history import TicketEvent
from ..security.authorization import CLOSED_STATE, RESOLVED_STATE, STAFF_ROLES
from ..worktime import DEMO_CALENDAR, BusinessClock
from .work_calendar import clock_for, resolve_work_calendar

INITIAL_STATE_CODE = "NUEVO"

# Estados en los que el reloj no corre: ya se resolvió o se cerró.
STOPPING_STATES = frozenset({RESOLVED_STATE, CLOSED_STATE})


class SlaMode(StrEnum):
    """Cómo debe estar el reloj de un ticket según su estado."""

    RUNNING = "corriendo"
    PAUSED = "pausado"
    STOPPED = "detenido"


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
class _Terms:
    """Las condiciones que se copian a un período nuevo."""

    policy_id: int | None
    response_minutes: int | None
    resolution_minutes: int
    pause_on_hold: bool
    warning_percent: int | None

    @classmethod
    def of_policy(cls, policy: PoliticaSla) -> "_Terms":
        return cls(
            policy_id=policy.id,
            response_minutes=policy.tiempo_objetivo_respuesta_minutos,
            resolution_minutes=policy.tiempo_objetivo_resolucion_minutos,
            pause_on_hold=policy.pausa_en_espera,
            warning_percent=policy.umbral_aviso_consumo_porcentaje,
        )

    @classmethod
    def of_period(cls, period: PeriodoSla) -> "_Terms":
        return cls(
            policy_id=period.politica_sla_id,
            response_minutes=period.tiempo_objetivo_respuesta_minutos,
            resolution_minutes=period.tiempo_objetivo_resolucion_minutos,
            pause_on_hold=period.pausa_en_espera,
            warning_percent=period.umbral_aviso_porcentaje,
        )


def warning_seconds(objective_seconds: int, percent: int) -> int:
    """Los segundos laborales de consumo en que se alcanza el umbral de aviso: el menor
    consumo `c` tal que `c * 100 // objetivo >= porcentaje`, es decir, el entero
    siguiente a `objetivo * porcentaje / 100` (si no es exacto)."""
    return -(-objective_seconds * percent // 100)


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


# --- Consultas ------------------------------------------------------------------


def current_time() -> datetime:
    """El instante actual según la base de datos (`now()`, el de la transacción).

    Es el mismo que ponen los eventos del historial, así que un período abre en el
    mismo instante que el evento que lo provocó.
    """
    return db.session.scalar(db.select(func.now()))


def list_periods(ticket_id: int) -> list[PeriodoSla]:
    """Los períodos del ticket, del más antiguo al más reciente."""
    return list(
        db.session.scalars(
            db.select(PeriodoSla)
            .where(PeriodoSla.ticket_id == ticket_id)
            .order_by(PeriodoSla.fecha_inicio, PeriodoSla.id)
        )
    )


def first_response_at(ticket_id: int) -> datetime | None:
    """Cuándo recibió el ticket su primera respuesta, o None si aún no.

    Es el primer comentario público del personal que sigue visible. Asignar el
    ticket o cambiar su estado no cuenta (fase 5 del roadmap).
    """
    return _first_responses([ticket_id]).get(ticket_id)


def _first_responses(ticket_ids: Iterable[int]) -> dict[int, datetime]:
    """La primera respuesta de cada ticket que ya la tiene, en una sola consulta."""
    rows = db.session.execute(
        db.select(Comment.ticket_id, func.min(Comment.fecha_creacion))
        .join(User, User.id == Comment.autor_usuario_id)
        .join(Role, Role.id == User.rol_id)
        .where(
            Comment.ticket_id.in_(list(ticket_ids)),
            Comment.tipo == CommentType.PUBLICO.value,
            Comment.activo.is_(True),
            Role.codigo.in_([role.value for role in STAFF_ROLES]),
        )
        .group_by(Comment.ticket_id)
    ).all()

    return dict(rows)


def accumulated_seconds(ticket_id: int) -> int:
    """Lo que el ticket lleva consumido en los períodos ya cerrados."""
    return int(
        db.session.scalar(
            db.select(func.coalesce(func.sum(PeriodoSla.segundos_consumidos), 0)).where(
                PeriodoSla.ticket_id == ticket_id,
                PeriodoSla.fecha_fin.is_not(None),
            )
        )
    )


# --- Cambios en vivo --------------------------------------------------------------


def reconcile_sla(
    ticket: Ticket,
    actor: User | None,
    *,
    reason: str | None = None,
    now: datetime | None = None,
) -> PeriodoSla | None:
    """Deja los períodos del ticket como corresponde a su prioridad y su estado.

    La llaman, al terminar, la creación del ticket, el cambio de prioridad y el
    cambio de estado. `actor` es quien provocó el cambio (None si fue el sistema) y
    `reason`, el motivo de un cambio de prioridad: ambos quedan en el período nuevo
    (RN-88). Devuelve el período vigente, o None si el ticket no tiene SLA ahora
    (sin política para su prioridad, resuelto o cerrado). Si nada cambió no hace
    nada.
    """
    state = db.session.get(Estado, ticket.estado_id)

    return _reconcile(
        ticket.id,
        ticket.prioridad_id,
        state.codigo,
        now or current_time(),
        actor_id=None if actor is None else actor.id,
        reason=reason,
    )


def _reconcile(
    ticket_id: int,
    priority_id: int,
    state_code: str,
    now: datetime,
    *,
    actor_id: int | None,
    reason: str | None,
) -> PeriodoSla | None:
    open_period = _open_period(ticket_id)
    last = open_period or _last_period(ticket_id)

    if last is not None and last.prioridad_id == priority_id:
        # Misma prioridad: las condiciones no cambian.
        terms = _Terms.of_period(last)
    else:
        policy = _active_policy(priority_id)
        terms = None if policy is None else _Terms.of_policy(policy)

    mode = _mode_for(state_code, terms)

    if open_period is not None:
        if (
            mode is not SlaMode.STOPPED
            and open_period.prioridad_id == priority_id
            and _mode_of(open_period) is mode
        ):
            return open_period

        _close(open_period, now)

    if mode is SlaMode.STOPPED:
        return None

    return _open(ticket_id, priority_id, terms, mode, now, actor_id, reason)


def _mode_for(state_code: str, terms: _Terms | None) -> SlaMode:
    if terms is None or state_code in STOPPING_STATES:
        return SlaMode.STOPPED

    if state_code == ON_HOLD_STATE_CODE and terms.pause_on_hold:
        return SlaMode.PAUSED

    return SlaMode.RUNNING


def _mode_of(period: PeriodoSla) -> SlaMode:
    return SlaMode.PAUSED if period.esta_pausado else SlaMode.RUNNING


def _open(
    ticket_id: int,
    priority_id: int,
    terms: _Terms,
    mode: SlaMode,
    now: datetime,
    actor_id: int | None,
    reason: str | None,
) -> PeriodoSla:
    """Abre un período con lo que le queda al ticket de sus objetivos."""
    resolved = resolve_work_calendar()
    consumed = accumulated_seconds(ticket_id)
    due = response_due = warning_due = None

    if mode is SlaMode.RUNNING:
        clock = resolved.clock
        due = clock.add_business_seconds(
            now, max(terms.resolution_minutes * 60 - consumed, 0)
        )

        if terms.warning_percent is not None:
            warning = warning_seconds(terms.resolution_minutes * 60, terms.warning_percent)
            warning_due = clock.add_business_seconds(now, max(warning - consumed, 0))
        responded = first_response_at(ticket_id)

        if terms.response_minutes is not None and (
            responded is None or responded > now
        ):
            response_due = clock.add_business_seconds(
                now, max(terms.response_minutes * 60 - consumed, 0)
            )

    period = PeriodoSla(
        ticket_id=ticket_id,
        politica_sla_id=terms.policy_id,
        prioridad_id=priority_id,
        calendario_laboral_id=None if resolved.record is None else resolved.record.id,
        tiempo_objetivo_respuesta_minutos=terms.response_minutes,
        tiempo_objetivo_resolucion_minutos=terms.resolution_minutes,
        pausa_en_espera=terms.pause_on_hold,
        fecha_inicio=now,
        segundos_consumidos=0,
        fecha_vencimiento_respuesta=response_due,
        fecha_vencimiento_resolucion=due,
        umbral_aviso_porcentaje=terms.warning_percent,
        fecha_umbral_aviso=warning_due,
        usuario_cambio_id=actor_id,
        motivo_cambio=reason,
    )
    db.session.add(period)
    db.session.flush()

    return period


def _close(period: PeriodoSla, now: datetime) -> None:
    """Cierra el período y anota lo que consumió (nada si estaba pausado)."""
    end = max(now, period.fecha_inicio)

    if period.esta_pausado:
        consumed = 0
    else:
        consumed = _clock_of(period).business_seconds_between(period.fecha_inicio, end)

    period.fecha_fin = end
    period.segundos_consumidos = consumed
    db.session.flush()


def _clock_of(period: PeriodoSla) -> BusinessClock:
    """El reloj del calendario con que se calculó el período."""
    return _ClockCache().of(period)


class _ClockCache:
    """Un reloj por cada calendario distinto: la mayoría de los períodos comparten uno,
    así que evaluar muchos tickets no construye uno por ticket."""

    def __init__(self) -> None:
        self._clocks: dict[int | None, BusinessClock] = {}

    def of(self, period: PeriodoSla) -> BusinessClock:
        key = period.calendario_laboral_id

        if key not in self._clocks:
            self._clocks[key] = (
                BusinessClock(DEMO_CALENDAR, app_zone())
                if key is None
                else clock_for(db.session.get(CalendarioLaboral, key))
            )

        return self._clocks[key]


def _active_policy(priority_id: int) -> PoliticaSla | None:
    return db.session.scalar(
        db.select(PoliticaSla).where(
            PoliticaSla.prioridad_id == priority_id,
            PoliticaSla.activo.is_(True),
        )
    )


def _open_period(ticket_id: int) -> PeriodoSla | None:
    return db.session.scalar(
        db.select(PeriodoSla).where(
            PeriodoSla.ticket_id == ticket_id,
            PeriodoSla.fecha_fin.is_(None),
        )
    )


def _last_period(ticket_id: int) -> PeriodoSla | None:
    return db.session.scalar(
        db.select(PeriodoSla)
        .where(PeriodoSla.ticket_id == ticket_id)
        .order_by(PeriodoSla.fecha_inicio.desc(), PeriodoSla.id.desc())
        .limit(1)
    )


# --- Evaluación -----------------------------------------------------------------------


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

    now = now or current_time()
    periods = _periods_by_ticket(ids)
    # Un ticket cuyo último período está cerrado solo tiene SLA si terminó (resuelto o
    # cerrado). Si no, es que su prioridad no tiene política.
    finished = [tid for tid, rows in periods.items() if rows[-1].fecha_fin is not None]
    stopped = _stopped_among(finished)
    answered = _first_responses(periods)
    clocks = _ClockCache()

    return {
        ticket_id: (
            _snapshot(
                periods[ticket_id],
                now,
                answered.get(ticket_id),
                clocks,
                stopped=ticket_id in stopped,
            )
            if ticket_id in periods
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
    periods: list[PeriodoSla],
    now: datetime,
    responded_at: datetime | None,
    clocks: "_ClockCache",
    *,
    stopped: bool,
) -> SlaSnapshot | None:
    period = periods[-1]

    if period.fecha_fin is not None and not stopped:
        return None

    earlier = periods[:-1]
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
    clocks = _ClockCache()

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


# --- Reconstrucción desde el historial ----------------------------------------------


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

    _reconcile(
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
        _reconcile(
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
    _reconcile(
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
