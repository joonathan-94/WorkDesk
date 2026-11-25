"""Carga de los tickets de demostración: crear los nuevos y refrescar los existentes."""

from datetime import UTC, datetime, time
from io import BytesIO

from sqlalchemy import delete
from werkzeug.datastructures import FileStorage

from ...extensions import db
from ...formatting import app_zone
from ...models import (
    CommentType,
    MotivoCierre,
    Notificacion,
    StateAction,
    Ticket,
    TicketEvent,
    TicketHistory,
)
from ...sla.rebuild import rebuild_ticket_periods
from ...sla.work_calendar import resolve_work_calendar
from ...tickets.assignment import assign_technician, set_group
from ...tickets.attachments import add_attachments
from ...tickets.comments import add_comment
from ...tickets.editing import change_priority, update_ticket
from ...tickets.lifecycle import change_state
from ...tickets.relations import add_relation, mark_duplicate
from ...tickets.requesters import add_requester, remove_requester
from ...tickets.service import (
    TicketRuleError,
    create_ticket,
)
from ...worktime import (
    DEMO_CALENDAR,
    BusinessClock,
    WorkCalendar,
)
from ..demo_tickets_data import (
    DEMO_TICKETS,
    DemoTicket,
)
from .catalogs import Catalogs
from .common import (
    LIMIT_MARGIN,
    MARKER_KEY,
    SOLICITANTE,
    DemoTicketsError,
    DemoTicketsResult,
)
from .dates import event_ids_after, refresh_dates, write_new_dates
from .validation import validate_demo_tickets

# --- Carga ----------------------------------------------------------------


def seed_demo_tickets(
    now: datetime | None = None,
    tickets: tuple[DemoTicket, ...] | None = None,
    calendar: WorkCalendar | None = None,
) -> DemoTicketsResult:
    """Crea los tickets de demostración que faltan y refresca los que ya existen.

    `now` fija el instante de referencia (los tests lo usan para que las
    fechas sean deterministas), `tickets` permite cargar otra lista (por
    defecto, `DEMO_TICKETS`) y `calendar` otro calendario laboral (por
    defecto, el vigente del sistema: el que guardó el Administrador o, si no
    hay ninguno, `DEMO_CALENDAR`). Hace commit. Si algo falla, no queda nada a
    medias: se revierte todo y se lanza `DemoTicketsError`.
    """
    tickets = DEMO_TICKETS if tickets is None else tickets

    if calendar is None:
        # El calendario vigente: el que guardó el Administrador o, si no hay
        # ninguno, el de por defecto. La lista está escrita para el de por
        # defecto, así que solo con él se comprueba que cada hora cae dentro de
        # la jornada; con uno guardado, las horas se pasan a horario laboral al
        # planificar (`planned_times`).
        resolved = resolve_work_calendar()
        clock = resolved.clock
        validate_demo_tickets(tickets, DEMO_CALENDAR if resolved.is_default else None)
    else:
        validate_demo_tickets(tickets, calendar)
        clock = BusinessClock(calendar, app_zone())

    now = (now or datetime.now(UTC)).astimezone(clock.zone)
    limit = now - LIMIT_MARGIN
    latest = clock.latest_before(limit)

    catalogs = Catalogs.load(tickets)

    created = 0
    refreshed = 0
    new_ticket_ids: list[int] = []

    try:
        for demo in tickets:
            times = planned_times(demo, clock, now, latest)
            ticket = find_demo_ticket(demo.clave)

            if ticket is None:
                create_demo_ticket(demo, catalogs, times)
                new_ticket_ids.append(find_demo_ticket(demo.clave).id)
                created += 1
            else:
                refresh_dates(ticket, demo, times, limit)
                refreshed += 1

        # Los servicios abrieron los períodos de SLA con la hora real de la carga y
        # el historial acaba de moverse a fechas pasadas: se calculan de nuevo sobre
        # esa línea de tiempo, con lo que los tickets quedan en tiempo, por vencer,
        # vencidos o pausados según su historia.
        for demo in tickets:
            rebuild_ticket_periods(find_demo_ticket(demo.clave))

        # Los servicios también avisaron a las personas de cada ticket, con la hora de
        # la carga y sin leer: la historia de un ticket demo es del pasado y no debe
        # llenar a nadie de avisos nuevos. Los avisos de ejemplo tienen su propio
        # comando (`seed-demo-notifications`).
        if new_ticket_ids:
            db.session.execute(
                delete(Notificacion).where(Notificacion.ticket_id.in_(new_ticket_ids))
            )

        db.session.commit()
    except TicketRuleError as error:
        db.session.rollback()
        raise DemoTicketsError(f"No se pudo cargar un ticket demo: {error}") from error
    except Exception:
        db.session.rollback()
        raise

    return DemoTicketsResult(
        created=created,
        refreshed=refreshed,
        warnings=tuple(catalogs.warnings),
    )


