"""Visibilidad por evento del historial de un ticket (docs/13, sección 9).

Regla crítica: un evento interno nunca llega al Solicitante, ni en el
historial del detalle ni en los conteos. El filtro lo aplica la consulta
(`visible_history_condition`), no la plantilla.
"""

import pytest
from flask_login import AnonymousUserMixin

from src.workdesk.extensions import db
from src.workdesk.models import (
    HistoryVisibility,
    Ticket,
    TicketEvent,
    TicketHistory,
    User,
)
from src.workdesk.models.ticket_history import DEFAULT_EVENT_VISIBILITY
from src.workdesk.security import can_view_internal_activity
from src.workdesk.tickets.service import (
    list_ticket_history,
    record_ticket_event,
    visible_history_condition,
)
from tests.ticket_helpers import login, make_ticket, plain_text

ALL_ROLES = ("SOLICITANTE", "TECNICO", "SUPERVISOR", "ADMINISTRADOR")

CRITICAL_PRIORITY = {"prioridad_id": 4, "codigo": "CRITICA", "nombre": "Crítica"}


def _ticket(app, catalog, creator_id):
    """Crea un ticket y devuelve (id interno, identificador público)."""
    public_id = make_ticket(app, catalog, creator_id)

    with app.app_context():
        return (
            db.session.scalar(
                db.select(Ticket.id).where(Ticket.public_id == public_id)
            ),
            public_id,
        )


def _record(app, ticket_id, actor_id, event, **kwargs):
    with app.app_context():
        record_ticket_event(
            db.session.get(Ticket, ticket_id),
            event,
            actor=db.session.get(User, actor_id),
            **kwargs,
        )
        db.session.commit()


def _visible_event_types(app, ticket_id, user_id) -> list[str]:
    with app.app_context():
        ticket = db.session.get(Ticket, ticket_id)
        viewer = db.session.get(User, user_id)

        return [e.tipo_evento for e in list_ticket_history(ticket, viewer)]


def _count_history(ticket_id, *conditions) -> int:
    return db.session.scalar(
        db.select(db.func.count(TicketHistory.id)).where(
            TicketHistory.ticket_id == ticket_id,
            *conditions,
        )
    )


# --- Vocabulario y valores por defecto ------------------------------------


def test_every_event_has_a_default_visibility():
    assert set(DEFAULT_EVENT_VISIBILITY) == set(TicketEvent)
    assert all(
        isinstance(value, HistoryVisibility)
        for value in DEFAULT_EVENT_VISIBILITY.values()
    )


def test_a_recorded_event_uses_the_default_visibility_of_its_type(
    app,
    make_user,
    catalog,
):
    staff = make_user("TECNICO")
    ticket_id, _ = _ticket(app, catalog, staff["id"])

    _record(app, ticket_id, staff["id"], TicketEvent.PRIORIDAD_CAMBIADA)

    with app.app_context():
        entries = db.session.scalars(
            db.select(TicketHistory).where(TicketHistory.ticket_id == ticket_id)
        ).all()

    assert len(entries) == 2
    assert {e.visibilidad for e in entries} == {"PUBLICO"}


def test_the_visibility_of_an_event_can_be_overridden(app, make_user, catalog):
    staff = make_user("TECNICO")
    ticket_id, _ = _ticket(app, catalog, staff["id"])

    _record(
        app,
        ticket_id,
        staff["id"],
        TicketEvent.PRIORIDAD_CAMBIADA,
        visibility=HistoryVisibility.INTERNO,
    )

    with app.app_context():
        internal = db.session.scalars(
            db.select(TicketHistory).where(
                TicketHistory.ticket_id == ticket_id,
                TicketHistory.visibilidad == "INTERNO",
            )
        ).all()

    assert [e.tipo_evento for e in internal] == ["PRIORIDAD_CAMBIADA"]


def test_an_unknown_event_is_rejected_and_leaves_nothing_pending(
    app,
    make_user,
    catalog,
):
    staff = make_user("TECNICO")
    ticket_id, _ = _ticket(app, catalog, staff["id"])

    with app.app_context():
        ticket = db.session.get(Ticket, ticket_id)
        actor = db.session.get(User, staff["id"])
        before = _count_history(ticket_id)

        with pytest.raises(ValueError):
            record_ticket_event(ticket, "EVENTO_INVENTADO", actor=actor)

        assert not db.session.new
        assert _count_history(ticket_id) == before


def test_an_unknown_visibility_is_rejected_and_leaves_nothing_pending(
    app,
    make_user,
    catalog,
):
    staff = make_user("TECNICO")
    ticket_id, _ = _ticket(app, catalog, staff["id"])

    with app.app_context():
        ticket = db.session.get(Ticket, ticket_id)
        actor = db.session.get(User, staff["id"])

        with pytest.raises(ValueError):
            record_ticket_event(
                ticket,
                TicketEvent.PRIORIDAD_CAMBIADA,
                actor=actor,
                visibility="SECRETO",
            )

        assert not db.session.new


