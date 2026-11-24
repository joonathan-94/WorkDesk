"""La pantalla de carga de trabajo (`/workload`, docs/11 UI-006).

Lo importante: solo la ve el personal (403 al Solicitante, comprobado en el backend), cada
cifra enlaza con el listado que la explica y **su valor es el total de ese listado** (los
enlaces se leen de la propia página y se vuelven a resolver con los filtros del listado), y la
pantalla explica lo que podría parecer un error: un ticket con dos técnicos suma en cada uno.
"""

import html as htmllib
import re
from urllib.parse import parse_qs, urlparse

import pytest

from src.workdesk.extensions import db
from src.workdesk.models import Grupo, User
from src.workdesk.sla.queries import SlaFilter
from src.workdesk.tickets.queries import TAB_ALL, TicketFilters, list_tickets
from tests.demo_data import DEMO_PASSWORD, SOLICITANTES
from tests.ticket_helpers import login, text

# Las tarjetas y las celdas con enlace: (href, número).
KPI = re.compile(
    r'<a\s+class="kpi-card[^"]*"\s+href="([^"]+)"\s*>.*?kpi-label">([^<]+)<.*?kpi-value">(\d+)<',
    re.DOTALL,
)
CELL = re.compile(r'<a\s+href="(/tickets\?[^"]+)"\s+aria-label="(\d+) ([^:]+):', re.DOTALL)


def sign_in(client, username):
    login(client, {"username": username, "password": DEMO_PASSWORD})


def filters_of(href, app):
    """Los filtros del listado que expresa un enlace (lo mismo que lee `/tickets`)."""
    query = {key: values[0] for key, values in parse_qs(urlparse(htmllib.unescape(href)).query).items()}
    technician = query.get("tecnico")

    return TicketFilters(
        state_id=int(query["estado"]) if "estado" in query else None,
        priority_id=int(query["prioridad"]) if "prioridad" in query else None,
        group_id=int(query["grupo"]) if "grupo" in query else None,
        technician_id=int(technician) if technician and technician.isdigit() else None,
        unassigned=technician == "ninguno",
        active_only=query.get("activos") == "1",
        sla=SlaFilter(query["sla"]) if "sla" in query else None,
    )


def total_of(app, href):
    with app.app_context():
        staff = db.session.scalar(db.select(User).where(User.username == "camila.rojas"))

        return list_tickets(staff, filters_of(href, app), tab=TAB_ALL).total


# --- Quién entra -------------------------------------------------------------------------


@pytest.mark.parametrize("username", ["diego.soto", "camila.rojas"])
def test_the_staff_sees_the_workload(seeded, client, username):
    sign_in(client, username)
    page = client.get("/workload")

    assert page.status_code == 200
    assert "Carga de trabajo" in text(page)


def test_the_administrator_sees_the_workload(seeded, client, make_user):
    login(client, make_user("ADMINISTRADOR", username="jefe"))

    assert client.get("/workload").status_code == 200


@pytest.mark.parametrize("username", SOLICITANTES)
def test_a_requester_gets_403_and_no_data(seeded, client, username):
    sign_in(client, username)
    page = client.get("/workload")

    assert page.status_code == 403
    assert "Soporte Redes" not in page.get_data(as_text=True)


def test_an_anonymous_visitor_is_sent_to_login(client):
    response = client.get("/workload")

    assert response.status_code == 302 and "/login" in response.headers["Location"]


def test_the_menu_shows_the_entry_only_to_the_staff(seeded, client):
    sign_in(client, "diego.soto")
    assert 'href="/workload"' in client.get("/dashboard").get_data(as_text=True)

    client.post("/logout")
    sign_in(client, SOLICITANTES[0])
    assert 'href="/workload"' not in client.get("/dashboard").get_data(as_text=True)


# --- Cada cifra es el total de su listado ----------------------------------------------------


def test_every_linked_number_equals_the_total_of_its_list(seeded, client, app):
    sign_in(client, "camila.rojas")
    html = client.get("/workload").get_data(as_text=True)

    cards = KPI.findall(html)
    cells = CELL.findall(html)

    assert len(cards) == 4
    assert len(cells) >= 20

    for href, label, value in cards:
        assert total_of(app, href) == int(value), label

    for href, value, label in cells:
        assert total_of(app, href) == int(value), (label, href)


