"""Reglas de negocio del SLA que protegen el trabajo (docs/06, RN-85, RN-86 y RN-87).

Se cumplen por construcción, pero una regla sin prueba puede romperse sin que nadie lo
note:

- **RN-85:** el SLA pertenece al ticket, no al técnico. Asignar, reasignar, quitar a un
  técnico, cambiar el grupo o escalar no tocan sus períodos.
- **RN-86:** el incumplimiento no bloquea nada. Con el SLA vencido se sigue comentando,
  esperando, reanudando, resolviendo, cerrando y reabriendo, y resolver no borra el
  incumplimiento.
- **RN-87:** que un técnico tenga muchos tickets no detiene el reloj de ninguno: cada uno
  consume su propio tiempo laboral desde su propio inicio.

Usan la hora fija de las pruebas de SLA (`clock`, ver `tests/sla_helpers.py`): lunes 16 de
noviembre de 2026, de 09:00 a 18:00 en Santiago. Un ticket Alta (6 h) creado a las 10:00
vence a las 16:00; uno Media (12 h), el martes a las 13:00.
"""

import pytest

from src.workdesk.extensions import db
from src.workdesk.groups.service import create_group
from src.workdesk.models import CommentType, StateAction
from src.workdesk.sla.evaluation import SlaStatus, evaluate_ticket_sla
from src.workdesk.sla.periods import list_periods
from src.workdesk.tickets.assignment import (
    assign_technician,
    escalate_ticket,
    set_group,
    unassign_technician,
)
from src.workdesk.tickets.comments import add_comment
from tests.sla_helpers import (
    act,
    at,
    close,
    hold,
    new_ticket,
    reopen,
    resolve,
    resume,
    work_on,
)
from tests.ticket_helpers import login, person, plain_text, ticket_by_public_id


@pytest.fixture()
def people(make_user, catalog):
    return {
        "sup": make_user("SUPERVISOR", username="supervisor"),
        "tec": make_user("TECNICO", username="tecnico"),
        "tec2": make_user("TECNICO", username="otro_tecnico"),
        "admin": make_user("ADMINISTRADOR", username="admin_sla"),
    }


def shapes(ticket) -> list[tuple]:
    """Lo que identifica los períodos de un ticket (con sus ids: nada se reemplaza)."""
    return [
        (
            p.id,
            p.fecha_inicio,
            p.fecha_fin,
            p.segundos_consumidos,
            p.fecha_vencimiento_resolucion,
            p.fecha_umbral_aviso,
            p.usuario_cambio_id,
        )
        for p in list_periods(ticket.id)
    ]


# --- RN-85: el SLA es del ticket, no del técnico --------------------------------


def test_changing_who_works_a_ticket_never_touches_its_sla(app, clock, people, catalog):
    with app.app_context():
        ticket = new_ticket(catalog, people["sup"]["id"], "MEDIA")
        supervisor = person(people["sup"]["id"])
        before = shapes(ticket)

        first = assign_technician(ticket, people["tec"]["id"], actor=supervisor)
        db.session.commit()
        assign_technician(ticket, people["tec2"]["id"], actor=supervisor)
        db.session.commit()
        unassign_technician(ticket, first.id, actor=supervisor, reason="Reparto")
        db.session.commit()

        group = create_group(actor=person(people["admin"]["id"]), nombre="Redes")
        db.session.commit()
        set_group(ticket, group.id, actor=supervisor, expected_version=ticket.version)
        db.session.commit()
        escalate_ticket(
            ticket,
            actor=supervisor,
            expected_version=ticket.version,
            group_id=group.id,
            technician_id=people["tec"]["id"],
            reason="Hace falta más experiencia",
        )
        db.session.commit()

        # El mismo período (mismo id, mismos vencimientos): ninguna de esas operaciones
        # lo cerró ni abrió otro.
        assert shapes(ticket) == before
        assert len(before) == 1


def test_a_ticket_keeps_the_time_it_has_consumed_when_its_technician_changes(
    app, clock, people, catalog
):
    with app.app_context():
        ticket = new_ticket(catalog, people["sup"]["id"], "MEDIA")
        supervisor = person(people["sup"]["id"])
        assign_technician(ticket, people["tec"]["id"], actor=supervisor)
        db.session.commit()

        # Martes a las 11:00: 8 h del lunes y 2 h del martes.
        consumed_with_first = evaluate_ticket_sla(ticket.id, at(17, 11)).consumed_seconds
        assignment = ticket.tecnicos_vigentes[0]
        unassign_technician(ticket, assignment.id, actor=supervisor, reason="Cambio de turno")
        assign_technician(ticket, people["tec2"]["id"], actor=supervisor)
        db.session.commit()

        assert consumed_with_first == 10 * 3600
        assert evaluate_ticket_sla(ticket.id, at(17, 11)).consumed_seconds == 10 * 3600


