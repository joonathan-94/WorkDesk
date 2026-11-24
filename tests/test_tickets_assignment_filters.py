"""Filtros del listado por técnico, grupo, «sin asignar», «en trabajo», «esperan mi
revisión» y «cerrado desde», y las columnas Técnico(s) y Grupo.

Son el destino de los enlaces de los dashboards y de la carga de trabajo: cada contador
tiene que poder abrir el listado que lo explica. Técnico, grupo y «sin asignar» son solo
del personal (el grupo es un dato interno); «esperan mi revisión» solo vale para un
Solicitante.
"""

import re
from datetime import UTC, datetime

import pytest

from src.workdesk.extensions import db
from src.workdesk.models import Grupo, TicketTechnician
from src.workdesk.tickets.assignment import assign_technician
from src.workdesk.tickets.queries import TAB_ALL, TicketFilters, list_tickets
from tests.ticket_helpers import (
    login,
    make_ticket,
    set_state,
    text,
    ticket_by_public_id,
)


@pytest.fixture()
def team(make_user, catalog):
    return {
        "ana": make_user("TECNICO", username="ana"),
        "beto": make_user("TECNICO", username="beto"),
        "boss": make_user("SUPERVISOR", username="jefa"),
        "req": make_user("SOLICITANTE", username="req"),
        "other": make_user("SOLICITANTE", username="other"),
    }


def user_of(app, data):
    from src.workdesk.models import User

    return db.session.get(User, data["id"])


def numbers(app, who, **filters):
    """Los números de los tickets que `who` ve con esos filtros (todas las pestañas)."""
    with app.app_context():
        page = list_tickets(user_of(app, who), TicketFilters(**filters), tab=TAB_ALL)

        return {ticket.public_id for ticket in page.items}


def assign(app, number, technician, actor):
    with app.app_context():
        assign_technician(
            ticket_by_public_id(number), technician["id"], actor=user_of(app, actor)
        )
        db.session.commit()


def unassign(app, number, technician):
    with app.app_context():
        link = db.session.scalar(
            db.select(TicketTechnician).where(
                TicketTechnician.ticket_id == ticket_by_public_id(number).id,
                TicketTechnician.tecnico_id == technician["id"],
            )
        )
        link.fecha_desasignacion = datetime.now(UTC)
        db.session.commit()


def group_ticket(app, number, name):
    with app.app_context():
        group = Grupo(nombre=name)
        db.session.add(group)
        db.session.flush()
        ticket_by_public_id(number).grupo_id = group.id
        db.session.commit()

        return group.id


@pytest.fixture()
def scene(app, catalog, team):
    """Cinco tickets: de Ana, de Beto, de los dos, sin asignar y de Ana pero retirada."""
    boss = team["boss"]
    made = {
        name: make_ticket(app, catalog, boss["id"], title=f"Ticket {name}")
        for name in ("ana", "beto", "both", "none", "retired")
    }
    assign(app, made["ana"], team["ana"], boss)
    assign(app, made["beto"], team["beto"], boss)
    assign(app, made["both"], team["ana"], boss)
    assign(app, made["both"], team["beto"], boss)
    assign(app, made["retired"], team["ana"], boss)
    unassign(app, made["retired"], team["ana"])

    return made


# --- Técnico y «sin asignar» ---------------------------------------------------------------


def test_the_technician_filter_uses_the_current_assignments(app, team, scene):
    ana = numbers(app, team["boss"], technician_id=team["ana"]["id"])

    # Un ticket con dos técnicos cuenta para cada uno; el retirado ya no.
    assert ana == {scene["ana"], scene["both"]}
    assert numbers(app, team["boss"], technician_id=team["beto"]["id"]) == {
        scene["beto"],
        scene["both"],
    }


def test_unassigned_means_no_current_technician(app, team, scene):
    assert numbers(app, team["boss"], unassigned=True) == {scene["none"], scene["retired"]}


