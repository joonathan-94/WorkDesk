import re
from datetime import UTC, datetime

import pytest

from src.workdesk.extensions import db
from src.workdesk.models import Categoria, Estado
from tests.ticket_helpers import (
    login,
    make_ticket,
    plain_text,
    set_created,
    set_state,
    text,
)

STAFF_ROLES = ("TECNICO", "SUPERVISOR", "ADMINISTRADOR")
ALL_ROLES = ("SOLICITANTE",) + STAFF_ROLES


def listed(response) -> list[str]:
    """Identificadores públicos que muestra la página, en orden y sin
    repetir (cada ticket aparece en la tabla y en la tarjeta móvil)."""
    found = re.findall(
        r'href="/tickets/(\d+)"',
        response.get_data(as_text=True),
    )

    return list(dict.fromkeys(found))


@pytest.fixture()
def staff(make_user, catalog):
    return make_user("TECNICO", username="personal")


@pytest.fixture()
def staff_session(client, staff):
    login(client, staff)

    return staff


# --- Acceso -----------------------------------------------------------


def test_anonymous_user_is_redirected_to_login(client, catalog):
    response = client.get("/tickets")

    assert response.status_code == 302
    assert "/login" in response.location


@pytest.mark.parametrize("role_code", ALL_ROLES)
def test_every_role_can_open_the_list(client, make_user, catalog, role_code):
    login(client, make_user(role_code))

    assert client.get("/tickets").status_code == 200


def test_the_heading_depends_on_the_role(client, make_user, catalog):
    login(client, make_user("SOLICITANTE"))

    assert "Mis tickets" in text(client.get("/tickets"))

    client.post("/logout")
    login(client, make_user("TECNICO"))
    content = client.get("/tickets").get_data(as_text=True)

    assert '<h1 class="page-title">Tickets</h1>' in content


def test_the_navigation_label_depends_on_the_role(
    client,
    make_user,
    catalog,
):
    login(client, make_user("SOLICITANTE"))
    solicitante = client.get("/dashboard").get_data(as_text=True)

    client.post("/logout")
    login(client, make_user("TECNICO"))
    technician = client.get("/dashboard").get_data(as_text=True)

    assert 'href="/tickets"' in solicitante
    assert "Mis tickets" in solicitante
    assert 'href="/tickets"' in technician
    assert "Mis tickets" not in technician


# --- Visibilidad ------------------------------------------------------


def test_a_solicitante_only_sees_their_own_tickets(
    client,
    app,
    make_user,
    catalog,
    staff,
):
    mine = make_user("SOLICITANTE", username="mio")
    other = make_user("SOLICITANTE", username="otro")
    created = make_ticket(app, catalog, mine["id"], title="Creado por mí")
    requested = make_ticket(
        app,
        catalog,
        staff["id"],
        title="A mi nombre",
        requester_ids=[mine["id"]],
    )
    make_ticket(app, catalog, other["id"], title="De otra persona")
    make_ticket(
        app,
        catalog,
        staff["id"],
        title="Para otra persona",
        requester_ids=[other["id"]],
    )
    login(client, mine)

    response = client.get("/tickets")

    assert sorted(listed(response)) == sorted([created, requested])
    assert "De otra persona" not in text(response)
    assert "Para otra persona" not in text(response)


def test_staff_sees_everyone_s_tickets(client, app, make_user, catalog, staff_session):
    owner = make_user("SOLICITANTE", username="dueno")
    first = make_ticket(app, catalog, owner["id"])
    second = make_ticket(app, catalog, staff_session["id"])

    assert sorted(listed(client.get("/tickets"))) == sorted([first, second])


def test_staff_sees_the_requesters_column_and_a_solicitante_does_not(
    client,
    app,
    make_user,
    catalog,
    staff,
):
    mine = make_user(
        "SOLICITANTE",
        username="mio",
        nombre="Ana",
        apellido="Acosta",
    )
    other = make_user(
        "SOLICITANTE",
        username="otro",
        nombre="Beto",
        apellido="Barros",
    )
    make_ticket(
        app,
        catalog,
        staff["id"],
        requester_ids=[mine["id"], other["id"]],
    )

    login(client, mine)
    as_solicitante = plain_text(client.get("/tickets"))

    client.post("/logout")
    login(client, staff)
    as_staff = plain_text(client.get("/tickets"))

    assert "Solicitante(s)" not in as_solicitante
    assert "Beto Barros" not in as_solicitante
    assert "Solicitante(s)" in as_staff
    # Se muestra el primero y cuántos más hay.
    assert "Ana Acosta +1" in as_staff


def test_a_ticket_without_requesters_shows_a_dash_to_staff(
    client,
    app,
    catalog,
    staff_session,
):
    make_ticket(app, catalog, staff_session["id"], title="Sin solicitante")

    assert "Sin solicitante" in text(client.get("/tickets"))