def test_the_filters_are_carried_into_the_links_and_the_numbers_still_match(
    seeded, client, app
):
    with app.app_context():
        group = db.session.scalar(db.select(Grupo).where(Grupo.nombre == "Soporte Redes"))
        group_id = group.id

    sign_in(client, "camila.rojas")
    html = client.get(f"/workload?grupo={group_id}").get_data(as_text=True)
    cards = KPI.findall(html)

    assert all(f"grupo={group_id}" in href for href, _, _ in cards)

    for href, label, value in cards:
        assert total_of(app, href) == int(value), label

    for href, value, label in CELL.findall(html):
        assert total_of(app, href) == int(value), (label, href)


def test_a_link_opens_the_list_it_explains(seeded, client):
    sign_in(client, "camila.rojas")
    html = client.get("/workload").get_data(as_text=True)

    for href, _, _ in KPI.findall(html):
        assert client.get(htmllib.unescape(href)).status_code == 200


# --- Contenido --------------------------------------------------------------------------------


def test_the_page_shows_every_section_and_the_demo_team(seeded, client):
    sign_in(client, "camila.rojas")
    content = text(client.get("/workload"))

    for expected in (
        "Tickets activos",
        "Sin asignar",
        "Críticos",
        "SLA en riesgo",
        "Carga por técnico",
        "Carga por grupo",
        "Soporte Redes",
        "Soporte Usuarios",
        "Aplicaciones",
        "Sin grupo",
        "Valentina Pizarro",
        "Diego Soto",
        "Felipe Araya",
        "Francisca Muñoz",
        "No es un error",
    ):
        assert expected in content, expected


def test_a_high_load_is_shown_with_text_and_does_not_block(seeded, client, app):
    app.config["WORKLOAD_HIGH_ACTIVE_TICKETS"] = 1
    sign_in(client, "camila.rojas")
    content = text(client.get("/workload"))

    assert "Carga alta" in content
    assert "no impide asignar" in content

    app.config["WORKLOAD_HIGH_ACTIVE_TICKETS"] = 0
    off = text(client.get("/workload"))

    assert "Carga alta" not in off


def test_the_distribution_bars_have_a_text_equivalent(seeded, client):
    sign_in(client, "camila.rojas")
    html = client.get("/workload").get_data(as_text=True)

    bars = re.findall(r'class="distribution"[^>]*aria-label="([^"]*)"', html)

    assert bars and all(re.search(r"\d+ \w+", label) for label in bars)


# --- Filtros de la pantalla ----------------------------------------------------------------------


def technician_names(html):
    return re.findall(r'<th scope="row">\s*<a href="/tickets[^>]*>\s*([^<]+?)\s*</a>', html)


def test_the_technician_filter_and_the_search_restrict_only_the_table(seeded, client, app):
    sign_in(client, "camila.rojas")

    with app.app_context():
        diego = db.session.scalar(db.select(User).where(User.username == "diego.soto"))
        diego_id = diego.id

    everyone = client.get("/workload").get_data(as_text=True)
    one = client.get(f"/workload?tecnico={diego_id}").get_data(as_text=True)
    found = client.get("/workload?q=pizarro").get_data(as_text=True)

    assert len(technician_names(everyone)) >= 4
    assert technician_names(one) == ["Diego Soto"]
    assert technician_names(found) == ["Valentina Pizarro"]
    # Los indicadores del equipo no cambian.
    assert KPI.findall(one) == KPI.findall(everyone)


def test_the_order_changes_the_table(seeded, client):
    sign_in(client, "camila.rojas")
    by_name = technician_names(client.get("/workload?orden=nombre").get_data(as_text=True))
    by_load = technician_names(client.get("/workload?orden=activos").get_data(as_text=True))

    assert by_name == sorted(by_name, key=lambda n: n.split()[-1])
    assert by_load[0] == "Valentina Pizarro"


def test_invalid_parameters_are_ignored(seeded, client):
    sign_in(client, "camila.rojas")

    for query in ("grupo=abc", "grupo=999999", "prioridad=-1", "estado=x", "orden=zzz",
                  "tecnico=999999", "q=" + "x" * 500):
        assert client.get(f"/workload?{query}").status_code == 200, query


def test_a_search_without_matches_says_so(seeded, client):
    sign_in(client, "camila.rojas")

    assert "Ningún técnico coincide" in text(client.get("/workload?q=zzzzzz"))


def test_an_empty_system_shows_zeros_and_no_error(client, make_user, catalog):
    login(client, make_user("SUPERVISOR", username="jefa"))
    page = client.get("/workload")

    assert page.status_code == 200
    assert "Todavía no hay grupos" in text(page)
