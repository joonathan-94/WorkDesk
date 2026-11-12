import re

import pytest

from src.workdesk.extensions import db
from src.workdesk.models import AdminAuditLog, User
from src.workdesk.security import verify_password

NON_ADMIN_ROLES = ("SOLICITANTE", "TECNICO", "SUPERVISOR")
SUBPATHS = ("", "/edit", "/role", "/deactivate", "/activate", "/reset-password")
TEMPORARY_PASSWORD = "ClaveTemporal789xyz"
GENERATED_PASSWORD = re.compile(
    r'id="temporary-password"\s*>([^<]+)</code>'
)


def login(client, user_data, password=None):
    return client.post(
        "/login",
        data={
            "username": user_data["username"],
            "password": password or user_data["password"],
        },
    )


def admin_session(client, make_user):
    admin_data = make_user("ADMINISTRADOR")
    login(client, admin_data)

    return admin_data


def text(response) -> str:
    return " ".join(response.get_data(as_text=True).split())


def state(app, user_data):
    with app.app_context():
        user = db.session.get(User, user_data["id"])

        return {
            "nombre": user.nombre,
            "email": user.email,
            "username": user.username,
            "telefono": user.telefono,
            "role": user.rol.codigo,
            "active": user.activo,
            "hash": user.password_hash,
            "token_version": user.token_version,
            "must_change": user.debe_cambiar_password,
            "failed": user.intentos_fallidos,
            "locked_until": user.bloqueado_hasta,
        }


def audit(app):
    with app.app_context():
        return list(
            db.session.scalars(
                db.select(AdminAuditLog).order_by(AdminAuditLog.id)
            )
        )


def audit_actions(app):
    return [entry.accion for entry in audit(app)]


def set_user(app, user_data, **changes):
    with app.app_context():
        user = db.session.get(User, user_data["id"])

        for key, value in changes.items():
            setattr(user, key, value)

        db.session.commit()


def profile_form(**overrides):
    data = {
        "nombre": "Silvio",
        "apellido": "Dante",
        "email": "silvio.dante@workdesk.local",
        "telefono": "",
        "cargo": "",
        "departamento_area": "",
    }
    data.update(overrides)

    return data


# --- Control de acceso ------------------------------------------------


@pytest.mark.parametrize("subpath", SUBPATHS)
def test_anonymous_user_is_redirected_to_login(
    client,
    seeded_roles,
    make_user,
    subpath,
):
    target = make_user("TECNICO")

    response = client.get(f"/users/{target['id']}{subpath}")

    assert response.status_code == 302
    assert "/login" in response.location


@pytest.mark.parametrize("subpath", SUBPATHS)
@pytest.mark.parametrize("role_code", NON_ADMIN_ROLES)
def test_non_admin_roles_are_forbidden_on_get_and_post(
    client,
    app,
    seeded_roles,
    make_user,
    role_code,
    subpath,
):
    actor = make_user(role_code)
    target = make_user("TECNICO", username="objetivo")
    login(client, actor)
    before = state(app, target)

    url = f"/users/{target['id']}{subpath}"

    assert client.get(url).status_code == 403

    # El detalle es de solo lectura: solo las rutas de acción aceptan POST.
    if subpath:
        response = client.post(url, data={"rol": "ADMINISTRADOR"})

        assert response.status_code == 403

    assert state(app, target) == before
    assert audit(app) == []


@pytest.mark.parametrize("subpath", SUBPATHS)
def test_unknown_user_returns_not_found(
    client,
    seeded_roles,
    make_user,
    subpath,
):
    admin_session(client, make_user)

    assert client.get(f"/users/99999{subpath}").status_code == 404


