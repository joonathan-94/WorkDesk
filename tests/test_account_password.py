from datetime import UTC, datetime, timedelta

from src.workdesk.extensions import db
from src.workdesk.models import AdminAuditLog, User
from src.workdesk.security import verify_password

NEW_PASSWORD = "NuevaClaveSegura456!"
STARTED_KEY = "session_started_at"


def login(client, user_data, password=None):
    return client.post(
        "/login",
        data={
            "username": user_data["username"],
            "password": password or user_data["password"],
        },
    )


def submit_change(client, user_data, *, new=NEW_PASSWORD, confirm=None):
    return client.post(
        "/account/password",
        data={
            "current_password": user_data["password"],
            "new_password": new,
            "confirm_password": new if confirm is None else confirm,
        },
    )


def user_state(app, user_data):
    with app.app_context():
        user = db.session.get(User, user_data["id"])

        return {
            "hash": user.password_hash,
            "token_version": user.token_version,
            "failed_attempts": user.intentos_fallidos,
            "locked_until": user.bloqueado_hasta,
            "must_change": user.debe_cambiar_password,
        }


def update_user(app, user_data, **changes):
    with app.app_context():
        user = db.session.get(User, user_data["id"])

        for key, value in changes.items():
            setattr(user, key, value)

        db.session.commit()


def audit_actions(app):
    with app.app_context():
        return list(
            db.session.scalars(
                db.select(AdminAuditLog.accion).order_by(AdminAuditLog.id)
            )
        )


def logged_in(client, make_user, role="TECNICO"):
    user_data = make_user(role)
    login(client, user_data)

    return user_data


def assert_redirects_to(response, path):
    assert response.status_code == 302
    assert response.location.endswith(path)


# --- Acceso -----------------------------------------------------------


def test_anonymous_user_is_redirected_to_login(client):
    for response in (
        client.get("/account/password"),
        client.post("/account/password"),
    ):
        assert response.status_code == 302
        assert "/login" in response.location


def test_page_is_shown_to_an_authenticated_user(client, app, make_user):
    logged_in(client, make_user)

    response = client.get("/account/password")
    content = response.get_data(as_text=True)
    # Se normalizan los espacios del HTML para comparar el texto visible.
    visible_text = " ".join(content.split())
    min_length = app.config["PASSWORD_MIN_LENGTH"]

    assert response.status_code == 200
    assert "Cambiar contraseña" in content
    assert "contraseña temporal" not in content
    assert "Volver al dashboard" in content
    assert f"Mínimo {min_length} caracteres." in visible_text


def test_post_without_csrf_token_is_rejected(client, app, make_user):
    user_data = logged_in(client, make_user)
    app.config["WTF_CSRF_ENABLED"] = True

    response = submit_change(client, user_data)

    assert response.status_code == 400
    assert verify_password(
        user_state(app, user_data)["hash"],
        user_data["password"],
    )


# --- Cambio correcto --------------------------------------------------


def test_valid_change_updates_the_password(client, app, make_user):
    user_data = logged_in(client, make_user)
    before = user_state(app, user_data)

    response = submit_change(client, user_data)

    assert_redirects_to(response, "/dashboard")

    after = user_state(app, user_data)

    assert verify_password(after["hash"], NEW_PASSWORD)
    assert not verify_password(after["hash"], user_data["password"])
    assert after["token_version"] == before["token_version"] + 1
    assert after["must_change"] is False


def test_user_stays_logged_in_and_sees_confirmation(
    client,
    make_user,
):
    user_data = logged_in(client, make_user)

    response = submit_change(client, user_data)
    dashboard = client.get(response.location)

    assert dashboard.status_code == 200
    assert "Tu contraseña se actualizó correctamente." in (
        dashboard.get_data(as_text=True)
    )


def test_valid_change_is_audited(client, app, make_user):
    user_data = logged_in(client, make_user)

    submit_change(client, user_data)

    assert audit_actions(app) == ["PASSWORD_CAMBIADA"]


