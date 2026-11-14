import re
from datetime import UTC, datetime

import pytest

from src.workdesk.extensions import db
from src.workdesk.models import (
    Categoria,
    Prioridad,
    Ticket,
    TicketHistory,
    TicketRequester,
    Ubicacion,
    User,
)
from src.workdesk.tickets import routes as ticket_routes
from src.workdesk.tickets.service import TicketRuleError, create_ticket

STAFF_ROLES = ("TECNICO", "SUPERVISOR", "ADMINISTRADOR")
ALL_ROLES = ("SOLICITANTE",) + STAFF_ROLES


def login(client, user_data):
    return client.post(
        "/login",
        data={
            "username": user_data["username"],
            "password": user_data["password"],
        },
    )


def text(response) -> str:
    return " ".join(response.get_data(as_text=True).split())


def options(response, field_id: str) -> list[tuple[str, bool, str]]:
    """Opciones de un <select>: (valor, preseleccionada, texto)."""
    html = response.get_data(as_text=True)
    block = re.search(
        rf'<select[^>]*id="{field_id}".*?</select>',
        html,
        re.DOTALL,
    ).group(0)

    return [
        (value, "selected" in attributes, label)
        for value, attributes, label in re.findall(
            r'<option\s+value="(\d*)"([^>]*)>\s*([^<]*?)\s*</option>',
            block,
            re.DOTALL,
        )
    ]


@pytest.fixture()
def catalog(app, seeded_roles, seeded_catalogs):
    """Categorías, una ubicación y las prioridades ya cargadas."""
    with app.app_context():
        hardware = Categoria(nombre="Hardware", orden=1)
        networks = Categoria(nombre="Redes", orden=2)
        location = Ubicacion(nombre="Casa matriz", tipo="SUCURSAL")
        db.session.add_all([hardware, networks, location])
        db.session.commit()

        return {
            "hardware": hardware.id,
            "networks": networks.id,
            "fallback": db.session.scalar(
                db.select(Categoria.id).where(
                    Categoria.codigo == "SIN_CLASIFICAR"
                )
            ),
            "location": location.id,
            "medium": db.session.scalar(
                db.select(Prioridad.id).where(Prioridad.codigo == "MEDIA")
            ),
            "high": db.session.scalar(
                db.select(Prioridad.id).where(Prioridad.codigo == "ALTA")
            ),
        }


def valid_data(catalog, **overrides):
    data = {
        "titulo": "VPN sin acceso",
        "descripcion": "No puedo conectarme desde casa.",
        "categoria": catalog["hardware"],
        "prioridad": catalog["medium"],
        "ubicacion": catalog["location"],
    }
    data.update(overrides)

    return data


def tickets(app) -> list[dict]:
    """Resumen de los tickets guardados, del más antiguo al más reciente."""
    with app.app_context():
        result = []

        for ticket in db.session.scalars(db.select(Ticket).order_by(Ticket.id)):
            result.append(
                {
                    "id": ticket.id,
                    "public_id": ticket.public_id,
                    "titulo": ticket.titulo,
                    "descripcion": ticket.descripcion,
                    "creador": ticket.creado_por_usuario_id,
                    "estado": ticket.estado.codigo,
                    "categoria": ticket.categoria_id,
                    "prioridad": ticket.prioridad_id,
                    "ubicacion": ticket.ubicacion_id,
                    "solicitantes": [
                        r.solicitante_id
                        for r in ticket.solicitantes
                        if r.fecha_retiro is None
                    ],
                }
            )

        return result


def make_ticket(app, catalog, creator_id, requester_ids=(), **overrides):
    """Crea un ticket con el servicio y devuelve su identificador público."""
    with app.app_context():
        values = {
            "actor": db.session.get(User, creator_id),
            "title": "Problema con el correo",
            "description": "No puedo enviar mensajes.",
            "category_id": catalog["hardware"],
            "priority_id": catalog["medium"],
            "requester_ids": requester_ids,
        }
        values.update(overrides)

        ticket = create_ticket(**values)
        db.session.commit()

        return ticket.public_id


# --- Acceso -----------------------------------------------------------


def test_anonymous_user_is_redirected_to_login(client, catalog):
    for path in ("/tickets/new", "/tickets/1"):
        response = client.get(path)

        assert response.status_code == 302
        assert "/login" in response.location


