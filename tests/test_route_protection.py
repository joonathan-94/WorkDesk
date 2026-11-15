"""Red de seguridad sobre TODAS las rutas de la aplicación.

Estos tests recorren el mapa de rutas real en lugar de una lista escrita a
mano: así, una ruta nueva queda cubierta automáticamente y no puede quedar
sin autenticación ni sin protección CSRF por olvido. Si un test falla porque
se añadió una ruta, no se debe "arreglar" el test: o se protege la ruta, o,
si de verdad es pública, se añade a `PUBLIC_ENDPOINTS` de forma consciente.
"""

import pytest

from src.workdesk.extensions import csrf

# Rutas que pueden abrirse sin iniciar sesión, y por qué.
PUBLIC_ENDPOINTS = {
    "auth.login": "pantalla de inicio de sesión",
    "system.health": "comprobación de estado de la aplicación y la base de datos",
    "static": "archivos estáticos (CSS, JavaScript e imágenes)",
}

METHODS = ("GET", "POST")


def routes_to_check(app):
    """(endpoint, método, URL) de cada ruta y método que se pueden probar."""
    adapter = app.url_map.bind("localhost")
    found = []

    for rule in app.url_map.iter_rules():
        for method in METHODS:
            if method not in rule.methods:
                continue

            # Cualquier valor sirve para los parámetros: la autenticación y
            # el CSRF se comprueban antes de buscar el recurso.
            values = {name: 1 for name in rule.arguments}

            found.append(
                (
                    rule.endpoint,
                    method,
                    adapter.build(rule.endpoint, values, method=method),
                )
            )

    return found


def find_unprotected(client, app) -> list[str]:
    """Rutas que, sin sesión, no redirigen al inicio de sesión."""
    unprotected = []

    for endpoint, method, url in routes_to_check(app):
        if endpoint in PUBLIC_ENDPOINTS:
            continue

        response = client.open(url, method=method)

        # Sin sesión, la respuesta debe ser la redirección al inicio de
        # sesión; cualquier otra cosa (200, 403, 404...) delata una ruta que
        # no está protegida o que decide demasiado tarde.
        if response.status_code != 302 or "/login" not in response.location:
            unprotected.append(
                f"{method} {url} ({endpoint}) → {response.status_code}"
            )

    return unprotected


def find_without_csrf(client, app) -> list[str]:
    """Rutas POST que aceptan una petición sin token CSRF."""
    app.config["WTF_CSRF_ENABLED"] = True
    accepted = []

    for endpoint, method, url in routes_to_check(app):
        if method != "POST":
            continue

        response = client.post(url, data={})

        # La protección CSRF se aplica a todas las rutas que modifican
        # estado, incluidas las públicas como el login.
        if response.status_code != 400:
            accepted.append(
                f"POST {url} ({endpoint}) → {response.status_code}"
            )

    return accepted


def test_the_route_map_is_not_empty(app):
    # Si el recorrido no encontrara rutas, los tests siguientes pasarían sin
    # comprobar nada.
    endpoints = {endpoint for endpoint, _, _ in routes_to_check(app)}

    assert len(endpoints) > 30
    assert set(PUBLIC_ENDPOINTS) <= endpoints


def test_every_route_requires_a_session_except_the_public_ones(client, app):
    assert find_unprotected(client, app) == []


@pytest.mark.parametrize("endpoint", sorted(PUBLIC_ENDPOINTS))
def test_the_public_routes_are_really_public(client, app, endpoint):
    # La lista de rutas públicas no debe quedarse con entradas que ya no
    # existen: se comprueba que cada una responde sin pedir sesión.
    urls = [
        url
        for name, method, url in routes_to_check(app)
        if name == endpoint and method == "GET"
    ]

    assert urls, f"{endpoint} ya no existe: quítala de PUBLIC_ENDPOINTS"

    url = "/static/css/app.css" if endpoint == "static" else urls[0]
    response = client.get(url)

    assert not (
        response.status_code == 302 and "/login" in (response.location or "")
    )


def test_every_post_route_rejects_a_request_without_a_csrf_token(client, app):
    assert find_without_csrf(client, app) == []


def test_there_are_post_routes_to_protect(app):
    post_routes = [r for r in routes_to_check(app) if r[1] == "POST"]

    assert len(post_routes) > 20


# --- Que la red de seguridad realmente detecta los problemas ------------


def test_the_check_detects_a_route_left_without_authentication(client, app):
    @app.get("/abierta")
    def abierta():
        return "sin protección"

    assert find_unprotected(client, app) == ["GET /abierta (abierta) → 200"]


def test_the_check_detects_a_post_route_exempt_from_csrf(client, app):
    @app.post("/sin-csrf")
    @csrf.exempt
    def sin_csrf():
        return "aceptada"

    # La ruta aceptada es la única que debe aparecer en el informe.
    assert find_without_csrf(client, app) == ["POST /sin-csrf (sin_csrf) → 200"]
