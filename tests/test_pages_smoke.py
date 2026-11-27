"""Humo y presupuesto de consultas de las pantallas, con los 108 tickets de demostración.

Las pruebas de cada módulo cubren sus pantallas con los datos mínimos que arman. Esta recorre
las pantallas con datos realistas (los 108 tickets de `seed-demo-tickets`: cerrados,
resueltos, reabiertos, duplicados, con adjuntos, con SLA vencido o en pausa...) y comprueba
dos cosas que los casos mínimos no ven:

- **Nada se rompe con datos reales.** Una plantilla que falla con una combinación poco común
  (un ticket reabierto con un duplicado y un adjunto, por ejemplo) hace fallar el test: en
  las pruebas las excepciones de la aplicación no se esconden detrás de una página de error.
- **Las consultas están acotadas.** Cada pantalla tiene un presupuesto de consultas a la base
  de datos, con margen sobre lo medido. Si una pantalla empieza a hacer una consulta por
  fila (el clásico N+1), el presupuesto se supera aunque funcione bien con pocos datos.

Los presupuestos son techos con margen, no cifras exactas: lo medido hoy es un listado de 14
o 15 consultas, un detalle de hasta 22 para el personal y de hasta 12 para el Solicitante, y
las pantallas de acción de hasta 23. Si una mejora legítima necesita más, se sube el techo
a conciencia en este archivo.
"""

import pytest
from sqlalchemy import event

from src.workdesk.extensions import db
from src.workdesk.models import (
    Attachment,
    Grupo,
    Prioridad,
    Ticket,
    TicketRequester,
    User,
)
from src.workdesk.seeds.demo_tickets_data import DEMO_TICKETS
from tests.demo_data import DEMO_PASSWORD
from tests.ticket_helpers import login

ROLE_USERS = {
    "SOLICITANTE": "javiera.torres",
    "TECNICO": "diego.soto",
    "SUPERVISOR": "camila.rojas",
}

# Techos de consultas por petición (ver el docstring del módulo).
BUDGET_PAGE = 20
BUDGET_DETAIL_STAFF = 30
BUDGET_DETAIL_REQUESTER = 18
BUDGET_SCREEN = 30
# El dashboard del personal reúne seis consultas de la carga de trabajo, los tickets
# prioritarios con su SLA, la actividad y los bloques de rol: es la pantalla más densa.
BUDGET_STAFF_DASHBOARD = 26

PAGES_FOR_EVERYONE = [
    "/dashboard",
    "/tickets",
    "/tickets?vista=todos",
    "/tickets?vista=cerrados",
    "/tickets?sla=vencido&vista=todos",
    "/tickets?orden=sla&vista=todos",
    "/tickets?sla=riesgo&vista=todos",
    "/tickets?tecnico=ninguno&activos=1&vista=todos",
    "/tickets?revision=1&cerrado_desde=2026-11-01&vista=todos",
    "/tickets/new",
    "/knowledge",
    "/knowledge?q=impresora",
    "/notifications",
    "/notifications?vista=no-leidas",
    "/account",
]
# La carga de trabajo es del personal: el Solicitante recibe 403.
STAFF_PAGES = [
    "/knowledge/manage",
    "/knowledge/new",
    "/workload",
    "/workload?grupo=1&prioridad=1&estado=1",
    "/workload?q=a&orden=nombre",
]
GROUP_PAGES = ["/groups", "/reassign"]
ADMIN_PAGES = [
    "/admin",
    "/users",
    "/admin/sla",
    "/admin/sla/calendar",
    "/admin/states",
    "/admin/categories",
    "/admin/priorities",
    "/admin/locations",
    "/admin/wait-reasons",
    "/admin/sla/deactivate",
    "/admin/settings/seguridad",
    "/admin/settings/cierre",
    "/admin/settings/archivos",
    "/admin/settings/colaboracion",
    "/admin/settings/operacion",
    "/admin/settings/creacion",
    "/admin/notifications",
    "/admin/audit",
    "/admin/audit?vista=accesos",
    "/admin/audit?vista=tickets",
]