def test_anonymous_post_creates_nothing(client, app, catalog):
    response = client.post("/tickets/new", data=valid_data(catalog))

    assert response.status_code == 302
    assert "/login" in response.location
    assert tickets(app) == []


@pytest.mark.parametrize("role_code", ALL_ROLES)
def test_every_role_can_open_the_form(client, make_user, catalog, role_code):
    login(client, make_user(role_code))

    response = client.get("/tickets/new")

    assert response.status_code == 200
    assert "Crear ticket" in text(response)


def test_create_ticket_appears_in_the_navigation(client, make_user, catalog):
    login(client, make_user("SOLICITANTE"))

    content = client.get("/dashboard").get_data(as_text=True)

    assert 'href="/tickets/new"' in content


# --- Contenido del formulario -----------------------------------------


def test_the_form_has_the_documented_fields_and_hints(
    client,
    make_user,
    catalog,
):
    login(client, make_user("SOLICITANTE"))

    response = client.get("/tickets/new")
    content = response.get_data(as_text=True)

    for name in ("titulo", "descripcion", "categoria", "prioridad", "ubicacion"):
        assert f'name="{name}"' in content

    assert 'maxlength="200"' in content
    assert 'maxlength="2000"' in content
    assert "0/2000" in text(response)
    assert "No incluyas contraseñas ni información sensible." in text(response)


def test_a_solicitante_does_not_see_the_requesters_section(
    client,
    make_user,
    catalog,
):
    login(client, make_user("SOLICITANTE"))

    content = client.get("/tickets/new").get_data(as_text=True)

    assert 'name="solicitantes"' not in content
    assert "section-requesters" not in content


@pytest.mark.parametrize("role_code", STAFF_ROLES)
def test_staff_sees_only_active_solicitantes_as_requesters(
    client,
    make_user,
    catalog,
    role_code,
):
    make_user("SOLICITANTE", username="ana", apellido="Zapata")
    make_user("SOLICITANTE", username="beto", activo=False)
    make_user("SUPERVISOR", username="sup")
    login(client, make_user(role_code, username="quien_crea"))

    response = client.get("/tickets/new")
    content = text(response)

    assert response.get_data(as_text=True).count('name="solicitantes"') == 1
    assert "(ana)" in content
    # Los inactivos y quienes no son Solicitantes no se ofrecen.
    assert "(beto)" not in content
    assert "(sup)" not in content
    assert "(quien_crea)" not in content


def test_the_requesters_are_listed_by_last_name(client, make_user, catalog):
    make_user("SOLICITANTE", username="zeta", apellido="Zapata")
    make_user("SOLICITANTE", username="alfa", apellido="Acosta")
    login(client, make_user("TECNICO"))

    content = text(client.get("/tickets/new"))

    assert content.index("(alfa)") < content.index("(zeta)")


def test_the_requesters_list_is_filterable_with_javascript_only(
    client,
    make_user,
    catalog,
):
    make_user("SOLICITANTE", username="ana")
    login(client, make_user("TECNICO"))

    content = client.get("/tickets/new").get_data(as_text=True)

    # El buscador nace oculto: sin JavaScript no hay un control que no sirve.
    assert re.search(r"data-checklist-search\s+hidden", content)
    assert "js/common/checklist-filter.js" in content
    assert "js/common/char-counter.js" in content


def test_category_options_put_the_fallback_last(client, make_user, catalog):
    login(client, make_user("SOLICITANTE"))

    result = options(client.get("/tickets/new"), "categoria")

    assert [label for _, _, label in result] == [
        "Selecciona una categoría",
        "Hardware",
        "Redes",
        "Sin clasificar",
    ]
    # Hay que elegir: ninguna categoría viene preseleccionada.
    assert not any(selected for _, selected, _ in result)


def test_the_fallback_goes_last_even_if_it_has_the_lowest_order(
    client,
    make_user,
    catalog,
):
    # Con orden 0 sería la primera por orden; el formulario la pasa al final.
    login(client, make_user("SOLICITANTE"))

    labels = [
        label
        for _, _, label in options(client.get("/tickets/new"), "categoria")
    ]

    assert labels[-1] == "Sin clasificar"


