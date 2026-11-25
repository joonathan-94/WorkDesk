"""La advertencia de posibles duplicados al crear un ticket (RF-061; docs/06, RN-175).

Lo esencial: **nunca impide crear**, **nunca enseña un ticket que la persona no pueda
ver** y se puede ajustar o desactivar desde la configuración.
"""

import re
from datetime import timedelta

import pytest

from src.workdesk import settings
from src.workdesk.configuration import save_setting
from src.workdesk.extensions import db
from src.workdesk.models import Categoria, Ticket, User
from src.workdesk.models.categoria import FALLBACK_CATEGORY_CODE
from src.workdesk.sla.periods import current_time
from src.workdesk.tickets.similar import (
    MAX_WORDS,
    find_similar_tickets,
    significant_words,
)
from tests.ticket_helpers import login, make_ticket, plain_text, set_state

TITLE = "La impresora del segundo piso no imprime"


@pytest.fixture()
def people(make_user, catalog):
    return {
        "req": make_user("SOLICITANTE", username="req_dup"),
        "otro": make_user("SOLICITANTE", username="otro_dup"),
        "tec": make_user("TECNICO", username="tec_dup"),
        "admin": make_user("ADMINISTRADOR", username="admin_dup"),
    }


def _existing(app, catalog, people, title=TITLE, who="req", **extra):
    return make_ticket(
        app,
        catalog,
        people[who]["id"],
        requester_ids=[people[who]["id"]],
        title=title,
        **extra,
    )


def _category(app, fallback=False):
    with app.app_context():
        condition = (
            Categoria.codigo == FALLBACK_CATEGORY_CODE
            if fallback
            else Categoria.codigo.is_(None) | (Categoria.codigo != FALLBACK_CATEGORY_CODE)
        )

        return db.session.scalar(db.select(Categoria.id).where(condition).order_by(Categoria.id))


def _similar(app, people, title, who="tec", category_id=None):
    with app.app_context():
        category = category_id or db.session.scalar(db.select(Ticket.categoria_id).limit(1))

        return [
            ticket.titulo
            for ticket in find_similar_tickets(
                db.session.get(User, people[who]["id"]),
                title=title,
                category_id=category or _category(app),
            )
        ]


def _set(app, people, setting, value):
    with app.app_context():
        save_setting(setting, value, actor=db.session.get(User, people["admin"]["id"]))
        db.session.commit()


# --- Las palabras ------------------------------------------------------------------------


def test_only_meaningful_words_are_compared():
    assert significant_words("No me imprime LA impresora, urgente por favor") == [
        "imprime",
        "impresora",
    ]
    assert significant_words("de la el y") == []
    assert significant_words("Correo correo CORREO") == ["correo"]
    assert len(significant_words(" ".join(f"palabra{n}" for n in range(30)))) == MAX_WORDS


# --- Qué se considera parecido ---------------------------------------------------------------


@pytest.mark.parametrize(
    "title",
    [
        "Impresora del piso no imprime nada",
        "La impresora no imprime",
        "IMPRESORAS del segundo piso",
        "segundo piso impresora",
    ],
)
def test_similar_titles_are_found(app, catalog, people, title):
    _existing(app, catalog, people)

    assert _similar(app, people, title) == [TITLE]


@pytest.mark.parametrize(
    "title", ["No tengo correo", "Impresora nueva", "El segundo monitor parpadea"]
)
def test_different_titles_are_not(app, catalog, people, title):
    _existing(app, catalog, people)

    assert _similar(app, people, title) == []


def test_accents_do_not_matter(app, catalog, people):
    _existing(app, catalog, people, title="Configuración de la cámara")

    assert _similar(app, people, "configuracion camara") == ["Configuración de la cámara"]


def test_a_one_word_title_needs_only_that_word(app, catalog, people):
    _existing(app, catalog, people)

    assert _similar(app, people, "Impresora") == [TITLE]


def test_the_most_similar_come_first_and_the_list_is_short(app, catalog, people):
    _existing(app, catalog, people, title="Impresora piso")
    _existing(app, catalog, people, title="Impresora segundo piso no imprime")

    for number in range(7):
        _existing(app, catalog, people, title=f"Impresora piso numero {number}")

    found = _similar(app, people, "Impresora del segundo piso no imprime")

    assert found[0] == "Impresora segundo piso no imprime"
    assert len(found) == 5


def test_closed_tickets_are_ignored_but_resolved_ones_are_not(app, catalog, people):
    closed = _existing(app, catalog, people, title="Impresora piso cerrada")
    resolved = _existing(app, catalog, people, title="Impresora piso resuelta")
    set_state(app, closed, "CERRADO")
    set_state(app, resolved, "RESUELTO")

    assert _similar(app, people, "Impresora piso") == ["Impresora piso resuelta"]


def test_old_tickets_are_outside_the_window(app, catalog, people):
    number = _existing(app, catalog, people)

    with app.app_context():
        db.session.execute(
            db.update(Ticket)
            .where(Ticket.public_id == str(number))
            .values(fecha_creacion=current_time() - timedelta(days=31))
        )
        db.session.commit()

    assert _similar(app, people, "Impresora segundo piso") == []
    _set(app, people, settings.DUPLICATE_WINDOW_DAYS, 60)
    assert _similar(app, people, "Impresora segundo piso") == [TITLE]


