"""Las pantallas de la reasignación masiva (`/reassign`, docs/11 UI-007, docs/07 CU-014).

Flujo: elegir → revisar (no cambia nada) → confirmar → resultado. Lo importante: solo el
Supervisor y el Administrador entran (403 al resto, también en los POST), el resumen es
exactamente lo que se ejecuta, el servidor no confía en lo que viaja en el formulario (todo
se valida de nuevo al confirmar), y un doble envío no duplica nada.
"""

import re

import pytest
from sqlalchemy import event

from src.workdesk.extensions import db
from src.workdesk.models import Notificacion, TicketTechnician, User
from src.workdesk.tickets.assignment import assign_technician
from tests.demo_data import DEMO_PASSWORD
from tests.ticket_helpers import (
    audit_entries,
    login,
    make_ticket,
    set_state,
    ticket_by_public_id,
)
from tests.ticket_helpers import (
    plain_text as text,
)


@pytest.fixture()
def team(make_user, catalog):
    return {
        "req": make_user("SOLICITANTE", username="req1"),
        "boss": make_user("SUPERVISOR", username="jefa"),
        "admin": make_user("ADMINISTRADOR", username="admin1"),
        "tec": make_user("TECNICO", username="tecnico1"),
        "origin": make_user("TECNICO", username="origen", nombre="Valentina", apellido="Pizarro"),
        "dest1": make_user("TECNICO", username="destino1", nombre="Diego", apellido="Soto"),
        "dest2": make_user("TECNICO", username="destino2", nombre="Felipe", apellido="Araya"),
    }


def assigned(app, catalog, team, count=3, priority="medium"):
    numbers = []

    for _ in range(count):
        number = make_ticket(
            app,
            catalog,
            team["req"]["id"],
            requester_ids=[team["req"]["id"]],
            priority_id=catalog[priority],
        )

        with app.app_context():
            assign_technician(
                ticket_by_public_id(number),
                team["origin"]["id"],
                actor=db.session.get(User, team["boss"]["id"]),
            )
            db.session.commit()

        numbers.append(number)

    return numbers


def ids(app, numbers):
    with app.app_context():
        return [ticket_by_public_id(n).id for n in numbers]


def technicians_of(app, number):
    with app.app_context():
        return sorted(a.tecnico.username for a in ticket_by_public_id(number).tecnicos_vigentes)


def review_data(app, team, numbers, destinations=("dest1",), reason="Vacaciones", **extra):
    return {
        "origen": team["origin"]["id"],
        "tickets": ids(app, numbers),
        "destinos": [team[d]["id"] for d in destinations],
        "motivo": reason,
        **extra,
    }


def confirm_data(app, team, numbers, destinations=("dest1",), reason="Vacaciones"):
    ticket_ids = sorted(ids(app, numbers))

    return {
        "origen": team["origin"]["id"],
        "motivo": reason,
        "movimientos": [
            f"{ticket_id}:{team[destinations[i % len(destinations)]]['id']}"
            for i, ticket_id in enumerate(ticket_ids)
        ],
    }


# --- Quién entra ------------------------------------------------------------------------------


@pytest.mark.parametrize("role", ["req", "tec"])
def test_requesters_and_technicians_get_403_everywhere(app, client, team, role):
    login(client, team[role])

    assert client.get("/reassign").status_code == 403
    assert client.post("/reassign/review", data={}).status_code == 403
    assert client.post("/reassign/confirm", data={}).status_code == 403


@pytest.mark.parametrize("role", ["boss", "admin"])
def test_supervisors_and_administrators_enter(app, client, team, role):
    login(client, team[role])

    assert client.get("/reassign").status_code == 200


def test_the_menu_entry_is_only_for_supervisors_and_administrators(app, client, team):
    for role, visible in (("boss", True), ("admin", True), ("tec", False), ("req", False)):
        login(client, team[role])
        html = client.get("/dashboard").get_data(as_text=True)

        assert ('href="/reassign"' in html) is visible, role
        client.post("/logout")


def test_a_forged_post_by_a_technician_changes_nothing(app, client, catalog, team):
    numbers = assigned(app, catalog, team, count=2)
    login(client, team["tec"])

    response = client.post("/reassign/confirm", data=confirm_data(app, team, numbers))

    assert response.status_code == 403
    assert all(technicians_of(app, n) == ["origen"] for n in numbers)


# --- Paso 1: elegir ------------------------------------------------------------------------------


def test_the_first_step_lists_the_technicians_with_their_load(app, client, catalog, team):
    assigned(app, catalog, team, count=2)
    login(client, team["boss"])
    content = text(client.get("/reassign"))

    assert "Pizarro, Valentina — 2 activos" in content
    assert "Soto, Diego — 0 activos" in content
    assert "Reasignación masiva" in content


