"""Cabeceras de seguridad y de caché de todas las respuestas (`security/headers.py`)
y la forma común de los errores JSON (`responses.py`)."""

import pytest

from src.workdesk.responses import json_error
from src.workdesk.security.headers import CONTENT_SECURITY_POLICY, PERMISSIONS_POLICY
from tests.ticket_helpers import login

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": PERMISSIONS_POLICY,
    "X-Permitted-Cross-Domain-Policies": "none",
}


def test_the_login_page_carries_the_security_headers(client):
    response = client.get("/login")

    for name, value in SECURITY_HEADERS.items():
        assert response.headers[name] == value, name

    assert response.headers["Cache-Control"] == "no-store"


def test_every_kind_of_response_carries_them(client, make_user):
    login(client, make_user("TECNICO"))

    responses = {
        "página": client.get("/dashboard"),
        "redirección": client.get("/"),
        "JSON": client.get("/notifications/unread-count"),
        "403": client.get("/admin"),
        "404": client.get("/no-existe"),
        "salud": client.get("/health"),
    }

    for kind, response in responses.items():
        for name in SECURITY_HEADERS:
            assert name in response.headers, f"{kind}: falta {name}"


def test_pages_with_session_data_are_never_cached(client, make_user):
    login(client, make_user("TECNICO"))

    assert client.get("/dashboard").headers["Cache-Control"] == "no-store"
    assert client.get("/tickets").headers["Cache-Control"] == "no-store"
    assert client.get("/workload").headers["Cache-Control"] == "no-store"


def test_the_reassignment_screens_are_never_cached(client, make_user):
    login(client, make_user("SUPERVISOR"))

    assert client.get("/reassign").headers["Cache-Control"] == "no-store"


def test_a_route_that_sets_its_own_cache_policy_keeps_it(client, make_user):
    # El contador de la campana fija `no-store` por su cuenta: no se duplica ni se pisa.
    login(client, make_user("TECNICO"))

    assert client.get("/notifications/unread-count").headers["Cache-Control"] == "no-store"


def test_static_files_keep_their_own_caching(client):
    response = client.get("/static/css/app.css")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] != "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_the_policy_only_allows_what_workdesk_serves():
    directives = dict(
        part.split(" ", 1) for part in CONTENT_SECURITY_POLICY.split("; ")
    )

    assert directives["default-src"] == "'self'"
    # Sin JavaScript en línea ni de otros sitios.
    assert directives["script-src"] == "'self'"
    assert directives["frame-ancestors"] == "'none'"
    assert directives["object-src"] == "'none'"
    assert directives["form-action"] == "'self'"

    for value in directives.values():
        assert "http" not in value and "*" not in value


@pytest.mark.parametrize("secure", [True, False])
def test_strict_transport_security_only_when_served_over_https(app, secure):
    app.config["SESSION_COOKIE_SECURE"] = secure
    response = app.test_client().get("/login")

    assert ("Strict-Transport-Security" in response.headers) is secure


def test_json_errors_share_one_shape(app):
    with app.test_request_context():
        response = json_error("lock_held", "Alguien edita.", 409)

    assert response.status_code == 409
    assert response.get_json() == {
        "ok": False,
        "error": "lock_held",
        "message": "Alguien edita.",
    }
    assert response.headers["Cache-Control"] == "no-store"