def test_only_active_catalog_values_are_offered(
    client,
    app,
    make_user,
    catalog,
):
    with app.app_context():
        db.session.get(Categoria, catalog["networks"]).activo = False
        db.session.get(Ubicacion, catalog["location"]).activo = False
        db.session.get(Prioridad, catalog["high"]).activo = False
        db.session.commit()

    login(client, make_user("SOLICITANTE"))
    response = client.get("/tickets/new")

    categories = [label for _, _, label in options(response, "categoria")]
    priorities = [label for _, _, label in options(response, "prioridad")]
    locations = [label for _, _, label in options(response, "ubicacion")]

    assert "Redes" not in categories
    assert "Alta" not in priorities
    assert "Casa matriz" not in locations


def test_medium_priority_is_preselected(client, make_user, catalog):
    login(client, make_user("SOLICITANTE"))

    result = options(client.get("/tickets/new"), "prioridad")
    selected = [label for _, is_selected, label in result if is_selected]

    assert selected == ["Media"]
    assert [label for _, _, label in result] == [
        "Selecciona una prioridad",
        "Baja",
        "Media",
        "Alta",
        "Crítica",
    ]


def test_no_priority_is_preselected_when_medium_is_inactive(
    client,
    app,
    make_user,
    catalog,
):
    with app.app_context():
        db.session.get(Prioridad, catalog["medium"]).activo = False
        db.session.commit()

    login(client, make_user("SOLICITANTE"))

    result = options(client.get("/tickets/new"), "prioridad")

    assert not any(selected for _, selected, _ in result)


# --- Creación ---------------------------------------------------------


def test_a_solicitante_creates_a_ticket_as_their_own_requester(
    client,
    app,
    make_user,
    catalog,
):
    requester = make_user("SOLICITANTE")
    login(client, requester)

    response = client.post("/tickets/new", data=valid_data(catalog))

    (ticket,) = tickets(app)

    assert response.status_code == 302
    assert response.location.endswith(f"/tickets/{ticket['public_id']}")
    assert ticket["titulo"] == "VPN sin acceso"
    assert ticket["estado"] == "NUEVO"
    assert ticket["creador"] == requester["id"]
    assert ticket["solicitantes"] == [requester["id"]]
    assert ticket["categoria"] == catalog["hardware"]
    assert ticket["prioridad"] == catalog["medium"]
    assert ticket["ubicacion"] == catalog["location"]


def test_the_creation_shows_a_confirmation_in_the_detail(
    client,
    app,
    make_user,
    catalog,
):
    login(client, make_user("SOLICITANTE"))

    response = client.post(
        "/tickets/new",
        data=valid_data(catalog),
        follow_redirects=True,
    )
    (ticket,) = tickets(app)

    assert response.status_code == 200
    assert (
        f"Ticket #{ticket['public_id']} creado correctamente."
        in text(response)
    )
    assert "VPN sin acceso" in text(response)


def test_the_creation_is_recorded_in_the_history(
    client,
    app,
    make_user,
    catalog,
):
    creator = make_user("SOLICITANTE")
    login(client, creator)

    client.post("/tickets/new", data=valid_data(catalog))

    with app.app_context():
        (entry,) = db.session.scalars(db.select(TicketHistory))

        assert entry.tipo_evento == "TICKET_CREADO"
        assert entry.actor_usuario_id == creator["id"]


def test_a_solicitante_cannot_register_other_requesters(
    client,
    app,
    make_user,
    catalog,
):
    creator = make_user("SOLICITANTE", username="creador")
    other = make_user("SOLICITANTE", username="otro")
    login(client, creator)

    # Envío manipulado: un Solicitante no elige solicitantes.
    client.post(
        "/tickets/new",
        data=valid_data(catalog, solicitantes=[other["id"]]),
    )

    (ticket,) = tickets(app)

    assert ticket["solicitantes"] == [creator["id"]]


@pytest.mark.parametrize("role_code", STAFF_ROLES)
def test_staff_can_create_a_ticket_without_requesters(
    client,
    app,
    make_user,
    catalog,
    role_code,
):
    staff = make_user(role_code)
    login(client, staff)

    client.post("/tickets/new", data=valid_data(catalog))

    (ticket,) = tickets(app)

    assert ticket["creador"] == staff["id"]
    assert ticket["solicitantes"] == []