def test_an_inactive_technician_with_work_can_be_chosen(app, client, catalog, team):
    numbers = assigned(app, catalog, team, count=2)

    with app.app_context():
        db.session.get(User, team["origin"]["id"]).activo = False
        db.session.commit()

    login(client, team["boss"])
    page = client.get(f"/reassign?origen={team['origin']['id']}")
    content = text(page)

    assert "(inactivo)" in content
    assert "está desactivado" in content
    assert all(f"#{n}" in content for n in numbers)
    assert "Pizarro, Valentina" not in content.split("Técnicos de destino")[1]


def test_the_origin_page_shows_its_tickets_all_marked_and_the_destinations(app, client, catalog, team):
    numbers = assigned(app, catalog, team, count=3)
    login(client, team["boss"])
    html = client.get(f"/reassign?origen={team['origin']['id']}").get_data(as_text=True)

    assert len(re.findall(r'name="tickets"[^>]*checked', html, re.DOTALL)) == 3
    assert all(f"#{n}" in text_of(html) for n in numbers)
    assert "Soto, Diego" in html and "Araya, Felipe" in html
    # El origen no es destino de sí mismo.
    destinations = html.split("Técnicos de destino")[1]

    assert "Pizarro" not in destinations


def text_of(html):
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def test_the_filters_narrow_the_list(app, client, catalog, team):
    low = assigned(app, catalog, team, count=2, priority="medium")
    high = assigned(app, catalog, team, count=1, priority="high")
    login(client, team["boss"])
    base = f"/reassign?origen={team['origin']['id']}"
    content = text(client.get(f"{base}&prioridad={catalog['high']}"))

    assert f"#{high[0]}" in content
    assert not any(f"#{n}" in content for n in low)


def test_closed_and_resolved_tickets_are_not_offered(app, client, catalog, team):
    open_one, closed, resolved = assigned(app, catalog, team, count=3)
    set_state(app, closed, "CERRADO")
    set_state(app, resolved, "RESUELTO")
    login(client, team["boss"])
    content = text(client.get(f"/reassign?origen={team['origin']['id']}"))

    assert f"#{open_one}" in content
    assert f"#{closed}" not in content and f"#{resolved}" not in content


def test_an_unknown_origin_shows_only_the_first_step(app, client, team):
    login(client, team["boss"])
    content = text(client.get("/reassign?origen=999999"))

    assert "Técnico de origen" in content
    assert "Técnicos de destino" not in content


# --- Paso 2: revisar -------------------------------------------------------------------------------


def test_the_review_shows_the_plan_and_changes_nothing(app, client, catalog, team):
    numbers = assigned(app, catalog, team, count=3)
    login(client, team["boss"])
    page = client.post("/reassign/review", data=review_data(app, team, numbers, ("dest1", "dest2")))
    content = text(page)

    assert page.status_code == 200
    assert "Todavía no se cambió nada" in content
    assert "Vacaciones" in content
    assert all(f"#{n}" in content for n in numbers)
    assert content.count("Diego Soto") >= 2 and "Felipe Araya" in content
    assert "Quedaría con" in content
    # Nada cambió.
    assert all(technicians_of(app, n) == ["origen"] for n in numbers)

    with app.app_context():
        assert [e for e in audit_entries() if e.accion == "REASIGNACION_MASIVA"] == []


def test_the_review_carries_exactly_the_plan_to_confirm(app, client, catalog, team):
    numbers = assigned(app, catalog, team, count=4)
    login(client, team["boss"])
    html = client.post(
        "/reassign/review", data=review_data(app, team, numbers, ("dest1", "dest2"))
    ).get_data(as_text=True)

    moves = re.findall(r'name="movimientos"\s+value="(\d+):(\d+)"', html)
    expected = confirm_data(app, team, numbers, ("dest1", "dest2"))["movimientos"]

    assert [f"{a}:{b}" for a, b in moves] == expected


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"tickets": []}, "al menos un ticket"),
        ({"destinos": []}, "al menos un técnico de destino"),
        ({"motivo": "   "}, "motivo"),
        ({"motivo": "x" * 501}, "500"),
        ({"destinos": ["boss"]}, "activos de la lista"),
        ({"destinos": ["origin"]}, "activos de la lista"),
    ],
)
def test_the_review_reports_what_is_wrong_and_keeps_the_selection(
    app, client, catalog, team, change, message
):
    numbers = assigned(app, catalog, team, count=2)
    data = review_data(app, team, numbers)

    for key, value in change.items():
        data[key] = [team[v]["id"] for v in value] if key == "destinos" else value

    login(client, team["boss"])
    page = client.post("/reassign/review", data=data)
    content = text(page)

    assert page.status_code == 200
    assert message in content
    assert "Técnicos de destino" in content
    assert all(technicians_of(app, n) == ["origen"] for n in numbers)


