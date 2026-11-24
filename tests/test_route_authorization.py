"""Red de seguridad de autorización sobre las rutas de la aplicación.

Complementa a `test_route_protection.py` (que comprueba autenticación y CSRF):
aquí se comprueba **quién** puede usar cada ruta. Igual que aquel, recorre el
mapa de rutas real en lugar de una lista escrita a mano, así que una ruta nueva
queda cubierta sin tocar el test y es *segura por defecto*:

- **Tickets (propiedad).** Un Solicitante sin relación con un ticket recibe 404
  en cualquier ruta `/tickets/<n>/...`, con cualquier método. Los números son
  correlativos: con un 403 (o un 200) cualquiera podría descubrir cuáles
  existen o ver el de otra persona.
- **Tickets (rol).** Un Solicitante que sí es solicitante del ticket solo puede
  usar las rutas de `REQUESTER_ENDPOINTS`; todas las demás son del personal y
  responden 403.
- **Áreas de administración.** `users`, `catalogs`, `admin` y `sla` son del
  Administrador y `groups` del Administrador y los Supervisores: el resto de
  roles recibe 403.

Si un test falla porque se añadió una ruta, no se debe «arreglar» el test: o se
protege la ruta (comprobar el acceso al ticket antes de nada y, después, el rol),
o, si de verdad un Solicitante debe poder usarla, se añade a
`REQUESTER_ENDPOINTS` de forma consciente y con su razón.
"""

import pytest

from tests.ticket_helpers import login, make_ticket

# Rutas de un ticket que un Solicitante puede usar sobre un ticket suyo. Cada
# una vuelve a comprobar el detalle (si el comentario es suyo, si el plazo no
# venció, si es solicitante vigente...): aquí solo se declara que no son
# exclusivas del personal.
REQUESTER_ENDPOINTS = {
    "tickets.detail": "ve el ticket y su historial público",
    "tickets.add_ticket_comment": "escribe comentarios públicos (RN-159)",
    "tickets.edit_ticket_comment": "edita sus comentarios dentro del plazo",
    "tickets.delete_ticket_comment": "elimina sus comentarios dentro del plazo",
    "tickets.add_ticket_attachments": "adjunta archivos (RN-160)",
    "tickets.download_ticket_attachment": "descarga los archivos que puede ver",
    "tickets.delete_ticket_attachment": "elimina sus archivos dentro del plazo",
    "tickets.change_ticket_state": (
        "confirma, rechaza o reabre; la política de cada acción decide (RN-161)"
    ),
}

# Rutas que, para cada área, solo pueden usar los roles indicados. `sla.` (el
# calendario laboral y los objetivos de SLA) se añadió en v0.5.0: sus rutas ya
# eran del Administrador, pero este recorrido no las cubría.
ADMIN_ONLY_PREFIXES = ("users.", "catalogs.", "admin.", "sla.")
STAFF_METHODS = ("GET", "POST")


def ticket_routes(app):
    """(endpoint, método, regla) de las rutas `/tickets/<public_id>/...`."""
    found = []

    for rule in app.url_map.iter_rules():
        if not rule.rule.startswith("/tickets/<public_id>"):
            continue

        for method in STAFF_METHODS:
            if method in rule.methods:
                found.append((rule.endpoint, method, rule))

    return found


def build(app, rule, public_id) -> str:
    """URL de la regla con el ticket indicado. El resto de parámetros no
    importan: la propiedad y el rol se comprueban antes de buscar nada más.
    `start` es una acción de estado exclusiva del personal."""
    values = {
        name: (public_id if name == "public_id" else "start" if name == "action_slug" else 1)
        for name in rule.arguments
    }

    return app.url_map.bind("localhost").build(rule.endpoint, values)


def find_visible_to_strangers(client, app, public_id) -> list[str]:
    """Rutas de tickets que no responden 404 a quien no tiene relación con el
    ticket."""
    return [
        f"{method} {build(app, rule, public_id)} ({endpoint}) → "
        f"{client.open(build(app, rule, public_id), method=method).status_code}"
        for endpoint, method, rule in ticket_routes(app)
        if client.open(build(app, rule, public_id), method=method).status_code != 404
    ]


def find_open_to_requesters(client, app, public_id) -> list[str]:
    """Rutas exclusivas del personal que un solicitante del ticket puede usar
    (todo lo que no es de `REQUESTER_ENDPOINTS` debe responder 403)."""
    return [
        f"{method} {build(app, rule, public_id)} ({endpoint}) → "
        f"{client.open(build(app, rule, public_id), method=method).status_code}"
        for endpoint, method, rule in ticket_routes(app)
        if endpoint not in REQUESTER_ENDPOINTS
        and client.open(build(app, rule, public_id), method=method).status_code != 403
    ]


@pytest.fixture()
def staff(make_user, catalog):
    return make_user("TECNICO", username="tecnico")


@pytest.fixture()
def requester(make_user, catalog):
    return make_user("SOLICITANTE", username="solicitante")


@pytest.fixture()
def stranger(make_user, catalog):
    return make_user("SOLICITANTE", username="ajeno")


@pytest.fixture()
def ticket_id(app, catalog, staff, requester):
    return make_ticket(app, catalog, staff["id"], requester_ids=[requester["id"]])


# --- Tickets -----------------------------------------------------------------


