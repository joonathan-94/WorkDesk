"""Ayudantes compartidos por los tests del seed de tickets de demostración
(`tests/test_seed_demo_tickets_*.py`): lectura del historial y de las filas que el
seed escribe, instantáneas de fechas y de contenido, y cómo ejecutar el comando.
"""

import re
from datetime import time, timedelta

from sqlalchemy import update

from src.workdesk.extensions import db
from src.workdesk.models import (
    Attachment,
    Comment,
    Ticket,
    TicketEvent,
    TicketHistory,
    TicketRelation,
    TicketRequester,
    TicketTechnician,
    User,
    Validation,
)
from src.workdesk.seeds.demo_tickets_data import (
    DEMO_TICKETS,
)
from src.workdesk.tickets.editing import update_ticket
from tests.demo_data import DEMO_PASSWORD, ROLES, ZONE


def run_command(app):
    return app.test_cli_runner().invoke(args=["seed-demo-tickets"])


def by_clave(key):
    """El ticket demo con esa clave, aunque después le hayan cambiado el título."""
    return db.session.scalar(
        db.select(Ticket)
        .join(TicketHistory, TicketHistory.ticket_id == Ticket.id)
        .where(
            TicketHistory.tipo_evento == TicketEvent.TICKET_CREADO.value,
            TicketHistory.contexto["demo_clave"].as_string() == key,
        )
    )


def user(username):
    return db.session.scalar(db.select(User).where(User.username == username))


def history_of(ticket):
    return list(
        db.session.scalars(
            db.select(TicketHistory)
            .where(TicketHistory.ticket_id == ticket.id)
            .order_by(TicketHistory.id)
        )
    )


def validations_of(ticket):
    return list(
        db.session.scalars(
            db.select(Validation)
            .where(Validation.ticket_id == ticket.id)
            .order_by(Validation.id)
        )
    )


def lifecycle_of(ticket):
    return [e for e in history_of(ticket) if e.tipo_evento in LIFECYCLE_EVENTS]


def relations_of(ticket):
    return list(
        db.session.scalars(
            db.select(TicketRelation)
            .where(
                db.or_(
                    TicketRelation.ticket_origen_id == ticket.id,
                    TicketRelation.ticket_destino_id == ticket.id,
                )
            )
            .order_by(TicketRelation.id)
        )
    )


def requesters_of(ticket):
    return list(
        db.session.scalars(
            db.select(TicketRequester)
            .where(TicketRequester.ticket_id == ticket.id)
            .order_by(TicketRequester.id)
        )
    )


# Estado al que lleva cada acción de estado implementada (independiente de la
# tabla de transiciones, para no comprobar el seed con sus propios datos).
ACTION_DESTINATION = {
    "INICIAR": "EN_PROGRESO",
    "PONER_EN_ESPERA": "EN_ESPERA",
    "REACTIVAR": "EN_PROGRESO",
    "RESOLVER": "RESUELTO",
    "CIERRE_DIRECTO": "CERRADO",
    "CONFIRMAR": "CERRADO",
    "RECHAZAR": "EN_PROGRESO",
    "CIERRE_EXCEPCIONAL": "CERRADO",
    "REABRIR": "EN_PROGRESO",
}

# Eventos que dejan la resolución, el cierre y la reapertura (y los cambios de
# estado operativos).
LIFECYCLE_EVENTS = (
    "ESTADO_CAMBIADO",
    "TICKET_RESUELTO",
    "VALIDACION_ACEPTADA",
    "VALIDACION_RECHAZADA",
    "TICKET_CERRADO",
    "TICKET_REABIERTO",
)


def final_state(demo) -> str:
    """Estado en que debe quedar un ticket demo: el del último cambio de
    estado de sus ajustes, o Nuevo si no tiene ninguno."""
    state = "NUEVO"

    for adjustment in demo.ajustes:
        # Asignar un técnico a un ticket Nuevo lo pasa a Asignado.
        if adjustment.asignar is not None and state == "NUEVO":
            state = "ASIGNADO"

        if adjustment.estado is not None:
            state = ACTION_DESTINATION[adjustment.estado]

        # Marcar un duplicado cierra el ticket.
        if adjustment.duplicado_de is not None:
            state = "CERRADO"

    return state


def initial_requesters(demo) -> list[str]:
    """Solicitantes con los que nace un ticket demo: quien crea siendo
    Solicitante es su propio solicitante; el personal indica a quiénes."""
    if ROLES[demo.creado_por] == "SOLICITANTE":
        return [demo.creado_por]

    return list(demo.solicitantes)


def final_requesters(demo) -> list[str]:
    """Solicitantes vigentes de un ticket demo tras todos sus ajustes."""
    current = initial_requesters(demo)

    for step in demo.ajustes:
        if step.retirar_solicitante is not None:
            current.remove(step.retirar_solicitante)

        if step.agregar_solicitante is not None:
            current.append(step.agregar_solicitante)

    return current


def comments_of(ticket):
    return list(
        db.session.scalars(
            db.select(Comment)
            .where(Comment.ticket_id == ticket.id)
            .order_by(Comment.id)
        )
    )


def attachments_of(ticket):
    return list(
        db.session.scalars(
            db.select(Attachment)
            .where(Attachment.ticket_id == ticket.id)
            .order_by(Attachment.id)
        )
    )