def test_the_review_drops_tickets_the_origin_no_longer_has(app, client, catalog, team):
    kept, taken = assigned(app, catalog, team, count=2)

    with app.app_context():
        link = db.session.scalar(
            db.select(TicketTechnician).where(
                TicketTechnician.ticket_id == ticket_by_public_id(taken).id
            )
        )
        link.fecha_desasignacion = link.fecha_asignacion
        db.session.commit()

    login(client, team["boss"])
    content = text(
        client.post("/reassign/review", data=review_data(app, team, [kept, taken]), follow_redirects=True)
    )

    assert f"#{kept}" in content and "Todavía no se cambió nada" in content
    assert "ya no estaban asignados" in content


def test_the_review_with_nothing_still_assigned_says_so(app, client, catalog, team):
    [number] = assigned(app, catalog, team, count=1)
    set_state(app, number, "CERRADO")
    login(client, team["boss"])
    content = text(client.post("/reassign/review", data=review_data(app, team, [number])))

    assert "Ninguno de esos tickets sigue asignado" in content


def test_a_review_without_a_valid_origin_goes_back_to_the_start(app, client, team):
    login(client, team["boss"])
    response = client.post("/reassign/review", data={"origen": 999999, "motivo": "x"})

    assert response.status_code == 302 and response.headers["Location"].endswith("/reassign")


# --- Paso 3: confirmar --------------------------------------------------------------------------------


def test_confirming_moves_the_tickets_and_shows_the_result(app, client, catalog, team):
    numbers = assigned(app, catalog, team, count=3)
    login(client, team["boss"])
    page = client.post(
        "/reassign/confirm", data=confirm_data(app, team, numbers, ("dest1", "dest2"))
    )
    content = text(page)

    assert page.status_code == 200
    assert "Reasignación terminada" in content
    assert "Se reasignaron 3 tickets" in content
    assert technicians_of(app, numbers[0]) == ["destino1"]
    assert technicians_of(app, numbers[1]) == ["destino2"]

    with app.app_context():
        entries = [e for e in audit_entries() if e.accion == "REASIGNACION_MASIVA"]

        assert len(entries) == 1 and entries[0].motivo == "Vacaciones"


def test_the_full_flow_from_the_screens(app, client, catalog, team):
    numbers = assigned(app, catalog, team, count=2)
    login(client, team["admin"])

    reviewed = client.post("/reassign/review", data=review_data(app, team, numbers)).get_data(as_text=True)
    moves = re.findall(r'name="movimientos"\s+value="([^"]+)"', reviewed)
    result = client.post(
        "/reassign/confirm",
        data={"origen": team["origin"]["id"], "motivo": "Vacaciones", "movimientos": moves},
    )

    assert "Se reasignaron 2 tickets" in text(result)
    assert all(technicians_of(app, n) == ["destino1"] for n in numbers)


def test_a_double_submit_does_not_duplicate_anything(app, client, catalog, team):
    numbers = assigned(app, catalog, team, count=2)
    data = confirm_data(app, team, numbers)
    login(client, team["boss"])
    client.post("/reassign/confirm", data=data)
    second = text(client.post("/reassign/confirm", data=data))

    assert "No se pudo reasignar ningún ticket" in second
    assert second.count("ya no está asignado") == 2
    assert all(technicians_of(app, n) == ["destino1"] for n in numbers)

    with app.app_context():
        assert len([e for e in audit_entries() if e.accion == "REASIGNACION_MASIVA"]) == 1


def test_a_closed_ticket_is_reported_as_skipped(app, client, catalog, team):
    first, second = assigned(app, catalog, team, count=2)
    data = confirm_data(app, team, [first, second])
    set_state(app, second, "CERRADO")
    login(client, team["boss"])
    content = text(client.post("/reassign/confirm", data=data))

    assert "Se reasignaron 1 ticket." in content and "1 se omitió" in content
    assert "Omitidos" in content and "El ticket está cerrado." in content


def test_the_server_does_not_trust_the_hidden_fields(app, client, catalog, team):
    numbers = assigned(app, catalog, team, count=2)
    other = assigned(app, catalog, team, count=1)[0]

    with app.app_context():
        # Un ticket de otro técnico colado en el envío.
        link = db.session.scalar(
            db.select(TicketTechnician).where(
                TicketTechnician.ticket_id == ticket_by_public_id(other).id
            )
        )
        link.fecha_desasignacion = link.fecha_asignacion
        db.session.commit()
        assign_technician(
            ticket_by_public_id(other),
            team["dest2"]["id"],
            actor=db.session.get(User, team["boss"]["id"]),
        )
        db.session.commit()

    data = confirm_data(app, team, [*numbers, other])
    login(client, team["boss"])
    content = text(client.post("/reassign/confirm", data=data))

    assert "Se reasignaron 2 tickets" in content
    assert technicians_of(app, other) == ["destino2"]