# Quién entra en qué pantallas: 200 si puede, 403 si no.
ALLOWED = {
    "SOLICITANTE": PAGES_FOR_EVERYONE,
    "TECNICO": PAGES_FOR_EVERYONE + STAFF_PAGES,
    "SUPERVISOR": PAGES_FOR_EVERYONE + STAFF_PAGES + GROUP_PAGES,
    "ADMINISTRADOR": PAGES_FOR_EVERYONE + STAFF_PAGES + GROUP_PAGES + ADMIN_PAGES,
}
EVERY_PAGE = PAGES_FOR_EVERYONE + STAFF_PAGES + GROUP_PAGES + ADMIN_PAGES

# Las pantallas de acción de un ticket para el personal. Algunas no corresponden al estado
# del ticket (cerrarlo si ya está cerrado): entonces vuelven al detalle con un aviso.
TICKET_SCREENS = [
    "edit",
    "priority",
    "relations",
    "requesters",
    "assignment",
    "escalate",
    "duplicate",
    "status/start",
    "status/hold",
    "status/resume",
    "status/resolve",
    "status/close",
    "status/close-exceptional",
    "status/reopen",
    "knowledge",
]


class QueryCounter:
    """Cuenta las consultas que la aplicación manda a la base de datos."""

    def __init__(self):
        self.count = 0

    def __enter__(self):
        event.listen(db.engine, "before_cursor_execute", self._count)

        return self

    def __exit__(self, *exc):
        event.remove(db.engine, "before_cursor_execute", self._count)

    def _count(self, *_args):
        self.count += 1


def sign_in(client, role, make_user):
    if role == "ADMINISTRADOR":
        login(client, make_user("ADMINISTRADOR", username="admin_smoke"))
    else:
        login(client, {"username": ROLE_USERS[role], "password": DEMO_PASSWORD})


def get(client, url):
    """GET con el número de consultas que costó."""
    with client.application.app_context(), QueryCounter() as counter:
        response = client.get(url)

    return response, counter.count


def all_ticket_numbers(client):
    with client.application.app_context():
        return [
            number
            for number in db.session.scalars(db.select(Ticket.public_id).order_by(Ticket.id))
        ]


def visible_to(client, username):
    """Los tickets que un Solicitante debe ver, por la regla de siempre y sin usar las
    funciones de la aplicación: los que creó y aquellos donde es solicitante vigente."""
    with client.application.app_context():
        user_id = db.session.scalar(db.select(User.id).where(User.username == username))
        created = set(
            db.session.scalars(
                db.select(Ticket.public_id).where(Ticket.creado_por_usuario_id == user_id)
            )
        )
        requested = set(
            db.session.scalars(
                db.select(Ticket.public_id)
                .join(TicketRequester, TicketRequester.ticket_id == Ticket.id)
                .where(
                    TicketRequester.solicitante_id == user_id,
                    TicketRequester.fecha_retiro.is_(None),
                )
            )
        )

    return created | requested


# --- Pantallas generales ---------------------------------------------------------------


@pytest.mark.parametrize("role", list(ALLOWED))
def test_every_page_answers_as_expected_for_each_role(seeded, client, make_user, role):
    sign_in(client, role, make_user)

    for url in EVERY_PAGE:
        response, queries = get(client, url)
        expected = 200 if url in ALLOWED[role] else 403

        assert response.status_code == expected, f"{role} {url}"
        budget = (
            BUDGET_STAFF_DASHBOARD
            if url == "/dashboard" and role != "SOLICITANTE"
            else BUDGET_PAGE
        )

        assert queries <= budget, f"{role} {url} hizo {queries} consultas"


def test_a_listing_costs_the_same_with_few_or_many_tickets(seeded, client, make_user):
    # Con los 108 tickets de la demostración el listado hace las mismas consultas que con
    # una página: no hay una consulta por fila (el techo de arriba lo vigila de forma
    # general; esto lo comprueba entre páginas).
    sign_in(client, "SUPERVISOR", make_user)

    _first, on_first_page = get(client, "/tickets?vista=todos")
    _second, on_second_page = get(client, "/tickets?vista=todos&page=2")

    assert on_first_page == on_second_page


