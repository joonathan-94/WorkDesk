"""Centro de notificaciones y campana (docs/11, UI-008 y sección 30; docs/04, RF-085 y
RF-086). Lo ven los cuatro roles, cada uno las suyas; todo lo que cambia algo es POST
con CSRF y la notificación de otra persona no existe para quien la pide."""

import re
from datetime import UTC, datetime

import pytest

from src.workdesk.extensions import db
from src.workdesk.models import Notificacion, NotificationEvent, Ticket
from src.workdesk.notifications.service import PAGE_SIZE, notify
from tests.ticket_helpers import login, make_ticket, person, plain_text

URL = "/notifications"
ROLES = ["SOLICITANTE", "TECNICO", "SUPERVISOR", "ADMINISTRADOR"]
EVENT = NotificationEvent.TICKET_ASIGNADO


# --- Auxiliares -------------------------------------------------------------


@pytest.fixture()
def tecnico(make_user, catalog):
    return make_user("TECNICO", username="tecnico")


@pytest.fixture()
def otro(make_user, tecnico):
    return make_user("TECNICO", username="otro")


@pytest.fixture()
def ticket_id(app, catalog, tecnico):
    return make_ticket(app, catalog, tecnico["id"], title="Impresora sin tinta")


def send(user_id, message="Hola", *, ticket_number=None, read=False, **extra) -> int:
    """Crea una notificación (y la marca como leída si se pide). Devuelve su id.

    Necesita el contexto de aplicación abierto: los tests lo piden con `seed`.
    """
    ticket = None

    if ticket_number is not None:
        ticket = db.session.scalar(
            db.select(Ticket).where(Ticket.public_id == ticket_number)
        )

    notification = notify(
        person(user_id),
        extra.pop("event", EVENT),
        message=message,
        ticket=ticket,
        **extra,
    )

    if read:
        notification.leida = True
        notification.fecha_lectura = datetime.now(UTC)

    db.session.commit()

    return notification.id


def status_of(app, notification_id) -> tuple[bool, object]:
    with app.app_context():
        row = db.session.get(Notificacion, notification_id)

        return row.leida, row.fecha_lectura


def unread_in_db(app, user_id) -> int:
    with app.app_context():
        return db.session.scalar(
            db.select(db.func.count(Notificacion.id)).where(
                Notificacion.usuario_id == user_id, Notificacion.leida.is_(False)
            )
        )


@pytest.fixture()
def seed(app):
    """Permite crear notificaciones con el contexto de aplicación abierto."""
    with app.app_context():
        yield


# --- Acceso -------------------------------------------------------------------


def test_an_anonymous_user_is_sent_to_the_login(client):
    for method, address in (
        (client.get, URL),
        (client.get, f"{URL}/unread-count"),
        (client.post, f"{URL}/1/read"),
        (client.post, f"{URL}/1/open"),
        (client.post, f"{URL}/read-all"),
    ):
        response = method(address)

        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


@pytest.mark.parametrize("role", ROLES)
def test_every_role_has_a_notification_center(client, make_user, catalog, role):
    login(client, make_user(role, username="persona"))
    response = client.get(URL)
    page = plain_text(response)

    assert response.status_code == 200
    assert "Notificaciones" in page
    assert "Todavía no tienes notificaciones" in page
    assert "Marcar todas como leídas" not in page


@pytest.mark.parametrize("role", ROLES)
def test_every_role_sees_the_bell_and_the_menu_option(client, make_user, catalog, role):
    login(client, make_user(role, username="persona"))
    html = client.get("/dashboard").get_data(as_text=True)

    assert "data-notifications-bell" in html
    assert f'href="{URL}"' in html
    assert re.search(r'data-label="Notificaciones"', html)


def test_the_menu_option_is_active_in_the_center(client, make_user, catalog):
    login(client, make_user("TECNICO", username="persona"))
    html = client.get(URL).get_data(as_text=True)

    assert re.search(r'data-label="Notificaciones"\s*aria-current="page"', html)


# --- El listado ----------------------------------------------------------------------


def test_the_list_shows_my_notifications_and_not_anyone_elses(
    app, client, seed, tecnico, otro
):
    send(tecnico["id"], "Aviso mío")
    send(otro["id"], "Aviso del otro")
    login(client, tecnico)
    page = plain_text(client.get(URL))

    assert "Aviso mío" in page
    assert "Aviso del otro" not in page


