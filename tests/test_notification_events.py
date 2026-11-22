"""Avisos que generan los eventos de un ticket (docs/06, RN-94 a RN-96 y RN-168; docs/04,
RF-068).

Las operaciones de los tickets (cambiar el estado, asignar, escalar y comentar) avisan a
quien corresponde al terminar, dentro de su propia transacción. Aquí se comprueba a
quién avisan, a quién nunca, y que un Solicitante no reciba nada que no vería en el
historial.
"""

import pytest

from src.workdesk.extensions import db
from src.workdesk.models import (
    CommentType,
    Notificacion,
    NotificationEvent,
    StateAction,
)
from src.workdesk.notifications.events import STATE_NOTICES
from src.workdesk.tickets.assignment import (
    assign_technician,
    escalate_ticket,
    unassign_technician,
)
from src.workdesk.tickets.comments import add_comment
from src.workdesk.tickets.lifecycle import change_state
from src.workdesk.tickets.requesters import remove_requester
from src.workdesk.tickets.state_actions import STATE_ACTIONS
from tests.ticket_helpers import make_ticket, person, ticket_by_public_id

E = NotificationEvent
A = StateAction


# --- Ayudas -----------------------------------------------------------------


@pytest.fixture()
def team(make_user, catalog):
    return {
        "req": make_user("SOLICITANTE", username="req1", nombre="Javiera", apellido="Torres"),
        "other": make_user("SOLICITANTE", username="req2", nombre="Paula", apellido="Contreras"),
        "stranger": make_user("SOLICITANTE", username="req3", nombre="Matías", apellido="Fuentes"),
        "tec": make_user("TECNICO", username="tec", nombre="Diego", apellido="Soto"),
        "tec2": make_user("TECNICO", username="tec2", nombre="Camila", apellido="Rojas"),
        "sup": make_user("SUPERVISOR", username="sup", nombre="Nora", apellido="Vega"),
    }


@pytest.fixture()
def ticket_id(app, catalog, team):
    """Un ticket con dos solicitantes (`req` y `other`) y sin técnicos."""
    return make_ticket(
        app,
        catalog,
        team["sup"]["id"],
        requester_ids=[team["req"]["id"], team["other"]["id"]],
    )


def inbox(app, team, who):
    """Los avisos de una persona, de la más antigua a la más reciente."""
    with app.app_context():
        rows = db.session.scalars(
            db.select(Notificacion)
            .where(Notificacion.usuario_id == team[who]["id"])
            .order_by(Notificacion.id)
        )

        return [(n.tipo_evento, n.titulo, n.mensaje) for n in rows]


def events_of(app, team, who):
    return [event for event, _title, _message in inbox(app, team, who)]


def everyone_empty(app, team, *, except_for=()):
    return {
        who: inbox(app, team, who) for who in team if who not in except_for
    } == {who: [] for who in team if who not in except_for}


def clear(app):
    with app.app_context():
        db.session.execute(db.delete(Notificacion))
        db.session.commit()


def assign(app, team, ticket_id, who="tec", by="sup"):
    with app.app_context():
        assign_technician(
            ticket_by_public_id(ticket_id), team[who]["id"], actor=person(team[by]["id"])
        )
        db.session.commit()


def act(app, team, ticket_id, by, action, text=None):
    with app.app_context():
        ticket = ticket_by_public_id(ticket_id)
        change_state(
            ticket,
            actor=person(team[by]["id"]),
            action=action,
            expected_version=ticket.version,
            text=text,
        )
        db.session.commit()


def comment(app, team, ticket_id, by, kind, content="Texto del comentario"):
    with app.app_context():
        add_comment(
            ticket_by_public_id(ticket_id),
            actor=person(team[by]["id"]),
            content=content,
            kind=kind,
        )
        db.session.commit()


# --- Crear un ticket ------------------------------------------------------------


def test_creating_a_ticket_notifies_nobody(app, team, ticket_id):
    assert everyone_empty(app, team)


# --- Asignar -----------------------------------------------------------------------


def test_assigning_notifies_the_technician_and_the_requesters(app, team, ticket_id):
    assign(app, team, ticket_id)

    assert events_of(app, team, "tec") == [E.TICKET_ASIGNADO]
    assert events_of(app, team, "req") == [E.TICKET_ASIGNADO]
    assert events_of(app, team, "other") == [E.TICKET_ASIGNADO]
    assert everyone_empty(app, team, except_for=("tec", "req", "other"))

    # El solicitante sabe quién lo atiende; el técnico, de qué ticket se trata.
    assert "Diego Soto" in inbox(app, team, "req")[0][2]
    assert f"#{ticket_id}" in inbox(app, team, "tec")[0][2]


