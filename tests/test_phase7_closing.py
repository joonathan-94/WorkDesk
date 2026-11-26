"""Lo que corrigió el cierre de `v0.7.0` (docs/14): la ubicación obligatoria (RF-019), el
tamaño de los archivos, `sla-status` con el SLA apagado, el estado editorial en el editor
de artículos, los selectores de Grupos y la salida de los comandos en la consola."""

import ast
from pathlib import Path

import pytest

from src.workdesk.extensions import db
from src.workdesk.formatting import format_size
from src.workdesk.groups.service import create_group
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

PACKAGE = Path(__file__).resolve().parent.parent / "src" / "workdesk"


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


# --- Ubicación obligatoria (RF-019) -------------------------------------------------------


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


# --- Tamaño de los archivos ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("size", "text"),
    [
        (0, "1 KB"),
        (10, "1 KB"),
        (1024, "1 KB"),
        (1025, "2 KB"),
        (500 * 1024, "500 KB"),
        (1024 * 1024 - 1, "1024 KB"),
        (1024 * 1024, "1 MB"),
        (1536 * 1024, "1,5 MB"),
        # Un límite nunca aparenta ser mayor: 1,99 MB es «1,9 MB».
        (2 * 1024 * 1024 - 1, "1,9 MB"),
        (10 * 1024 * 1024, "10 MB"),
    ],
)
def test_a_size_is_shown_as_a_person_reads_it(size, text):
    assert format_size(size) == text


def test_a_limit_below_one_megabyte_is_not_shown_as_zero(app, client, people):
    app.config["UPLOAD_MAX_BYTES"] = 512 * 1024
    login(client, people["req"])

    assert "Hasta 5 archivos de 512 KB" in plain_text(client.get("/tickets/new"))


# --- Otros arreglos -----------------------------------------------------------------------


def test_sla_status_says_when_the_sla_is_switched_off(app, catalog, people):
    number = make_ticket(app, catalog, people["tec"]["id"])
    app.config["SLA_ENABLED"] = False

    output = app.test_cli_runner().invoke(args=["sla-status", number]).output

    assert "SLA: apagado" in output
    assert "política" not in output


def test_the_article_editor_shows_the_editorial_state(app, client, people):
    login(client, people["admin"])

    assert "Estado editorial" in plain_text(client.get("/knowledge/new"))


def test_the_two_pickers_of_a_group_have_their_own_ids(
    app, client, catalog, people, make_user
):
    # Con un candidato para cada selector, el detalle muestra los dos.
    make_user("SUPERVISOR", username="sup_c")

    with app.app_context():
        group = create_group(actor=person(people["admin"]["id"]), nombre="Soporte", descripcion="")
        db.session.commit()
        group_id = group.id

    login(client, people["admin"])
    html = client.get(f"/groups/{group_id}").get_data(as_text=True)

    assert html.count('id="tecnico-a-agregar"') == 1
    assert html.count('id="supervisor-a-designar"') == 1
    assert 'for="tecnico-a-agregar"' in html and 'for="supervisor-a-designar"' in html


def _texts_of(path: Path):
    """Las cadenas del módulo, sin los docstrings (que nunca se imprimen)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = {
        id(node.body[0].value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef)
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
    }

    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
    ]


def test_command_output_can_be_written_to_a_windows_console():
    """La consola de Windows, al redirigir la salida a un archivo o a otro programa, escribe
    en cp1252: un carácter fuera de ella (como «→») hacía fallar el comando entero."""
    modules = [
        *(PACKAGE / "cli").glob("*.py"),
        *(PACKAGE / "seeds").rglob("*.py"),
        PACKAGE / "scheduler.py",
    ]
    unwritable = sorted(
        f"{path.relative_to(PACKAGE).as_posix()}: {text[:60]!r}"
        for path in modules
        for text in _texts_of(path)
        if text.encode("cp1252", "replace").decode("cp1252") != text
    )

    assert len(modules) > 10
    assert unwritable == []