def test_unread_notifications_are_marked_and_read_ones_are_not(
    app, client, seed, tecnico
):
    send(tecnico["id"], "Sin leer")
    send(tecnico["id"], "Ya leída", read=True)
    login(client, tecnico)
    response = client.get(URL)
    html = response.get_data(as_text=True)

    assert html.count("notification--unread") == 1
    assert html.count('class="notification"') == 1
    # El punto azul es decoración: el estado también se dice con texto.
    assert plain_text(response).count("(no leída)") == 1
    assert html.count("notification__dot") == 2


def test_a_notification_shows_its_event_title_message_date_and_ticket(
    app, client, seed, tecnico, ticket_id
):
    send(
        tecnico["id"],
        "Se te asignó el ticket.",
        ticket_number=ticket_id,
        title="Ticket asignado",
        event=NotificationEvent.SLA_VENCIDO,
    )
    login(client, tecnico)
    page = plain_text(client.get(URL))

    assert "SLA vencido" in page
    assert "Ticket asignado" in page
    assert "Se te asignó el ticket." in page
    assert f"Ticket #{ticket_id}" in page
    assert re.search(r"\d{2}-\d{2}-\d{4} \d{2}:\d{2}", page)


def test_a_notification_without_a_title_shows_its_event_name(app, client, seed, tecnico):
    send(tecnico["id"], "Detalle", event=NotificationEvent.TICKET_REABIERTO)
    login(client, tecnico)

    # Una vez como nombre del evento y otra como título.
    assert plain_text(client.get(URL)).count("Ticket reabierto") == 2


def test_a_general_notice_without_a_ticket_has_nothing_to_open(
    app, client, seed, tecnico
):
    notification_id = send(tecnico["id"], "Aviso general")
    login(client, tecnico)
    html = client.get(URL).get_data(as_text=True)

    assert f"{URL}/{notification_id}/open" not in html
    # Pero sí se puede marcar como leída.
    assert f"{URL}/{notification_id}/read" in html


def test_a_notification_with_a_ticket_opens_it_and_can_also_be_marked(
    app, client, seed, tecnico, ticket_id
):
    notification_id = send(tecnico["id"], "Con ticket", ticket_number=ticket_id)
    login(client, tecnico)
    html = client.get(URL).get_data(as_text=True)

    # El título abre el ticket (y la marca) y el botón solo la marca.
    assert f'action="{URL}/{notification_id}/open"' in html
    assert f'action="{URL}/{notification_id}/read"' in html
    assert f'action="{URL}/read-all"' in html


def test_the_forms_keep_the_filter_and_the_page_they_were_shown_in(
    app, client, seed, tecnico
):
    for number in range(PAGE_SIZE + 5):
        send(tecnico["id"], f"Mensaje {number}")

    login(client, tecnico)

    def hidden_values(address):
        html = client.get(address).get_data(as_text=True)
        # Solo los formularios de notificaciones (el buscador de la barra superior
        # también envía un `vista`).
        forms = re.findall(
            r'<form[^>]*action="/notifications/[^"]*"[^>]*>(.*?)</form>', html, re.DOTALL
        )
        filters = {v for form in forms for v in re.findall(r'name="vista"\s+value="([^"]*)"', form)}
        pages = {v for form in forms for v in re.findall(r'name="page"\s+value="([^"]*)"', form)}

        assert forms

        return filters, pages

    # Cada formulario devuelve a la misma pestaña y a la misma página.
    assert hidden_values(f"{URL}?vista=no-leidas&page=2") == ({"no-leidas"}, {"2"})
    assert hidden_values(URL) == ({"todas"}, {"1"})


def test_the_current_tab_is_the_one_marked_active(app, client, seed, tecnico):
    send(tecnico["id"], "Hola")
    login(client, tecnico)

    def tabs(address):
        html = client.get(address).get_data(as_text=True)

        return {
            label: "active" in classes.split()
            for classes, label in re.findall(
                r'<a\s+class="([^"]*nav-link[^"]*)"[^>]*>\s*(Todas|No leídas)', html
            )
        }

    assert tabs(URL) == {"Todas": True, "No leídas": False}
    assert tabs(f"{URL}?vista=no-leidas") == {"Todas": False, "No leídas": True}