def test_new_password_works_for_a_new_login_and_old_does_not(
    client,
    app,
    make_user,
):
    user_data = logged_in(client, make_user)
    submit_change(client, user_data)

    fresh_client = app.test_client()

    old_login = login(fresh_client, user_data)
    new_login = login(fresh_client, user_data, NEW_PASSWORD)

    assert old_login.status_code == 200
    assert_redirects_to(new_login, "/dashboard")


def test_other_sessions_are_invalidated(client, app, make_user):
    user_data = logged_in(client, make_user)

    other_client = app.test_client()
    login(other_client, user_data)
    assert other_client.get("/dashboard").status_code == 200

    submit_change(client, user_data)

    response = other_client.get("/dashboard")

    assert response.status_code == 302
    assert "/login" in response.location


def test_change_does_not_extend_the_session_duration(client, make_user):
    user_data = logged_in(client, make_user)

    with client.session_transaction() as client_session:
        started_at = client_session[STARTED_KEY]

    submit_change(client, user_data)

    with client.session_transaction() as client_session:
        assert client_session[STARTED_KEY] == started_at


def test_valid_change_clears_failed_attempts(client, app, make_user):
    user_data = logged_in(client, make_user)
    update_user(app, user_data, intentos_fallidos=2)

    submit_change(client, user_data)

    assert user_state(app, user_data)["failed_attempts"] == 0


# --- Errores de validación -------------------------------------------


def test_wrong_current_password_is_rejected_and_counted(
    client,
    app,
    make_user,
):
    user_data = logged_in(client, make_user)
    before = user_state(app, user_data)

    response = client.post(
        "/account/password",
        data={
            "current_password": "ClaveIncorrecta000",
            "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
        },
    )
    content = response.get_data(as_text=True)
    after = user_state(app, user_data)

    assert response.status_code == 200
    assert "La contraseña actual no es correcta." in content
    assert after["hash"] == before["hash"]
    assert after["token_version"] == before["token_version"]
    assert after["failed_attempts"] == 1
    assert audit_actions(app) == []


def test_form_never_echoes_submitted_passwords(client, make_user):
    user_data = logged_in(client, make_user)

    response = client.post(
        "/account/password",
        data={
            "current_password": "ClaveIncorrecta000",
            "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
        },
    )
    content = response.get_data(as_text=True)

    assert "ClaveIncorrecta000" not in content
    assert NEW_PASSWORD not in content
    assert user_data["password"] not in content


def test_repeated_wrong_current_password_locks_the_account(
    client,
    app,
    make_user,
):
    user_data = logged_in(client, make_user)
    max_attempts = app.config["LOGIN_MAX_FAILED_ATTEMPTS"]

    for _ in range(max_attempts - 1):
        response = client.post(
            "/account/password",
            data={
                "current_password": "ClaveIncorrecta000",
                "new_password": NEW_PASSWORD,
                "confirm_password": NEW_PASSWORD,
            },
        )
        assert response.status_code == 200

    response = client.post(
        "/account/password",
        data={
            "current_password": "ClaveIncorrecta000",
            "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
        },
    )

    assert_redirects_to(response, "/login")
    assert user_state(app, user_data)["locked_until"] is not None

    # La sesión se cerró y la cuenta no permite iniciar sesión.
    assert client.get("/dashboard").status_code == 302
    assert login(client, user_data).status_code == 200


def test_locked_account_rejects_even_the_correct_current_password(
    client,
    app,
    make_user,
):
    user_data = logged_in(client, make_user)
    before = user_state(app, user_data)
    update_user(
        app,
        user_data,
        intentos_fallidos=5,
        bloqueado_hasta=datetime.now(UTC) + timedelta(minutes=10),
    )

    response = submit_change(client, user_data)
    content = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "bloqueada temporalmente" in content
    assert user_state(app, user_data)["hash"] == before["hash"]


