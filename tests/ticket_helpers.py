"""Funciones auxiliares compartidas por los tests de tickets."""

import re
from datetime import UTC, datetime

from src.workdesk.extensions import db
from src.workdesk.models import (
    Estado,
    MotivoCierre,
    Ticket,
    TicketRequester,
    User,
)
from src.workdesk.tickets.service import create_ticket


def login(client, user_data):
    return client.post(
        "/login",
        data={
            "username": user_data["username"],
            "password": user_data["password"],
        },
    )


def text(response) -> str:
    """Texto de la respuesta con los espacios y saltos de línea colapsados."""
    return " ".join(response.get_data(as_text=True).split())


def plain_text(response) -> str:
    """Texto visible de la respuesta: sin etiquetas y con los espacios
    colapsados (útil cuando un dato va dentro de un <span>)."""
    return " ".join(re.sub(r"<[^>]+>", " ", response.get_data(as_text=True)).split())


def make_ticket(app, catalog, creator_id, requester_ids=(), **overrides):
    """Crea un ticket con el servicio y devuelve su identificador público."""
    with app.app_context():
        values = {
            "actor": db.session.get(User, creator_id),
            "title": "Problema con el correo",
            "description": "No puedo enviar mensajes.",
            "category_id": catalog["hardware"],
            "priority_id": catalog["medium"],
            "requester_ids": requester_ids,
        }
        values.update(overrides)

        ticket = create_ticket(**values)
        db.session.commit()

        return ticket.public_id


def ticket_by_public_id(public_id) -> Ticket:
    """El ticket por su identificador público (dentro de un app context)."""
    return db.session.scalar(
        db.select(Ticket).where(Ticket.public_id == public_id)
    )


def person(user_id) -> User:
    """El usuario por su id (dentro de un app context)."""
    return db.session.get(User, user_id)


def set_state(app, public_id, code):
    with app.app_context():
        # Se consultan los ids antes de modificar: con la fila a medio cambiar
        # (fecha de cierre sin motivo) la base de datos rechazaría el estado
        # intermedio.
        state_id = db.session.scalar(
            db.select(Estado.id).where(Estado.codigo == code)
        )
        reason_id = db.session.scalar(
            db.select(MotivoCierre.id).where(
                MotivoCierre.codigo == "CANCELACION"
            )
        )
        ticket = ticket_by_public_id(public_id)
        ticket.estado_id = state_id

        if code == "CERRADO":
            ticket.fecha_cierre = datetime.now(UTC)
            ticket.motivo_cierre_id = reason_id

        db.session.commit()


def set_created(app, public_id, moment):
    with app.app_context():
        ticket_by_public_id(public_id).fecha_creacion = moment
        db.session.commit()


def retire(app, public_id, requester_id):
    with app.app_context():
        link = db.session.scalar(
            db.select(TicketRequester).where(
                TicketRequester.ticket_id == ticket_by_public_id(public_id).id,
                TicketRequester.solicitante_id == requester_id,
            )
        )
        link.fecha_retiro = datetime.now(UTC)
        db.session.commit()