def test_the_message_is_escaped(app, client, seed, tecnico):
    send(tecnico["id"], "<script>alert(1)</script>", title="<b>negrita</b>")
    login(client, tecnico)
    html = client.get(URL).get_data(as_text=True)

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<b>negrita</b>" not in html


def test_the_tabs_show_how_many_there_are(app, client, seed, tecnico):
    for number in range(3):
        send(tecnico["id"], f"Mensaje {number}")

    send(tecnico["id"], "Leída", read=True)
    login(client, tecnico)

    assert "Todas (4) No leídas (3)" in plain_text(client.get(URL))


def test_the_unread_view_hides_the_read_ones(app, client, seed, tecnico):
    send(tecnico["id"], "Pendiente")
    send(tecnico["id"], "Terminada", read=True)
    login(client, tecnico)
    page = plain_text(client.get(f"{URL}?vista=no-leidas"))

    assert "Pendiente" in page
    assert "Terminada" not in page


def test_the_unread_view_with_nothing_unread_says_so(app, client, seed, tecnico):
    send(tecnico["id"], "Terminada", read=True)
    login(client, tecnico)

    assert "No tienes notificaciones sin leer." in plain_text(
        client.get(f"{URL}?vista=no-leidas")
    )


@pytest.mark.parametrize("query", ["vista=otra", "vista=", "page=abc", "page=-3", "page=0"])
def test_an_invalid_filter_or_page_is_ignored(app, client, seed, tecnico, query):
    send(tecnico["id"], "Hola")
    login(client, tecnico)
    response = client.get(f"{URL}?{query}")

    assert response.status_code == 200
    assert "Hola" in plain_text(response)


def test_a_page_beyond_the_last_is_empty_not_an_error(app, client, seed, tecnico):
    send(tecnico["id"], "Hola")
    login(client, tecnico)

    assert client.get(f"{URL}?page=99").status_code == 200


def test_the_list_is_paginated_keeping_the_filter(app, client, seed, tecnico):
    for number in range(PAGE_SIZE + 5):
        send(tecnico["id"], f"Mensaje {number}")

    login(client, tecnico)
    first = client.get(f"{URL}?vista=no-leidas")
    second = client.get(f"{URL}?vista=no-leidas&page=2")
    first_html = first.get_data(as_text=True)

    assert "Página 1 de 2" in plain_text(first)
    assert "Anterior" not in plain_text(first)
    assert re.search(r'href="/notifications\?vista=no-leidas&amp;page=2"', first_html)
    assert "Página 2 de 2" in plain_text(second)
    assert "Siguiente" not in plain_text(second)
    assert re.search(r'href="/notifications\?vista=no-leidas"', second.get_data(as_text=True))
    assert plain_text(first).count("Mensaje ") == PAGE_SIZE
    assert plain_text(second).count("Mensaje ") == 5


def test_mark_all_is_offered_only_when_something_is_unread(app, client, seed, tecnico):
    send(tecnico["id"], "Leída", read=True)
    login(client, tecnico)

    assert "Marcar todas como leídas" not in plain_text(client.get(URL))

    send(tecnico["id"], "Nueva")

    assert "Marcar todas como leídas" in plain_text(client.get(URL))


# --- Marcar como leída (RF-086) ---------------------------------------------------------


def test_marking_one_as_read_returns_to_the_list(app, client, seed, tecnico):
    notification_id = send(tecnico["id"], "Hola")
    login(client, tecnico)

    response = client.post(f"{URL}/{notification_id}/read")

    assert response.status_code == 302
    assert response.headers["Location"] == URL
    assert status_of(app, notification_id)[0] is True


def test_marking_keeps_the_filter_and_the_page(app, client, seed, tecnico):
    notification_id = send(tecnico["id"], "Hola")
    login(client, tecnico)

    response = client.post(
        f"{URL}/{notification_id}/read", data={"vista": "no-leidas", "page": "2"}
    )

    assert response.headers["Location"] == f"{URL}?vista=no-leidas&page=2"


def test_a_garbage_filter_on_return_falls_back_to_the_plain_list(
    app, client, seed, tecnico
):
    notification_id = send(tecnico["id"], "Hola")
    login(client, tecnico)

    response = client.post(
        f"{URL}/{notification_id}/read", data={"vista": "http://malo", "page": "x"}
    )

    assert response.headers["Location"] == URL


