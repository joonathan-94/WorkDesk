"""El dashboard operacional del personal (`dashboard/staff.py`, UI-002, RF-093 a RF-096).

La regla central de la fase: **cada contador coincide con el total del listado al que enlaza**.
Se comprueba leyendo los enlaces de la propia página y resolviéndolos con los filtros del
listado. Lo demás: qué ve cada rol (Mi trabajo solo el Técnico, Administración solo el
Administrador), el orden de los tickets prioritarios, que la actividad reciente nunca copia el
contenido de un comentario y que el costo en consultas es fijo.
"""

import html as htmllib
import re
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pytest

from src.workdesk.dashboard.staff import (
    PRIORITY_TICKETS,
    RECENT_ACTIVITY,
    RESOLVED_WINDOW_DAYS,
    staff_dashboard,
)
from src.workdesk.extensions import db
from src.workdesk.formatting import start_of_local_day
from src.workdesk.models import Estado, Prioridad, Ticket, TicketHistory, User
from src.workdesk.tickets.comments import add_comment
from src.workdesk.tickets.queries import TAB_ALL, TAB_OPEN, list_tickets
from tests.demo_data import DEMO_PASSWORD, NOW, SOLICITANTES
from tests.test_workload_screen import KPI, filters_of
from tests.ticket_helpers import login, make_ticket, text

STAFF = {"TECNICO": "diego.soto", "SUPERVISOR": "camila.rojas"}


def sign_in(client, username):
    login(client, {"username": username, "password": DEMO_PASSWORD})


def user(username):
    return db.session.scalar(db.select(User).where(User.username == username))


def total_of(app, href):
    """El total del listado al que lleva `href` (pestaña «Abiertos» si no indica otra)."""
    clean = htmllib.unescape(href)
    tab = parse_qs(urlparse(clean).query).get("vista", ["abiertos"])[0]

    with app.app_context():
        return list_tickets(
            user("camila.rojas"),
            filters_of(href, app),
            tab=TAB_ALL if tab == "todos" else TAB_OPEN,
        ).total


# --- Cada cifra es el total de su listado -------------------------------------------------


@pytest.mark.parametrize("role", STAFF)
def test_every_counter_equals_the_total_of_the_list_it_links_to(seeded, client, app, role):
    sign_in(client, STAFF[role])
    cards = KPI.findall(client.get("/dashboard").get_data(as_text=True))
    labels = [label for _, label, _ in cards]

    assert labels == [
        "Tickets abiertos",
        "Sin asignar",
        "Críticos",
        "Fuera de SLA",
        "Próximos a vencer",
        "En espera",
    ]

    for href, label, value in cards:
        assert total_of(app, href) == int(value), label


def test_the_counters_match_the_workload_screen(seeded, client, app):
    """El dashboard y la carga de trabajo usan las mismas definiciones y cifras."""
    sign_in(client, "camila.rojas")
    dashboard = {
        label: int(value)
        for _, label, value in KPI.findall(client.get("/dashboard").get_data(as_text=True))
    }
    workload = {
        label: int(value)
        for _, label, value in KPI.findall(client.get("/workload").get_data(as_text=True))
    }

    assert dashboard["Sin asignar"] == workload["Sin asignar"]
    assert dashboard["Críticos"] == workload["Críticos"]
    assert dashboard["Fuera de SLA"] + dashboard["Próximos a vencer"] == workload["SLA en riesgo"]


def test_the_demonstration_shows_every_counter_with_something(seeded, app):
    with app.app_context():
        summary = staff_dashboard(user("camila.rojas"), now=NOW).overview.summary

        assert summary.unassigned > 0 and summary.critical > 0
        assert summary.overdue > 0 and summary.on_hold > 0


# --- Quién ve qué ---------------------------------------------------------------------------------


def test_only_the_technician_sees_my_work(seeded, client):
    sign_in(client, "diego.soto")
    assert "Mi trabajo" in text(client.get("/dashboard"))

    client.post("/logout")
    sign_in(client, "camila.rojas")
    assert "Mi trabajo" not in text(client.get("/dashboard"))


def test_only_the_administrator_sees_the_administration_block(seeded, client, make_user):
    for username in STAFF.values():
        sign_in(client, username)
        assert "Usuarios activos" not in text(client.get("/dashboard"))
        client.post("/logout")

    login(client, make_user("ADMINISTRADOR", username="jefe"))
    content = text(client.get("/dashboard"))

    assert "Usuarios activos" in content
    assert "Calendario laboral" in content
    assert "Políticas de SLA" in content
    assert "Por defecto (sin configurar)" in content
    assert "4 de 4 prioridades con política activa" in content


def test_the_administration_block_counts_the_active_users(seeded, app, make_user):
    admin = make_user("ADMINISTRADOR", username="jefe")

    with app.app_context():
        block = staff_dashboard(db.session.get(User, admin["id"]), now=NOW).admin
        active = db.session.scalar(
            db.select(db.func.count(User.id)).where(User.activo.is_(True))
        )

        assert sum(total for _, total in block.users_by_role) == active
        assert block.calendar_configured is False
        assert (block.policies_defined, block.priorities_total) == (4, 4)


@pytest.mark.parametrize("username", SOLICITANTES)
def test_a_requester_cannot_build_the_staff_dashboard(seeded, app, username):
    with app.app_context(), pytest.raises(PermissionError):
        staff_dashboard(user(username), now=NOW)


# --- Mi trabajo ------------------------------------------------------------------------------------


