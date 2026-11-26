"""La ubicación obligatoria al crear un ticket (RF-019, RF-116 y RN-177).

`LOCATION_REQUIRED` es un interruptor de la pantalla «Creación de tickets». Solo rige
mientras haya alguna ubicación activa (si no, nadie podría crear tickets) y no es
retroactivo: un ticket antiguo sin ubicación se sigue editando sin ella, pero a uno que la
tiene no se le puede quitar.
"""

import pytest

from src.workdesk.extensions import db
from src.workdesk.models import Ticket, Ubicacion
from src.workdesk.seeds import DemoTicketsError, seed_demo_tickets
from src.workdesk.tickets.editing import update_ticket
from src.workdesk.tickets.service import TicketRuleError, location_required
from tests.demo_data import NOW, prepare
from tests.ticket_helpers import (
    login,
    make_ticket,
    person,
    plain_text,
    ticket_by_public_id,
)


@pytest.fixture()
def people(make_user, catalog):
    return {
        "req": make_user("SOLICITANTE", username="req_c"),
        "tec": make_user("TECNICO", username="tec_c"),
        "admin": make_user("ADMINISTRADOR", username="admin_c"),
    }


def _require_location(app, value=True):
    app.config["LOCATION_REQUIRED"] = value


def _ticket_count(app):
    with app.app_context():
        return db.session.scalar(db.select(db.func.count(Ticket.id)))


def test_it_is_required_only_when_switched_on_and_there_are_active_locations(
    app, catalog
):
    with app.app_context():
        assert location_required() is False

        _require_location(app)
        assert location_required() is True

        db.session.get(Ubicacion, catalog["location"]).activo = False
        db.session.commit()

        # Sin ninguna ubicación activa nadie podría crear tickets: no se exige.
        assert location_required() is False


def test_the_service_refuses_a_new_ticket_without_location(app, catalog, people):
    _require_location(app)

    with pytest.raises(TicketRuleError, match="Indica la ubicación"):
        make_ticket(app, catalog, people["tec"]["id"])

    number = make_ticket(app, catalog, people["tec"]["id"], location_id=catalog["location"])

    assert number
    assert _ticket_count(app) == 1


def _new_ticket_data(catalog, **changes):
    return {
        "titulo": "Monitor apagado",
        "descripcion": "No enciende.",
        "categoria": str(catalog["hardware"]),
        "prioridad": str(catalog["medium"]),
        **changes,
    }


def test_the_form_asks_for_it(app, client, catalog, people):
    _require_location(app)
    login(client, people["req"])

    form = client.get("/tickets/new").get_data(as_text=True)
    response = client.post("/tickets/new", data=_new_ticket_data(catalog))

    assert "Selecciona una ubicación" in form
    assert "Sin ubicación" not in form
    assert response.status_code == 200
    assert "Selecciona una ubicación." in plain_text(response)
    assert _ticket_count(app) == 0

    created = client.post(
        "/tickets/new", data=_new_ticket_data(catalog, ubicacion=str(catalog["location"]))
    )

    assert created.status_code == 302
    assert _ticket_count(app) == 1


def test_switched_off_the_location_stays_optional(app, client, catalog, people):
    login(client, people["req"])

    assert "Sin ubicación" in client.get("/tickets/new").get_data(as_text=True)
    assert client.post("/tickets/new", data=_new_ticket_data(catalog)).status_code == 302


def _edit(ticket_number, actor_id, location_id):
    ticket = ticket_by_public_id(ticket_number)

    return update_ticket(
        ticket,
        actor=person(actor_id),
        expected_version=ticket.version,
        title=ticket.titulo,
        description=ticket.descripcion,
        category_id=ticket.categoria_id,
        location_id=location_id,
    )


def test_a_ticket_with_location_cannot_lose_it(app, catalog, people):
    number = make_ticket(app, catalog, people["tec"]["id"], location_id=catalog["location"])
    _require_location(app)

    with app.app_context(), pytest.raises(TicketRuleError, match="obligatoria"):
        _edit(number, people["tec"]["id"], None)


def test_an_older_ticket_without_location_can_still_be_edited(app, client, catalog, people):
    number = make_ticket(app, catalog, people["tec"]["id"], title="Antes de la regla")
    _require_location(app)

    with app.app_context():
        assert _edit(number, people["tec"]["id"], None) is False

    login(client, people["tec"])
    # Su pantalla de edición sigue ofreciendo «Sin ubicación».
    assert "Sin ubicación" in client.get(f"/tickets/{number}/edit").get_data(as_text=True)


def test_the_setting_lives_in_the_ticket_creation_screen(app, client, people):
    login(client, people["admin"])

    page = plain_text(client.get("/admin/settings/creacion"))

    assert "Exigir la ubicación al crear un ticket" in page
    assert "Días hacia atrás que se revisan" in page


def test_the_demo_seed_stops_before_loading_when_it_is_required(app):
    prepare(app)

    with app.app_context():
        db.session.add(Ubicacion(nombre="Oficina central"))
        db.session.commit()
        _require_location(app)

        with pytest.raises(DemoTicketsError, match="Creación de tickets"):
            seed_demo_tickets(now=NOW)

        assert db.session.scalar(db.select(db.func.count(Ticket.id))) == 0