def assignments_of(ticket):
    return list(
        db.session.scalars(
            db.select(TicketTechnician)
            .where(TicketTechnician.ticket_id == ticket.id)
            .order_by(TicketTechnician.id)
        )
    )


def count(model):
    return db.session.scalar(db.select(db.func.count()).select_from(model))


def local(value):
    return value.astimezone(ZONE)


def workdays_between(start, end):
    """Días laborales (lunes a viernes) en el intervalo (start, end]."""
    return sum(
        1
        for n in range(1, (end - start).days + 1)
        if (start + timedelta(days=n)).weekday() < 5
    )


def assert_inside_the_default_calendar(moment):
    """Lunes a viernes, dentro de la jornada 09:00-18:00."""
    when = local(moment)

    assert when.weekday() < 5, when
    assert time(9, 0) <= when.time() < time(18, 0), when


def all_event_times():
    return [
        event.fecha_hora
        for demo in DEMO_TICKETS
        for event in history_of(by_clave(demo.clave))
    ]


def date_snapshot():
    """Todas las fechas de todos los tickets demo, por clave."""
    snapshot = {}

    for demo in DEMO_TICKETS:
        ticket = by_clave(demo.clave)

        snapshot[demo.clave] = (
            ticket.fecha_creacion,
            ticket.fecha_modificacion,
            [event.fecha_hora for event in history_of(ticket)],
            [
                (link.fecha_asociacion, link.fecha_retiro)
                for link in requesters_of(ticket)
            ],
            [
                (a.fecha_asignacion, a.fecha_desasignacion)
                for a in assignments_of(ticket)
            ],
            [
                (c.fecha_creacion, c.fecha_modificacion, c.fecha_eliminacion)
                for c in comments_of(ticket)
            ],
            [
                (f.fecha_subida, f.fecha_eliminacion)
                for f in attachments_of(ticket)
            ],
            ticket.fecha_resolucion,
            ticket.fecha_cierre,
            [v.fecha_validacion for v in validations_of(ticket)],
            [(r.fecha_creacion, r.fecha_desactivacion) for r in relations_of(ticket)],
        )

    return snapshot


def content_snapshot():
    """Todo lo que NO son fechas: no debe cambiar al refrescar."""
    snapshot = {}

    for demo in DEMO_TICKETS:
        ticket = by_clave(demo.clave)

        snapshot[demo.clave] = (
            ticket.id,
            ticket.public_id,
            ticket.titulo,
            ticket.descripcion,
            ticket.categoria_id,
            ticket.prioridad_id,
            ticket.ubicacion_id,
            ticket.grupo_id,
            ticket.estado_id,
            ticket.version,
            [
                (event.id, event.tipo_evento, event.actor_usuario_id, event.detalle)
                for event in history_of(ticket)
            ],
            [
                (link.solicitante_id, link.fecha_retiro is None, link.retirado_por_usuario_id)
                for link in requesters_of(ticket)
            ],
            [a.tecnico_id for a in assignments_of(ticket)],
            [
                (c.autor_usuario_id, c.tipo, c.contenido, c.activo, c.editado)
                for c in comments_of(ticket)
            ],
            [
                (f.nombre_original, f.hash, f.comentario_id, f.activo)
                for f in attachments_of(ticket)
            ],
            ticket.resolucion,
            ticket.motivo_cierre_id,
            ticket.cerrado_por_usuario_id,
            ticket.cerrado_automaticamente,
            [
                (
                    v.solicitante_id,
                    v.ciclo_resolucion,
                    v.tipo_validacion,
                    v.motivo_rechazo,
                    v.comentario_adicional,
                )
                for v in validations_of(ticket)
            ],
            [
                (
                    r.tipo.codigo,
                    r.ticket_origen_id,
                    r.ticket_destino_id,
                    r.activo,
                    r.comentario,
                    r.usuario_creacion_id,
                )
                for r in relations_of(ticket)
            ],
        )

    return snapshot


def set_event_time(event, moment):
    """Simula una edición hecha a mano en `moment` (el servicio sella la hora real)."""
    db.session.execute(
        update(TicketHistory.__table__)
        .where(TicketHistory.__table__.c.id == event.id)
        .values(fecha_hora=moment)
    )
    db.session.execute(
        update(Ticket.__table__)
        .where(Ticket.__table__.c.id == event.ticket_id)
        .values(fecha_modificacion=moment)
    )
    db.session.commit()


def edit_by_hand(ticket, title, moment):
    update_ticket(
        ticket,
        actor=user("diego.soto"),
        expected_version=ticket.version,
        title=title,
        description=ticket.descripcion,
        category_id=ticket.categoria_id,
        location_id=ticket.ubicacion_id,
    )
    db.session.commit()

    event = history_of(ticket)[-1]
    set_event_time(event, moment)

    return event




def page_text(client, public_id) -> str:
    html = client.get(f"/tickets/{public_id}").get_data(as_text=True)

    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def log_in(app, username):
    client = app.test_client()
    client.post(
        "/login",
        data={"username": username, "password": DEMO_PASSWORD},
    )

    return client


def events_of(ticket, *kinds):
    return [
        event
        for event in history_of(ticket)
        if event.tipo_evento in {kind.value for kind in kinds}
    ]