@pytest.mark.parametrize("role_code", STAFF_ROLES)
def test_staff_can_create_a_ticket_for_several_requesters(
    client,
    app,
    make_user,
    catalog,
    role_code,
):
    first = make_user("SOLICITANTE", username="uno")
    second = make_user("SOLICITANTE", username="dos")
    staff = make_user(role_code, username="quien_crea")
    login(client, staff)

    client.post(
        "/tickets/new",
        data=valid_data(catalog, solicitantes=[first["id"], second["id"]]),
    )

    (ticket,) = tickets(app)

    # El creador y los solicitantes se registran por separado (RN-13).
    assert ticket["creador"] == staff["id"]
    assert ticket["solicitantes"] == [first["id"], second["id"]]


def test_the_creator_is_not_a_requester_unless_chosen(
    client,
    app,
    make_user,
    catalog,
):
    requester = make_user("SOLICITANTE")
    staff = make_user("TECNICO")
    login(client, staff)

    client.post(
        "/tickets/new",
        data=valid_data(catalog, solicitantes=[requester["id"]]),
    )

    (ticket,) = tickets(app)

    assert staff["id"] not in ticket["solicitantes"]


@pytest.mark.parametrize(
    "case",
    ["inactive", "other_role", "unknown", "not_a_number"],
)
def test_invalid_requesters_are_rejected(
    client,
    app,
    make_user,
    catalog,
    case,
):
    inactive = make_user("SOLICITANTE", username="inactivo", activo=False)
    supervisor = make_user("SUPERVISOR", username="sup")
    login(client, make_user("TECNICO"))

    invalid = {
        "inactive": inactive["id"],
        "other_role": supervisor["id"],
        "unknown": 999999,
        "not_a_number": "abc",
    }[case]

    response = client.post(
        "/tickets/new",
        data=valid_data(catalog, solicitantes=[invalid]),
    )

    assert response.status_code == 200
    assert tickets(app) == []

    expected = (
        "La selección no es válida."
        if case == "not_a_number"
        else "Elige solicitantes de la lista."
    )

    assert expected in text(response)


def test_a_chosen_requester_stays_checked_after_an_error(
    client,
    make_user,
    catalog,
):
    requester = make_user("SOLICITANTE", username="ana")
    login(client, make_user("TECNICO"))

    response = client.post(
        "/tickets/new",
        data=valid_data(catalog, titulo="", solicitantes=[requester["id"]]),
    )

    assert re.search(
        rf'value="{requester["id"]}"\s+checked',
        response.get_data(as_text=True),
    )


def test_title_and_description_are_trimmed(client, app, make_user, catalog):
    login(client, make_user("SOLICITANTE"))

    client.post(
        "/tickets/new",
        data=valid_data(
            catalog,
            titulo="  Con espacios  ",
            descripcion="\n  Texto  \n",
        ),
    )

    (ticket,) = tickets(app)

    assert ticket["titulo"] == "Con espacios"
    assert ticket["descripcion"] == "Texto"


def test_the_fallback_category_is_a_valid_choice(
    client,
    app,
    make_user,
    catalog,
):
    login(client, make_user("SOLICITANTE"))

    client.post(
        "/tickets/new",
        data=valid_data(catalog, categoria=catalog["fallback"]),
    )

    (ticket,) = tickets(app)

    assert ticket["categoria"] == catalog["fallback"]


def test_the_location_is_optional(client, app, make_user, catalog):
    login(client, make_user("SOLICITANTE"))

    client.post("/tickets/new", data=valid_data(catalog, ubicacion=""))

    (ticket,) = tickets(app)

    assert ticket["ubicacion"] is None


# --- Validaciones -----------------------------------------------------


def post_invalid(client, app, catalog, **overrides):
    response = client.post(
        "/tickets/new",
        data=valid_data(catalog, **overrides),
    )

    assert response.status_code == 200
    assert tickets(app) == []

    return response


@pytest.fixture()
def solicitante_session(client, make_user, catalog):
    login(client, make_user("SOLICITANTE"))


