"""El dashboard del Solicitante (`dashboard/requester.py`, UI-002 y RF-097).

La regla central: **cada contador coincide con el total del listado al que enlaza**. Se
comprueba con los tickets de demostración para cada uno de los seis solicitantes. Lo demás:
qué se ve (y qué nunca se ve: SLA, grupos, carga), los bordes de «últimos 7 días» y el caso de
quien todavía no tiene nada.
"""

import re
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import event

from src.workdesk.dashboard.requester import CLOSED_WINDOW_DAYS, requester_dashboard
from src.workdesk.extensions import db
from src.workdesk.models import Estado, Ticket, User
from src.workdesk.seeds.demo_tickets_data import DEMO_TICKETS
from src.workdesk.tickets.queries import (
    TAB_ALL,
    TAB_CLOSED,
    TAB_OPEN,
    TicketFilters,
    list_tickets,
)
from tests.demo_data import DEMO_PASSWORD, NOW, SOLICITANTES
from tests.ticket_helpers import (
    login,
    make_ticket,
    set_state,
    text,
    ticket_by_public_id,
)


def requester(username):
    return db.session.scalar(db.select(User).where(User.username == username))


def total(user, tab, **filters):
    return list_tickets(user, TicketFilters(**filters), tab=tab).total


# --- Cada cifra es el total de su listado ---------------------------------------------------


@pytest.mark.parametrize("username", SOLICITANTES)
def test_every_counter_equals_the_total_of_the_list_it_links_to(seeded, app, username):
    with app.app_context():
        user = requester(username)
        data = requester_dashboard(user, now=NOW)
        in_progress = db.session.scalar(
            db.select(Estado.id).where(Estado.codigo == "EN_PROGRESO")
        )

        assert data.open == total(user, TAB_OPEN)
        assert data.in_progress == total(user, TAB_OPEN, state_id=in_progress)
        assert data.pending_review == total(user, TAB_ALL, pending_review=True)
        assert data.recently_closed == total(
            user, TAB_CLOSED, closed_from=data.closed_since
        )
        assert data.closed_since == NOW.date() - timedelta(days=CLOSED_WINDOW_DAYS)


def test_the_demonstration_gives_every_requester_something_to_review(seeded, app):
    with app.app_context():
        for username in SOLICITANTES:
            data = requester_dashboard(requester(username), now=NOW)

            assert data.pending_review >= 1, username
            assert data.pending_ticket is not None, username

        with_closures = [
            username
            for username in SOLICITANTES
            if requester_dashboard(requester(username), now=NOW).recently_closed
        ]

        assert len(with_closures) >= 3


def test_a_requester_only_counts_his_own_tickets(seeded, app):
    with app.app_context():
        counts = [requester_dashboard(requester(u), now=NOW).open for u in SOLICITANTES]
        everything = db.session.scalar(db.select(db.func.count()).select_from(Ticket))

        assert sum(counts) < everything
        assert all(count < len(DEMO_TICKETS) for count in counts)


# --- La pantalla ---------------------------------------------------------------------------


def sign_in(client, username):
    return login(client, {"username": username, "password": DEMO_PASSWORD})


def test_the_page_shows_the_four_counters_the_alert_and_the_lists(seeded, client):
    sign_in(client, SOLICITANTES[0])
    page = client.get("/dashboard")
    content = text(page)

    assert page.status_code == 200

    for label in (
        "Tickets abiertos",
        "En progreso",
        "Requieren tu revisión",
        "Cerrados recientemente",
        "Mis tickets recientes",
        "Notificaciones recientes",
        "Atendido por",
        "Crear ticket",
    ):
        assert label in content, label

    assert "pendiente de revisión" in content or "pendientes de revisión" in content


def test_the_counters_link_to_the_filtered_lists(seeded, client):
    sign_in(client, SOLICITANTES[0])
    html = client.get("/dashboard").get_data(as_text=True)

    assert "revision=1" in html
    assert "vista=cerrados" in html and "cerrado_desde=" in html
    assert 'href="/tickets"' in html


@pytest.mark.parametrize("username", SOLICITANTES)
def test_the_requester_never_sees_sla_groups_or_the_load_of_technicians(
    seeded, client, username
):
    sign_in(client, username)
    content = text(client.get("/dashboard")).lower()

    assert not re.search(r"\bsla\b", content)

    for forbidden in ("vencido", "próximo a vencer", "carga de trabajo", "grupo"):
        assert forbidden not in content, forbidden


def test_a_resolved_ticket_waiting_for_the_review_is_marked(seeded, client):
    sign_in(client, SOLICITANTES[0])
    page = text(client.get("/dashboard"))

    assert "Requiere tu revisión" in page


def test_staff_get_the_operational_dashboard_not_the_requester_one(seeded, client):
    login(client, {"username": "diego.soto", "password": DEMO_PASSWORD})
    content = text(client.get("/dashboard"))

    assert "Tickets abiertos prioritarios" in content
    assert "Requieren tu revisión" not in content


