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
  ticket (`evaluation.py`).
- **Primera respuesta** es el primer comentario público del personal.

`reconcile_sla` es el único punto de entrada de los cambios en vivo: la creación
del ticket, el cambio de prioridad y el cambio de estado la llaman al terminar.
Mira cómo está el ticket y deja los períodos como deben estar, así que es
idempotente. Ninguna función hace commit: los períodos se confirman o se revierten
junto con la operación que los provocó.

Este módulo es la mitad de **escritura**. Cómo está el SLA en un momento dado lo dice
`evaluation.py`, y recalcular períodos desde el historial es de `rebuild.py`.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sqlalchemy import func

from .. import settings
from ..configuration import value_of
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
    User,
)
from ..models.comment import CommentType
from ..models.estado import ON_HOLD_STATE_CODE
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


# --- Consultas ------------------------------------------------------------------


def current_time() -> datetime:
    """El instante actual según la base de datos (`now()`, el de la transacción).

    Es el mismo que ponen los eventos del historial, así que un período abre en el
    mismo instante que el evento que lo provocó.
    """
    return db.session.scalar(db.select(func.now()))


def sla_enabled() -> bool:
    """Si el SLA se aplica (interruptor general, docs/11, UI-022).

    Apagado, WorkDesk **no muestra ni avisa nada del SLA** (insignias, filtros, orden,
    indicadores, advertencias y avisos del planificador), pero **sigue calculando** los
    períodos de cada ticket: al encenderlo los datos ya están al día y no hay que
    reconstruir nada.
    """
    return value_of(settings.SLA_ENABLED)


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
    return first_responses([ticket_id]).get(ticket_id)


def first_responses(ticket_ids: Iterable[int]) -> dict[int, datetime]:
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

    return reconcile(
        ticket.id,
        ticket.prioridad_id,
        state.codigo,
        now or current_time(),
        actor_id=None if actor is None else actor.id,
        reason=reason,
    )


def reconcile(
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

    notified: tuple[datetime | None, datetime | None] = (None, None)

    if last is not None and last.prioridad_id == priority_id:
        # Misma prioridad: las condiciones no cambian, ni lo ya avisado.
        terms = _Terms.of_period(last)
        notified = (last.fecha_aviso_umbral_enviado, last.fecha_aviso_vencimiento_enviado)
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

    return _open(ticket_id, priority_id, terms, mode, now, actor_id, reason, notified)


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
    notified: tuple[datetime | None, datetime | None] = (None, None),
) -> PeriodoSla:
    """Abre un período con lo que le queda al ticket de sus objetivos.

    `notified` son los avisos de umbral y de vencimiento que el planificador ya
    envió con las mismas condiciones (ver `PeriodoSla.fecha_aviso_umbral_enviado`).
    """
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
        fecha_aviso_umbral_enviado=notified[0],
        fecha_aviso_vencimiento_enviado=notified[1],
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
    return ClockCache().of(period)


class ClockCache:
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