def find_demo_ticket(key: str) -> Ticket | None:
    """El ticket que el seed cargó con esa clave, si existe.

    Se busca por la marca del evento de creación, que es inmutable: el ticket
    se reconoce aunque después cambie de título.
    """
    return db.session.scalar(
        db.select(Ticket)
        .join(TicketHistory, TicketHistory.ticket_id == Ticket.id)
        .where(
            TicketHistory.tipo_evento == TicketEvent.TICKET_CREADO.value,
            TicketHistory.contexto[MARKER_KEY].as_string() == key,
        )
        .limit(1)
    )


# --- Fechas planificadas --------------------------------------------------


def planned_times(
    demo: DemoTicket, clock: BusinessClock, now: datetime, latest: datetime
) -> list[datetime]:
    """Momentos de la historia: [creación, ajuste 1, ajuste 2, ...].

    Depende solo de los datos, del calendario y del día de la carga, así que
    dos ejecuciones el mismo día producen exactamente lo mismo. Todo cae en
    tiempo laboral y nunca después de `latest` (el último momento laboral que
    ya pasó).

    - Creación: `hace_dias` días laborales antes del día laboral de hoy (si hoy
      no es laboral, se cuenta desde el día laboral anterior), a la hora
      indicada.
    - Cada ajuste: `despues_horas` horas laborales después del paso anterior.
    """
    hour, minute = (int(part) for part in demo.hora.split(":"))
    day = clock.workdays_before(now.date(), demo.hace_dias)
    # Con un calendario de franjas la hora pedida puede caer en una pausa o fuera
    # de horario: se pasa al siguiente momento en que se trabaja (con el
    # calendario por defecto ya lo es y no se mueve).
    created = clock.into_business(clock.at(day, time(hour, minute)))
    times = [min(created, latest)]

    for adjustment in demo.ajustes:
        moment = clock.add_hours(times[-1], adjustment.despues_horas)
        times.append(max(times[-1], min(moment, latest)))

    return times


# --- Crear ----------------------------------------------------------------


def create_demo_ticket(demo: DemoTicket, catalogs: Catalogs, times: list[datetime]) -> None:
    creator = catalogs.users[demo.creado_por]

    if creator.rol.codigo == SOLICITANTE:
        requesters = [creator]
    else:
        requesters = [catalogs.users[username] for username in demo.solicitantes]

    location = catalogs.location(demo.ubicacion)

    ticket = create_ticket(
        actor=creator,
        title=demo.titulo,
        description=demo.descripcion,
        category_id=catalogs.category(demo.categoria, fallback_ok=True).id,
        priority_id=catalogs.priorities[demo.prioridad].id,
        location_id=None if location is None else location.id,
        requester_ids=[requester.id for requester in requesters],
    )

    steps: list[tuple[int, list[int]]] = []

    event_ids = event_ids_after(ticket.id, 0)
    steps.append((0, event_ids))
    last_event_id = event_ids[-1]
    modified_at = None

    for step, adjustment in enumerate(demo.ajustes, start=1):
        version_before = ticket.version
        apply_adjustment(ticket, adjustment, catalogs)

        event_ids = event_ids_after(ticket.id, last_event_id)
        if event_ids:
            steps.append((step, event_ids))
            last_event_id = event_ids[-1]

        # Como en la aplicación, solo lo que sube la versión del ticket cuenta
        # como una modificación (y mueve "Actualizado"): agregar o retirar
        # solicitantes, o asignar a un técnico más, no lo hacen.
        if ticket.version != version_before:
            modified_at = times[step]

    write_new_dates(ticket, demo.clave, steps, times, modified_at)


def apply_adjustment(ticket: Ticket, adjustment, catalogs: Catalogs) -> None:
    """Ejecuta un paso de ajuste con los servicios reales.

    El orden es el de quien trabaja un ticket: corregir datos, reclasificar,
    asignar, cambiar solicitantes, relacionar, responder y, al final, cambiar el
    estado. Cada paso solo actúa si el ajuste lo trae."""
    actor = catalogs.users[adjustment.actor]

    _edit_data(ticket, adjustment, actor, catalogs)
    _change_priority(ticket, adjustment, actor, catalogs)
    _change_group(ticket, adjustment, actor, catalogs)
    _assign(ticket, adjustment, actor, catalogs)
    _change_requesters(ticket, adjustment, actor, catalogs)
    _relate(ticket, adjustment, actor)

    public, note = _comment(ticket, adjustment, actor)
    _attach(ticket, adjustment, actor, public or note)

    _mark_duplicate(ticket, adjustment, actor)
    _change_state(ticket, adjustment, actor, catalogs)


def _edit_data(ticket, adjustment, actor, catalogs) -> None:
    fields = (adjustment.titulo, adjustment.descripcion, adjustment.categoria)

    if all(value is None for value in fields):
        return

    category_id = ticket.categoria_id

    if adjustment.categoria is not None:
        category = catalogs.category(adjustment.categoria, fallback_ok=False)
        if category is not None:
            category_id = category.id

    update_ticket(
        ticket,
        actor=actor,
        expected_version=ticket.version,
        title=adjustment.titulo or ticket.titulo,
        description=adjustment.descripcion or ticket.descripcion,
        category_id=category_id,
        location_id=ticket.ubicacion_id,
    )


