import re

import pytest

from src.workdesk.catalogs.service import (
    create_category,
    create_location,
    deactivate_item,
)
from src.workdesk.extensions import db
from src.workdesk.models import (
    AdminAuditLog,
    Categoria,
    Prioridad,
    Ubicacion,
    User,
)

NON_ADMIN_ROLES = ("SOLICITANTE", "TECNICO", "SUPERVISOR")

# Plantillas de ruta: se completan con los identificadores de `ids`.
READ_ROUTES = (
    "/admin/categories",
    "/admin/categories/new",
    "/admin/categories/{category}/edit",
    "/admin/categories/{category}/deactivate",
    "/admin/priorities",
    "/admin/priorities/{priority}/edit",
    "/admin/priorities/{priority}/deactivate",
    "/admin/locations",
    "/admin/locations/new",
    "/admin/locations/{location}/edit",
    "/admin/locations/{location}/deactivate",
)
ID_ROUTES = tuple(route for route in READ_ROUTES if "{" in route) + (
    "/admin/categories/{category}/activate",
    "/admin/priorities/{priority}/activate",
    "/admin/locations/{location}/activate",
)
ACTION_ROUTES = ID_ROUTES + (
    "/admin/categories/new",
    "/admin/locations/new",
)


def login(client, user_data):
    return client.post(
        "/login",
        data={
            "username": user_data["username"],
            "password": user_data["password"],
        },
    )


def admin_session(client, make_user):
    admin_data = make_user("ADMINISTRADOR")
    login(client, admin_data)

    return admin_data


def text(response) -> str:
    return " ".join(response.get_data(as_text=True).split())


def audit(app) -> list[AdminAuditLog]:
    with app.app_context():
        return list(
            db.session.scalars(
                db.select(AdminAuditLog).order_by(AdminAuditLog.id)
            )
        )


def by_code(model, code):
    return db.session.scalar(db.select(model).where(model.codigo == code))


@pytest.fixture()
def ids(app, seeded_roles, seeded_catalogs, make_user):
    """Una categoría normal, una prioridad y una ubicación ya creadas."""
    admin_data = make_user("ADMINISTRADOR", username="creador")

    with app.app_context():
        actor = db.session.get(User, admin_data["id"])
        category = create_category(actor=actor, nombre="Redes", orden=4)
        location = create_location(
            actor=actor,
            nombre="Casa matriz",
            descripcion="Santiago centro",
            tipo="SUCURSAL",
        )
        db.session.commit()

        return {
            "category": category.id,
            "fallback": by_code(Categoria, "SIN_CLASIFICAR").id,
            "priority": by_code(Prioridad, "MEDIA").id,
            "location": location.id,
        }


def deactivate(app, model, item_id):
    with app.app_context():
        actor = db.session.scalar(
            db.select(User).where(User.username == "creador")
        )
        deactivate_item(db.session.get(model, item_id), actor=actor)
        db.session.commit()


def row(app, model, item_id):
    with app.app_context():
        item = db.session.get(model, item_id)
        db.session.expunge(item)

        return item


# --- Control de acceso ------------------------------------------------


@pytest.mark.parametrize("route", READ_ROUTES + ID_ROUTES[-3:])
def test_anonymous_user_is_redirected_to_login(client, ids, route):
    response = client.get(route.format(**ids))

    assert response.status_code == 302
    assert "/login" in response.location


@pytest.mark.parametrize("route", READ_ROUTES + ID_ROUTES[-3:])
@pytest.mark.parametrize("role_code", NON_ADMIN_ROLES)
def test_non_admin_roles_are_forbidden_on_get(
    client,
    make_user,
    ids,
    role_code,
    route,
):
    login(client, make_user(role_code))

    assert client.get(route.format(**ids)).status_code == 403


