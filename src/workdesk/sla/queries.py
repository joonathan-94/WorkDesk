"""El estado del SLA en las consultas del listado de tickets (docs/06, RN-169;
docs/10, 28.1).

Filtrar y ordenar el listado por SLA tiene que ocurrir en la base de datos, antes de
paginar, así que el estado del SLA se expresa aquí como condiciones SQL sobre
`tickets`. Son el **equivalente exacto** de `evaluate_tickets_sla` (`evaluation.py`): un
test comprueba que ambos dan el mismo resultado para cada tipo de ticket y en cada
momento, incluidos los bordes (un segundo antes y después de cada fecha de aviso y de
vencimiento). Si se cambia uno hay que cambiar el otro.

Lo que permite expresarlo sin calcular tiempo laboral en SQL es que cada período
guarda sus fechas ya calculadas: `fecha_vencimiento_resolucion` (cuándo vence) y
`fecha_umbral_aviso` (cuándo alcanza el umbral de aviso). Con ellas:

- **Vencido:** algún período llegó a su vencimiento (`fecha_vencimiento_resolucion`
  no posterior al fin del período, o a `now` si sigue vigente), o el período en que
  está el ticket —pausado o ya cerrado— nació con más consumo que su objetivo
  (`segundos_consumidos` de los períodos cerrados). Un incumplimiento no se borra.
- **Pausado:** hay un período vigente sin vencimiento y no está vencido.
- **Próximo a vencer:** hay un período vigente cuya fecha de aviso ya llegó y no está
  vencido.
- **Dentro de plazo:** tiene SLA y no es ninguno de los anteriores (incluye al ticket
  resuelto o cerrado que no incumplió: su reloj está detenido).
- **Sin SLA:** nunca tuvo períodos, o su prioridad no tiene política (el último período
  está cerrado y el ticket no está resuelto ni cerrado).
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    DateTime,
    and_,
    case,
    exists,
    func,
    literal,
    not_,
    null,
    or_,
    select,
)
from sqlalchemy.orm import aliased

from ..models import Estado, PeriodoSla, Ticket
from .evaluation import SlaSnapshot, SlaStatus
from .periods import STOPPING_STATES


class SlaFilter(StrEnum):
    """Los valores del filtro «SLA» del listado (el parámetro `sla` de la URL)."""

    DENTRO = "dentro"
    PROXIMO = "proximo"
    VENCIDO = "vencido"
    PAUSADO = "pausado"
    SIN_SLA = "sin"
    # No es una opción más de la partición: es la unión de «próximo a vencer» y
    # «vencido» (los dashboards cuentan «SLA en riesgo» y enlazan con ella).
    RIESGO = "riesgo"


# Las cinco opciones que se excluyen entre sí: todo ticket está en exactamente una.
SLA_PARTITION = (
    SlaFilter.DENTRO,
    SlaFilter.PROXIMO,
    SlaFilter.VENCIDO,
    SlaFilter.PAUSADO,
    SlaFilter.SIN_SLA,
)


# Nombre visible de cada opción, en el orden en que se ofrecen.
SLA_FILTER_LABELS = {
    SlaFilter.DENTRO: "Dentro de plazo",
    SlaFilter.PROXIMO: "Próximo a vencer",
    SlaFilter.VENCIDO: "Vencido",
    SlaFilter.RIESGO: "En riesgo (próximo o vencido)",
    SlaFilter.PAUSADO: "Pausado",
    SlaFilter.SIN_SLA: "Sin SLA",
}

_FILTER_OF_STATUS = {
    SlaStatus.DENTRO: SlaFilter.DENTRO,
    SlaStatus.PROXIMO_A_VENCER: SlaFilter.PROXIMO,
    SlaStatus.VENCIDO: SlaFilter.VENCIDO,
    SlaStatus.PAUSADO: SlaFilter.PAUSADO,
}


def filter_of(snapshot: SlaSnapshot | None) -> SlaFilter:
    """La opción del filtro a la que pertenece un ticket según su evaluación en Python
    (`None` es un ticket sin SLA). Es lo que `sla_condition` debe seleccionar."""
    return SlaFilter.SIN_SLA if snapshot is None else _FILTER_OF_STATUS[snapshot.status]


def parse_filter(value: str | None) -> SlaFilter | None:
    """La opción que corresponde al valor de la URL, o None si no es una."""
    try:
        return SlaFilter(value)
    except ValueError:
        return None


# Lo que devuelve `sla_risk`: un ticket vencido o próximo a vencer (o NULL si no está en
# riesgo).
RISK_OVERDUE = "VENCIDO"
RISK_NEAR_DUE = "PROXIMO"


def sla_risk(now: datetime):
    """Expresión SQL sobre `tickets`: `RISK_OVERDUE` si está vencido, `RISK_NEAR_DUE` si está
    próximo a vencer y NULL en cualquier otro caso. Es exactamente lo que dicen
    `sla_condition(VENCIDO)` y `sla_condition(PROXIMO)` (un test lo comprueba), pero cada
    subconsulta se evalúa una sola vez por ticket.

    Contar las dos cosas con dos condiciones repite «tiene SLA» e «incumplió» para cada
    ticket: PostgreSQL no comparte el resultado de una subconsulta entre dos expresiones.
    Medido con unos 17 000 tickets en trabajo, la carga de trabajo pasaba la mitad de su
    tiempo repitiéndolas. Para que se calcule una vez, quien cuenta varias cosas la pone en
    una CTE materializada (ver `workload/queries.py`)."""
    now_value = literal(now, DateTime(timezone=True))

    return case(
        (not_(_has_sla()), null()),
        (_breached(now_value), literal(RISK_OVERDUE)),
        (_warning_reached(now_value), literal(RISK_NEAR_DUE)),
        else_=null(),
    )


def sla_condition(option: SlaFilter, now: datetime):
    """Condición SQL sobre `tickets` con los que están en esa opción del filtro en
    `now`. Se usa dentro de una consulta que ya tiene `tickets` en su `FROM`."""
    if option is SlaFilter.RIESGO:
        # «Vencido o próximo», evaluando cada subconsulta una sola vez.
        return sla_risk(now).is_not(None)

    now_value = literal(now, DateTime(timezone=True))
    breached = _breached(now_value)
    has_sla = _has_sla()
    open_paused = _period_exists(
        lambda p: (p.fecha_fin.is_(None), p.fecha_vencimiento_resolucion.is_(None))
    )
    warning_reached = _warning_reached(now_value)

    if option is SlaFilter.SIN_SLA:
        return not_(has_sla)

    if option is SlaFilter.VENCIDO:
        return and_(has_sla, breached)

    not_breached = and_(has_sla, not_(breached))

    if option is SlaFilter.PAUSADO:
        return and_(not_breached, open_paused)

    if option is SlaFilter.PROXIMO:
        return and_(not_breached, warning_reached)

    return and_(not_breached, not_(open_paused), not_(warning_reached))


def sla_urgency_order():
    """El orden «SLA más urgente»: primero el que vence antes (los ya vencidos, con su
    vencimiento en el pasado, van delante), y al final los que no tienen un reloj en
    marcha (pausados, detenidos o sin SLA). Empata por antigüedad."""
    period = aliased(PeriodoSla)
    due = (
        select(period.fecha_vencimiento_resolucion)
        .where(period.ticket_id == Ticket.id, period.fecha_fin.is_(None))
        .correlate(Ticket)
        .scalar_subquery()
    )

    return (due.asc().nulls_last(), Ticket.fecha_creacion.asc(), Ticket.id.asc())


# --- Piezas ------------------------------------------------------------------------


def _period_exists(conditions):
    """«Existe un período de este ticket que cumple `conditions(período)`»."""
    period = aliased(PeriodoSla)

    return (
        exists()
        .where(period.ticket_id == Ticket.id, *conditions(period))
        .correlate(Ticket)
    )


def _warning_reached(now_value):
    """Hay un período en marcha cuya fecha de aviso ya llegó."""
    return _period_exists(
        lambda p: (
            p.fecha_fin.is_(None),
            p.fecha_vencimiento_resolucion.is_not(None),
            p.fecha_umbral_aviso.is_not(None),
            p.fecha_umbral_aviso <= now_value,
        )
    )


def _has_sla():
    """Tiene SLA: algún período, y o hay uno vigente o el ticket está resuelto o
    cerrado (un último período cerrado en un ticket en trabajo es una prioridad sin
    política)."""
    stopped = Ticket.estado_id.in_(
        select(Estado.id).where(Estado.codigo.in_(sorted(STOPPING_STATES)))
    )
    any_period = _period_exists(lambda p: ())
    open_period = _period_exists(lambda p: (p.fecha_fin.is_(None),))

    return and_(any_period, or_(open_period, stopped))


def _breached(now_value):
    """El ticket incumplió su objetivo de resolución."""
    # Algún período llegó a su vencimiento: hasta su fin, o hasta `now` si sigue vigente.
    due_reached = _period_exists(
        lambda p: (
            p.fecha_vencimiento_resolucion.is_not(None),
            p.fecha_vencimiento_resolucion <= func.coalesce(p.fecha_fin, now_value),
        )
    )

    # El último período no tiene vencimiento (nació pausado, o se cerró estándolo) pero
    # lo consumido antes ya alcanza su objetivo.
    last = aliased(PeriodoSla)
    newest = aliased(PeriodoSla)
    closed = aliased(PeriodoSla)
    newest_id = (
        select(func.max(newest.id))
        .where(newest.ticket_id == Ticket.id)
        .correlate(Ticket)
        .scalar_subquery()
    )
    closed_seconds = (
        select(func.coalesce(func.sum(closed.segundos_consumidos), 0))
        .where(closed.ticket_id == Ticket.id, closed.fecha_fin.is_not(None))
        .correlate(Ticket)
        .scalar_subquery()
    )
    paused_over_consumed = (
        exists()
        .where(
            last.ticket_id == Ticket.id,
            last.id == newest_id,
            last.fecha_vencimiento_resolucion.is_(None),
            closed_seconds >= last.tiempo_objetivo_resolucion_minutos * 60,
        )
        .correlate(Ticket)
    )

    return or_(due_reached, paused_over_consumed)