def test_another_category_does_not_count_unless_one_of_them_is_unclassified(
    app, catalog, people
):
    _existing(app, catalog, people)
    fallback = _category(app, fallback=True)

    with app.app_context():
        other = Categoria(nombre="Otra categoría de prueba")
        db.session.add(other)
        db.session.commit()
        other_id = other.id

    assert _similar(app, people, TITLE, category_id=other_id) == []
    # Quien no sabe clasificar mira en todas.
    assert _similar(app, people, TITLE, category_id=fallback) == [TITLE]


def test_a_requester_only_sees_their_own_tickets(app, catalog, people):
    _existing(app, catalog, people, title="Impresora piso de otra persona", who="otro")
    _existing(app, catalog, people, title="Impresora piso mía", who="req")

    assert _similar(app, people, "Impresora piso", who="req") == ["Impresora piso mía"]
    assert len(_similar(app, people, "Impresora piso", who="tec")) == 2


def test_the_sensitivity_is_configurable_and_zero_days_turns_it_off(app, catalog, people):
    _existing(app, catalog, people)
    # Un título largo que comparte solo dos palabras: con el mínimo normal (2) avisa.
    long_title = "Impresora piso tinta color amarillo borroso"
    assert _similar(app, people, long_title) == [TITLE]

    _set(app, people, settings.DUPLICATE_MIN_WORDS, 5)

    assert _similar(app, people, long_title) == []

    _set(app, people, settings.DUPLICATE_MIN_WORDS, 1)
    assert _similar(app, people, "Impresora nueva") == [TITLE]

    _set(app, people, settings.DUPLICATE_WINDOW_DAYS, 0)
    assert _similar(app, people, TITLE) == []


# --- La pantalla --------------------------------------------------------------------------


def _data(app, **changes):
    with app.app_context():
        ticket = db.session.scalar(db.select(Ticket).limit(1))
        values = {
            "titulo": TITLE,
            "descripcion": "Sigue sin imprimir.",
            "categoria": str(ticket.categoria_id),
            "prioridad": str(ticket.prioridad_id),
        }

    values.update(changes)

    return values


def _count(app):
    with app.app_context():
        return db.session.scalar(db.select(db.func.count(Ticket.id)))


def _confirmation(response) -> str:
    return re.search(
        r'name="confirmado" value="([0-9a-f]+)"', response.get_data(as_text=True)
    ).group(1)


def test_a_similar_ticket_is_shown_before_creating(app, client, catalog, people):
    number = _existing(app, catalog, people)
    login(client, people["req"])

    response = client.post("/tickets/new", data=_data(app))
    text = plain_text(response)

    assert response.status_code == 200
    assert "Puede que ya exista un ticket sobre esto" in text
    assert f"#{number}" in text and "Crear de todos modos" in text
    assert "Sigue sin imprimir." in response.get_data(as_text=True)
    assert _count(app) == 1


def test_confirming_creates_the_ticket(app, client, catalog, people):
    _existing(app, catalog, people)
    login(client, people["req"])
    data = _data(app)
    warned = client.post("/tickets/new", data=data)

    response = client.post(
        "/tickets/new", data={**data, "confirmado": _confirmation(warned)}
    )

    assert response.status_code == 302
    assert _count(app) == 2


def test_changing_the_title_after_the_warning_checks_again(app, client, catalog, people):
    _existing(app, catalog, people)
    login(client, people["req"])
    warned = client.post("/tickets/new", data=_data(app))

    response = client.post(
        "/tickets/new",
        data={
            **_data(app, titulo="La impresora segundo piso otra vez"),
            "confirmado": _confirmation(warned),
        },
    )

    assert response.status_code == 200
    assert _count(app) == 1


def test_a_made_up_confirmation_does_not_skip_the_check(app, client, catalog, people):
    _existing(app, catalog, people)
    login(client, people["req"])

    response = client.post("/tickets/new", data={**_data(app), "confirmado": "1"})

    assert response.status_code == 200
    assert _count(app) == 1


def test_without_similar_tickets_it_is_created_at_once(app, client, catalog, people):
    _existing(app, catalog, people)
    login(client, people["req"])

    response = client.post(
        "/tickets/new", data=_data(app, titulo="No puedo entrar al correo")
    )

    assert response.status_code == 302
    assert _count(app) == 2


def test_form_errors_come_first_without_looking_for_duplicates(
    app, client, catalog, people
):
    _existing(app, catalog, people)
    login(client, people["req"])

    response = client.post("/tickets/new", data=_data(app, descripcion=""))

    assert "Puede que ya exista" not in plain_text(response)
    assert _count(app) == 1


def test_a_requester_is_never_told_about_other_peoples_tickets(
    app, client, catalog, people
):
    _existing(app, catalog, people, who="otro")
    login(client, people["req"])

    response = client.post("/tickets/new", data=_data(app))

    assert response.status_code == 302
    assert _count(app) == 2