def test_mismatched_confirmation_is_rejected(client, app, make_user):
    user_data = logged_in(client, make_user)
    before = user_state(app, user_data)

    response = submit_change(
        client,
        user_data,
        confirm="OtraClaveDistinta789!",
    )
    after = user_state(app, user_data)

    assert response.status_code == 200
    assert "Las contraseñas no coinciden." in response.get_data(
        as_text=True
    )
    assert after["hash"] == before["hash"]
    assert after["failed_attempts"] == 0


def test_too_short_new_password_is_rejected(client, app, make_user):
    user_data = logged_in(client, make_user)
    before = user_state(app, user_data)

    response = submit_change(client, user_data, new="corta")
    after = user_state(app, user_data)

    assert response.status_code == 200
    assert "al menos" in response.get_data(as_text=True)
    assert after["hash"] == before["hash"]
    assert after["failed_attempts"] == 0
    assert audit_actions(app) == []


def test_new_password_equal_to_current_is_rejected(
    client,
    app,
    make_user,
):
    user_data = logged_in(client, make_user)

    response = submit_change(client, user_data, new=user_data["password"])

    assert response.status_code == 200
    assert "distinta de la actual" in response.get_data(as_text=True)
    assert audit_actions(app) == []


def test_missing_fields_are_reported(client, make_user):
    logged_in(client, make_user)

    response = client.post("/account/password", data={})
    content = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Ingresa tu contraseña actual." in content
    assert "Ingresa la nueva contraseña." in content


# --- Cambio obligatorio ----------------------------------------------


def login_with_mandatory_change(client, app, make_user, role="TECNICO"):
    user_data = make_user(role)
    update_user(app, user_data, debe_cambiar_password=True)
    login(client, user_data)

    return user_data


def test_pending_change_redirects_every_page_to_the_change_screen(
    client,
    app,
    make_user,
):
    login_with_mandatory_change(client, app, make_user)

    for path in ("/dashboard", "/", "/admin", "/login", "/no-existe"):
        response = client.get(path)

        assert_redirects_to(response, "/account/password")


def test_pending_change_blocks_actions_on_other_routes(
    client,
    app,
    make_user,
):
    login_with_mandatory_change(
        client,
        app,
        make_user,
        role="ADMINISTRADOR",
    )

    assert_redirects_to(client.get("/admin"), "/account/password")


def test_pending_change_still_allows_the_change_screen_and_logout(
    client,
    app,
    make_user,
):
    login_with_mandatory_change(client, app, make_user)

    page = client.get("/account/password")
    content = page.get_data(as_text=True)

    assert page.status_code == 200
    assert "contraseña temporal" in content
    assert "Cerrar sesión" in content
    assert "Volver al dashboard" not in content

    assert_redirects_to(client.post("/logout"), "/login")


def test_pending_change_still_allows_technical_routes(
    client,
    app,
    make_user,
):
    login_with_mandatory_change(client, app, make_user)

    assert client.get("/health").status_code == 200
    assert client.get("/static/css/auth.css").status_code == 200


def test_completing_the_change_releases_the_restriction(
    client,
    app,
    make_user,
):
    user_data = login_with_mandatory_change(client, app, make_user)

    response = submit_change(client, user_data)

    assert_redirects_to(response, "/dashboard")
    assert user_state(app, user_data)["must_change"] is False
    assert client.get("/dashboard").status_code == 200


def test_failed_change_keeps_the_restriction(client, app, make_user):
    user_data = login_with_mandatory_change(client, app, make_user)

    submit_change(client, user_data, new="corta")

    assert user_state(app, user_data)["must_change"] is True
    assert_redirects_to(client.get("/dashboard"), "/account/password")


def test_users_without_pending_change_are_not_restricted(
    client,
    make_user,
):
    logged_in(client, make_user)

    assert client.get("/dashboard").status_code == 200
