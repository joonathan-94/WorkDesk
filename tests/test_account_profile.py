import re

import pytest

from src.workdesk.extensions import db
from src.workdesk.models import AdminAuditLog, User

ALL_ROLES = ("SOLICITANTE", "TECNICO", "SUPERVISOR", "ADMINISTRADOR")


def login(client, user_data):
    return client.post(
        "/login",
        data={
            "username": user_data["username"],
            "password": user_data["password"],
        },
    )


def logged_in(client, make_user, role="TECNICO", **kwargs):
    user_data = make_user(role, **kwargs)
    login(client, user_data)

    return user_data


def text(response) -> str:
    return " ".join(response.get_data(as_text=True).split())


def snapshot(app, user_data):
    with app.app_context():
        user = db.session.get(User, user_data["id"])

        return {
            "nombre": user.nombre,
            "apellido": user.apellido,
            "email": user.email,
            "username": user.username,
            "role": user.rol.codigo,
            "telefono": user.telefono,
            "cargo": user.cargo,
            "area": user.departamento_area,
        }


def audit(app):
    with app.app_context():
        return list(
            db.session.scalars(
                db.select(AdminAuditLog).order_by(AdminAuditLog.id)
            )
        )


def contact(**overrides):
    data = {
        "telefono": "+56 9 5555 0000",
        "cargo": "Analista",
        "departamento_area": "Soporte TI",
    }
    data.update(overrides)

    return data


# --- Acceso -----------------------------------------------------------


def test_anonymous_user_is_redirected_to_login(client):
    for response in (client.get("/account"), client.post("/account")):
        assert response.status_code == 302
        assert "/login" in response.location


@pytest.mark.parametrize("role_code", ALL_ROLES)
def test_every_role_can_open_my_account(
    client,
    seeded_roles,
    make_user,
    role_code,
):
    logged_in(client, make_user, role_code)

    response = client.get("/account")

    assert response.status_code == 200
    assert "Mi cuenta" in response.get_data(as_text=True)


def test_my_account_is_blocked_while_a_password_change_is_pending(
    client,
    seeded_roles,
    make_user,
):
    logged_in(client, make_user, debe_cambiar_password=True)

    response = client.get("/account")

    assert response.status_code == 302
    assert response.location.endswith("/account/password")


# --- Contenido --------------------------------------------------------


def test_my_account_shows_the_own_data(client, seeded_roles, make_user):
    logged_in(client, make_user, "SUPERVISOR")

    content = text(client.get("/account"))

    assert "Supervisor Pruebas" in content
    assert "supervisor_test" in content
    assert "supervisor_test@workdesk.local" in content
    assert "Supervisor" in content
    assert "los gestiona un Administrador" in content


def test_my_account_prefills_the_editable_fields(
    client,
    seeded_roles,
    make_user,
):
    logged_in(
        client,
        make_user,
        telefono="+56 9 1111 2222",
        cargo="Técnico",
        departamento_area="Redes",
    )

    content = client.get("/account").get_data(as_text=True)

    assert 'value="+56 9 1111 2222"' in content
    assert 'value="Técnico"' in content
    assert 'value="Redes"' in content


def test_my_account_links_to_the_password_change(
    client,
    seeded_roles,
    make_user,
):
    logged_in(client, make_user)

    content = client.get("/account").get_data(as_text=True)

    assert 'href="/account/password"' in content


def test_my_account_does_not_expose_administrative_actions(
    client,
    seeded_roles,
    make_user,
):
    logged_in(client, make_user, "TECNICO")

    content = client.get("/account").get_data(as_text=True)

    assert 'href="/admin"' not in content
    assert "/users" not in content


# --- Edición ----------------------------------------------------------


def test_user_can_update_the_contact_information(
    client,
    app,
    seeded_roles,
    make_user,
):
    user_data = logged_in(client, make_user)

    response = client.post(
        "/account",
        data=contact(),
        follow_redirects=True,
    )
    saved = snapshot(app, user_data)

    assert "Tus datos se actualizaron." in text(response)
    assert saved["telefono"] == "+56 9 5555 0000"
    assert saved["cargo"] == "Analista"
    assert saved["area"] == "Soporte TI"


def test_update_is_audited_by_the_user_with_only_the_changed_fields(
    client,
    app,
    seeded_roles,
    make_user,
):
    user_data = logged_in(client, make_user, cargo="Técnico")

    client.post("/account", data=contact(cargo="Técnico"))

    (entry,) = audit(app)

    assert entry.accion == "USUARIO_MODIFICADO"
    assert entry.actor_usuario_id == user_data["id"]
    assert entry.entidad_id == user_data["id"]
    assert entry.valor_anterior == {"telefono": None, "departamento_area": None}
    assert entry.valor_nuevo == {
        "telefono": "+56 9 5555 0000",
        "departamento_area": "Soporte TI",
    }


