"""Escritura y refresco de las fechas de los tickets de demostración.

Los servicios sellan cada fila con la hora real de la carga. Aquí se reescriben,
con un `UPDATE` directo, solo en las filas que el propio seed creó:

- `write_new_dates`: al crear un ticket, cada fila toma la fecha de su evento.
- `refresh_dates`: al volver a ejecutar el seed, todo se desplaza al nuevo día.

Las dos se apoyan en la misma idea: cada fila «sigue» al evento del historial
que la originó (su `contexto` guarda el id de la fila), así que basta saber qué
momento le toca a cada evento para saber qué fecha lleva cada fila.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import update

from ...extensions import db
from ...models import (
    Attachment,
    Comment,
    Ticket,
    TicketEvent,
    TicketHistory,
    TicketRelation,
    TicketRequester,
    TicketTechnician,
    Validation,
)
from ..demo_tickets_data import DemoTicket
from .common import MARKER_KEY, MARKER_STEP, is_own

# Fechas del propio ticket que siguen al último evento de ese tipo, mientras el
# ticket siga resuelto o cerrado (una reapertura ya las limpió).
_STATE_DATES = (
    ("fecha_resolucion", TicketEvent.TICKET_RESUELTO),
    ("fecha_cierre", TicketEvent.TICKET_CERRADO),
)


def event_ids_after(ticket_id: int, after_id: int) -> list[int]:
    return list(
        db.session.scalars(
            db.select(TicketHistory.id)
            .where(TicketHistory.ticket_id == ticket_id, TicketHistory.id > after_id)
            .order_by(TicketHistory.id)
        )
    )


# --- Piezas comunes ---------------------------------------------------------


def _dates_by_entity(
    events, time_of: dict[int, datetime], context_key: str, event_type=None
) -> dict[int, datetime]:
    """{id de la fila: momento de su evento} para los eventos cuyo contexto trae
    `context_key` (y, si se indica, solo los de ese tipo). Si una fila tiene varios
    eventos, vale el último."""
    dates: dict[int, datetime] = {}

    for event in events:
        entity_id = (event.contexto or {}).get(context_key)

        if entity_id is None:
            continue

        if event_type is not None and event.tipo_evento != event_type.value:
            continue

        dates[entity_id] = time_of[event.id]

    return dates


def _last_event_time(events, time_of, event_type) -> datetime | None:
    moments = [time_of[e.id] for e in events if e.tipo_evento == event_type.value]

    return moments[-1] if moments else None


def _set_dates(table, column: str, dates: dict[int, datetime]) -> None:
    """Escribe `column` en cada fila de `dates` ({id: fecha})."""
    for row_id, moment in dates.items():
        db.session.execute(
            update(table).where(table.c.id == row_id).values(**{column: moment})
        )


def _write_ticket_row(ticket, events, time_of, created_at, modified_at) -> None:
    """Creación y modificación del ticket y, si sigue resuelto o cerrado, la fecha
    de resolución y de cierre (las del último evento de ese tipo)."""
    dates = {"fecha_creacion": created_at, "fecha_modificacion": modified_at}

    for column, event_type in _STATE_DATES:
        moment = _last_event_time(events, time_of, event_type)

        if getattr(ticket, column) is not None and moment is not None:
            dates[column] = moment

    tickets = Ticket.__table__
    db.session.execute(update(tickets).where(tickets.c.id == ticket.id).values(**dates))


def _follow_events(table, stored, unconditional, conditional) -> None:
    """Hace que cada fila guardada siga a sus eventos.

    `unconditional` y `conditional` son {columna: {id de la fila: fecha}}. Las
    primeras se escriben siempre que la fila tenga ese evento; las segundas solo
    si la fila ya tiene un valor en esa columna (una edición que no existe, o una
    eliminación que nunca ocurrió, no se inventa)."""
    for row in stored:
        values = {
            column: dates[row.id]
            for column, dates in unconditional.items()
            if row.id in dates
        }

        for column, dates in conditional.items():
            if getattr(row, column) is not None and row.id in dates:
                values[column] = dates[row.id]

        if values:
            db.session.execute(
                update(table).where(table.c.id == row.id).values(**values)
            )


# --- Al crear el ticket -----------------------------------------------------


def write_new_dates(
    ticket: Ticket,
    key: str,
    steps: list[tuple[int, list[int]]],
    times: list[datetime],
    modified_at: datetime | None,
) -> None:
    """Fecha y marca de las filas que este proceso acaba de crear.

    `steps` es [(número de paso, ids de los eventos que ese paso generó)] y
    `times[paso]` el momento planificado de cada paso."""
    history = TicketHistory.__table__
    step_of = {event_id: step for step, ids in steps for event_id in ids}
    time_of = {event_id: times[step] for event_id, step in step_of.items()}

    # Los ids crecen con los pasos: ordenar por id es ordenar por paso.
    events = db.session.execute(
        db.select(history.c.id, history.c.tipo_evento, history.c.contexto)
        .where(history.c.id.in_(list(step_of)))
        .order_by(history.c.id)
    ).all()

    _write_ticket_row(ticket, events, time_of, times[0], modified_at)
    _set_dates(
        Validation.__table__,
        "fecha_validacion",
        _dates_by_entity(events, time_of, "validacion_id"),
    )
    _write_new_requester_dates(ticket, events, time_of, times[0])

    # Un comentario o nota, un archivo y una asignación nacen en el momento de su
    # evento.
    _set_dates(
        Comment.__table__,
        "fecha_creacion",
        _dates_by_entity(events, time_of, "comentario_id"),
    )
    _set_dates(
        Attachment.__table__,
        "fecha_subida",
        _dates_by_entity(events, time_of, "archivo_id"),
    )
    _set_dates(
        TicketTechnician.__table__,
        "fecha_asignacion",
        _dates_by_entity(events, time_of, "asignacion_id"),
    )

    # Una relación nace (y, si se quita, se desactiva) en el momento de su evento.
    # El cierre de un duplicado lleva el mismo `relacion_id`, pero su fecha no es la
    # de la relación: solo cuentan los eventos de la relación.
    relations = TicketRelation.__table__
    _set_dates(
        relations,
        "fecha_creacion",
        _dates_by_entity(events, time_of, "relacion_id", TicketEvent.RELACION_AGREGADA),
    )
    _set_dates(
        relations,
        "fecha_desactivacion",
        _dates_by_entity(
            events, time_of, "relacion_id", TicketEvent.RELACION_ELIMINADA
        ),
    )

    _stamp_events(events, time_of, step_of, key)


def _write_new_requester_dates(ticket, events, time_of, created_at) -> None:
    """Los solicitantes de la creación se asocian cuando nace el ticket; los que se
    agregan o retiran después, en el momento de su evento. Una sola actualización
    por fila, para que el retiro nunca preceda a la asociación."""
    requesters = TicketRequester.__table__
    links: dict[int, dict] = {
        link_id: {"fecha_asociacion": created_at}
        for link_id in db.session.scalars(
            db.select(requesters.c.id).where(requesters.c.ticket_id == ticket.id)
        )
    }

    for column, event_type in (
        ("fecha_asociacion", TicketEvent.SOLICITANTE_AGREGADO),
        ("fecha_retiro", TicketEvent.SOLICITANTE_RETIRADO),
    ):
        for link_id, moment in _dates_by_entity(
            events, time_of, "participacion_id", event_type
        ).items():
            links[link_id][column] = moment

    for link_id, values in links.items():
        db.session.execute(
            update(requesters).where(requesters.c.id == link_id).values(**values)
        )


def _stamp_events(events, time_of, step_of, key: str) -> None:
    """Fecha de cada evento y la marca del seed en su contexto."""
    history = TicketHistory.__table__

    for event in events:
        marker = {MARKER_KEY: key, MARKER_STEP: step_of[event.id]}

        db.session.execute(
            update(history)
            .where(history.c.id == event.id)
            .values(
                fecha_hora=time_of[event.id],
                contexto={**(event.contexto or {}), **marker},
            )
        )


# --- Al volver a ejecutar el seed ---------------------------------------------


@dataclass(frozen=True)
class _Plan:
    """Cómo se desplaza la historia de un ticket ya cargado."""

    new_time: dict[int, datetime]  # nuevo momento de cada evento
    by_old_time: dict[datetime, datetime]  # momento antiguo -> nuevo
    shift: timedelta  # cuánto se movió el último evento del seed
    new_last_own: datetime  # nuevo momento del último evento del seed
    old_created: datetime
    new_created: datetime
    limit: datetime  # nada queda después de este instante

    def clamp(self, moment: datetime) -> datetime:
        return min(max(moment, self.new_created), self.limit)


def refresh_dates(
    ticket: Ticket, demo: DemoTicket, times: list[datetime], limit: datetime
) -> None:
    """Reescribe las fechas de un ticket ya cargado, relativas al día de hoy.

    - Los eventos del seed (con su marca) vuelven a su momento planificado.
    - Los eventos que no son del seed (ediciones hechas a mano después) se
      desplazan lo mismo que el último evento del seed, para que sigan después
      de él y nunca queden en el futuro.
    - La fecha de modificación acompaña al evento que la originó. Los
      solicitantes de la creación se asocian en la nueva fecha de creación y
      los que se agregaron o retiraron después siguen a sus eventos.
    - Los comentarios y notas siguen a sus eventos (publicación, edición y
      eliminación).

    No toca el contenido del ticket ni crea ningún evento.
    """
    db.session.refresh(ticket)

    history = TicketHistory.__table__
    events = db.session.execute(
        db.select(
            history.c.id,
            history.c.fecha_hora,
            history.c.contexto,
            history.c.tipo_evento,
        )
        .where(history.c.ticket_id == ticket.id)
        .order_by(history.c.id)
    ).all()

    plan = _plan_refresh(ticket, demo, times, limit, events)

    _refresh_ticket_row(ticket, events, plan)
    _refresh_events(events, plan)
    _refresh_assignments(ticket, events, plan)
    _refresh_requesters(ticket, events, plan)
    _refresh_comments(ticket, events, plan)
    _refresh_relations(events, plan)
    _refresh_attachments(ticket, events, plan)


def _plan_refresh(ticket, demo, times, limit, events) -> _Plan:
    last_step = len(demo.ajustes)
    new_time: dict[int, datetime] = {}

    for event in events:
        if is_own(event.contexto, demo.clave):
            step = min(int(event.contexto.get(MARKER_STEP, 0)), last_step)
            new_time[event.id] = times[step]

    old_last_own = max(e.fecha_hora for e in events if e.id in new_time)
    new_last_own = max(new_time.values())
    shift = new_last_own - old_last_own

    running = new_last_own
    for event in events:
        if event.id not in new_time:
            running = min(max(event.fecha_hora + shift, running), limit)
            new_time[event.id] = running

    return _Plan(
        new_time=new_time,
        by_old_time={event.fecha_hora: new_time[event.id] for event in events},
        shift=shift,
        new_last_own=new_last_own,
        old_created=ticket.fecha_creacion,
        new_created=times[0],
        limit=limit,
    )


def _refresh_ticket_row(ticket, events, plan: _Plan) -> None:
    old_modified = ticket.fecha_modificacion

    # La fecha de modificación acompaña al evento que la originó.
    if old_modified is None:
        new_modified = None
    else:
        new_modified = plan.by_old_time.get(old_modified) or min(
            max(old_modified + plan.shift, plan.new_last_own), plan.limit
        )

    _write_ticket_row(ticket, events, plan.new_time, plan.new_created, new_modified)


def _refresh_events(events, plan: _Plan) -> None:
    """La fecha de cada evento y la de cada validación (la de su evento)."""
    history = TicketHistory.__table__

    for event in events:
        db.session.execute(
            update(history)
            .where(history.c.id == event.id)
            .values(fecha_hora=plan.new_time[event.id])
        )

    _set_dates(
        Validation.__table__,
        "fecha_validacion",
        _dates_by_entity(events, plan.new_time, "validacion_id"),
    )


def _refresh_assignments(ticket, events, plan: _Plan) -> None:
    """Las asignaciones siguen a sus eventos. Una sola actualización por fila,
    para que la desasignación nunca preceda a la asignación.

    Una asignación que no tiene su propio evento también debe seguir al ticket: un
    escalamiento hecho a mano cierra las asignaciones y crea la nueva en la misma
    transacción que su evento, así que sus fechas coinciden con la hora de ese
    evento y se mueven con él. Si no coinciden con ninguno, se conservan. El cierre
    nunca queda antes de la asignación (la base de datos lo exige)."""
    technicians = TicketTechnician.__table__
    assigned_at = _dates_by_entity(
        events, plan.new_time, "asignacion_id", TicketEvent.TECNICO_ASIGNADO
    )
    unassigned_at = _dates_by_entity(
        events, plan.new_time, "asignacion_id", TicketEvent.TECNICO_DESASIGNADO
    )

    stored = db.session.execute(
        db.select(
            technicians.c.id,
            technicians.c.fecha_asignacion,
            technicians.c.fecha_desasignacion,
        ).where(technicians.c.ticket_id == ticket.id)
    ).all()

    for row in stored:
        assigned = assigned_at.get(row.id) or plan.by_old_time.get(
            row.fecha_asignacion, row.fecha_asignacion
        )
        values = {"fecha_asignacion": assigned}

        if row.fecha_desasignacion is not None:
            closed = unassigned_at.get(row.id) or plan.by_old_time.get(
                row.fecha_desasignacion, row.fecha_desasignacion
            )
            values["fecha_desasignacion"] = max(assigned, closed)

        db.session.execute(
            update(technicians).where(technicians.c.id == row.id).values(**values)
        )


def _refresh_requesters(ticket, events, plan: _Plan) -> None:
    """Los solicitantes que se agregaron o retiraron después de crear el ticket
    siguen a sus eventos (tanto los del seed como los hechos a mano); los demás se
    desplazan con el ticket."""
    requesters = TicketRequester.__table__
    added_at = _dates_by_entity(
        events, plan.new_time, "participacion_id", TicketEvent.SOLICITANTE_AGREGADO
    )
    retired_at = _dates_by_entity(
        events, plan.new_time, "participacion_id", TicketEvent.SOLICITANTE_RETIRADO
    )
    delta = plan.new_created - plan.old_created

    links = db.session.execute(
        db.select(
            requesters.c.id, requesters.c.fecha_asociacion, requesters.c.fecha_retiro
        ).where(requesters.c.ticket_id == ticket.id)
    ).all()

    for link in links:
        if link.id in added_at:
            associated = added_at[link.id]
        elif link.fecha_asociacion == plan.old_created:
            associated = plan.new_created
        else:
            associated = plan.clamp(link.fecha_asociacion + delta)

        if link.fecha_retiro is None:
            retired = None
        elif link.id in retired_at:
            retired = max(associated, retired_at[link.id])
        else:
            retired = max(associated, plan.clamp(link.fecha_retiro + delta))

        db.session.execute(
            update(requesters)
            .where(requesters.c.id == link.id)
            .values(fecha_asociacion=associated, fecha_retiro=retired)
        )


def _refresh_comments(ticket, events, plan: _Plan) -> None:
    """Los comentarios y notas siguen a sus eventos (los del seed y los hechos a
    mano): la fecha de publicación, la de la última edición y la de la eliminación.
    Lo que no tiene evento se conserva."""
    comments = Comment.__table__
    stored = db.session.execute(
        db.select(
            comments.c.id, comments.c.fecha_modificacion, comments.c.fecha_eliminacion
        ).where(comments.c.ticket_id == ticket.id)
    ).all()

    def by(event_type):
        return _dates_by_entity(events, plan.new_time, "comentario_id", event_type)

    _follow_events(
        comments,
        stored,
        {"fecha_creacion": by(TicketEvent.COMENTARIO_AGREGADO)},
        {
            "fecha_modificacion": by(TicketEvent.COMENTARIO_EDITADO),
            "fecha_eliminacion": by(TicketEvent.COMENTARIO_ELIMINADO),
        },
    )


def _refresh_relations(events, plan: _Plan) -> None:
    """Las relaciones siguen a los eventos de relación: la fecha de creación y, si
    se quitó, la de desactivación (los del seed y los hechos a mano). El evento de
    cierre de un duplicado lleva el mismo `relacion_id`, pero no es el de la
    relación."""
    relations = TicketRelation.__table__

    def by(event_type):
        return _dates_by_entity(events, plan.new_time, "relacion_id", event_type)

    related_at = by(TicketEvent.RELACION_AGREGADA)
    unrelated_at = by(TicketEvent.RELACION_ELIMINADA)
    stored = db.session.execute(
        db.select(relations.c.id, relations.c.fecha_desactivacion).where(
            relations.c.id.in_([*related_at, *unrelated_at])
        )
    ).all()

    _follow_events(
        relations,
        stored,
        {"fecha_creacion": related_at},
        {"fecha_desactivacion": unrelated_at},
    )


def _refresh_attachments(ticket, events, plan: _Plan) -> None:
    """Los adjuntos siguen a sus eventos: la fecha de subida y, si se eliminó, la
    de eliminación."""
    files = Attachment.__table__
    stored = db.session.execute(
        db.select(files.c.id, files.c.fecha_eliminacion).where(
            files.c.ticket_id == ticket.id
        )
    ).all()

    def by(event_type):
        return _dates_by_entity(events, plan.new_time, "archivo_id", event_type)

    _follow_events(
        files,
        stored,
        {"fecha_subida": by(TicketEvent.ARCHIVO_ADJUNTADO)},
        {"fecha_eliminacion": by(TicketEvent.ARCHIVO_ELIMINADO)},
    )
