from src.workdesk.extensions import db
from src.workdesk.models import User


def login(client, username: str, password: str):
    return client.post(
        "/login",
        data={
            "username": username,
            "password": password,
        },
    )


def test_valid_login_redirects_to_dashboard(client, admin_user):
    response = login(
        client,
        admin_user["username"],
        admin_user["password"],
    )

    assert response.status_code == 302
    assert response.location.endswith("/dashboard")

    dashboard_response = client.get("/dashboard")

    assert dashboard_response.status_code == 200


def test_invalid_password_is_rejected(client, admin_user):
    response = login(
        client,
        admin_user["username"],
        "ContraseñaIncorrecta123!",
    )

    content = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Usuario o contraseña incorrectos." in content


def test_inactive_user_cannot_login(
    client,
    app,
    admin_user,
):
    with app.app_context():
        user = db.session.get(User, admin_user["id"])
        user.activo = False
        db.session.commit()

    response = login(
        client,
        admin_user["username"],
        admin_user["password"],
    )

    content = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Usuario o contraseña incorrectos." in content


def test_logout_ends_authenticated_session(client, admin_user):
    login(
        client,
        admin_user["username"],
        admin_user["password"],
    )

    response = client.post("/logout")

    assert response.status_code == 302
    assert response.location.endswith("/login")

    dashboard_response = client.get("/dashboard")

    assert dashboard_response.status_code == 302
    assert "/login" in dashboard_response.location


def test_user_is_locked_after_max_failed_attempts(
    client,
    app,
    admin_user,
):
    for _ in range(5):
        login(
            client,
            admin_user["username"],
            "ContraseñaIncorrecta123!",
        )

    with app.app_context():
        user = db.session.get(User, admin_user["id"])

        assert user.intentos_fallidos == 5
        assert user.bloqueado_hasta is not None

    response = login(
        client,
        admin_user["username"],
        admin_user["password"],
    )

    content = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Usuario o contraseña incorrectos." in content


def test_token_version_invalidates_existing_session(
    client,
    app,
    admin_user,
):
    response = login(
        client,
        admin_user["username"],
        admin_user["password"],
    )

    assert response.status_code == 302

    with app.app_context():
        user = db.session.get(User, admin_user["id"])
        user.token_version += 1
        db.session.commit()

    dashboard_response = client.get("/dashboard")

    assert dashboard_response.status_code == 302
    assert "/login" in dashboard_response.location