@pytest.mark.parametrize(
    "tamper",
    [
        lambda data, team: data.update(movimientos=["abc"]),
        lambda data, team: data.update(movimientos=["1:2:3"]),
        lambda data, team: data.update(movimientos=[]),
        lambda data, team: data.update(origen=""),
        lambda data, team: data.update(motivo=""),
    ],
)
def test_tampered_confirmations_are_rejected_without_changes(app, client, catalog, team, tamper):
    numbers = assigned(app, catalog, team, count=2)
    data = confirm_data(app, team, numbers)
    tamper(data, team)
    login(client, team["boss"])
    response = client.post("/reassign/confirm", data=data)

    assert response.status_code == 302
    assert all(technicians_of(app, n) == ["origen"] for n in numbers)


def test_a_non_technician_destination_is_rejected_without_changes(app, client, catalog, team):
    numbers = assigned(app, catalog, team, count=2)
    data = confirm_data(app, team, numbers)
    data["movimientos"] = [f"{ticket_id}:{team['boss']['id']}" for ticket_id in sorted(ids(app, numbers))]
    login(client, team["boss"])
    response = client.post("/reassign/confirm", data=data, follow_redirects=True)

    assert "activos de la lista" in text(response)
    assert all(technicians_of(app, n) == ["origen"] for n in numbers)


def test_the_requester_is_told_the_technician_changed_but_not_why(app, client, catalog, team):
    [number] = assigned(app, catalog, team, count=1)
    login(client, team["boss"])
    client.post("/reassign/confirm", data=confirm_data(app, team, [number], reason="Motivo reservado"))

    with app.app_context():
        messages = list(
            db.session.scalars(
                db.select(Notificacion.mensaje)
                .join(User, User.id == Notificacion.usuario_id)
                .where(User.username == "req1")
            )
        )

    assert any("Diego Soto" in m for m in messages)
    assert not any("Motivo reservado" in m for m in messages)


# --- Carga de trabajo y datos de demostración ----------------------------------------------------------


def test_the_workload_links_to_the_reassignment_only_for_those_who_can_use_it(seeded, client):
    login(client, {"username": "camila.rojas", "password": DEMO_PASSWORD})
    supervisor = client.get("/workload").get_data(as_text=True)

    assert "Ir a reasignación" in supervisor and "/reassign?origen=" in supervisor

    client.post("/logout")
    login(client, {"username": "diego.soto", "password": DEMO_PASSWORD})
    technician = client.get("/workload").get_data(as_text=True)

    assert "Ir a reasignación" not in technician and "/reassign" not in technician


def test_emptying_a_demonstration_technician_through_the_screens(seeded, client, app):
    with app.app_context():
        origin = db.session.scalar(db.select(User).where(User.username == "valentina.pizarro"))
        origin_id = origin.id
        targets = [
            db.session.scalar(db.select(User.id).where(User.username == name))
            for name in ("diego.soto", "felipe.araya")
        ]

    login(client, {"username": "camila.rojas", "password": DEMO_PASSWORD})
    page = client.get(f"/reassign?origen={origin_id}").get_data(as_text=True)
    tickets = re.findall(r'name="tickets"\s+value="(\d+)"', page)

    assert len(tickets) >= 8

    reviewed = client.post(
        "/reassign/review",
        data={"origen": origin_id, "tickets": tickets, "destinos": targets, "motivo": "Vacaciones"},
    ).get_data(as_text=True)
    moves = re.findall(r'name="movimientos"\s+value="([^"]+)"', reviewed)

    assert len(moves) == len(tickets)

    result = text(
        client.post(
            "/reassign/confirm",
            data={"origen": origin_id, "motivo": "Vacaciones", "movimientos": moves},
        )
    )

    assert f"Se reasignaron {len(tickets)} tickets" in result

    workload = text(client.get("/workload"))

    assert "Valentina Pizarro" in workload
    assert "Sin tickets activos" in workload


# --- Consultas ----------------------------------------------------------------------------------------------------


def count_queries(app, call):
    statements = []

    def record(conn, cursor, statement, *args):
        statements.append(statement)

    with app.app_context():
        event.listen(db.engine, "before_cursor_execute", record)

        try:
            call()
        finally:
            event.remove(db.engine, "before_cursor_execute", record)

    return len(statements)


def test_the_origin_page_costs_the_same_with_few_or_many_tickets(app, client, catalog, team):
    assigned(app, catalog, team, count=2)
    login(client, team["boss"])
    url = f"/reassign?origen={team['origin']['id']}"
    few = count_queries(app, lambda: client.get(url))

    assigned(app, catalog, team, count=15)
    many = count_queries(app, lambda: client.get(url))

    assert few == many
    assert many <= 30