def test_a_technician_who_takes_a_ticket_is_not_notified_of_it(app, team, ticket_id):
    assign(app, team, ticket_id, by="tec")

    assert inbox(app, team, "tec") == []
    assert events_of(app, team, "req") == [E.TICKET_ASIGNADO]


def test_the_notification_points_to_the_ticket(app, team, ticket_id):
    assign(app, team, ticket_id)

    with app.app_context():
        notification = db.session.scalar(
            db.select(Notificacion).where(Notificacion.usuario_id == team["tec"]["id"])
        )

        assert notification.ticket.public_id == ticket_id


def test_removing_a_technician_notifies_him_unless_he_leaves_by_himself(app, team, ticket_id):
    assign(app, team, ticket_id)
    clear(app)

    with app.app_context():
        ticket = ticket_by_public_id(ticket_id)
        unassign_technician(ticket, ticket.tecnicos_vigentes[0].id, actor=person(team["sup"]["id"]))
        db.session.commit()

    assert events_of(app, team, "tec") == [E.TICKET_REASIGNADO]
    assert everyone_empty(app, team, except_for=("tec",))

    assign(app, team, ticket_id, by="tec")
    clear(app)

    with app.app_context():
        ticket = ticket_by_public_id(ticket_id)
        unassign_technician(ticket, ticket.tecnicos_vigentes[0].id, actor=person(team["tec"]["id"]))
        db.session.commit()

    assert everyone_empty(app, team)


# --- Escalar ----------------------------------------------------------------------


def test_escalating_to_another_technician_tells_both_technicians_and_nobody_else(
    app, team, ticket_id
):
    assign(app, team, ticket_id)
    clear(app)

    with app.app_context():
        ticket = ticket_by_public_id(ticket_id)
        escalate_ticket(
            ticket,
            actor=person(team["sup"]["id"]),
            expected_version=ticket.version,
            group_id=None,
            technician_id=team["tec2"]["id"],
            reason="Motivo reservado del escalamiento",
        )
        db.session.commit()

    assert events_of(app, team, "tec2") == [E.TICKET_REASIGNADO]
    assert events_of(app, team, "tec") == [E.TICKET_REASIGNADO]
    # Es interno: los solicitantes no se enteran y el motivo no se copia a ningún aviso.
    assert everyone_empty(app, team, except_for=("tec", "tec2"))

    for who in ("tec", "tec2"):
        assert "Motivo reservado" not in inbox(app, team, who)[0][2]


# --- Cambios de estado ----------------------------------------------------------


def test_starting_work_notifies_requesters_and_technicians_but_not_the_actor(app, team, ticket_id):
    assign(app, team, ticket_id)
    clear(app)
    act(app, team, ticket_id, "sup", A.INICIAR)

    assert events_of(app, team, "req") == [E.ESTADO_CAMBIADO]
    assert events_of(app, team, "other") == [E.ESTADO_CAMBIADO]
    assert events_of(app, team, "tec") == [E.ESTADO_CAMBIADO]
    assert everyone_empty(app, team, except_for=("req", "other", "tec"))


def test_a_technician_who_was_removed_receives_no_more_state_notices(app, team, ticket_id):
    assign(app, team, ticket_id)

    with app.app_context():
        ticket = ticket_by_public_id(ticket_id)
        unassign_technician(ticket, ticket.tecnicos_vigentes[0].id, actor=person(team["sup"]["id"]))
        db.session.commit()

    clear(app)
    act(app, team, ticket_id, "sup", A.INICIAR)

    assert inbox(app, team, "tec") == []
    assert events_of(app, team, "req") == [E.ESTADO_CAMBIADO]


def test_the_actor_is_never_notified_of_his_own_change(app, team, ticket_id):
    assign(app, team, ticket_id)
    clear(app)
    act(app, team, ticket_id, "tec", A.INICIAR)

    assert inbox(app, team, "tec") == []
    assert events_of(app, team, "req") == [E.ESTADO_CAMBIADO]