def test_a_technician_who_works_nowhere_matches_nothing(app, team, scene, make_user):
    idle = make_user("TECNICO", username="idle")

    assert numbers(app, team["boss"], technician_id=idle["id"]) == set()


# --- Grupo ---------------------------------------------------------------------------------


def test_the_group_filter(app, team, scene):
    group_id = group_ticket(app, scene["ana"], "Soporte")
    group_ticket(app, scene["beto"], "Redes")

    assert numbers(app, team["boss"], group_id=group_id) == {scene["ana"]}


# --- En trabajo ----------------------------------------------------------------------------


def test_active_only_leaves_out_resolved_and_closed(app, team, scene):
    set_state(app, scene["ana"], "RESUELTO")
    set_state(app, scene["beto"], "CERRADO")

    active = numbers(app, team["boss"], active_only=True)

    assert active == {scene["both"], scene["none"], scene["retired"]}


def test_active_only_combines_with_the_technician(app, team, scene):
    set_state(app, scene["ana"], "RESUELTO")

    assert numbers(
        app, team["boss"], technician_id=team["ana"]["id"], active_only=True
    ) == {scene["both"]}


# --- Esperan mi revisión (Solicitante) --------------------------------------------------------


@pytest.fixture()
def review_scene(app, catalog, team):
    boss, req, other = team["boss"], team["req"], team["other"]
    made = {
        "mine": make_ticket(app, catalog, boss["id"], requester_ids=[req["id"]]),
        "theirs": make_ticket(app, catalog, boss["id"], requester_ids=[other["id"]]),
        # Lo creó el solicitante pero no figura como tal: lo ve, no puede validarlo.
        "created_only": make_ticket(app, catalog, req["id"]),
        "open": make_ticket(app, catalog, boss["id"], requester_ids=[req["id"]]),
    }
    for key in ("mine", "theirs", "created_only"):
        set_state(app, made[key], "RESUELTO")

    # `created_only` lo crea el solicitante, que queda como su propio solicitante: se lo
    # quita para que solo sea el creador.
    with app.app_context():
        from src.workdesk.models import TicketRequester

        for link in db.session.scalars(
            db.select(TicketRequester).where(
                TicketRequester.ticket_id == ticket_by_public_id(made["created_only"]).id
            )
        ):
            link.fecha_retiro = datetime.now(UTC)
        db.session.commit()

    return made


def test_pending_review_is_the_resolved_tickets_where_I_am_a_current_requester(
    app, team, review_scene
):
    assert numbers(app, team["req"], pending_review=True) == {review_scene["mine"]}


def test_without_the_filter_the_requester_sees_the_resolved_ones_he_cannot_validate(
    app, team, review_scene
):
    visible = numbers(app, team["req"])

    assert {review_scene["mine"], review_scene["created_only"], review_scene["open"]} <= visible
    assert review_scene["theirs"] not in visible


def test_pending_review_means_nothing_for_the_staff(app, team, review_scene):
    everything = numbers(app, team["boss"])

    assert numbers(app, team["boss"], pending_review=True) == everything


# --- Cerrado desde -------------------------------------------------------------------------


def test_closed_since_counts_local_days(app, team, scene):
    app.config["APP_TIMEZONE"] = "America/Santiago"
    # En noviembre Santiago va a UTC-3: la medianoche local del día 10 son las 03:00 UTC.
    before = datetime(2026, 11, 10, 2, 59, 59, tzinfo=UTC)
    exactly = datetime(2026, 11, 10, 3, 0, 0, tzinfo=UTC)

    for key, moment in (("ana", before), ("beto", exactly)):
        set_state(app, scene[key], "CERRADO")

        with app.app_context():
            ticket_by_public_id(scene[key]).fecha_cierre = moment
            db.session.commit()

    from datetime import date

    closed = numbers(app, team["boss"], closed_from=date(2026, 11, 10))

    assert closed == {scene["beto"]}


# --- Lo que un Solicitante no puede usar -----------------------------------------------------------