# --- Qué ve cada rol -------------------------------------------------------


def test_staff_sees_internal_events_and_the_requester_does_not(
    app,
    make_user,
    catalog,
):
    requester = make_user("SOLICITANTE")
    staff = make_user("TECNICO")
    ticket_id, _ = _ticket(app, catalog, requester["id"])

    _record(
        app,
        ticket_id,
        staff["id"],
        TicketEvent.PRIORIDAD_CAMBIADA,
        visibility=HistoryVisibility.INTERNO,
    )

    assert _visible_event_types(app, ticket_id, staff["id"]) == [
        "TICKET_CREADO",
        "PRIORIDAD_CAMBIADA",
    ]
    assert _visible_event_types(app, ticket_id, requester["id"]) == [
        "TICKET_CREADO"
    ]


@pytest.mark.parametrize("role", ALL_ROLES)
def test_the_sql_condition_matches_the_policy_for_every_role(
    app,
    make_user,
    catalog,
    role,
):
    creator = make_user("TECNICO", username="creador")
    viewer = make_user(role, username="visor")
    ticket_id, _ = _ticket(app, catalog, creator["id"])

    _record(
        app,
        ticket_id,
        creator["id"],
        TicketEvent.PRIORIDAD_CAMBIADA,
        visibility=HistoryVisibility.INTERNO,
    )

    with app.app_context():
        user = db.session.get(User, viewer["id"])
        condition = visible_history_condition(user)
        internal_visible = _count_history(
            ticket_id,
            TicketHistory.visibilidad == "INTERNO",
            condition,
        )
        public_visible = _count_history(
            ticket_id,
            TicketHistory.visibilidad == "PUBLICO",
            condition,
        )

        assert (internal_visible == 1) is can_view_internal_activity(user)
        assert public_visible == 1


def test_a_count_built_with_the_condition_excludes_internal_events(
    app,
    make_user,
    catalog,
):
    requester = make_user("SOLICITANTE")
    staff = make_user("TECNICO")
    ticket_id, _ = _ticket(app, catalog, requester["id"])

    for _ in range(3):
        _record(
            app,
            ticket_id,
            staff["id"],
            TicketEvent.PRIORIDAD_CAMBIADA,
            visibility=HistoryVisibility.INTERNO,
        )

    def count(user_id):
        with app.app_context():
            return _count_history(
                ticket_id,
                visible_history_condition(db.session.get(User, user_id)),
            )

    assert count(requester["id"]) == 1
    assert count(staff["id"]) == 4


def test_the_condition_hides_everything_from_anonymous_and_inactive_users(
    app,
    make_user,
    catalog,
):
    staff = make_user("TECNICO", username="activo")
    inactive = make_user("TECNICO", username="inactivo", activo=False)
    inactive_requester = make_user(
        "SOLICITANTE",
        username="solicitante_inactivo",
        activo=False,
    )
    ticket_id, _ = _ticket(app, catalog, staff["id"])

    with app.app_context():
        ticket = db.session.get(Ticket, ticket_id)

        for viewer in (
            AnonymousUserMixin(),
            db.session.get(User, inactive["id"]),
            db.session.get(User, inactive_requester["id"]),
        ):
            assert list_ticket_history(ticket, viewer) == []


# --- Detalle del ticket ----------------------------------------------------


def test_the_detail_never_shows_internal_events_to_the_requester(
    client,
    app,
    make_user,
    catalog,
):
    requester = make_user("SOLICITANTE", username="ana")
    staff = make_user("TECNICO", username="tec")
    ticket_id, public_id = _ticket(app, catalog, requester["id"])

    _record(
        app,
        ticket_id,
        staff["id"],
        TicketEvent.PRIORIDAD_CAMBIADA,
        old_value={"prioridad_id": 2, "codigo": "MEDIA", "nombre": "Media"},
        new_value=CRITICAL_PRIORITY,
        context={"motivo": "Afecta a toda la sucursal"},
        visibility=HistoryVisibility.INTERNO,
    )

    login(client, requester)
    as_requester = plain_text(client.get(f"/tickets/{public_id}"))

    assert "Ticket creado" in as_requester
    assert "Prioridad cambiada" not in as_requester
    assert "Crítica" not in as_requester
    assert "Afecta a toda la sucursal" not in as_requester

    client.post("/logout")
    login(client, staff)
    as_staff = plain_text(client.get(f"/tickets/{public_id}"))

    assert "Prioridad cambiada" in as_staff
    assert "Prioridad: «Media» → «Crítica»" in as_staff
    assert "Afecta a toda la sucursal" in as_staff
