from datetime import UTC, datetime

import pytest

from src.workdesk import create_app

STARTED_KEY = "session_started_at"
ACTIVITY_KEY = "session_last_activity"


def now_timestamp() -> float:
    return datetime.now(UTC).timestamp()


def login(client, admin_user):
    return client.post(
        "/login",
        data={
            "username": admin_user["username"],
            "password": admin_user["password"],
        },
    )


def set_session_times(client, *, started_ago, activity_ago):
    """Retrocede las marcas de tiempo de la sesión (en segundos)."""
    now = now_timestamp()

    with client.session_transaction() as client_session:
        client_session[STARTED_KEY] = now - started_ago
        client_session[ACTIVITY_KEY] = now - activity_ago


def assert_redirected_to_login(response):
    assert response.status_code == 302
    assert "/login" in response.location


def test_login_starts_the_session_clock(client, admin_user):
    login(client, admin_user)

    with client.session_transaction() as client_session:
        assert STARTED_KEY in client_session
        assert ACTIVITY_KEY in client_session


def test_active_session_within_limits_is_accepted_and_renewed(
    client,
    admin_user,
):
    login(client, admin_user)
    set_session_times(client, started_ago=600, activity_ago=600)

    with client.session_transaction() as client_session:
        previous_activity = client_session[ACTIVITY_KEY]

    response = client.get("/dashboard")

    assert response.status_code == 200

    with client.session_transaction() as client_session:
        assert client_session[ACTIVITY_KEY] > previous_activity


def test_session_expires_after_idle_limit(client, app, admin_user):
    login(client, admin_user)

    idle_seconds = app.config["SESSION_IDLE_MINUTES"] * 60
    set_session_times(
        client,
        started_ago=idle_seconds + 60,
        activity_ago=idle_seconds + 60,
    )

    response = client.get("/dashboard")

    assert_redirected_to_login(response)

    # La sesión quedó cerrada: ya no se puede volver a entrar.
    assert_redirected_to_login(client.get("/dashboard"))


def test_expired_session_shows_message_on_login(
    client,
    app,
    admin_user,
):
    login(client, admin_user)

    idle_seconds = app.config["SESSION_IDLE_MINUTES"] * 60
    set_session_times(
        client,
        started_ago=idle_seconds + 60,
        activity_ago=idle_seconds + 60,
    )

    response = client.get("/dashboard", follow_redirects=True)

    assert response.status_code == 200
    assert "Tu sesión expiró" in response.get_data(as_text=True)


def test_session_expires_after_max_duration_even_if_active(
    client,
    app,
    admin_user,
):
    login(client, admin_user)

    max_seconds = app.config["SESSION_MAX_HOURS"] * 3600
    set_session_times(
        client,
        started_ago=max_seconds + 60,
        activity_ago=5,
    )

    response = client.get("/dashboard")

    assert_redirected_to_login(response)


def test_authenticated_session_without_clock_is_rejected(
    client,
    admin_user,
):
    login(client, admin_user)

    with client.session_transaction() as client_session:
        client_session.pop(STARTED_KEY)
        client_session.pop(ACTIVITY_KEY)

    response = client.get("/dashboard")

    assert_redirected_to_login(response)


def test_limits_are_read_from_configuration(client, app, admin_user):
    app.config["SESSION_IDLE_MINUTES"] = 1

    login(client, admin_user)

    set_session_times(client, started_ago=30, activity_ago=30)
    assert client.get("/dashboard").status_code == 200

    set_session_times(client, started_ago=120, activity_ago=120)
    assert_redirected_to_login(client.get("/dashboard"))


def test_health_does_not_renew_or_expire_the_session(
    client,
    app,
    admin_user,
):
    login(client, admin_user)

    idle_seconds = app.config["SESSION_IDLE_MINUTES"] * 60
    set_session_times(
        client,
        started_ago=idle_seconds + 60,
        activity_ago=idle_seconds + 60,
    )

    with client.session_transaction() as client_session:
        previous_activity = client_session[ACTIVITY_KEY]

    response = client.get("/health")

    assert response.status_code == 200

    with client.session_transaction() as client_session:
        assert client_session[ACTIVITY_KEY] == previous_activity


def test_logout_clears_the_session_clock(client, admin_user):
    login(client, admin_user)

    client.post("/logout")

    with client.session_transaction() as client_session:
        assert STARTED_KEY not in client_session
        assert ACTIVITY_KEY not in client_session


def test_user_can_login_again_after_expiration(
    client,
    app,
    admin_user,
):
    login(client, admin_user)

    idle_seconds = app.config["SESSION_IDLE_MINUTES"] * 60
    set_session_times(
        client,
        started_ago=idle_seconds + 60,
        activity_ago=idle_seconds + 60,
    )
    client.get("/dashboard")

    login(client, admin_user)

    assert client.get("/dashboard").status_code == 200


@pytest.mark.parametrize(
    ("config_key", "invalid_value"),
    [
        ("SESSION_IDLE_MINUTES", 0),
        ("SESSION_MAX_HOURS", 0),
        ("SESSION_IDLE_MINUTES", -5),
    ],
)
def test_app_rejects_non_positive_session_limits(
    config_key,
    invalid_value,
):
    config = {
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        config_key: invalid_value,
    }

    with pytest.raises(RuntimeError, match=config_key):
        create_app(config)