def test_the_title_is_required(client, app, catalog, solicitante_session):
    response = post_invalid(client, app, catalog, titulo="   ")

    assert "Ingresa un título." in text(response)


def test_the_description_is_required(client, app, catalog, solicitante_session):
    response = post_invalid(client, app, catalog, descripcion="  ")

    assert "Describe tu solicitud." in text(response)


def test_the_title_has_a_maximum_length(
    client,
    app,
    catalog,
    solicitante_session,
):
    response = post_invalid(client, app, catalog, titulo="a" * 201)

    assert "Máximo 200 caracteres." in text(response)


def test_the_description_has_a_maximum_length(
    client,
    app,
    catalog,
    solicitante_session,
):
    response = post_invalid(client, app, catalog, descripcion="a" * 2001)

    assert "Máximo 2000 caracteres." in text(response)


def test_the_description_accepts_exactly_the_maximum(
    client,
    app,
    catalog,
    solicitante_session,
):
    client.post(
        "/tickets/new",
        data=valid_data(catalog, descripcion="a" * 2000),
    )

    assert len(tickets(app)) == 1


def test_line_breaks_count_once_toward_the_limit(
    client,
    app,
    catalog,
    solicitante_session,
):
    # Un navegador envía cada salto de línea como CRLF, pero la persona (y el
    # contador) los cuenta como un carácter: 1000 líneas de una letra son
    # 1999 caracteres, dentro del límite.
    description = "\r\n".join(["a"] * 1000)

    client.post(
        "/tickets/new",
        data=valid_data(catalog, descripcion=description),
    )

    (ticket,) = tickets(app)

    assert "\r" not in ticket["descripcion"]
    assert len(ticket["descripcion"]) == 1999


def test_the_category_is_required(client, app, catalog, solicitante_session):
    response = post_invalid(client, app, catalog, categoria="")

    assert "Selecciona una categoría." in text(response)


def test_the_priority_is_required_even_though_medium_is_the_default(
    client,
    app,
    catalog,
    solicitante_session,
):
    # La preselección solo existe al abrir el formulario: un envío sin
    # prioridad no queda en Media sin que nadie la haya elegido.
    data = valid_data(catalog)
    del data["prioridad"]

    response = client.post("/tickets/new", data=data)

    assert "Selecciona una prioridad." in text(response)
    assert tickets(app) == []


@pytest.mark.parametrize("field", ["categoria", "prioridad", "ubicacion"])
def test_unknown_catalog_ids_are_rejected(
    client,
    app,
    catalog,
    solicitante_session,
    field,
):
    response = post_invalid(client, app, catalog, **{field: 999999})

    assert "Selecciona" in text(response)


@pytest.mark.parametrize("field", ["categoria", "prioridad", "ubicacion"])
def test_a_non_numeric_catalog_id_is_rejected(
    client,
    app,
    catalog,
    solicitante_session,
    field,
):
    response = post_invalid(client, app, catalog, **{field: "abc"})

    assert "Ingresa un número entero." in text(response)


@pytest.mark.parametrize(
    ("field", "key"),
    [
        ("categoria", "networks"),
        ("prioridad", "high"),
        ("ubicacion", "location"),
    ],
)
def test_inactive_catalog_values_are_rejected(
    client,
    app,
    catalog,
    solicitante_session,
    field,
    key,
):
    model = {
        "categoria": Categoria,
        "prioridad": Prioridad,
        "ubicacion": Ubicacion,
    }[field]

    with app.app_context():
        db.session.get(model, catalog[key]).activo = False
        db.session.commit()

    response = post_invalid(client, app, catalog, **{field: catalog[key]})

    assert "Selecciona" in text(response)


def test_the_form_keeps_what_was_typed_after_an_error(
    client,
    app,
    catalog,
    solicitante_session,
):
    response = post_invalid(
        client,
        app,
        catalog,
        titulo="Mi título",
        descripcion="Mi descripción",
        categoria="",
        prioridad=catalog["high"],
    )
    content = response.get_data(as_text=True)

    assert 'value="Mi título"' in content
    assert "Mi descripción</textarea>" in content
    assert [
        label for _, selected, label in options(response, "prioridad") if selected
    ] == ["Alta"]