# --- Un Solicitante sin nada ----------------------------------------------------------------


def test_a_new_requester_sees_zeros_and_empty_states(client, make_user, catalog):
    login(client, make_user("SOLICITANTE", username="nuevo"))
    page = client.get("/dashboard")
    content = text(page)

    assert page.status_code == 200
    assert "Todavía no tienes tickets" in content
    assert "No tienes notificaciones" in content
    assert "pendiente de revisión" not in content and "pendientes de revisión" not in content


def test_the_counters_of_a_new_requester_are_zero(app, make_user, catalog):
    make_user("SOLICITANTE", username="nuevo")

    with app.app_context():
        data = requester_dashboard(requester("nuevo"))

        assert (data.open, data.in_progress, data.pending_review, data.recently_closed) == (0, 0, 0, 0)
        assert data.pending_ticket is None and data.recent_tickets == []


# --- La alerta de revisión ---------------------------------------------------------------------


def test_with_one_pending_ticket_the_alert_opens_it(app, client, make_user, catalog):
    staff = make_user("TECNICO", username="tec")
    solicitante = make_user("SOLICITANTE", username="uno")
    number = make_ticket(app, catalog, staff["id"], requester_ids=[solicitante["id"]])
    set_state(app, number, "RESUELTO")
    login(client, solicitante)

    html = client.get("/dashboard").get_data(as_text=True)

    assert "Tienes 1 solicitud pendiente de revisión" in html
    assert f'href="/tickets/{number}"' in html
    assert "Revisar resolución" in html


def test_with_several_pending_tickets_the_alert_opens_the_list(app, client, make_user, catalog):
    staff = make_user("TECNICO", username="tec")
    solicitante = make_user("SOLICITANTE", username="uno")

    for _ in range(2):
        number = make_ticket(app, catalog, staff["id"], requester_ids=[solicitante["id"]])
        set_state(app, number, "RESUELTO")

    login(client, solicitante)
    html = client.get("/dashboard").get_data(as_text=True)

    assert "Tienes 2 solicitudes pendientes de revisión" in html
    assert "Ver las solicitudes" in html


def test_the_creator_who_is_not_a_requester_has_nothing_to_review(app, make_user, catalog):
    creator = make_user("SOLICITANTE", username="creador")
    other = make_user("SOLICITANTE", username="otro")
    number = make_ticket(app, catalog, creator["id"], requester_ids=[other["id"]])

    with app.app_context():
        # Lo creó él, pero el solicitante vigente es otra persona.
        from src.workdesk.models import TicketRequester

        for link in db.session.scalars(
            db.select(TicketRequester).where(
                TicketRequester.ticket_id == ticket_by_public_id(number).id,
                TicketRequester.solicitante_id == creator["id"],
            )
        ):
            link.fecha_retiro = datetime.now(UTC)

        db.session.commit()

    set_state(app, number, "RESUELTO")

    with app.app_context():
        assert requester_dashboard(requester("creador")).pending_review == 0
        assert requester_dashboard(requester("otro")).pending_review == 1


# --- «Cerrados recientemente»: el borde de los 7 días ------------------------------------------------


def test_closed_recently_counts_local_days(app, make_user, catalog):
    app.config["APP_TIMEZONE"] = "America/Santiago"
    staff = make_user("TECNICO", username="tec")
    solicitante = make_user("SOLICITANTE", username="uno")
    now = datetime(2026, 11, 18, 15, 0, tzinfo=UTC)
    # Hoy es el 18; los últimos 7 días empiezan el 11 a las 00:00 locales (UTC-3: 03:00 UTC).
    inside = datetime(2026, 11, 11, 3, 0, 0, tzinfo=UTC)
    outside = datetime(2026, 11, 11, 2, 59, 59, tzinfo=UTC)

    for moment in (inside, outside):
        number = make_ticket(app, catalog, staff["id"], requester_ids=[solicitante["id"]])
        set_state(app, number, "CERRADO")

        with app.app_context():
            ticket_by_public_id(number).fecha_cierre = moment
            db.session.commit()

    with app.app_context():
        data = requester_dashboard(requester("uno"), now=now)

        assert data.closed_since == date(2026, 11, 11)
        assert data.recently_closed == 1


# --- Consultas -----------------------------------------------------------------------------------------


def test_the_dashboard_costs_a_fixed_number_of_queries(seeded, client):
    sign_in(client, SOLICITANTES[0])
    statements = []

    def count(conn, cursor, statement, *args):
        statements.append(statement)

    with client.application.app_context():
        event.listen(db.engine, "before_cursor_execute", count)

        try:
            assert client.get("/dashboard").status_code == 200
        finally:
            event.remove(db.engine, "before_cursor_execute", count)

    assert len(statements) <= 16, len(statements)
