"""Cuánto cuesta una petición mínima autenticada (revisión previa a `v0.7.0`).

`test_pages_smoke` pone techos con margen a las pantallas completas; estos son exactos y
miden lo que toda pantalla paga antes de hacer su trabajo. Medido antes del cambio: tres
consultas en una pantalla completa (usuario, **rol** y contador de notificaciones) porque el
rol se cargaba aparte, de forma perezosa, en el primer lugar que lo miraba.

Ahora `load_user` trae el usuario con su rol en una sola consulta. Si alguien lo deshace
(o añade otra consulta por petición), esto falla, y con la configuración en la base de datos
(`v0.7.0`) es el contador que dirá cuánto cuesta leerla.
"""

import pytest
from sqlalchemy import event

from src.workdesk.extensions import db
from tests.ticket_helpers import login

ROLES = ["SOLICITANTE", "TECNICO", "SUPERVISOR", "ADMINISTRADOR"]


def _statements(client, url):
    seen = []

    def record(_conn, _cursor, statement, *_rest):
        seen.append(" ".join(statement.split()))

    with client.application.app_context():
        event.listen(db.engine, "before_cursor_execute", record)
        try:
            response = client.get(url)
        finally:
            event.remove(db.engine, "before_cursor_execute", record)

    return response, seen


@pytest.mark.parametrize("role", ROLES)
def test_a_minimal_page_costs_two_queries(client, make_user, role):
    login(client, make_user(role))

    response, statements = _statements(client, "/account")

    assert response.status_code == 200
    # El usuario con su rol, y el contador de la campana.
    assert len(statements) == 2, statements


@pytest.mark.parametrize("role", ROLES)
def test_the_role_comes_with_the_user_not_in_a_query_of_its_own(client, make_user, role):
    login(client, make_user(role))

    _response, statements = _statements(client, "/account")

    assert not any(s.startswith("SELECT roles.") for s in statements), statements
    assert "JOIN roles" in statements[0], statements[0]


def test_the_notification_poll_costs_two_queries(client, make_user):
    # La consulta que el navegador repite cada 30 segundos en cada pestaña abierta.
    login(client, make_user("TECNICO"))

    response, statements = _statements(client, "/notifications/unread-count")

    assert response.get_json() == {"unread": 0}
    assert len(statements) == 2, statements