def test_putting_a_ticket_on_hold_and_resuming_it(app, team, ticket_id):
    assign(app, team, ticket_id)
    act(app, team, ticket_id, "sup", A.INICIAR)
    clear(app)
    act(app, team, ticket_id, "sup", A.PONER_EN_ESPERA)

    assert events_of(app, team, "req") == [E.TICKET_EN_ESPERA]
    assert events_of(app, team, "tec") == [E.TICKET_EN_ESPERA]

    act(app, team, ticket_id, "sup", A.REACTIVAR)

    assert events_of(app, team, "req") == [E.TICKET_EN_ESPERA, E.ESTADO_CAMBIADO]


def test_resolving_asks_the_requesters_to_review_and_tells_the_technicians(app, team, ticket_id):
    assign(app, team, ticket_id)
    act(app, team, ticket_id, "sup", A.INICIAR)
    clear(app)
    act(app, team, ticket_id, "sup", A.RESOLVER, text="Se cambió el cable")

    assert events_of(app, team, "req") == [E.VALIDACION_PENDIENTE]
    assert events_of(app, team, "other") == [E.VALIDACION_PENDIENTE]
    assert events_of(app, team, "tec") == [E.TICKET_RESUELTO]
    # RN-95: el aviso les permite acceder al ticket.
    assert inbox(app, team, "req")[0][0] == E.VALIDACION_PENDIENTE
    # La solución se lee en el ticket: no se copia al aviso.
    assert "cable" not in inbox(app, team, "req")[0][2]


def test_confirming_closes_and_tells_the_technicians_and_the_other_requester(app, team, ticket_id):
    assign(app, team, ticket_id)
    act(app, team, ticket_id, "sup", A.RESOLVER)
    clear(app)
    act(app, team, ticket_id, "req", A.CONFIRMAR)

    assert events_of(app, team, "tec") == [E.TICKET_CERRADO]
    assert events_of(app, team, "other") == [E.TICKET_CERRADO]
    assert inbox(app, team, "req") == []


def test_rejecting_the_solution_tells_the_technicians_to_pick_it_up_again(app, team, ticket_id):
    assign(app, team, ticket_id)
    act(app, team, ticket_id, "sup", A.RESOLVER)
    clear(app)
    act(app, team, ticket_id, "req", A.RECHAZAR, text="Sigue fallando")

    assert events_of(app, team, "tec") == [E.ESTADO_CAMBIADO]
    assert "rechazó" in inbox(app, team, "tec")[0][2]
    # El motivo del rechazo se lee en el ticket y no se copia al aviso.
    assert "Sigue fallando" not in inbox(app, team, "tec")[0][2]


def test_reopening_by_a_requester_tells_the_technicians(app, team, ticket_id):
    # RN-96.
    assign(app, team, ticket_id)
    act(app, team, ticket_id, "sup", A.RESOLVER)
    act(app, team, ticket_id, "req", A.CONFIRMAR)
    clear(app)
    act(app, team, ticket_id, "req", A.REABRIR)

    assert events_of(app, team, "tec") == [E.TICKET_REABIERTO]
    assert events_of(app, team, "other") == [E.TICKET_REABIERTO]
    assert inbox(app, team, "req") == []


def test_a_direct_close_by_staff_tells_the_requesters(app, team, ticket_id):
    act(app, team, ticket_id, "sup", A.CIERRE_DIRECTO)

    assert events_of(app, team, "req") == [E.TICKET_CERRADO]
    assert events_of(app, team, "other") == [E.TICKET_CERRADO]
    assert everyone_empty(app, team, except_for=("req", "other"))


def test_a_ticket_without_technicians_only_notifies_the_requesters(app, team, ticket_id):
    act(app, team, ticket_id, "tec", A.INICIAR)

    assert events_of(app, team, "req") == [E.ESTADO_CAMBIADO]
    assert everyone_empty(app, team, except_for=("req", "other"))


def test_the_state_changes_of_an_assignment_are_not_notified_twice(app, team, ticket_id):
    # Asignar pasa el ticket de Nuevo a Asignado, pero solo avisa la asignación.
    assign(app, team, ticket_id)

    assert events_of(app, team, "req") == [E.TICKET_ASIGNADO]


def test_every_state_action_declares_who_it_notifies():
    # Una acción nueva obliga a decidir a quién avisa (aunque sea a nadie, a propósito).
    assert set(STATE_ACTIONS) <= set(STATE_NOTICES)


# --- Comentarios (RF-068) -----------------------------------------------------------


