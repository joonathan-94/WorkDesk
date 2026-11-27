"""La exportación del listado de tickets (RF-099 a RF-101).

Las filas salen de `listing_statement`, la consulta del propio listado: la misma
visibilidad, los mismos filtros, la misma pestaña y el mismo orden. Las columnas son las
que esa persona ve en el listado: el personal tiene además los solicitantes, los técnicos,
el grupo y el SLA; el Solicitante no ve nada de eso (RN-169) ni tampoco aquí. La
descripción no se exporta: el listado tampoco la muestra y puede traer datos personales.

Se lee por tramos de `CHUNK` tickets, con sus solicitantes y técnicos cargados por lote,
así que el número de consultas crece con los tramos y no con las filas.

**El SLA se decide en SQL,** de todos los tickets a la vez (`sla_condition` en un `CASE`
con las opciones del filtro), y no con `evaluate_tickets_sla`, que calcula el tiempo
laboral en Python ticket a ticket. Medido con unos 20 000 tickets: eran 15 de los 21
segundos de la exportación, y ahora toda la exportación tarda unos 4. Las dos formas son
equivalentes (lo comprueba `test_sla_indicators`, y aquí `test_exports`), y es además lo
que filtra el listado: la columna dice lo mismo que el filtro «SLA».
"""

from sqlalchemy import case
from sqlalchemy.orm import joinedload

from ..exports import Table
from ..extensions import db
from ..models import Estado, Ticket
from ..security import STAFF_ROLES, has_any_role
from ..sla import periods as sla_periods
from ..sla.queries import SLA_FILTER_LABELS, SlaFilter, sla_condition
from .queries import (
    TicketFilters,
    count_tickets_by_tab,
    listing_conditions,
    listing_statement,
    tab_conditions,
)

CHUNK = 500

_COMMON_HEADERS = ("Número", "Título", "Estado", "Prioridad", "Categoría", "Ubicación")
_STAFF_HEADERS = ("Solicitantes", "Técnicos", "Grupo")
_DATE_HEADERS = ("Creado", "Actualizado", "Resuelto", "Cerrado", "Motivo de cierre")


def count_ticket_rows(user, filters: TicketFilters, tab: str, now) -> int:
    """Cuántas filas tendría la exportación: el contador de la pestaña del listado."""
    return count_tickets_by_tab(user, filters, now)[tab]


def ticket_table(user, filters: TicketFilters, *, tab: str, sort: str, now) -> Table:
    staff = has_any_role(user, *STAFF_ROLES)
    show_sla = staff and sla_periods.sla_enabled()
    headers = list(_COMMON_HEADERS)

    if staff:
        headers += _STAFF_HEADERS

    if show_sla:
        headers.append("SLA")

    headers += _DATE_HEADERS

    statement = listing_statement(user, filters, tab=tab, sort=sort, now=now).options(
        joinedload(Ticket.ubicacion), joinedload(Ticket.motivo_cierre)
    )

    slas = _sla_labels(user, filters, tab, now) if show_sla else {}

    return Table("Tickets", headers, _rows(statement, staff, show_sla, slas))


def _rows(statement, staff: bool, show_sla: bool, slas: dict[int, str]):
    offset = 0

    while True:
        tickets = list(db.session.scalars(statement.limit(CHUNK).offset(offset)).unique())

        if not tickets:
            return

        for ticket in tickets:
            yield _row(ticket, staff, show_sla, slas)

        if len(tickets) < CHUNK:
            return

        offset += CHUNK


# El orden en que el `CASE` pregunta: las opciones se excluyen entre sí, así que el orden no
# cambia el resultado, pero PostgreSQL deja de evaluar en la primera que se cumple (las más
# baratas o las más frecuentes primero).
_SLA_ORDER = (SlaFilter.SIN_SLA, SlaFilter.VENCIDO, SlaFilter.PAUSADO, SlaFilter.PROXIMO, SlaFilter.DENTRO)


def _sla_labels(user, filters: TicketFilters, tab: str, now) -> dict[int, str]:
    """La etiqueta del SLA de todos los tickets de la exportación, en una sola consulta con
    las mismas condiciones del listado. Medido con unos 20 000 tickets: preguntarlo por
    tramos de 500 ids costaba 3,1 s; de una vez, 0,13 s."""
    status = case(
        *((sla_condition(option, now), option.value) for option in _SLA_ORDER),
        else_=None,
    )

    return {
        row.id: SLA_FILTER_LABELS[SlaFilter(row.sla)]
        for row in db.session.execute(
            db.select(Ticket.id, status.label("sla"))
            .join(Estado, Estado.id == Ticket.estado_id)
            .where(*listing_conditions(user, filters, now), *tab_conditions(tab))
        )
    }


def _names(people) -> str:
    return ", ".join(f"{person.nombre} {person.apellido}" for person in people)


def _row(ticket: Ticket, staff: bool, show_sla: bool, slas: dict) -> list:
    row = [
        int(ticket.public_id),
        ticket.titulo,
        ticket.estado.nombre_visible,
        ticket.prioridad.nombre,
        ticket.categoria.nombre,
        ticket.ubicacion.nombre if ticket.ubicacion else None,
    ]

    if staff:
        row += [
            _names(link.solicitante for link in ticket.solicitantes_vigentes),
            _names(link.tecnico for link in ticket.tecnicos_vigentes),
            ticket.grupo.nombre if ticket.grupo else None,
        ]

    if show_sla:
        row.append(slas[ticket.id])

    return row + [
        ticket.fecha_creacion,
        ticket.fecha_actualizacion,
        ticket.fecha_resolucion,
        ticket.fecha_cierre,
        ticket.motivo_cierre.nombre if ticket.motivo_cierre else None,
    ]