@pytest.mark.parametrize("route", ACTION_ROUTES)
@pytest.mark.parametrize("role_code", NON_ADMIN_ROLES)
def test_non_admin_roles_cannot_change_anything(
    client,
    app,
    make_user,
    ids,
    role_code,
    route,
):
    login(client, make_user(role_code))
    entries_before = len(audit(app))

    response = client.post(route.format(**ids), data={"nombre": "Intruso"})

    assert response.status_code == 403
    assert len(audit(app)) == entries_before

    with app.app_context():
        assert db.session.scalar(
            db.select(Categoria).where(Categoria.nombre == "Intruso")
        ) is None


@pytest.mark.parametrize("route", READ_ROUTES)
def test_administrator_can_open_every_screen(client, make_user, ids, route):
    admin_session(client, make_user)

    assert client.get(route.format(**ids)).status_code == 200


@pytest.mark.parametrize(
    "route",
    [
        "/admin/categories/99999/edit",
        "/admin/categories/99999/deactivate",
        "/admin/categories/99999/activate",
        "/admin/priorities/99999/edit",
        "/admin/priorities/99999/deactivate",
        "/admin/priorities/99999/activate",
        "/admin/locations/99999/edit",
        "/admin/locations/99999/deactivate",
        "/admin/locations/99999/activate",
    ],
)
def test_unknown_ids_return_404(client, make_user, ids, route):
    admin_session(client, make_user)

    assert client.get(route).status_code == 404


def test_post_without_csrf_token_is_rejected(client, app, make_user, ids):
    admin_session(client, make_user)
    app.config["WTF_CSRF_ENABLED"] = True

    response = client.post("/admin/categories/new", data={"nombre": "Nueva"})

    assert response.status_code == 400

    with app.app_context():
        assert db.session.scalar(
            db.select(Categoria).where(Categoria.nombre == "Nueva")
        ) is None


# --- Navegación -------------------------------------------------------


def test_the_hub_links_to_the_three_catalogs(client, make_user, ids):
    admin_session(client, make_user)

    content = client.get("/admin").get_data(as_text=True)

    for path in ("/admin/categories", "/admin/priorities", "/admin/locations"):
        assert f'href="{path}"' in content


def test_catalog_screens_show_a_breadcrumb_to_the_hub(client, make_user, ids):
    admin_session(client, make_user)

    content = client.get("/admin/categories").get_data(as_text=True)

    assert 'aria-label="Ruta de navegación"' in content
    assert 'href="/admin"' in content


# --- Listados ---------------------------------------------------------


def test_categories_list_shows_every_category(client, make_user, ids):
    admin_session(client, make_user)

    content = text(client.get("/admin/categories"))

    assert "Categorías" in content
    assert "Sin clasificar" in content
    assert "Redes" in content
    assert "2 resultados" in content
    assert "Nueva categoría" in content


def test_the_fallback_category_is_shown_as_protected(client, make_user, ids):
    admin_session(client, make_user)

    content = client.get("/admin/categories").get_data(as_text=True)

    assert f"/admin/categories/{ids['category']}/deactivate" in content
    assert f"/admin/categories/{ids['fallback']}/edit" in content
    assert f"/admin/categories/{ids['fallback']}/deactivate" not in content
    assert "Protegida" in content


def test_priorities_list_shows_level_and_color_without_a_create_button(
    client,
    make_user,
    ids,
):
    admin_session(client, make_user)

    content = text(client.get("/admin/priorities"))

    for name in ("Baja", "Media", "Alta", "Crítica"):
        assert name in content

    assert "#EF4444" in content
    assert "Nueva prioridad" not in content
    assert "/admin/priorities/new" not in content


def test_the_last_active_priority_is_shown_as_protected(
    app,
    client,
    make_user,
    ids,
):
    for code in ("BAJA", "MEDIA", "ALTA"):
        with app.app_context():
            priority_id = by_code(Prioridad, code).id

        deactivate(app, Prioridad, priority_id)

    admin_session(client, make_user)

    content = client.get("/admin/priorities?estado=activo").get_data(
        as_text=True,
    )

    assert "Protegida" in content
    assert "/deactivate" not in content


def test_locations_list_shows_the_type_name(client, make_user, ids):
    admin_session(client, make_user)

    content = text(client.get("/admin/locations"))

    assert "Casa matriz" in content
    assert "Sucursal" in content
    assert "Santiago centro" in content