def test_the_read_button_disappears_once_read(app, client, seed, tecnico):
    notification_id = send(tecnico["id"], "Hola")
    login(client, tecnico)

    assert f"{URL}/{notification_id}/read" in client.get(URL).get_data(as_text=True)

    client.post(f"{URL}/{notification_id}/read")

    assert f"{URL}/{notification_id}/read" not in client.get(URL).get_data(as_text=True)


def test_marking_someone_elses_notification_is_a_404_and_changes_nothing(
    app, client, seed, tecnico, otro
):
    theirs = send(otro["id"], "Del otro")
    login(client, tecnico)

    assert client.post(f"{URL}/{theirs}/read").status_code == 404
    assert client.post(f"{URL}/{theirs}/open").status_code == 404
    assert status_of(app, theirs)[0] is False


def test_an_unknown_notification_is_a_404(app, client, seed, tecnico):
    login(client, tecnico)

    assert client.post(f"{URL}/999999/read").status_code == 404
    assert client.post(f"{URL}/999999/open").status_code == 404


def test_marking_changes_state_so_a_get_is_not_allowed(app, client, seed, tecnico):
    notification_id = send(tecnico["id"], "Hola")
    login(client, tecnico)

    for action in ("read", "open"):
        assert client.get(f"{URL}/{notification_id}/{action}").status_code == 405

    assert client.get(f"{URL}/read-all").status_code == 405
    assert status_of(app, notification_id)[0] is False


def test_the_reading_date_is_the_first_one(app, client, seed, tecnico):
    notification_id = send(tecnico["id"], "Hola")
    login(client, tecnico)

    client.post(f"{URL}/{notification_id}/read")
    first = status_of(app, notification_id)[1]
    client.post(f"{URL}/{notification_id}/read")

    assert status_of(app, notification_id)[1] == first


def test_mark_all_reads_mine_only(app, client, seed, tecnico, otro):
    mine = [send(tecnico["id"], f"Mío {n}") for n in range(3)]
    theirs = send(otro["id"], "Del otro")
    login(client, tecnico)

    response = client.post(f"{URL}/read-all", data={"vista": "no-leidas"})

    assert response.status_code == 302
    assert response.headers["Location"] == f"{URL}?vista=no-leidas"
    assert all(status_of(app, item)[0] for item in mine)
    assert status_of(app, theirs)[0] is False


# --- CSRF -------------------------------------------------------------------------------


def test_every_form_carries_a_csrf_token_the_server_accepts(
    app, client, seed, tecnico, ticket_id
):
    with_ticket = send(tecnico["id"], "Con ticket", ticket_number=ticket_id)
    general = send(tecnico["id"], "General")
    login(client, tecnico)
    # Los tests desactivan el CSRF; aquí se activa para comprobar los formularios.
    app.config["WTF_CSRF_ENABLED"] = True
    html = client.get(URL).get_data(as_text=True)
    token = re.search(r'name="csrf_token"\s+value="([^"]+)"', html).group(1)

    # Cada formulario del listado (abrir, marcar y marcar todas) lleva el suyo.
    assert html.count('name="csrf_token"') >= 4

    for address in (
        f"{URL}/{with_ticket}/open",
        f"{URL}/{general}/read",
        f"{URL}/read-all",
    ):
        assert client.post(address).status_code == 400
        assert client.post(address, data={"csrf_token": token}).status_code == 302


# --- Abrir el ticket -----------------------------------------------------------------


def test_opening_marks_as_read_and_goes_to_the_ticket(
    app, client, seed, tecnico, ticket_id
):
    notification_id = send(tecnico["id"], "Hola", ticket_number=ticket_id)
    login(client, tecnico)

    response = client.post(f"{URL}/{notification_id}/open")

    assert response.status_code == 302
    assert response.headers["Location"] == f"/tickets/{ticket_id}"
    assert status_of(app, notification_id)[0] is True
    assert client.get(response.headers["Location"]).status_code == 200


def test_opening_a_general_notice_marks_it_and_returns_to_the_list(
    app, client, seed, tecnico
):
    notification_id = send(tecnico["id"], "Aviso general")
    login(client, tecnico)

    response = client.post(f"{URL}/{notification_id}/open")

    assert response.headers["Location"] == URL
    assert status_of(app, notification_id)[0] is True