def test_update_without_changes_only_warns(
    client,
    app,
    seeded_roles,
    make_user,
):
    logged_in(
        client,
        make_user,
        telefono="+56 9 5555 0000",
        cargo="Analista",
        departamento_area="Soporte TI",
    )

    response = client.post(
        "/account",
        data=contact(),
        follow_redirects=True,
    )

    assert "No había cambios que guardar." in text(response)
    assert audit(app) == []


def test_blank_values_clear_the_optional_fields(
    client,
    app,
    seeded_roles,
    make_user,
):
    user_data = logged_in(client, make_user, telefono="123", cargo="X")

    client.post(
        "/account",
        data=contact(telefono="  ", cargo="", departamento_area=""),
    )

    saved = snapshot(app, user_data)

    assert saved["telefono"] is None
    assert saved["cargo"] is None


def test_user_cannot_change_the_fields_managed_by_the_administrator(
    client,
    app,
    seeded_roles,
    make_user,
):
    user_data = logged_in(client, make_user, "SOLICITANTE")
    before = snapshot(app, user_data)

    client.post(
        "/account",
        data=contact(
            nombre="Intruso",
            apellido="Falso",
            email="intruso@workdesk.local",
            username="intruso",
            rol="ADMINISTRADOR",
        ),
    )
    after = snapshot(app, user_data)

    assert after["nombre"] == before["nombre"]
    assert after["apellido"] == before["apellido"]
    assert after["email"] == before["email"]
    assert after["username"] == before["username"]
    assert after["role"] == "SOLICITANTE"


def test_user_only_edits_the_own_account(
    client,
    app,
    seeded_roles,
    make_user,
):
    own = logged_in(client, make_user, "TECNICO")
    other = make_user("SUPERVISOR")

    client.post("/account", data=contact())

    assert snapshot(app, own)["cargo"] == "Analista"
    assert snapshot(app, other)["cargo"] is None


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"telefono": "1" * 31}, "Máximo 30 caracteres."),
        ({"cargo": "x" * 101}, "Máximo 100 caracteres."),
        ({"departamento_area": "x" * 101}, "Máximo 100 caracteres."),
    ],
)
def test_contact_fields_are_validated(
    client,
    app,
    seeded_roles,
    make_user,
    overrides,
    message,
):
    user_data = logged_in(client, make_user)
    before = snapshot(app, user_data)

    response = client.post("/account", data=contact(**overrides))

    assert response.status_code == 200
    assert message in text(response)
    assert snapshot(app, user_data) == before
    assert audit(app) == []


def test_post_without_csrf_token_is_rejected(
    client,
    app,
    seeded_roles,
    make_user,
):
    user_data = logged_in(client, make_user)
    before = snapshot(app, user_data)
    app.config["WTF_CSRF_ENABLED"] = True

    response = client.post("/account", data=contact())

    assert response.status_code == 400
    assert snapshot(app, user_data) == before


# --- Navegación y pantallas de contraseña ----------------------------


def test_my_account_is_the_active_option_in_the_account_pages(
    client,
    seeded_roles,
    make_user,
):
    logged_in(client, make_user)

    for path in ("/account", "/account/password"):
        content = client.get(path).get_data(as_text=True)
        active = re.search(
            r'class="sidebar-link is-active"\s+href="([^"]+)"',
            content,
        )

        assert active is not None
        assert active.group(1) == "/account"


def test_topbar_menu_offers_my_account_and_the_password_change(
    client,
    seeded_roles,
    make_user,
):
    logged_in(client, make_user)

    content = client.get("/dashboard").get_data(as_text=True)

    assert 'href="/account"' in content
    assert 'href="/account/password"' in content


def test_password_change_uses_the_main_layout_in_normal_mode(
    client,
    seeded_roles,
    make_user,
):
    logged_in(client, make_user)

    content = client.get("/account/password").get_data(as_text=True)

    assert "app-sidebar" in content
    assert "bootstrap.min.css" in content


def test_password_change_is_isolated_when_it_is_mandatory(
    client,
    seeded_roles,
    make_user,
):
    logged_in(client, make_user, debe_cambiar_password=True)

    content = client.get("/account/password").get_data(as_text=True)

    assert "app-sidebar" not in content
    assert "bootstrap" not in content
    assert "Cerrar sesión" in content
