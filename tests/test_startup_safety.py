"""La aplicación no arranca con una configuración insegura (`security/startup.py`)."""

import pytest

from src.workdesk import create_app
from src.workdesk.security.startup import (
    MIN_SECRET_KEY_LENGTH,
    SECURE_SESSION_COOKIE,
    SESSION_COOKIE,
    startup_warnings,
)
from tests.database import checked_database_url

STRONG_KEY = "k" * MIN_SECRET_KEY_LENGTH


def _build(**config):
    base = {
        "TESTING": True,
        "APP_ENV": "development",
        "SECRET_KEY": STRONG_KEY,
        # La URL pasa por la protección de siempre; crear la app no conecta.
        "SQLALCHEMY_DATABASE_URI": checked_database_url(),
    }
    base.update(config)

    return create_app(base)


def test_production_refuses_a_short_secret_key():
    with pytest.raises(RuntimeError, match="al menos 32 caracteres"):
        _build(APP_ENV="production", SECRET_KEY="k" * (MIN_SECRET_KEY_LENGTH - 1))


def test_production_accepts_a_long_secret_key():
    assert _build(APP_ENV="production", SESSION_COOKIE_SECURE=True).config["APP_ENV"] == "production"


def test_production_refuses_the_debug_mode():
    # El depurador de Werkzeug ejecuta código Python desde el navegador.
    with pytest.raises(RuntimeError, match="modo depuración"):
        _build(APP_ENV="production", DEBUG=True)


def test_the_debug_mode_is_allowed_outside_production():
    assert _build(DEBUG=True).debug is True


@pytest.mark.parametrize("placeholder", ["pega-aqui-la-clave-generada", " CHANGE-ME "])
def test_the_example_key_of_the_readme_is_refused_everywhere(placeholder):
    with pytest.raises(RuntimeError, match="valor de ejemplo"):
        _build(SECRET_KEY=placeholder)


def test_a_short_key_outside_production_is_only_a_warning():
    app = _build(SECRET_KEY="corta")

    assert any("menos de 32" in w for w in startup_warnings(app.config))


def test_production_over_plain_http_warns():
    warnings = startup_warnings({"APP_ENV": "production", "SECRET_KEY": STRONG_KEY})

    assert any("SESSION_COOKIE_SECURE=false" in w for w in warnings)


def test_the_session_cookie_does_not_reveal_the_framework():
    assert _build().config["SESSION_COOKIE_NAME"] == SESSION_COOKIE


def test_over_https_the_cookie_carries_the_host_prefix():
    # `__Host-` obliga al navegador a exigir Secure, Path=/ y ningún dominio.
    app = _build(SESSION_COOKIE_SECURE=True)

    assert app.config["SESSION_COOKIE_NAME"] == SECURE_SESSION_COOKIE
    assert SECURE_SESSION_COOKIE.startswith("__Host-")
    assert app.config["SESSION_COOKIE_PATH"] in (None, "/")
    assert app.config["SESSION_COOKIE_DOMAIN"] in (None, False)


def test_the_login_sets_the_workdesk_cookie(client, admin_user):
    response = client.post(
        "/login", data={"username": admin_user["username"], "password": admin_user["password"]}
    )

    cookies = response.headers.getlist("Set-Cookie")
    assert any(c.startswith(f"{SESSION_COOKIE}=") for c in cookies)
    assert not any(c.startswith("session=") for c in cookies)
    assert all("HttpOnly" in c and "SameSite=Lax" in c for c in cookies)