def test_a_requester_cannot_filter_by_technician_group_or_assignment(app, team, scene, catalog):
    mine = make_ticket(app, catalog, team["req"]["id"], title="Mío")
    assign(app, mine, team["ana"], team["boss"])
    group_id = group_ticket(app, mine, "Interno")

    everything = numbers(app, team["req"])

    assert mine in everything

    for filters in (
        {"technician_id": team["beto"]["id"]},
        {"unassigned": True},
        {"group_id": group_id + 100},
    ):
        assert numbers(app, team["req"], **filters) == everything


# --- Pantalla --------------------------------------------------------------------------------


def listed(response):
    return list(
        dict.fromkeys(re.findall(r'href="/tickets/(\d+)"', response.get_data(as_text=True)))
    )


def test_the_staff_sees_the_technician_and_group_columns(app, client, team, scene):
    group_ticket(app, scene["ana"], "Soporte Redes")
    login(client, team["boss"])

    page = text(client.get("/tickets?vista=todos"))

    assert "Técnico(s)" in page and "Grupo" in page
    assert "Soporte Redes" in page
    assert "Sin asignar" in page


def test_the_requester_sees_neither_technicians_nor_groups_in_the_list(
    app, client, team, scene, catalog
):
    mine = make_ticket(app, catalog, team["req"]["id"], title="Mío")
    assign(app, mine, team["ana"], team["boss"])
    group_ticket(app, mine, "Soporte Interno")
    login(client, team["req"])

    page = text(client.get("/tickets?vista=todos"))

    assert "Técnico(s)" not in page
    assert "Soporte Interno" not in page
    assert 'name="tecnico"' not in client.get("/tickets").get_data(as_text=True)


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("tecnico={ana}", {"ana", "both"}),
        ("tecnico=ninguno", {"none", "retired"}),
        ("tecnico=ninguno&activos=1", {"none", "retired"}),
    ],
)
def test_the_urls_of_the_dashboards_open_the_matching_list(
    app, client, team, scene, query, expected
):
    login(client, team["boss"])
    url = "/tickets?vista=todos&" + query.format(ana=team["ana"]["id"])

    shown = set(listed(client.get(url)))
    wanted = {scene[key] for key in expected if key in scene}

    assert shown == wanted


def test_invalid_values_in_the_url_are_ignored(app, client, team, scene):
    login(client, team["boss"])
    everything = set(listed(client.get("/tickets?vista=todos")))

    for query in ("tecnico=abc", "tecnico=99999", "grupo=99999", "grupo=x", "cerrado_desde=ayer"):
        assert set(listed(client.get(f"/tickets?vista=todos&{query}"))) == everything, query


def test_the_filters_survive_a_change_of_tab_and_page(app, client, team, scene):
    login(client, team["boss"])

    page = client.get(f"/tickets?tecnico={team['ana']['id']}&activos=1").get_data(as_text=True)

    assert f"tecnico={team['ana']['id']}" in page
    assert "activos=1" in page


def test_a_requester_url_with_staff_parameters_shows_all_his_tickets(
    app, client, team, scene, catalog
):
    mine = make_ticket(app, catalog, team["req"]["id"], title="Mío")
    login(client, team["req"])

    assert mine in listed(client.get("/tickets?vista=todos&tecnico=ninguno&grupo=1"))


def test_the_review_filter_in_the_url(app, client, team, review_scene):
    login(client, team["req"])

    assert listed(client.get("/tickets?vista=todos&revision=1")) == [review_scene["mine"]]


def test_the_at_risk_option_is_offered_to_the_staff_only(app, client, team, scene):
    login(client, team["boss"])

    assert "En riesgo (próximo o vencido)" in client.get("/tickets").get_data(as_text=True)
    assert client.get("/tickets?sla=riesgo").status_code == 200

    client.post("/logout")
    login(client, team["req"])

    assert "En riesgo" not in client.get("/tickets").get_data(as_text=True)
