"""Las páginas de error (`src/workdesk/errors.py`).

Cualquier error HTTP recibe la página de WorkDesk, no la genérica de Werkzeug, y ninguna
deja ver nada técnico: ni el mensaje de la excepción, ni la ruta interna, ni la pila.
"""

import pytest
from werkzeug.exceptions import Conflict, ServiceUnavailable

BRAND = "WorkDesk"


@pytest.fixture()
def broken_routes(app):
    """Tres rutas de prueba que fallan de distintas formas."""

    @app.get("/_prueba/fallo")
    def _fails():
        raise RuntimeError("detalle interno: /ruta/secreta y contraseña=no-mostrar")

    @app.get("/_prueba/conflicto")
    def _conflict():
        raise Conflict()

    @app.get("/_prueba/no-disponible")
    def _unavailable():
        raise ServiceUnavailable(retry_after=120)

    app.config["PROPAGATE_EXCEPTIONS"] = False

    return app


def test_an_unexpected_failure_shows_the_generic_page_and_nothing_technical(
    broken_routes, client
):
    response = client.get("/_prueba/fallo")
    body = response.get_data(as_text=True)

    assert response.status_code == 500
    assert "Error interno" in body
    assert BRAND in body

    for secret in ("RuntimeError", "detalle interno", "/ruta/secreta", "no-mostrar", "Traceback"):
        assert secret not in body


def test_a_method_the_route_does_not_accept_gets_its_own_page_and_the_allow_header(client):
    response = client.put("/login")
    body = response.get_data(as_text=True)

    assert response.status_code == 405
    assert "Acción no permitida" in body
    assert BRAND in body
    assert {"GET", "POST"} <= {m.strip() for m in response.headers["Allow"].split(",")}


def test_an_error_without_its_own_text_still_gets_the_workdesk_page(broken_routes, client):
    response = client.get("/_prueba/conflicto")
    body = response.get_data(as_text=True)

    assert response.status_code == 409
    assert "Solicitud no atendida" in body
    assert BRAND in body


def test_a_server_error_keeps_its_code_and_retry_after(broken_routes, client):
    response = client.get("/_prueba/no-disponible")

    assert response.status_code == 503
    assert "Error interno" in response.get_data(as_text=True)
    assert response.headers["Retry-After"] == "120"