def test_post_without_csrf_token_is_rejected(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    target = make_user("TECNICO")
    app.config["WTF_CSRF_ENABLED"] = True

    response = client.post(f"/users/{target['id']}/deactivate", data={})

    assert response.status_code == 400
    assert state(app, target)["active"] is True


# --- Detalle ----------------------------------------------------------


def test_list_links_to_each_user_detail(client, seeded_roles, make_user):
    admin_session(client, make_user)
    target = make_user("TECNICO")

    content = client.get("/users").get_data(as_text=True)

    assert f'href="/users/{target["id"]}"' in content


def test_detail_shows_the_data_and_the_actions(
    client,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    target = make_user("TECNICO")

    response = client.get(f"/users/{target['id']}")
    content = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "tecnico_test@workdesk.local" in content
    assert f"/users/{target['id']}/edit" in content
    assert f"/users/{target['id']}/role" in content
    assert f"/users/{target['id']}/reset-password" in content
    assert f"/users/{target['id']}/deactivate" in content
    assert f"/users/{target['id']}/activate" not in content


def test_detail_of_an_inactive_user_offers_reactivation(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    target = make_user("TECNICO", activo=False)

    content = client.get(f"/users/{target['id']}").get_data(as_text=True)

    assert "Inactivo" in content
    assert f"/users/{target['id']}/activate" in content
    assert f"/users/{target['id']}/deactivate" not in content


def test_detail_of_the_own_account_hides_the_restricted_actions(
    client,
    seeded_roles,
    make_user,
):
    admin = admin_session(client, make_user)

    content = client.get(f"/users/{admin['id']}").get_data(as_text=True)

    assert "Esta es tu cuenta" in " ".join(content.split())
    assert f"/users/{admin['id']}/edit" in content
    assert f"/users/{admin['id']}/role" not in content
    assert f"/users/{admin['id']}/deactivate" not in content
    assert f"/users/{admin['id']}/reset-password" not in content


# --- Edición ----------------------------------------------------------


def test_edit_form_is_prefilled_and_username_is_read_only(
    client,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    target = make_user("TECNICO")

    content = client.get(f"/users/{target['id']}/edit").get_data(as_text=True)

    assert 'value="Tecnico"' in content
    assert 'value="tecnico_test@workdesk.local"' in content
    assert 'name="username"' not in content
    assert "no se puede cambiar" in " ".join(content.split())


def test_edit_updates_the_data_and_audits_it(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    target = make_user("TECNICO")

    response = client.post(
        f"/users/{target['id']}/edit",
        data=profile_form(cargo="Consigliere"),
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Los datos del usuario se actualizaron." in text(response)
    assert state(app, target)["nombre"] == "Silvio"
    assert audit_actions(app) == ["USUARIO_MODIFICADO"]


def test_edit_without_changes_only_warns(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    target = make_user("TECNICO")

    response = client.post(
        f"/users/{target['id']}/edit",
        data=profile_form(
            nombre="Tecnico",
            apellido="Pruebas",
            email="tecnico_test@workdesk.local",
        ),
        follow_redirects=True,
    )

    assert "No había cambios que guardar." in text(response)
    assert audit(app) == []


def test_edit_rejects_the_email_of_another_user(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin = admin_session(client, make_user)
    target = make_user("TECNICO")

    response = client.post(
        f"/users/{target['id']}/edit",
        data=profile_form(email="administrador_test@workdesk.local"),
    )

    assert response.status_code == 200
    assert "Ya existe un usuario con ese correo." in text(response)
    assert state(app, target)["email"] == "tecnico_test@workdesk.local"
    assert state(app, admin)["email"] == "administrador_test@workdesk.local"
    assert audit(app) == []


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"nombre": ""}, "Ingresa el nombre."),
        ({"apellido": ""}, "Ingresa el apellido."),
        ({"email": "sin-arroba"}, "correo electrónico válido"),
        ({"telefono": "1" * 31}, "Máximo 30 caracteres."),
    ],
)
def test_edit_validates_each_field(
    client,
    app,
    seeded_roles,
    make_user,
    overrides,
    message,
):
    admin_session(client, make_user)
    target = make_user("TECNICO")
    before = state(app, target)

    response = client.post(
        f"/users/{target['id']}/edit",
        data=profile_form(**overrides),
    )

    assert response.status_code == 200
    assert message in text(response)
    assert state(app, target) == before


def test_edit_never_changes_the_username(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    target = make_user("TECNICO")

    client.post(
        f"/users/{target['id']}/edit",
        data=profile_form(username="intruso"),
    )

    assert state(app, target)["username"] == "tecnico_test"


def test_admin_can_edit_the_own_data(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin = admin_session(client, make_user)

    client.post(
        f"/users/{admin['id']}/edit",
        data=profile_form(
            nombre="Vito",
            apellido="Corleone",
            email="administrador_test@workdesk.local",
        ),
    )

    assert state(app, admin)["nombre"] == "Vito"


# --- Cambio de rol ----------------------------------------------------


def test_role_form_preselects_the_current_role(
    client,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    target = make_user("TECNICO")

    content = client.get(f"/users/{target['id']}/role").get_data(as_text=True)

    assert re.search(r'value="TECNICO"\s+selected', content)
    assert "iniciar sesión de nuevo" in " ".join(content.split())


def test_role_change_is_applied_audited_and_confirmed(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    target = make_user("TECNICO")

    response = client.post(
        f"/users/{target['id']}/role",
        data={"rol": "SUPERVISOR", "motivo": "Ascenso."},
        follow_redirects=True,
    )

    assert "ahora es Supervisor" in text(response)
    assert state(app, target)["role"] == "SUPERVISOR"

    (entry,) = audit(app)

    assert entry.accion == "CAMBIO_ROL"
    assert entry.motivo == "Ascenso."


def test_role_change_closes_the_open_sessions_of_the_user(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    target = make_user("TECNICO")

    target_client = app.test_client()
    login(target_client, target)
    assert target_client.get("/dashboard").status_code == 200

    client.post(f"/users/{target['id']}/role", data={"rol": "SUPERVISOR"})

    response = target_client.get("/dashboard")

    assert response.status_code == 302
    assert "/login" in response.location


def test_role_change_rejects_an_invalid_role(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    target = make_user("TECNICO")

    response = client.post(
        f"/users/{target['id']}/role",
        data={"rol": "SUPERADMIN"},
    )

    assert response.status_code == 200
    assert "Selecciona un rol válido." in text(response)
    assert state(app, target)["role"] == "TECNICO"


def test_role_change_to_the_same_role_is_reported(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    target = make_user("TECNICO")

    response = client.post(
        f"/users/{target['id']}/role",
        data={"rol": "TECNICO"},
        follow_redirects=True,
    )

    assert "El usuario ya tiene ese rol." in text(response)
    assert audit(app) == []


def test_role_change_rejects_a_too_long_reason(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    target = make_user("TECNICO")

    response = client.post(
        f"/users/{target['id']}/role",
        data={"rol": "SUPERVISOR", "motivo": "x" * 501},
    )

    assert response.status_code == 200
    assert "Máximo 500 caracteres." in text(response)
    assert state(app, target)["role"] == "TECNICO"


def test_admin_cannot_change_the_own_role(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin = admin_session(client, make_user)

    page = client.get(f"/users/{admin['id']}/role", follow_redirects=True)
    post = client.post(
        f"/users/{admin['id']}/role",
        data={"rol": "TECNICO"},
        follow_redirects=True,
    )

    assert "No puedes cambiar tu propio rol." in text(page)
    assert "No puedes cambiar tu propio rol." in text(post)
    assert state(app, admin)["role"] == "ADMINISTRADOR"
    assert audit(app) == []


# --- Desactivación y reactivación -------------------------------------


def test_deactivation_asks_for_confirmation_first(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    target = make_user("TECNICO")

    response = client.get(f"/users/{target['id']}/deactivate")
    content = text(response)

    assert response.status_code == 200
    assert "Desactivar cuenta" in content
    assert "no podrá iniciar sesión" in content
    assert state(app, target)["active"] is True


def test_deactivation_blocks_login_and_closes_sessions(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    target = make_user("TECNICO")

    target_client = app.test_client()
    login(target_client, target)

    response = client.post(
        f"/users/{target['id']}/deactivate",
        data={"motivo": "Dejó la empresa."},
        follow_redirects=True,
    )

    assert "fue desactivada" in text(response)
    assert state(app, target)["active"] is False
    assert target_client.get("/dashboard").status_code == 302

    # Tampoco puede iniciar una sesión nueva.
    fresh_client = app.test_client()
    assert login(fresh_client, target).status_code == 200
    assert fresh_client.get("/dashboard").status_code == 302

    (entry,) = audit(app)

    assert entry.accion == "USUARIO_DESACTIVADO"
    assert entry.motivo == "Dejó la empresa."


def test_deactivated_user_shows_in_the_inactive_filter(
    client,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    target = make_user("TECNICO")

    client.post(f"/users/{target['id']}/deactivate", data={})
    content = client.get("/users?estado=inactivo").get_data(as_text=True)

    assert "tecnico_test@workdesk.local" in content
    assert "administrador_test@workdesk.local" not in content


def test_admin_cannot_deactivate_the_own_account(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin = admin_session(client, make_user)

    page = client.get(f"/users/{admin['id']}/deactivate", follow_redirects=True)
    post = client.post(
        f"/users/{admin['id']}/deactivate",
        data={},
        follow_redirects=True,
    )

    assert "No puedes desactivar tu propia cuenta." in text(page)
    assert "No puedes desactivar tu propia cuenta." in text(post)
    assert state(app, admin)["active"] is True
    assert audit(app) == []


def test_deactivating_an_inactive_user_is_reported(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    target = make_user("TECNICO", activo=False)

    response = client.post(
        f"/users/{target['id']}/deactivate",
        data={},
        follow_redirects=True,
    )

    assert "El usuario ya está desactivado." in text(response)
    assert audit(app) == []


def test_reactivation_lets_the_user_login_again(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    target = make_user("TECNICO")
    client.post(f"/users/{target['id']}/deactivate", data={})

    page = client.get(f"/users/{target['id']}/activate")
    response = client.post(
        f"/users/{target['id']}/activate",
        data={"motivo": "Regresó."},
        follow_redirects=True,
    )

    fresh_client = app.test_client()
    login_response = login(fresh_client, target)

    assert "Reactivar cuenta" in text(page)
    assert "fue reactivada" in text(response)
    assert state(app, target)["active"] is True
    assert login_response.status_code == 302
    assert audit_actions(app) == ["USUARIO_DESACTIVADO", "USUARIO_ACTIVADO"]


def test_reactivating_an_active_user_is_reported(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    target = make_user("TECNICO")

    response = client.post(
        f"/users/{target['id']}/activate",
        data={},
        follow_redirects=True,
    )

    assert "El usuario ya está activo." in text(response)
    assert audit(app) == []


# --- Restablecimiento de contraseña ----------------------------------


def test_reset_with_generated_password_shows_it_once(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    target = make_user("TECNICO")
    set_user(app, target, intentos_fallidos=3)

    response = client.post(
        f"/users/{target['id']}/reset-password",
        data={"password_mode": "generate", "temporary_password": ""},
    )
    content = response.get_data(as_text=True)
    match = GENERATED_PASSWORD.search(content)
    after = state(app, target)

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert match is not None
    assert verify_password(after["hash"], match.group(1))
    assert after["must_change"] is True
    assert after["failed"] == 0

    # No se puede volver a consultar.
    assert match.group(1) not in client.get(
        f"/users/{target['id']}"
    ).get_data(as_text=True)


def test_reset_closes_sessions_and_forces_the_change_on_next_login(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    target = make_user("TECNICO")

    target_client = app.test_client()
    login(target_client, target)

    content = client.post(
        f"/users/{target['id']}/reset-password",
        data={"password_mode": "generate", "temporary_password": ""},
    ).get_data(as_text=True)
    password = GENERATED_PASSWORD.search(content).group(1)

    assert target_client.get("/dashboard").status_code == 302

    fresh_client = app.test_client()

    assert login(fresh_client, target).status_code == 200  # contraseña vieja
    assert login(fresh_client, target, password).status_code == 302
    assert fresh_client.get("/dashboard").location.endswith(
        "/account/password"
    )


def test_reset_with_a_typed_password_does_not_display_it(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    target = make_user("TECNICO")

    response = client.post(
        f"/users/{target['id']}/reset-password",
        data={
            "password_mode": "manual",
            "temporary_password": TEMPORARY_PASSWORD,
        },
    )
    content = response.get_data(as_text=True)

    assert response.status_code == 200
    assert TEMPORARY_PASSWORD not in content
    assert GENERATED_PASSWORD.search(content) is None
    assert verify_password(
        state(app, target)["hash"],
        TEMPORARY_PASSWORD,
    )


def test_reset_is_audited_without_the_password(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    target = make_user("TECNICO")

    content = client.post(
        f"/users/{target['id']}/reset-password",
        data={"password_mode": "generate", "temporary_password": ""},
    ).get_data(as_text=True)
    password = GENERATED_PASSWORD.search(content).group(1)

    (entry,) = audit(app)

    assert entry.accion == "PASSWORD_RESTABLECIDA"
    assert password not in f"{entry.valor_anterior} {entry.valor_nuevo}"


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (
            {"password_mode": "manual", "temporary_password": "corta"},
            "al menos",
        ),
        (
            {"password_mode": "manual", "temporary_password": ""},
            "Ingresa la contraseña temporal.",
        ),
        (
            {"password_mode": "otro", "temporary_password": ""},
            "Elige cómo definir la contraseña.",
        ),
    ],
)
def test_reset_rejects_an_invalid_password_choice(
    client,
    app,
    seeded_roles,
    make_user,
    data,
    message,
):
    admin_session(client, make_user)
    target = make_user("TECNICO")
    before = state(app, target)

    response = client.post(f"/users/{target['id']}/reset-password", data=data)

    assert response.status_code == 200
    assert message in text(response)
    assert state(app, target) == before
    assert audit(app) == []


def test_admin_cannot_reset_the_own_password_from_the_panel(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin = admin_session(client, make_user)
    before = state(app, admin)

    page = client.get(
        f"/users/{admin['id']}/reset-password",
        follow_redirects=True,
    )
    post = client.post(
        f"/users/{admin['id']}/reset-password",
        data={"password_mode": "generate", "temporary_password": ""},
        follow_redirects=True,
    )

    assert "usa «Cambiar contraseña»" in text(page)
    assert "usa «Cambiar contraseña»" in text(post)
    assert state(app, admin) == before
    assert audit(app) == []