def test_locations_list_shows_an_empty_state(client, make_user, seeded_roles):
    admin_session(client, make_user)

    content = text(client.get("/admin/locations"))

    assert "No hay ubicaciones con esos criterios." in content
    assert "0 resultados" in content


def test_lists_can_be_filtered_by_status(client, app, make_user, ids):
    deactivate(app, Categoria, ids["category"])
    admin_session(client, make_user)

    inactive = text(client.get("/admin/categories?estado=inactivo"))
    active = text(client.get("/admin/categories?estado=activo"))
    everything = text(client.get("/admin/categories"))

    assert "Redes" in inactive and "Sin clasificar" not in inactive
    assert "Sin clasificar" in active and "Redes" not in active
    assert "Redes" in everything and "Sin clasificar" in everything
    assert "Reactivar" in inactive


def test_an_invalid_status_filter_is_ignored(client, make_user, ids):
    admin_session(client, make_user)

    response = client.get("/admin/categories?estado=cualquiera")

    assert response.status_code == 200
    assert "2 resultados" in text(response)


def test_names_are_escaped_in_the_list(client, app, make_user, ids):
    with app.app_context():
        actor = db.session.scalar(
            db.select(User).where(User.username == "creador")
        )
        create_category(actor=actor, nombre="<script>alert(1)</script>")
        db.session.commit()

    admin_session(client, make_user)

    content = client.get("/admin/categories").get_data(as_text=True)

    assert "<script>alert(1)</script>" not in content
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in content


# --- Categorías: alta -------------------------------------------------


def test_new_category_form_has_no_code_field(client, make_user, ids):
    admin_session(client, make_user)

    content = client.get("/admin/categories/new").get_data(as_text=True)

    for field in ("nombre", "descripcion", "orden"):
        assert f'name="{field}"' in content

    assert 'name="codigo"' not in content


