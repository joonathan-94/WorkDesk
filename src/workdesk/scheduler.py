"""Planificador de tareas periódicas (docs/10, secciones 84 a 87; docs/06, RN-58, RN-59
y RN-170).

WorkDesk no necesita un programador de tareas externo (ni APScheduler ni Celery): las
tareas de esta fase son consultas a la base de datos que se pueden repetir sin riesgo.
`run-scheduler` las ejecuta una vez (para el Programador de tareas de Windows o `cron`)
o en un bucle simple que se deja en un proceso aparte, con el mismo código que la
aplicación web y la misma base de datos.

Hay dos tareas:

- **Avisos de SLA** (`run_sla_notices`): cuando un período de SLA en marcha alcanza su
  umbral de aviso o vence, avisa **una sola vez** a quien corresponde
  (`notifications/events.py`) y, al vencer, deja el incumplimiento registrado en el
  historial del ticket (`SLA_VENCIDO`, RN-91). La marca de «ya avisado» está en el propio
  período (`fecha_aviso_umbral_enviado` y `fecha_aviso_vencimiento_enviado`).
- **Cierre automático** (`run_auto_close`): cierra los tickets `Resuelto` que nadie
  validó en `AUTO_CLOSE_HOURS` horas (`tickets/lifecycle.py`, `close_automatically`).

**Idempotencia.** Ejecutar una tarea dos veces, o dos planificadores a la vez, no
duplica nada. Cada elemento se procesa en **su propia transacción**: se bloquea el
ticket, se **vuelve a comprobar** que sigue correspondiendo (otra transacción pudo
cambiarlo desde que se lo encontró) y solo entonces se actúa y se confirma. Si un
elemento falla se deshace solo ese y se sigue con los demás. Se bloquea siempre **el
ticket primero**, como los cambios de estado y de prioridad, para no bloquearse con la
gente que está trabajando.

Aquí sí se hace commit: este módulo es el que inicia las transacciones, no un servicio
que otros llaman.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from flask import current_app
from sqlalchemy import and_, or_

from .extensions import db
from .models import Estado, PeriodoSla, Ticket, TicketEvent
from .notifications.events import notify_sla_breach, notify_sla_warning
from .security.authorization import RESOLVED_STATE
from .sla.periods import current_time
from .tickets.lifecycle import close_automatically
from .tickets.service import record_ticket_event
from .tickets.versioning import lock_ticket

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SlaNoticeResult:
    """Cuántos avisos de SLA envió una ejecución."""

    warnings: int = 0
    breaches: int = 0


@dataclass(frozen=True)
class SchedulerResult:
    """Lo que hizo una ejecución completa del planificador."""

    warnings: int = 0
    breaches: int = 0
    closed: int = 0
    failures: int = 0


# --- Avisos de SLA ----------------------------------------------------------------


def _warning_reached(period: PeriodoSla, now: datetime) -> bool:
    return (
        period.fecha_umbral_aviso is not None
        and period.fecha_umbral_aviso <= now
        and period.fecha_aviso_umbral_enviado is None
    )


def _breach_reached(period: PeriodoSla, now: datetime) -> bool:
    return (
        period.fecha_vencimiento_resolucion is not None
        and period.fecha_vencimiento_resolucion <= now
        and period.fecha_aviso_vencimiento_enviado is None
    )


def _pending_notice_ids(now: datetime) -> list[int]:
    """Los períodos en marcha con un aviso por enviar. Es solo la lista de candidatos:
    cada uno se vuelve a comprobar bloqueado."""
    return list(
        db.session.scalars(
            db.select(PeriodoSla.id)
            .where(
                PeriodoSla.fecha_fin.is_(None),
                or_(
                    and_(
                        PeriodoSla.fecha_umbral_aviso <= now,
                        PeriodoSla.fecha_aviso_umbral_enviado.is_(None),
                    ),
                    and_(
                        PeriodoSla.fecha_vencimiento_resolucion <= now,
                        PeriodoSla.fecha_aviso_vencimiento_enviado.is_(None),
                    ),
                ),
            )
            .order_by(PeriodoSla.id)
        )
    )


def _send_notice(period_id: int, now: datetime) -> str | None:
    """Avisa del período si todavía corresponde y deja la marca. Devuelve «breach»,
    «warning» o None si ya no había nada que avisar. No hace commit."""
    ticket_id = db.session.scalar(
        db.select(PeriodoSla.ticket_id).where(PeriodoSla.id == period_id)
    )

    if ticket_id is None:
        return None

    ticket = db.session.get(Ticket, ticket_id)

    # Primero se bloquea el ticket y después se lee su período: es el orden de los
    # cambios de estado y de prioridad, que bloquean el ticket y luego tocan sus
    # períodos. En el orden contrario, si alguien cambiara el estado justo ahora, cada
    # uno esperaría al otro (guardar el aviso pide el ticket por su clave foránea) y
    # PostgreSQL abortaría a uno de los dos: un error para quien estaba trabajando. Con
    # el ticket bloqueado también se serializan dos planificadores a la vez.
    lock_ticket(ticket)

    period = db.session.scalar(
        db.select(PeriodoSla)
        .where(PeriodoSla.id == period_id)
        .execution_options(populate_existing=True)
    )

    # Bajo el bloqueo: pudo cerrarse (cambio de estado o de prioridad) o avisarlo
    # otro planificador mientras tanto.
    if period is None or period.fecha_fin is not None:
        return None

    breach = _breach_reached(period, now)

    if not breach and not _warning_reached(period, now):
        return None

    if breach:
        notify_sla_breach(ticket)
        # RN-91: además de avisar, el incumplimiento queda registrado en el historial
        # (interno: el SLA es solo del personal), en la misma transacción que el aviso.
        record_ticket_event(
            ticket,
            TicketEvent.SLA_VENCIDO,
            actor=None,
            detail="El SLA del ticket venció.",
            context={
                "periodo_id": period.id,
                "objetivo_minutos": period.tiempo_objetivo_resolucion_minutos,
                "vencimiento": period.fecha_vencimiento_resolucion.isoformat(),
            },
        )
        period.fecha_aviso_vencimiento_enviado = now
        # Si venció, el aviso de «próximo a vencer» ya no tiene sentido.
        if period.fecha_aviso_umbral_enviado is None:
            period.fecha_aviso_umbral_enviado = now

        return "breach"

    notify_sla_warning(ticket)
    period.fecha_aviso_umbral_enviado = now

    return "warning"


def run_sla_notices(now: datetime | None = None) -> tuple[SlaNoticeResult, int]:
    """Envía los avisos de SLA pendientes. Devuelve lo enviado y cuántos elementos
    fallaron. Cada período se procesa y confirma por separado."""
    now = now or current_time()
    warnings = breaches = failures = 0

    for period_id in _pending_notice_ids(now):
        try:
            outcome = _send_notice(period_id, now)
            db.session.commit()
        except Exception:
            db.session.rollback()
            failures += 1
            logger.exception("No se pudo avisar del SLA del período %s.", period_id)
            continue

        if outcome == "breach":
            breaches += 1
        elif outcome == "warning":
            warnings += 1

    return SlaNoticeResult(warnings, breaches), failures


# --- Cierre automático ----------------------------------------------------------


def _pending_close_ids(cutoff: datetime) -> list[int]:
    """Los tickets `Resuelto` cuya resolución es anterior al límite."""
    return list(
        db.session.scalars(
            db.select(Ticket.id)
            .join(Estado, Estado.id == Ticket.estado_id)
            .where(
                Estado.codigo == RESOLVED_STATE,
                Ticket.fecha_resolucion <= cutoff,
            )
            .order_by(Ticket.id)
        )
    )


def run_auto_close(now: datetime | None = None) -> tuple[int, int]:
    """Cierra los tickets `Resuelto` que nadie validó en `AUTO_CLOSE_HOURS` horas.

    Devuelve cuántos cerró y cuántos fallaron. Cada ticket se cierra en su propia
    transacción y `close_automatically` comprueba el plazo con el ticket bloqueado.
    """
    now = now or current_time()
    cutoff = now - timedelta(hours=current_app.config["AUTO_CLOSE_HOURS"])
    closed = failures = 0

    for ticket_id in _pending_close_ids(cutoff):
        try:
            ticket = db.session.get(Ticket, ticket_id)
            did_close = close_automatically(ticket, resolved_before=cutoff)
            db.session.commit()
        except Exception:
            db.session.rollback()
            failures += 1
            logger.exception("No se pudo cerrar automáticamente el ticket %s.", ticket_id)
            continue

        closed += int(did_close)

    return closed, failures


# --- Ejecución ----------------------------------------------------------------


def run_once(now: datetime | None = None) -> SchedulerResult:
    """Ejecuta las dos tareas una vez. `now` es el instante de referencia (por defecto,
    el de la base de datos); lo usan los tests."""
    now = now or current_time()
    notices, notice_failures = run_sla_notices(now)
    closed, close_failures = run_auto_close(now)

    return SchedulerResult(
        warnings=notices.warnings,
        breaches=notices.breaches,
        closed=closed,
        failures=notice_failures + close_failures,
    )


def run_loop(
    interval_seconds: int,
    *,
    should_stop: Callable[[], bool] = lambda: False,
    sleep: Callable[[float], None] = time.sleep,
    on_result: Callable[[SchedulerResult], None] | None = None,
) -> None:
    """Ejecuta `run_once` cada `interval_seconds` hasta que `should_stop` lo pida.

    Un error inesperado de una pasada se registra y no detiene el bucle: el planificador
    debe seguir vivo para la siguiente. Después de cada pasada se descarta la sesión
    para que la siguiente empiece con una transacción nueva (y un `now()` nuevo).
    """
    while not should_stop():
        try:
            result = run_once()

            if on_result is not None:
                on_result(result)
        except Exception:
            db.session.rollback()
            logger.exception("Falló una pasada del planificador.")
        finally:
            db.session.remove()

        if should_stop():
            break

        sleep(interval_seconds)