# --- RN-86: el incumplimiento no bloquea nada ------------------------------------


def make_breached_ticket(catalog, people, clock):
    """Un ticket Alta en progreso, ya vencido (venció el lunes a las 16:00)."""
    ticket = new_ticket(catalog, people["sup"]["id"], "ALTA")
    work_on(ticket, people["tec"]["id"])
    clock.set(at(17, 12))

    assert evaluate_ticket_sla(ticket.id, at(17, 12)).status is SlaStatus.VENCIDO

    return ticket


def test_a_breached_sla_does_not_stop_anyone_from_working_the_ticket(
    app, clock, people, catalog
):
    with app.app_context():
        ticket = make_breached_ticket(catalog, people, clock)
        technician = people["tec"]["id"]

        add_comment(
            ticket,
            actor=person(technician),
            content="Sigo trabajando en esto.",
            kind=CommentType.PUBLICO,
        )
        db.session.commit()
        hold(ticket, technician)
        resume(ticket, technician)

        assert ticket.estado.codigo == "EN_PROGRESO"
        assert evaluate_ticket_sla(ticket.id, at(17, 12)).status is SlaStatus.VENCIDO


def test_a_breached_ticket_can_be_resolved_and_the_breach_is_not_erased(
    app, clock, people, catalog
):
    with app.app_context():
        ticket = make_breached_ticket(catalog, people, clock)

        resolve(ticket, people["tec"]["id"])

        assert ticket.estado.codigo == "RESUELTO"
        # El reloj se detiene, pero el ticket sigue figurando como incumplido.
        assert evaluate_ticket_sla(ticket.id, at(17, 12)).status is SlaStatus.VENCIDO


def test_a_breached_ticket_can_be_closed_and_reopened(app, clock, people, catalog):
    with app.app_context():
        ticket = make_breached_ticket(catalog, people, clock)

        close(ticket, people["tec"]["id"])
        assert ticket.estado.codigo == "CERRADO"

        reopen(ticket, people["tec"]["id"])
        assert ticket.estado.codigo == "EN_PROGRESO"
        # Un incumplimiento no se borra por reabrir: sigue vencido.
        assert evaluate_ticket_sla(ticket.id, at(17, 12)).status is SlaStatus.VENCIDO

        resolve(ticket, people["tec"]["id"])
        assert ticket.estado.codigo == "RESUELTO"


def test_the_screen_still_offers_and_accepts_the_actions_on_a_breached_ticket(
    app, client, clock, people, catalog
):
    with app.app_context():
        ticket = make_breached_ticket(catalog, people, clock)
        public_id, version = ticket.public_id, ticket.version

    login(client, people["tec"])
    page = plain_text(client.get(f"/tickets/{public_id}"))

    # El detalle muestra el incumplimiento y, aun así, ofrece resolver.
    assert "Vencido" in page
    assert "Resolver" in page

    response = client.post(
        f"/tickets/{public_id}/status/resolve",
        data={"version": version, "texto": "Listo."},
    )

    assert response.status_code == 302

    with app.app_context():
        assert ticket_by_public_id(public_id).estado.codigo == "RESUELTO"


# --- RN-87: muchos tickets no detienen el reloj de ninguno ----------------------------


def test_having_many_tickets_does_not_stop_the_clock_of_any_of_them(
    app, clock, people, catalog
):
    technician = people["tec"]["id"]

    with app.app_context():
        supervisor = person(people["sup"]["id"])
        tickets = []

        # Tres tickets Media (12 h) del mismo técnico, abiertos a distintas horas.
        for moment in (at(16, 10), at(16, 14), at(17, 9)):
            clock.set(moment)
            ticket = new_ticket(catalog, people["sup"]["id"], "MEDIA")
            assign_technician(ticket, technician, actor=supervisor)
            db.session.commit()
            act(ticket, technician, StateAction.INICIAR)
            tickets.append(ticket)

        # El martes a las 11:00 cada uno lleva su propio tiempo laboral desde que se abrió:
        # 8 h + 2 h, 4 h + 2 h y 2 h.
        consumed = [
            evaluate_ticket_sla(ticket.id, at(17, 11)).consumed_seconds for ticket in tickets
        ]

        assert consumed == [10 * 3600, 6 * 3600, 2 * 3600]