# --- Pestañas ---------------------------------------------------------


@pytest.fixture()
def mixed(app, catalog, staff):
    """Un ticket nuevo, uno resuelto y uno cerrado."""
    new = make_ticket(app, catalog, staff["id"], title="Ticket nuevo")
    resolved = make_ticket(app, catalog, staff["id"], title="Ticket resuelto")
    closed = make_ticket(app, catalog, staff["id"], title="Ticket cerrado")
    set_state(app, resolved, "RESUELTO")
    set_state(app, closed, "CERRADO")

    return {"new": new, "resolved": resolved, "closed": closed}


def test_the_open_tab_is_the_default(client, mixed, staff_session):
    response = client.get("/tickets")

    assert sorted(listed(response)) == sorted([mixed["new"], mixed["resolved"]])
    assert re.search(
        r'class="nav-link active"\s+aria-current="page"[^>]*>\s*Abiertos',
        response.get_data(as_text=True),
    )


def test_the_closed_and_all_tabs(client, mixed, staff_session):
    closed = client.get("/tickets?vista=cerrados")
    everything = client.get("/tickets?vista=todos")

    assert listed(closed) == [mixed["closed"]]
    assert len(listed(everything)) == 3


def test_the_tabs_show_their_counters(client, mixed, staff_session):
    content = plain_text(client.get("/tickets"))

    assert "Todos 3 Abiertos 2 Cerrados 1" in content


def test_the_counters_follow_the_search(client, mixed, staff_session):
    content = plain_text(client.get("/tickets?q=cerrado"))

    assert "Todos 1 Abiertos 0 Cerrados 1" in content


def test_the_tab_links_keep_the_filters(client, mixed, staff_session):
    content = client.get("/tickets?q=ticket&orden=antiguos").get_data(
        as_text=True,
    )

    assert re.search(r'href="/tickets\?vista=cerrados[^"]*q=ticket', content)
    assert "orden=antiguos" in content


# --- Búsqueda y filtros -----------------------------------------------


def test_search_by_text_and_by_number(client, app, catalog, staff_session):
    vpn = make_ticket(app, catalog, staff_session["id"], title="Falla de VPN")
    make_ticket(app, catalog, staff_session["id"], title="Impresora")

    assert listed(client.get("/tickets?q=vpn")) == [vpn]
    assert listed(client.get(f"/tickets?q=%23{vpn}")) == [vpn]
    assert listed(client.get(f"/tickets?q={vpn}")) == [vpn]


def test_the_search_box_keeps_what_was_typed(client, catalog, staff_session):
    content = client.get("/tickets?q=mi+busqueda").get_data(as_text=True)

    assert 'value="mi busqueda"' in content


def test_staff_can_search_by_requester(
    client,
    app,
    make_user,
    catalog,
    staff_session,
):
    requester = make_user(
        "SOLICITANTE",
        username="zapata",
        nombre="Zoe",
        apellido="Zapata",
    )
    found = make_ticket(
        app,
        catalog,
        staff_session["id"],
        title="Sin pistas",
        requester_ids=[requester["id"]],
    )
    make_ticket(app, catalog, staff_session["id"], title="Otro")

    assert listed(client.get("/tickets?q=Zapata")) == [found]


def test_the_topbar_search_looks_in_every_tab(
    client,
    mixed,
    staff_session,
):
    dashboard = client.get("/dashboard").get_data(as_text=True)

    # El formulario de la barra superior lleva a /tickets, buscando en
    # todas las pestañas (un ticket cerrado también debe poder encontrarse).
    assert re.search(
        r'<form[^>]*action="/tickets"[^>]*role="search"',
        dashboard,
    )
    assert re.search(
        r'name="vista"\s+value="todos"',
        dashboard,
    )
    assert 'placeholder="Buscar ticket por ID o texto..."' in dashboard

    response = client.get(f"/tickets?q={mixed['closed']}&vista=todos")

    assert listed(response) == [mixed["closed"]]


def test_filter_by_state_priority_and_category(
    client,
    app,
    catalog,
    staff_session,
):
    base = make_ticket(app, catalog, staff_session["id"], title="Base")
    other = make_ticket(
        app,
        catalog,
        staff_session["id"],
        title="Otro",
        category_id=catalog["networks"],
        priority_id=catalog["high"],
    )
    set_state(app, other, "EN_PROGRESO")

    with app.app_context():
        in_progress = db.session.scalar(
            db.select(Estado.id).where(Estado.codigo == "EN_PROGRESO")
        )

    assert listed(client.get(f"/tickets?estado={in_progress}")) == [other]
    assert listed(client.get(f"/tickets?prioridad={catalog['high']}")) == [
        other
    ]
    assert listed(client.get(f"/tickets?categoria={catalog['hardware']}")) == [
        base
    ]