def _change_priority(ticket, adjustment, actor, catalogs) -> None:
    if adjustment.prioridad is None:
        return

    change_priority(
        ticket,
        actor=actor,
        expected_version=ticket.version,
        priority_id=catalogs.priorities[adjustment.prioridad].id,
        reason=adjustment.motivo,
    )


def _change_group(ticket, adjustment, actor, catalogs) -> None:
    if adjustment.grupo is None:
        return

    group = catalogs.group(adjustment.grupo)

    # Si el grupo falta o está desactivado, el ticket queda sin grupo (y se avisó).
    if group is not None:
        set_group(ticket, group.id, actor=actor, expected_version=ticket.version)


def _assign(ticket, adjustment, actor, catalogs) -> None:
    if adjustment.asignar is None:
        return

    assign_technician(ticket, catalogs.users[adjustment.asignar].id, actor=actor)


def _change_requesters(ticket, adjustment, actor, catalogs) -> None:
    # Primero se retira y después se agrega (en ese orden se puede cambiar a
    # una persona por otra en un mismo paso).
    if adjustment.retirar_solicitante is not None:
        retired = catalogs.users[adjustment.retirar_solicitante]
        participation = next(
            link
            for link in ticket.solicitantes_vigentes
            if link.solicitante_id == retired.id
        )

        remove_requester(
            ticket,
            participation.id,
            actor=actor,
            reason=adjustment.motivo_retiro,
        )

    if adjustment.agregar_solicitante is not None:
        add_requester(
            ticket,
            catalogs.users[adjustment.agregar_solicitante].id,
            actor=actor,
        )


def _relate(ticket, adjustment, actor) -> None:
    if adjustment.relacionar is None:
        return

    other = find_demo_ticket(adjustment.relacionar)

    if other is not None:
        add_relation(ticket, other.public_id, actor=actor)


def _comment(ticket, adjustment, actor):
    """El comentario público y la nota interna (en ese orden) antes del cambio de
    estado, como lo haría quien responde y luego cambia el ticket. Devuelve los dos
    (o None)."""
    public = note = None

    if adjustment.comentario is not None:
        public = add_comment(
            ticket,
            actor=actor,
            content=adjustment.comentario,
            kind=CommentType.PUBLICO,
        )

    if adjustment.nota_interna is not None:
        note = add_comment(
            ticket,
            actor=actor,
            content=adjustment.nota_interna,
            kind=CommentType.INTERNO,
        )

    return public, note


def _attach(ticket, adjustment, actor, comment) -> None:
    """El archivo cuelga del comentario público del paso; si no hay, de la nota; y
    si tampoco, del ticket. Se guarda de verdad con el servicio."""
    if adjustment.adjunto is None:
        return

    file_name, file_text = adjustment.adjunto

    add_attachments(
        ticket,
        actor=actor,
        uploads=[
            FileStorage(
                stream=BytesIO(file_text.encode("utf-8")),
                filename=file_name,
            )
        ],
        comment=comment,
    )


def _mark_duplicate(ticket, adjustment, actor) -> None:
    if adjustment.duplicado_de is None:
        return

    principal = find_demo_ticket(adjustment.duplicado_de)

    if principal is not None:
        mark_duplicate(
            ticket,
            principal.public_id,
            actor=actor,
            expected_version=ticket.version,
        )


def _change_state(ticket, adjustment, actor, catalogs) -> None:
    if adjustment.estado is None:
        return

    action = StateAction(adjustment.estado)

    if action is StateAction.PONER_EN_ESPERA:
        reason = catalogs.wait_reason(adjustment.motivo_espera)

        change_state(
            ticket,
            actor=actor,
            action=action,
            expected_version=ticket.version,
            wait_reason_id=None if reason is None else reason.id,
            # El texto libre exige un motivo que lo admita: sin motivo
            # (porque faltaba en el catálogo) no se guarda.
            text=None if reason is None else adjustment.texto,
        )
        return

    # Resolver, cerrar, confirmar, rechazar y reabrir: el texto es la explicación
    # de la solución, el motivo de un rechazo o de un cierre, según la acción. Un
    # motivo de cierre inexistente o desactivado se ignora y el servicio usa el de
    # por defecto.
    change_state(
        ticket,
        actor=actor,
        action=action,
        expected_version=ticket.version,
        close_reason_id=_active_close_reason_id(adjustment.motivo_cierre),
        text=adjustment.texto,
    )


def _active_close_reason_id(code: str | None) -> int | None:
    if code is None:
        return None

    return db.session.scalar(
        db.select(MotivoCierre.id).where(
            MotivoCierre.codigo == code,
            MotivoCierre.activo.is_(True),
        )
    )