def test_there_are_ticket_routes_to_check(app):
    endpoints = {endpoint for endpoint, _, _ in ticket_routes(app)}

    assert len(endpoints) > 25
    # Las rutas que el Solicitante puede usar existen: si una se renombra, hay
    # que actualizar la lista y no dejarla con entradas muertas.
    assert set(REQUESTER_ENDPOINTS) <= endpoints


def test_a_stranger_gets_a_404_on_every_ticket_route(client, app, stranger, ticket_id):
    login(client, stranger)

    assert find_visible_to_strangers(client, app, ticket_id) == []


def test_a_requester_can_only_use_the_routes_meant_for_requesters(
    client,
    app,
    requester,
    ticket_id,
):
    login(client, requester)

    assert find_open_to_requesters(client, app, ticket_id) == []


def test_the_routes_a_requester_may_use_do_respond_to_them(
    client,
    app,
    requester,
    ticket_id,
):
    # La lista de rutas permitidas no debe ser decorativa: el solicitante ve su
    # ticket y las rutas listadas no le responden 404 por no existir.
    login(client, requester)

    assert client.get(f"/tickets/{ticket_id}").status_code == 200


# --- Áreas de administración ---------------------------------------------------


def area_violations(client, app, prefixes, roles) -> list[str]:
    """Rutas de las áreas `prefixes` que no responden 403 con la sesión
    abierta. El rol se comprueba antes de buscar nada, así que cualquier valor
    sirve para los parámetros."""
    adapter = app.url_map.bind("localhost")
    violations = []

    for rule in app.url_map.iter_rules():
        if not rule.endpoint.startswith(prefixes):
            continue

        url = adapter.build(rule.endpoint, {name: 1 for name in rule.arguments})

        for method in STAFF_METHODS:
            if method not in rule.methods:
                continue

            status = client.open(url, method=method).status_code

            if status != 403:
                violations.append(f"{roles}: {method} {url} ({rule.endpoint}) → {status}")

    return violations


@pytest.mark.parametrize("role", ["SOLICITANTE", "TECNICO", "SUPERVISOR"])
def test_the_administration_areas_are_only_for_the_administrator(
    client,
    app,
    make_user,
    catalog,
    role,
):
    login(client, make_user(role, username="persona"))

    assert area_violations(client, app, ADMIN_ONLY_PREFIXES, role) == []


@pytest.mark.parametrize("role", ["SOLICITANTE", "TECNICO"])
def test_the_groups_area_is_only_for_administrators_and_supervisors(
    client,
    app,
    make_user,
    catalog,
    role,
):
    login(client, make_user(role, username="persona"))

    assert area_violations(client, app, ("groups.",), role) == []


@pytest.mark.parametrize("role", ["SOLICITANTE", "TECNICO"])
def test_the_reassignment_area_is_only_for_supervisors_and_administrators(
    client, app, make_user, catalog, role
):
    login(client, make_user(role, username="persona"))

    assert area_violations(client, app, ("reassignment.",), role) == []


def test_the_workload_area_is_closed_to_requesters(client, app, make_user, catalog):
    """La carga de trabajo es información de todo el equipo: solo el personal."""
    login(client, make_user("SOLICITANTE", username="persona"))

    assert area_violations(client, app, ("workload.",), "SOLICITANTE") == []


def test_there_are_administration_routes_to_check(app):
    endpoints = {
        rule.endpoint
        for rule in app.url_map.iter_rules()
        if rule.endpoint.startswith(ADMIN_ONLY_PREFIXES)
    }

    assert len(endpoints) > 30


# --- Que la red de seguridad realmente detecta los problemas ------------------


def test_the_check_detects_a_ticket_route_that_skips_the_ownership_check(
    client,
    app,
    stranger,
    ticket_id,
):
    """Una ruta nueva de tickets que olvida comprobar el acceso al ticket deja
    ver el de otra persona: el recorrido tiene que señalarla."""
    from flask_login import login_required

    @app.get("/tickets/<public_id>/olvidada")
    @login_required
    def olvidada(public_id):
        return "datos del ticket"

    login(client, stranger)
    found = find_visible_to_strangers(client, app, ticket_id)

    assert any("olvidada" in line for line in found)


def test_the_check_detects_a_staff_route_open_to_requesters(
    client,
    app,
    requester,
    ticket_id,
):
    """Una ruta de tickets que comprueba el acceso pero olvida el rol deja
    entrar a un solicitante a una función del personal."""
    from flask_login import login_required

    @app.get("/tickets/<public_id>/solo-personal")
    @login_required
    def solo_personal(public_id):
        return "función del personal"

    login(client, requester)
    found = find_open_to_requesters(client, app, ticket_id)

    assert any("solo_personal" in line for line in found)


def test_the_check_detects_an_administration_route_without_a_role_check(
    client,
    app,
    make_user,
    catalog,
):
    """Una ruta de administración nueva sin `admin_only` deja entrar a quien no
    es Administrador: el recorrido tiene que señalarla."""
    from flask_login import login_required

    @login_required
    def olvidada():
        return "configuración"

    app.add_url_rule(
        "/admin/olvidada",
        endpoint="admin.olvidada",
        view_func=olvidada,
    )

    login(client, make_user("TECNICO", username="persona"))
    found = area_violations(client, app, ADMIN_ONLY_PREFIXES, "TECNICO")

    assert any("/admin/olvidada" in line for line in found)