def test_a_catalog_rule_error_is_shown_without_saving(
    client,
    app,
    make_user,
    catalog,
    monkeypatch,
):
    def fail(**kwargs):
        raise TicketRuleError("La categoría seleccionada no está disponible.")

    monkeypatch.setattr(ticket_routes, "create_ticket", fail)
    login(client, make_user("SOLICITANTE"))

    response = client.post("/tickets/new", data=valid_data(catalog))

    assert response.status_code == 200
    assert "La categoría seleccionada no está disponible." in text(response)
    assert tickets(app) == []


def test_post_without_csrf_token_is_rejected(
    client,
    app,
    make_user,
    catalog,
):
    login(client, make_user("SOLICITANTE"))
    app.config["WTF_CSRF_ENABLED"] = True

    response = client.post("/tickets/new", data=valid_data(catalog))

    assert response.status_code == 400
    assert tickets(app) == []


# --- Detalle: quién puede verlo ---------------------------------------


def test_the_creator_can_view_their_ticket(client, app, make_user, catalog):
    creator = make_user("SOLICITANTE")
    public_id = make_ticket(app, catalog, creator["id"])
    login(client, creator)

    response = client.get(f"/tickets/{public_id}")

    assert response.status_code == 200
    assert f"#{public_id}" in text(response)
    assert "Problema con el correo" in text(response)


def test_a_current_requester_can_view_a_ticket_created_by_staff(
    client,
    app,
    make_user,
    catalog,
):
    requester = make_user("SOLICITANTE")
    staff = make_user("TECNICO")
    public_id = make_ticket(
        app,
        catalog,
        staff["id"],
        requester_ids=[requester["id"]],
    )
    login(client, requester)

    assert client.get(f"/tickets/{public_id}").status_code == 200


def test_a_removed_requester_gets_a_404(client, app, make_user, catalog):
    requester = make_user("SOLICITANTE")
    staff = make_user("TECNICO")
    public_id = make_ticket(
        app,
        catalog,
        staff["id"],
        requester_ids=[requester["id"]],
    )

    with app.app_context():
        link = db.session.scalar(db.select(TicketRequester))
        link.fecha_retiro = datetime.now(UTC)
        db.session.commit()

    login(client, requester)

    assert client.get(f"/tickets/{public_id}").status_code == 404


def test_someone_elses_ticket_looks_like_a_missing_one(
    client,
    app,
    make_user,
    catalog,
):
    owner = make_user("SOLICITANTE", username="dueno")
    stranger = make_user("SOLICITANTE", username="ajeno")
    public_id = make_ticket(app, catalog, owner["id"])
    login(client, stranger)

    foreign = client.get(f"/tickets/{public_id}")
    missing = client.get("/tickets/999999")

    # Misma respuesta para un ticket ajeno y para uno inexistente: no se
    # revela cuáles existen.
    assert foreign.status_code == missing.status_code == 404
    assert text(foreign) == text(missing)


@pytest.mark.parametrize("role_code", STAFF_ROLES)
def test_staff_can_view_any_ticket(client, app, make_user, catalog, role_code):
    owner = make_user("SOLICITANTE")
    public_id = make_ticket(app, catalog, owner["id"])
    login(client, make_user(role_code, username="personal"))

    assert client.get(f"/tickets/{public_id}").status_code == 200


@pytest.mark.parametrize(
    "public_id",
    ["abc", "1.5", "-1", "1e3", "٣", "²", "1%20"],
)
def test_a_public_id_that_is_not_a_number_is_a_404(
    client,
    make_user,
    catalog,
    public_id,
):
    login(client, make_user("ADMINISTRADOR"))

    assert client.get(f"/tickets/{public_id}").status_code == 404


def test_an_unknown_ticket_is_a_404_for_everyone(client, make_user, catalog):
    login(client, make_user("ADMINISTRADOR"))

    assert client.get("/tickets/999999").status_code == 404


# --- Detalle: contenido -----------------------------------------------


def test_the_detail_shows_the_summary(client, app, make_user, catalog):
    creator = make_user("SOLICITANTE")
    public_id = make_ticket(
        app,
        catalog,
        creator["id"],
        category_id=catalog["networks"],
        priority_id=catalog["high"],
    )
    login(client, creator)

    content = text(client.get(f"/tickets/{public_id}"))

    assert "Nuevo" in content
    assert "Alta" in content
    assert "Redes" in content
    assert "No puedo enviar mensajes." in content