def test_a_public_comment_from_staff_notifies_the_requesters(app, team, ticket_id):
    assign(app, team, ticket_id)
    clear(app)
    comment(app, team, ticket_id, "sup", CommentType.PUBLICO)

    assert events_of(app, team, "req") == [E.COMENTARIO_PUBLICO]
    assert events_of(app, team, "other") == [E.COMENTARIO_PUBLICO]
    assert everyone_empty(app, team, except_for=("req", "other"))


def test_a_comment_from_a_requester_notifies_the_assigned_technicians(app, team, ticket_id):
    assign(app, team, ticket_id)
    assign(app, team, ticket_id, who="tec2")
    clear(app)
    comment(app, team, ticket_id, "req", CommentType.PUBLICO)

    assert events_of(app, team, "tec") == [E.COMENTARIO_PUBLICO]
    assert events_of(app, team, "tec2") == [E.COMENTARIO_PUBLICO]
    assert "Javiera Torres" in inbox(app, team, "tec")[0][2]
    # Los demás solicitantes no se enteran de lo que escribe un compañero.
    assert everyone_empty(app, team, except_for=("tec", "tec2"))


def test_an_internal_note_notifies_only_the_other_assigned_technicians(app, team, ticket_id):
    assign(app, team, ticket_id)
    clear(app)
    comment(app, team, ticket_id, "sup", CommentType.INTERNO)

    assert events_of(app, team, "tec") == [E.NOTA_INTERNA]
    assert everyone_empty(app, team, except_for=("tec",))

    clear(app)
    comment(app, team, ticket_id, "tec", CommentType.INTERNO)

    assert everyone_empty(app, team)


def test_a_comment_notice_never_copies_the_text(app, team, ticket_id):
    assign(app, team, ticket_id)
    clear(app)
    comment(app, team, ticket_id, "sup", CommentType.INTERNO, "contraseña del router: 1234")
    comment(app, team, ticket_id, "sup", CommentType.PUBLICO, "texto público largo")

    for who in ("tec", "req"):
        for _event, _title, message in inbox(app, team, who):
            assert "1234" not in message
            assert "texto público" not in message


def test_a_retired_requester_receives_nothing(app, team, ticket_id):
    with app.app_context():
        ticket = ticket_by_public_id(ticket_id)
        participation = next(
            p for p in ticket.solicitantes_vigentes if p.solicitante_id == team["other"]["id"]
        )
        remove_requester(ticket, participation.id, actor=person(team["sup"]["id"]))
        db.session.commit()

    comment(app, team, ticket_id, "sup", CommentType.PUBLICO)

    assert events_of(app, team, "req") == [E.COMENTARIO_PUBLICO]
    assert inbox(app, team, "other") == []


# --- Lo que un Solicitante nunca recibe ----------------------------------------------


def test_a_requester_never_receives_internal_activity(app, team, ticket_id):
    assign(app, team, ticket_id)
    act(app, team, ticket_id, "sup", A.INICIAR)
    comment(app, team, ticket_id, "sup", CommentType.INTERNO, "algo reservado")

    with app.app_context():
        ticket = ticket_by_public_id(ticket_id)
        escalate_ticket(
            ticket,
            actor=person(team["sup"]["id"]),
            expected_version=ticket.version,
            group_id=None,
            technician_id=team["tec2"]["id"],
            reason="Motivo reservado",
        )
        db.session.commit()

    for who in ("req", "other"):
        events = set(events_of(app, team, who))

        assert events <= {E.TICKET_ASIGNADO, E.ESTADO_CAMBIADO}
        assert E.NOTA_INTERNA not in events
        assert E.TICKET_REASIGNADO not in events

        for _event, _title, message in inbox(app, team, who):
            assert "reservado" not in message
            assert "escal" not in message.lower()

    assert inbox(app, team, "stranger") == []


# --- Transacción y límites ----------------------------------------------------------


def test_the_notices_roll_back_with_the_operation(app, team, ticket_id):
    with app.app_context():
        assign_technician(
            ticket_by_public_id(ticket_id), team["tec"]["id"], actor=person(team["sup"]["id"])
        )
        db.session.rollback()

    assert everyone_empty(app, team)


def test_a_very_long_title_still_fits_in_the_notice(app, team, catalog):
    ticket_id = make_ticket(
        app,
        catalog,
        team["sup"]["id"],
        requester_ids=[team["req"]["id"]],
        title="T" * 200,
    )
    assign(app, team, ticket_id)

    message = inbox(app, team, "req")[0][2]

    assert f"#{ticket_id}" in message
    assert "…" in message
    assert len(message) < 200
