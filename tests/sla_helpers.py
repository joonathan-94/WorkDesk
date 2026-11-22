"""Ayudas compartidas por los tests de SLA: «la hora» fija y las operaciones sobre un
ticket que usan los períodos y los indicadores.

Los tests fijan la hora en noviembre de 2026, con el calendario por defecto (lunes a
viernes de 09:00 a 18:00, en Santiago): el lunes 16 es el primer día; el 21 y el 22 son
fin de semana.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from src.workdesk.extensions import db
from src.workdesk.models import PoliticaSla, Prioridad, StateAction, Ticket
from src.workdesk.tickets.editing import change_priority
from src.workdesk.tickets.lifecycle import change_state
from src.workdesk.tickets.service import create_ticket
from tests.ticket_helpers import person

ZONE = ZoneInfo("America/Santiago")
HOUR = 3600


def at(day, hour=0, minute=0):
    """Un momento de noviembre de 2026 en Santiago (lun 16 ... vie 20, sáb 21)."""
    return datetime(2026, 11, day, hour, minute, tzinfo=ZONE)


class FakeClock:
    """«La hora» que ven los períodos: se mueve a mano."""

    def __init__(self):
        self.now = at(16, 10)

    def set(self, moment):
        self.now = moment


def priority_id(code) -> int:
    return db.session.scalar(db.select(Prioridad.id).where(Prioridad.codigo == code))


def policy_of(code) -> PoliticaSla:
    return db.session.scalar(
        db.select(PoliticaSla)
        .join(Prioridad, Prioridad.id == PoliticaSla.prioridad_id)
        .where(Prioridad.codigo == code)
    )


def new_ticket(catalog, creator_id, code="MEDIA", title="Problema con el correo") -> Ticket:
    ticket = create_ticket(
        actor=person(creator_id),
        title=title,
        description="No puedo enviar mensajes.",
        category_id=catalog["hardware"],
        priority_id=priority_id(code),
    )
    db.session.commit()

    return ticket


def act(ticket, actor_id, action, **extra) -> None:
    change_state(
        ticket,
        actor=person(actor_id),
        action=action,
        expected_version=ticket.version,
        **extra,
    )
    db.session.commit()


def set_priority(ticket, actor_id, code, reason="Cambia el impacto") -> None:
    change_priority(
        ticket,
        actor=person(actor_id),
        expected_version=ticket.version,
        priority_id=priority_id(code),
        reason=reason,
    )
    db.session.commit()


def work_on(ticket, actor_id) -> None:
    act(ticket, actor_id, StateAction.INICIAR)


def hold(ticket, actor_id) -> None:
    act(ticket, actor_id, StateAction.PONER_EN_ESPERA)


def resume(ticket, actor_id) -> None:
    act(ticket, actor_id, StateAction.REACTIVAR)


def resolve(ticket, actor_id) -> None:
    act(ticket, actor_id, StateAction.RESOLVER)


def reopen(ticket, actor_id) -> None:
    act(ticket, actor_id, StateAction.REABRIR)


def close(ticket, actor_id) -> None:
    act(ticket, actor_id, StateAction.CIERRE_DIRECTO)