def test_create_category_redirects_with_a_confirmation(
    client,
    app,
    make_user,
    ids,
):
    admin = admin_session(client, make_user)

    response = client.post(
        "/admin/categories/new",
        data={"nombre": "Correo", "descripcion": "Buzones", "orden": "7"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "La categoría «Correo» fue creada." in text(response)

    with app.app_context():
        category = db.session.scalar(
            db.select(Categoria).where(Categoria.nombre == "Correo")
        )

        assert category.descripcion == "Buzones"
        assert category.orden == 7
        assert category.activo is True
        assert category.usuario_creacion_id == admin["id"]

    assert audit(app)[-1].accion == "CATALOGO_CREADO"


def test_create_category_with_blank_optional_fields(client, app, make_user, ids):
    admin_session(client, make_user)

    client.post(
        "/admin/categories/new",
        data={"nombre": "Correo", "descripcion": "", "orden": ""},
    )

    with app.app_context():
        category = db.session.scalar(
            db.select(Categoria).where(Categoria.nombre == "Correo")
        )

        assert category.descripcion is None
        assert category.orden is None


def test_create_category_requires_a_name(client, app, make_user, ids):
    admin_session(client, make_user)
    entries_before = len(audit(app))

    response = client.post("/admin/categories/new", data={"nombre": "   "})

    assert response.status_code == 200
    assert "Ingresa el nombre." in text(response)
    assert len(audit(app)) == entries_before


def test_create_category_rejects_a_repeated_name(client, make_user, ids):
    admin_session(client, make_user)

    response = client.post(
        "/admin/categories/new",
        data={"nombre": "REDES"},
    )

    assert response.status_code == 200
    assert "Ya existe una categoría con ese nombre." in text(response)
    assert 'value="REDES"' in response.get_data(as_text=True)


def test_create_category_rejects_an_invalid_order(client, make_user, ids):
    admin_session(client, make_user)

    not_a_number = client.post(
        "/admin/categories/new",
        data={"nombre": "Nueva", "orden": "abc"},
    )
    too_big = client.post(
        "/admin/categories/new",
        data={"nombre": "Nueva", "orden": "10000"},
    )
    negative = client.post(
        "/admin/categories/new",
        data={"nombre": "Nueva", "orden": "-1"},
    )

    assert "Ingresa un número entero." in text(not_a_number)
    # Lo escrito se conserva junto al error.
    assert 'value="abc"' in not_a_number.get_data(as_text=True)
    assert "Usa un número entre 0 y 9999." in text(too_big)
    assert "Usa un número entre 0 y 9999." in text(negative)


def test_create_category_rejects_overlong_values(client, make_user, ids):
    admin_session(client, make_user)

    response = client.post(
        "/admin/categories/new",
        data={"nombre": "a" * 101, "descripcion": "b" * 501},
    )

    assert text(response).count("Máximo") >= 2


# --- Categorías: edición ----------------------------------------------


def test_edit_category_form_is_prefilled(client, make_user, ids):
    admin_session(client, make_user)

    content = client.get(
        f"/admin/categories/{ids['category']}/edit",
    ).get_data(as_text=True)

    assert 'value="Redes"' in content
    assert 'value="4"' in content


def test_edit_keeps_an_order_of_zero(client, make_user, ids):
    admin_session(client, make_user)

    response = client.get(f"/admin/categories/{ids['fallback']}/edit")

    assert 'value="0"' in response.get_data(as_text=True)
    assert "categoría de respaldo" in text(response)


def test_edit_category_saves_the_changes(client, app, make_user, ids):
    admin_session(client, make_user)

    response = client.post(
        f"/admin/categories/{ids['category']}/edit",
        data={"nombre": "Redes y VPN", "descripcion": "", "orden": "4"},
        follow_redirects=True,
    )

    assert "La categoría «Redes y VPN» se actualizó." in text(response)

    entry = audit(app)[-1]

    assert entry.accion == "CATALOGO_MODIFICADO"
    assert entry.valor_anterior == {"nombre": "Redes"}
    assert entry.valor_nuevo == {"nombre": "Redes y VPN"}


def test_edit_category_without_changes_only_warns(client, app, make_user, ids):
    admin_session(client, make_user)
    entries_before = len(audit(app))

    response = client.post(
        f"/admin/categories/{ids['category']}/edit",
        data={"nombre": "Redes", "descripcion": "", "orden": "4"},
        follow_redirects=True,
    )

    assert "No había cambios que guardar." in text(response)
    assert len(audit(app)) == entries_before


def test_edit_category_rejects_another_ones_name(client, app, make_user, ids):
    admin_session(client, make_user)

    response = client.post(
        f"/admin/categories/{ids['category']}/edit",
        data={"nombre": "sin clasificar", "orden": "4"},
    )

    assert "Ya existe una categoría con ese nombre." in text(response)
    assert row(app, Categoria, ids["category"]).nombre == "Redes"


# --- Prioridades ------------------------------------------------------


def test_priority_form_shows_level_and_color_as_read_only(
    client,
    make_user,
    ids,
):
    admin_session(client, make_user)

    response = client.get(f"/admin/priorities/{ids['priority']}/edit")
    content = response.get_data(as_text=True)

    assert 'name="nombre"' in content
    assert 'name="nivel"' not in content
    assert 'name="color"' not in content
    assert "Nivel 2" in text(response)
    assert "#1D4ED8" in content


def test_edit_priority_changes_name_and_ignores_level_and_color(
    client,
    app,
    make_user,
    ids,
):
    admin_session(client, make_user)

    response = client.post(
        f"/admin/priorities/{ids['priority']}/edit",
        data={
            "nombre": "Normal",
            "descripcion": "Lo habitual.",
            "nivel": "9",
            "color": "#000000",
        },
        follow_redirects=True,
    )

    assert "La prioridad «Normal» se actualizó." in text(response)

    priority = row(app, Prioridad, ids["priority"])

    assert priority.nombre == "Normal"
    assert (priority.nivel, priority.color) == (2, "#1D4ED8")


def test_edit_priority_rejects_a_repeated_name(client, make_user, ids):
    admin_session(client, make_user)

    response = client.post(
        f"/admin/priorities/{ids['priority']}/edit",
        data={"nombre": "Alta"},
    )

    assert "Ya existe una prioridad con ese nombre." in text(response)


def test_priorities_cannot_be_created_from_the_interface(
    client,
    make_user,
    ids,
):
    admin_session(client, make_user)

    # No existe la ruta de alta: son exactamente cuatro (docs/11, UI-019).
    assert client.get("/admin/priorities/new").status_code == 404
    assert (
        client.post("/admin/priorities/new", data={"nombre": "X"}).status_code
        == 404
    )

    with client.application.app_context():
        assert db.session.scalar(db.select(db.func.count(Prioridad.id))) == 4


# --- Ubicaciones ------------------------------------------------------


def test_location_form_offers_the_controlled_types(client, make_user, ids):
    admin_session(client, make_user)

    content = text(client.get("/admin/locations/new"))

    assert "Sin especificar" in content

    for label in (
        "Sucursal",
        "Oficina",
        "Edificio",
        "Piso",
        "Área",
        "Instalación",
        "Otra",
    ):
        assert label in content


def test_create_location_with_a_type(client, app, make_user, ids):
    admin_session(client, make_user)

    response = client.post(
        "/admin/locations/new",
        data={"nombre": "Bodega", "tipo": "INSTALACION", "descripcion": ""},
        follow_redirects=True,
    )

    assert "La ubicación «Bodega» fue creada." in text(response)

    with app.app_context():
        location = db.session.scalar(
            db.select(Ubicacion).where(Ubicacion.nombre == "Bodega")
        )

        assert location.tipo == "INSTALACION"


def test_create_location_without_a_type(client, app, make_user, ids):
    admin_session(client, make_user)

    client.post("/admin/locations/new", data={"nombre": "Bodega", "tipo": ""})

    with app.app_context():
        location = db.session.scalar(
            db.select(Ubicacion).where(Ubicacion.nombre == "Bodega")
        )

        assert location.tipo is None


def test_create_location_rejects_an_unknown_type(client, app, make_user, ids):
    admin_session(client, make_user)

    response = client.post(
        "/admin/locations/new",
        data={"nombre": "Bodega", "tipo": "CASTILLO"},
    )

    assert "Selecciona un tipo válido." in text(response)

    with app.app_context():
        assert db.session.scalar(
            db.select(Ubicacion).where(Ubicacion.nombre == "Bodega")
        ) is None


def test_create_location_rejects_a_repeated_name(client, make_user, ids):
    admin_session(client, make_user)

    response = client.post(
        "/admin/locations/new",
        data={"nombre": "casa matriz"},
    )

    assert "Ya existe una ubicación con ese nombre." in text(response)


def test_edit_location_preselects_its_type(client, make_user, ids):
    admin_session(client, make_user)

    content = client.get(
        f"/admin/locations/{ids['location']}/edit",
    ).get_data(as_text=True)

    assert re.search(r'value="SUCURSAL"\s+selected', content)
    assert not re.search(r'value="OFICINA"\s+selected', content)


def test_edit_location_changes_its_type(client, app, make_user, ids):
    admin_session(client, make_user)

    response = client.post(
        f"/admin/locations/{ids['location']}/edit",
        data={
            "nombre": "Casa matriz",
            "tipo": "EDIFICIO",
            "descripcion": "Santiago centro",
        },
        follow_redirects=True,
    )

    assert "La ubicación «Casa matriz» se actualizó." in text(response)
    assert row(app, Ubicacion, ids["location"]).tipo == "EDIFICIO"


# --- Desactivar y reactivar -------------------------------------------


def test_deactivate_confirmation_screen_explains_the_effect(
    client,
    make_user,
    ids,
):
    admin_session(client, make_user)

    response = client.get(f"/admin/categories/{ids['category']}/deactivate")
    content = text(response)

    assert response.status_code == 200
    assert "Desactivar categoría" in content
    assert "dejará de poder elegirse en tickets nuevos" in content
    assert "Opcional. Queda registrado en la auditoría." in content


def test_deactivate_category_with_a_reason(client, app, make_user, ids):
    admin_session(client, make_user)

    response = client.post(
        f"/admin/categories/{ids['category']}/deactivate",
        data={"motivo": "Ya no se usa"},
        follow_redirects=True,
    )

    assert "La categoría «Redes» fue desactivada." in text(response)
    assert row(app, Categoria, ids["category"]).activo is False

    entry = audit(app)[-1]

    assert entry.accion == "CATALOGO_DESACTIVADO"
    assert entry.motivo == "Ya no se usa"
    assert entry.detalle == "Redes"


def test_deactivate_rejects_an_overlong_reason(client, app, make_user, ids):
    admin_session(client, make_user)

    response = client.post(
        f"/admin/categories/{ids['category']}/deactivate",
        data={"motivo": "x" * 501},
    )

    assert response.status_code == 200
    assert "Máximo 500 caracteres." in text(response)
    assert row(app, Categoria, ids["category"]).activo is True


@pytest.mark.parametrize("method", ["get", "post"])
def test_the_fallback_category_cannot_be_deactivated(
    client,
    app,
    make_user,
    ids,
    method,
):
    admin_session(client, make_user)

    response = getattr(client, method)(
        f"/admin/categories/{ids['fallback']}/deactivate",
        follow_redirects=True,
    )

    assert "categoría de respaldo" in text(response)
    assert row(app, Categoria, ids["fallback"]).activo is True


def test_the_last_active_priority_cannot_be_deactivated(
    client,
    app,
    make_user,
    ids,
):
    for code in ("BAJA", "MEDIA", "ALTA"):
        with app.app_context():
            priority_id = by_code(Prioridad, code).id

        deactivate(app, Prioridad, priority_id)

    with app.app_context():
        last_id = by_code(Prioridad, "CRITICA").id

    admin_session(client, make_user)

    response = client.post(
        f"/admin/priorities/{last_id}/deactivate",
        follow_redirects=True,
    )

    assert "Debe quedar al menos una prioridad activa." in text(response)
    assert row(app, Prioridad, last_id).activo is True


def test_deactivating_an_inactive_item_is_reported(client, app, make_user, ids):
    deactivate(app, Ubicacion, ids["location"])
    admin_session(client, make_user)

    response = client.get(
        f"/admin/locations/{ids['location']}/deactivate",
        follow_redirects=True,
    )

    assert "Este elemento ya está desactivado." in text(response)


def test_reactivate_location(client, app, make_user, ids):
    deactivate(app, Ubicacion, ids["location"])
    admin_session(client, make_user)

    screen = client.get(f"/admin/locations/{ids['location']}/activate")

    assert "Reactivar ubicación" in text(screen)

    response = client.post(
        f"/admin/locations/{ids['location']}/activate",
        data={"motivo": "Se reabrió"},
        follow_redirects=True,
    )

    assert "La ubicación «Casa matriz» fue reactivada." in text(response)
    assert row(app, Ubicacion, ids["location"]).activo is True

    entry = audit(app)[-1]

    assert entry.accion == "CATALOGO_ACTIVADO"
    assert entry.motivo == "Se reabrió"


def test_reactivating_an_active_item_is_reported(client, make_user, ids):
    admin_session(client, make_user)

    response = client.get(
        f"/admin/locations/{ids['location']}/activate",
        follow_redirects=True,
    )

    assert "Este elemento ya está activo." in text(response)


def test_reactivating_a_priority_with_a_taken_level_is_reported(
    client,
    app,
    make_user,
    ids,
):
    deactivate(app, Prioridad, ids["priority"])

    with app.app_context():
        db.session.add(Prioridad(codigo="OTRA", nombre="Otra", nivel=2))
        db.session.commit()

    admin_session(client, make_user)

    response = client.post(
        f"/admin/priorities/{ids['priority']}/activate",
        follow_redirects=True,
    )

    assert "ya hay otra prioridad activa con el mismo nivel" in text(response)
    assert row(app, Prioridad, ids["priority"]).activo is False