def test_the_selected_filters_are_marked_in_the_form(
    client,
    catalog,
    staff_session,
):
    content = client.get(
        f"/tickets?prioridad={catalog['high']}&categoria={catalog['networks']}"
    ).get_data(as_text=True)

    assert re.search(rf'value="{catalog["high"]}"\s+selected', content)
    assert re.search(rf'value="{catalog["networks"]}"\s+selected', content)


def test_filter_by_location_and_dates(client, app, catalog, staff_session):
    app.config["APP_TIMEZONE"] = "America/Santiago"
    here = make_ticket(
        app,
        catalog,
        staff_session["id"],
        title="Con ubicación",
        location_id=catalog["location"],
    )
    today = make_ticket(
        app,
        catalog,
        staff_session["id"],
        title="Sin ubicación",
    )
    set_created(app, here, datetime(2026, 3, 6, 2, 30, tzinfo=UTC))

    assert listed(
        client.get(f"/tickets?ubicacion={catalog['location']}")
    ) == [here]
    # 02:30 UTC del día 6 son las 23:30 del día 5 en Chile (UTC-3 en marzo).
    assert listed(
        client.get("/tickets?desde=2026-03-05&hasta=2026-03-05")
    ) == [here]
    # Desde el día 6 queda fuera: solo el ticket creado hoy.
    assert listed(client.get("/tickets?desde=2026-03-06")) == [today]


def test_more_filters_open_only_when_one_is_applied(
    client,
    catalog,
    staff_session,
):
    closed = client.get("/tickets").get_data(as_text=True)
    with_category = client.get(
        f"/tickets?categoria={catalog['hardware']}"
    ).get_data(as_text=True)
    with_main_filter = client.get(
        f"/tickets?prioridad={catalog['high']}"
    ).get_data(as_text=True)

    assert not re.search(r"<details\s+class=\"mt-3\"\s+open", closed)
    assert re.search(r"<details\s+class=\"mt-3\"\s+open", with_category)
    # Los filtros principales no abren "Más filtros".
    assert not re.search(r"<details\s+class=\"mt-3\"\s+open", with_main_filter)


@pytest.mark.parametrize(
    "query",
    [
        "estado=abc",
        "estado=99999",
        "prioridad=-1",
        "categoria=x",
        "ubicacion=1.5",
        "vista=inventada",
        "orden=inventado",
        "desde=2026-13-45",
        "hasta=no-es-fecha",
        "desde=",
        "page=abc",
        "page=-4",
        "page=0",
    ],
)
def test_invalid_url_values_are_ignored(client, catalog, staff_session, query):
    response = client.get(f"/tickets?{query}")

    assert response.status_code == 200


def test_invalid_values_behave_like_no_filter(
    client,
    app,
    catalog,
    staff_session,
):
    public_id = make_ticket(app, catalog, staff_session["id"])

    response = client.get("/tickets?estado=abc&vista=zzz&orden=zzz&page=abc")

    assert listed(response) == [public_id]


def test_inactive_catalog_values_can_still_be_filtered_and_are_marked(
    client,
    app,
    catalog,
    staff_session,
):
    old = make_ticket(
        app,
        catalog,
        staff_session["id"],
        title="Con categoría antigua",
        category_id=catalog["networks"],
    )

    with app.app_context():
        db.session.get(Categoria, catalog["networks"]).activo = False
        db.session.commit()

    response = client.get(f"/tickets?categoria={catalog['networks']}")

    # Un valor desactivado ya no se elige en tickets nuevos, pero sí se
    # puede filtrar: los tickets antiguos lo siguen usando.
    assert listed(response) == [old]
    assert "Redes (inactiva)" in text(response)


# --- Orden ------------------------------------------------------------


def test_the_sort_options_are_offered_and_the_current_one_is_selected(
    client,
    catalog,
    staff_session,
):
    content = client.get("/tickets?orden=prioridad").get_data(as_text=True)

    for label in (
        "Más recientes",
        "Más antiguos",
        "Mayor prioridad primero",
        "Recién actualizados",
    ):
        assert label in content

    assert re.search(r'value="prioridad"\s+selected', content)


def test_the_order_is_applied(client, app, catalog, staff_session):
    first = make_ticket(app, catalog, staff_session["id"])
    second = make_ticket(app, catalog, staff_session["id"])

    assert listed(client.get("/tickets")) == [second, first]
    assert listed(client.get("/tickets?orden=antiguos")) == [first, second]


# --- Paginación -------------------------------------------------------


@pytest.fixture()
def many(app, catalog, staff):
    # 25 tickets: dos páginas de 20 y 5.
    return [
        make_ticket(app, catalog, staff["id"], title=f"Lote {index:02d}")
        for index in range(25)
    ]