def test_the_detail_shows_the_location_or_a_dash(
    client,
    app,
    make_user,
    catalog,
):
    creator = make_user("SOLICITANTE")
    with_location = make_ticket(
        app,
        catalog,
        creator["id"],
        location_id=catalog["location"],
    )
    without_location = make_ticket(app, catalog, creator["id"])
    login(client, creator)

    assert "Casa matriz" in text(client.get(f"/tickets/{with_location}"))

    # Sin ubicación se muestra un guion, no la palabra "None".
    content = text(client.get(f"/tickets/{without_location}"))

    assert "Casa matriz" not in content
    assert "None" not in content


def test_the_detail_shows_dates_in_local_time(client, app, make_user, catalog):
    creator = make_user("SOLICITANTE")
    public_id = make_ticket(app, catalog, creator["id"])
    login(client, creator)

    content = text(client.get(f"/tickets/{public_id}"))

    assert re.search(r"Creado el \d{2}-\d{2}-\d{4} \d{2}:\d{2}", content)


def test_the_detail_shows_the_creation_in_the_history(
    client,
    app,
    make_user,
    catalog,
):
    creator = make_user("SOLICITANTE")
    public_id = make_ticket(app, catalog, creator["id"])
    login(client, creator)

    content = text(client.get(f"/tickets/{public_id}"))

    assert "Historial" in content
    assert "Ticket creado" in content


def test_staff_sees_the_creator_and_the_requesters(
    client,
    app,
    make_user,
    catalog,
):
    requester = make_user("SOLICITANTE", username="ana", nombre="Ana")
    staff = make_user("TECNICO", username="tec", nombre="Tecnico")
    public_id = make_ticket(
        app,
        catalog,
        staff["id"],
        requester_ids=[requester["id"]],
    )
    login(client, staff)

    content = text(client.get(f"/tickets/{public_id}"))

    assert "Creado por" in content
    assert "Tecnico Pruebas" in content
    assert "Ana Pruebas" in content
    assert "Sin solicitante" not in content


def test_staff_sees_when_there_is_no_requester(
    client,
    app,
    make_user,
    catalog,
):
    staff = make_user("TECNICO")
    public_id = make_ticket(app, catalog, staff["id"])
    login(client, staff)

    assert "Sin solicitante" in text(client.get(f"/tickets/{public_id}"))


def test_a_solicitante_does_not_see_internal_data(
    client,
    app,
    make_user,
    catalog,
):
    requester = make_user("SOLICITANTE")
    staff = make_user("TECNICO")
    public_id = make_ticket(
        app,
        catalog,
        staff["id"],
        requester_ids=[requester["id"]],
    )
    login(client, requester)

    content = text(client.get(f"/tickets/{public_id}"))

    assert "Creado por" not in content
    assert "Sin solicitante" not in content


def test_a_removed_requester_is_not_listed_to_staff(
    client,
    app,
    make_user,
    catalog,
):
    removed = make_user("SOLICITANTE", username="retirada", nombre="Retirada")
    staff = make_user("TECNICO")
    public_id = make_ticket(
        app,
        catalog,
        staff["id"],
        requester_ids=[removed["id"]],
    )

    with app.app_context():
        link = db.session.scalar(db.select(TicketRequester))
        link.fecha_retiro = datetime.now(UTC)
        db.session.commit()

    login(client, staff)
    content = text(client.get(f"/tickets/{public_id}"))

    assert "Retirada" not in content
    assert "Sin solicitante" in content


def test_the_ticket_text_is_escaped(client, app, make_user, catalog):
    creator = make_user("SOLICITANTE")
    public_id = make_ticket(
        app,
        catalog,
        creator["id"],
        title="<script>alert(1)</script>",
        description="<img src=x onerror=alert(2)>\nSegunda línea",
    )
    login(client, creator)

    content = client.get(f"/tickets/{public_id}").get_data(as_text=True)

    assert "<script>alert(1)</script>" not in content
    assert "<img src=x" not in content
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in content
    # Los saltos de línea se conservan (el estilo los respeta).
    assert 'class="ticket-text"' in content
    assert "Segunda línea" in content