# --- Detalle de todos los tickets ------------------------------------------------------------


@pytest.mark.parametrize("role", ["TECNICO", "SUPERVISOR", "ADMINISTRADOR"])
def test_the_staff_opens_every_ticket(seeded, client, make_user, role):
    sign_in(client, role, make_user)
    numbers = all_ticket_numbers(client)

    assert len(numbers) == len(DEMO_TICKETS)

    for number in numbers:
        response, queries = get(client, f"/tickets/{number}")

        assert response.status_code == 200, f"{role} #{number}"
        assert queries <= BUDGET_DETAIL_STAFF, f"{role} #{number} hizo {queries} consultas"


def test_a_requester_opens_exactly_their_own_tickets(seeded, client, make_user):
    sign_in(client, "SOLICITANTE", make_user)
    own = visible_to(client, ROLE_USERS["SOLICITANTE"])

    # La demostración da a cada persona unos pocos tickets: ni todos ni ninguno.
    assert 0 < len(own) < 30

    for number in all_ticket_numbers(client):
        response, queries = get(client, f"/tickets/{number}")

        assert response.status_code == (200 if number in own else 404), f"#{number}"
        assert queries <= BUDGET_DETAIL_REQUESTER, f"#{number} hizo {queries} consultas"


# --- Pantallas de acción -------------------------------------------------------------------------


# Una pantalla por caso: los 108 tickets con todas las pantallas en un solo test tardaban
# más de 30 s y dejaban a un proceso de `pytest-xdist` ocupado al final de la suite.
@pytest.mark.parametrize("screen", TICKET_SCREENS)
def test_every_action_screen_opens_for_every_ticket(seeded, client, make_user, screen):
    sign_in(client, "SUPERVISOR", make_user)

    for number in all_ticket_numbers(client):
        url = f"/tickets/{number}/{screen}"
        response, queries = get(client, url)

        # Abre la pantalla, o vuelve al detalle (o a «Relaciones», en el caso de
        # cerrar como duplicado) con un aviso si la acción ya no corresponde: ticket
        # cerrado, otro estado... Nunca un error ni el login.
        assert response.status_code in (200, 302), url

        if response.status_code == 302:
            back_to = (f"/tickets/{number}", f"/tickets/{number}/relations")

            assert response.headers["Location"].endswith(back_to), url

        assert queries <= BUDGET_SCREEN, f"{url} hizo {queries} consultas"


def test_every_attachment_downloads_as_a_file(seeded, client, make_user):
    sign_in(client, "SUPERVISOR", make_user)

    with client.application.app_context():
        attachments = [
            (attachment.ticket.public_id, attachment.id)
            for attachment in db.session.scalars(
                db.select(Attachment).where(Attachment.activo.is_(True))
            )
        ]

    assert attachments, "la demostración debe traer adjuntos"

    for number, attachment_id in attachments:
        response = client.get(f"/tickets/{number}/attachments/{attachment_id}/download")

        assert response.status_code == 200
        assert response.headers["Content-Disposition"].startswith("attachment")
        assert response.headers["X-Content-Type-Options"] == "nosniff"


# --- Pantallas de detalle de la administración -------------------------------------------------


def test_the_administration_detail_screens_open_with_bounded_queries(
    seeded, client, make_user
):
    sign_in(client, "ADMINISTRADOR", make_user)

    with client.application.app_context():
        urls = [f"/groups/{group_id}" for group_id in db.session.scalars(db.select(Grupo.id))]

        for user_id in db.session.scalars(db.select(User.id)):
            urls += [f"/users/{user_id}", f"/users/{user_id}/edit"]

        urls += [
            f"/admin/sla/priorities/{priority_id}/edit"
            for priority_id in db.session.scalars(db.select(Prioridad.id))
        ]

    assert len(urls) > 20

    for url in urls:
        response, queries = get(client, url)

        assert response.status_code == 200, url
        assert queries <= BUDGET_SCREEN, f"{url} hizo {queries} consultas"