def test_opening_does_not_grant_access_to_a_ticket_the_person_cannot_see(
    app, client, seed, make_user, tecnico, ticket_id
):
    stranger = make_user("SOLICITANTE", username="ajeno")
    notification_id = send(stranger["id"], "Hola", ticket_number=ticket_id)
    login(client, stranger)

    response = client.post(f"{URL}/{notification_id}/open")

    # Se marca como leída, pero el ticket sigue siendo de quien tiene acceso: 404.
    assert status_of(app, notification_id)[0] is True
    assert client.get(response.headers["Location"]).status_code == 404


# --- El contador de la campana -------------------------------------------------------


def test_the_unread_count_is_json_and_not_cached(app, client, seed, tecnico, otro):
    send(tecnico["id"], "Uno")
    send(tecnico["id"], "Dos")
    send(tecnico["id"], "Leída", read=True)
    send(otro["id"], "Del otro")
    login(client, tecnico)
    response = client.get(f"{URL}/unread-count")

    assert response.status_code == 200
    assert response.is_json
    assert response.get_json() == {"unread": 2}
    assert response.headers["Cache-Control"] == "no-store"


def test_the_count_follows_what_is_read(app, client, seed, tecnico):
    first = send(tecnico["id"], "Uno")
    send(tecnico["id"], "Dos")
    login(client, tecnico)

    assert client.get(f"{URL}/unread-count").get_json() == {"unread": 2}

    client.post(f"{URL}/{first}/read")

    assert client.get(f"{URL}/unread-count").get_json() == {"unread": 1}

    client.post(f"{URL}/read-all")

    assert client.get(f"{URL}/unread-count").get_json() == {"unread": 0}


def test_the_bell_shows_nothing_when_there_is_nothing_unread(client, make_user, catalog):
    login(client, make_user("TECNICO", username="persona"))
    html = client.get("/dashboard").get_data(as_text=True)

    assert re.search(r"data-bell-badge\s+aria-hidden=\"true\"\s+hidden", html)
    assert ">Notificaciones</span>" in html


def test_the_bell_shows_how_many_are_unread(app, client, seed, tecnico):
    for number in range(3):
        send(tecnico["id"], f"Mensaje {number}")

    send(tecnico["id"], "Leída", read=True)
    login(client, tecnico)
    html = client.get("/dashboard").get_data(as_text=True)

    assert re.search(r"data-bell-badge\s+aria-hidden=\"true\"\s*>3</span>", html)
    assert "Notificaciones: 3 sin leer" in html
    assert 'data-poll-seconds="30"' in html
    assert f'data-unread-url="{URL}/unread-count"' in html


def test_the_bell_caps_the_number_at_99(app, client, seed, tecnico):
    for _ in range(100):
        db.session.add(
            Notificacion(usuario_id=tecnico["id"], tipo_evento=EVENT.value, mensaje="Hola")
        )

    db.session.commit()
    login(client, tecnico)
    html = client.get("/dashboard").get_data(as_text=True)

    assert re.search(r">99\+</span>", html)
    assert "Notificaciones: 100 sin leer" in html


def test_the_bell_counts_only_my_notifications(app, client, seed, tecnico, otro):
    send(otro["id"], "Del otro")
    login(client, tecnico)

    assert "Notificaciones: " not in client.get("/dashboard").get_data(as_text=True)


def test_the_counter_is_up_to_date_on_every_page(app, client, seed, tecnico):
    notification_id = send(tecnico["id"], "Hola")
    login(client, tecnico)

    assert "Notificaciones: 1 sin leer" in client.get("/dashboard").get_data(as_text=True)

    client.post(f"{URL}/{notification_id}/read")

    assert "Notificaciones: " not in client.get("/tickets").get_data(as_text=True)


# --- El script de la campana -----------------------------------------------------------


def test_the_polling_script_is_served_without_external_dependencies(client, make_user, catalog):
    login(client, make_user("TECNICO", username="persona"))
    response = client.get("/static/js/common/notifications.js")
    source = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "data-notifications-bell" in source
    assert "visibilitychange" in source
    assert "http://" not in source and "https://" not in source


def test_the_page_loads_the_script(client, make_user, catalog):
    login(client, make_user("TECNICO", username="persona"))
    html = client.get("/dashboard").get_data(as_text=True)

    assert "js/common/notifications.js" in html