def test_the_list_is_paginated(client, many, staff_session):
    first = client.get("/tickets")
    second = client.get("/tickets?page=2")

    assert len(listed(first)) == 20
    assert len(listed(second)) == 5
    assert "Mostrando 1–20 de 25 tickets" in text(first)
    assert "Mostrando 21–25 de 25 tickets" in text(second)
    assert 'aria-label="Paginación"' in first.get_data(as_text=True)


def test_the_page_links_keep_the_search_and_the_filters(
    client,
    many,
    catalog,
    staff_session,
):
    content = client.get(
        "/tickets?q=lote&vista=todos&orden=antiguos"
    ).get_data(as_text=True)

    next_link = re.search(r'href="(/tickets\?[^"]*page=2[^"]*)"', content)

    assert next_link is not None
    assert "q=lote" in next_link.group(1)
    assert "vista=todos" in next_link.group(1)
    assert "orden=antiguos" in next_link.group(1)


def test_a_page_beyond_the_last_is_empty_not_an_error(
    client,
    many,
    staff_session,
):
    response = client.get("/tickets?page=99")

    assert response.status_code == 200
    assert listed(response) == []


def test_a_short_list_has_no_pagination(
    client,
    app,
    catalog,
    staff_session,
):
    make_ticket(app, catalog, staff_session["id"])

    content = client.get("/tickets").get_data(as_text=True)

    assert 'aria-label="Paginación"' not in content
    assert "Mostrando 1–1 de 1 ticket" in " ".join(content.split())


# --- Estados vacíos ---------------------------------------------------


def test_empty_states_for_staff(client, catalog, staff_session):
    assert "No hay tickets abiertos." in text(client.get("/tickets"))
    assert "No hay tickets cerrados." in text(
        client.get("/tickets?vista=cerrados")
    )
    assert "Todavía no hay tickets registrados." in text(
        client.get("/tickets?vista=todos")
    )


def test_empty_state_for_a_solicitante(client, make_user, catalog):
    login(client, make_user("SOLICITANTE"))

    assert "Todavía no tienes tickets." in text(
        client.get("/tickets?vista=todos")
    )


def test_a_search_without_results_offers_to_clear_the_filters(
    client,
    app,
    catalog,
    staff_session,
):
    make_ticket(app, catalog, staff_session["id"])

    response = client.get("/tickets?q=nadacoincide")

    assert "No se encontraron tickets con esos criterios." in text(response)
    assert "Limpiar filtros" in text(response)


# --- Contenido --------------------------------------------------------


def test_the_rows_show_the_ticket_data(
    client,
    app,
    catalog,
    staff_session,
):
    public_id = make_ticket(
        app,
        catalog,
        staff_session["id"],
        title="Falla de VPN",
        category_id=catalog["networks"],
        priority_id=catalog["high"],
    )

    response = client.get("/tickets")
    content = text(response)

    assert f"#{public_id}" in content
    assert "Falla de VPN" in content
    assert "Nuevo" in content
    assert "Alta" in content
    assert "Redes" in content
    assert re.search(r"\d{2}-\d{2}-\d{4} \d{2}:\d{2}", content)
    assert f'href="/tickets/{public_id}"' in response.get_data(as_text=True)


def test_the_list_has_cards_for_small_screens(
    client,
    app,
    catalog,
    staff_session,
):
    make_ticket(app, catalog, staff_session["id"])

    content = client.get("/tickets").get_data(as_text=True)

    assert "d-none d-md-block" in content
    assert "d-md-none" in content


def test_ticket_titles_are_escaped_in_the_list(
    client,
    app,
    catalog,
    staff_session,
):
    make_ticket(
        app,
        catalog,
        staff_session["id"],
        title="<script>alert(1)</script>",
    )

    content = client.get("/tickets").get_data(as_text=True)

    assert "<script>alert(1)</script>" not in content
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in content


def test_the_list_offers_to_create_a_ticket(client, catalog, staff_session):
    content = client.get("/tickets").get_data(as_text=True)

    assert 'href="/tickets/new"' in content


# --- Detalle y formulario ---------------------------------------------


@pytest.mark.parametrize(
    ("role_code", "label"),
    [("SOLICITANTE", "Mis tickets"), ("TECNICO", "Tickets")],
)
def test_the_detail_links_back_to_the_list(
    client,
    app,
    make_user,
    catalog,
    role_code,
    label,
):
    user = make_user(role_code)
    public_id = make_ticket(app, catalog, user["id"])
    login(client, user)

    content = client.get(f"/tickets/{public_id}").get_data(as_text=True)

    assert re.search(
        rf'<a href="/tickets">{label}</a>',
        content,
    )


def test_cancelling_the_form_goes_back_to_the_list(
    client,
    catalog,
    staff_session,
):
    content = client.get("/tickets/new").get_data(as_text=True)

    assert re.search(
        r'href="/tickets"\s*>\s*Cancelar',
        content,
    )