def test_my_work_equals_the_lists_it_links_to(seeded, client, app):
    sign_in(client, "diego.soto")
    html = client.get("/dashboard").get_data(as_text=True)
    section = html[html.index("my-work-title") : html.index("priority-title")]

    cells = re.findall(
        r'kpi-value">(\d+)</div>\s*<a\s+class="small"\s+href="([^"]+)"', section, re.DOTALL
    )

    assert len(cells) == 3

    for value, href in cells:
        assert total_of(app, href) == int(value), href


def test_resolved_by_me_counts_only_my_resolutions_in_the_last_seven_days(seeded, app):
    with app.app_context():
        for username in ("diego.soto", "felipe.araya", "valentina.pizarro", "francisca.munoz"):
            who = user(username)
            since = start_of_local_day(
                (NOW - timedelta(days=0)).date() - timedelta(days=RESOLVED_WINDOW_DAYS)
            )
            expected = db.session.scalar(
                db.select(db.func.count(TicketHistory.id)).where(
                    TicketHistory.actor_usuario_id == who.id,
                    TicketHistory.tipo_evento == "TICKET_RESUELTO",
                    TicketHistory.fecha_hora >= since,
                )
            )

            assert staff_dashboard(who, now=NOW).my_work.resolved_recently == expected


# --- Tickets prioritarios -----------------------------------------------------------------------------


def test_the_priority_tickets_are_active_and_ordered_by_priority(seeded, app):
    with app.app_context():
        data = staff_dashboard(user("camila.rojas"), now=NOW)
        tickets = data.priority_tickets
        levels = [ticket.prioridad.nivel for ticket in tickets]

        assert 0 < len(tickets) <= PRIORITY_TICKETS
        assert levels == sorted(levels, reverse=True)

        # Empieza por la prioridad más alta que haya en trabajo, no por cualquiera.
        highest = db.session.scalar(
            db.select(db.func.max(Prioridad.nivel))
            .select_from(Ticket)
            .join(Prioridad, Prioridad.id == Ticket.prioridad_id)
            .join(Estado, Estado.id == Ticket.estado_id)
            .where(Estado.codigo.not_in(["RESUELTO", "CERRADO"]))
        )

        assert levels[0] == highest
        assert all(t.estado.codigo not in ("RESUELTO", "CERRADO") for t in tickets)
        assert set(data.slas) == {t.id for t in tickets}

        # Dentro de una misma prioridad, el que vence antes va primero.
        for level in set(levels):
            dues = [
                data.slas[t.id].due_at
                for t in tickets
                if t.prioridad.nivel == level
                and data.slas[t.id] is not None
                and data.slas[t.id].due_at is not None
            ]

            assert dues == sorted(dues)


def test_the_priority_order_is_not_offered_in_the_list(seeded, client):
    sign_in(client, "camila.rojas")

    assert client.get("/tickets?orden=prioritarios").status_code == 200
    assert 'value="prioritarios"' not in client.get("/tickets").get_data(as_text=True)


# --- Actividad reciente ---------------------------------------------------------------------------------


def test_the_activity_is_the_latest_events_newest_first(seeded, app):
    with app.app_context():
        items = staff_dashboard(user("camila.rojas"), now=NOW).activity
        newest = db.session.scalars(
            db.select(TicketHistory.id)
            .order_by(TicketHistory.fecha_hora.desc(), TicketHistory.id.desc())
            .limit(RECENT_ACTIVITY)
        ).all()

        assert [item.entry.id for item in items] == list(newest)


def test_the_activity_never_copies_the_content_of_a_comment(
    app, client, make_user, catalog
):
    staff = make_user("TECNICO", username="tec")
    solicitante = make_user("SOLICITANTE", username="sol")
    number = make_ticket(app, catalog, solicitante["id"])

    with app.app_context():
        ticket = db.session.scalar(db.select(Ticket).where(Ticket.public_id == number))
        add_comment(
            ticket,
            actor=db.session.get(User, staff["id"]),
            content="CONTENIDO-SECRETO-777",
            kind="INTERNO",
        )
        db.session.commit()

    login(client, staff)
    content = client.get("/dashboard").get_data(as_text=True)

    assert "Comentario agregado" in content
    assert "CONTENIDO-SECRETO-777" not in content


# --- Estados especiales y consultas ------------------------------------------------------------------------


def test_an_empty_system_shows_zeros_and_empty_states(client, make_user, catalog):
    login(client, make_user("SUPERVISOR", username="jefa"))
    page = client.get("/dashboard")
    content = text(page)

    assert page.status_code == 200
    assert "No hay tickets en trabajo" in content
    assert "Todavía no hay actividad" in content
    assert "críticos sin asignar" not in content


def test_the_alert_names_the_unassigned_critical_tickets(seeded, client, app):
    sign_in(client, "camila.rojas")

    with app.app_context():
        expected = staff_dashboard(user("camila.rojas")).overview.summary.unassigned_critical

    content = text(client.get("/dashboard"))

    assert expected > 0
    assert f"Hay {expected} tickets críticos sin asignar" in content or expected == 1


def test_the_dashboard_costs_a_fixed_number_of_queries(seeded, client, app, make_user):
    from tests.test_pages_smoke import QueryCounter

    sign_in(client, "camila.rojas")

    with app.app_context(), QueryCounter() as few:
        assert client.get("/dashboard").status_code == 200

    for index in range(20):
        make_user("TECNICO", username=f"extra{index}")

    with app.app_context(), QueryCounter() as many:
        assert client.get("/dashboard").status_code == 200

    assert few.count == many.count
    assert many.count <= 30


def test_a_ticket_closed_is_not_active_work(seeded, app):
    with app.app_context():
        closed = db.session.scalar(db.select(Estado.id).where(Estado.codigo == "CERRADO"))
        data = staff_dashboard(user("camila.rojas"), now=NOW)

        assert all(t.estado_id != closed for t in data.priority_tickets)
