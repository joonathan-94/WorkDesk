"""La pantalla de auditoría (`/admin/audit`, UI-027, RF-108, RF-109 y RNF-025).

Solo el Administrador la consulta. Tiene tres pestañas (administrativa, accesos y tickets),
cada una con sus filtros validados, y cuesta las mismas consultas con una fila que con una
página llena.
"""

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import event

from src.workdesk.audit import AuditAction, record_admin_event
from src.workdesk.audit.labels import AUDIT_ACTION_LABELS, ENTITY_LABELS
from src.workdesk.catalogs.service import ENTITY_TYPES as CATALOG_ENTITY_TYPES
from src.workdesk.extensions import db
from src.workdesk.groups.service import ENTITY_TYPE as GROUP_ENTITY_TYPE
from src.workdesk.knowledge.service import ENTITY as ARTICLE_ENTITY_TYPE
from src.workdesk.models import AuthEvent, CommentType, Ticket
from src.workdesk.sla.policies import ENTITY_TYPE as POLICY_ENTITY_TYPE
from src.workdesk.tickets.comments import add_comment
from tests.ticket_helpers import login, make_ticket, person

PACKAGE = Path(__file__).resolve().parent.parent / "src" / "workdesk"


@pytest.fixture()
def admin(make_user):
    return make_user("ADMINISTRADOR", username="admin_audit", nombre="Ana", apellido="Admin")


def _record(app, action, *, actor_id=None, **values):
    with app.app_context():
        record_admin_event(
            action, actor=None if actor_id is None else person(actor_id), **values
        )
        db.session.commit()


def _rows(client, url):
    """Las filas de la tabla, como texto."""
    html = client.get(url).get_data(as_text=True)
    body = html.split("<tbody>", 1)[1].split("</tbody>", 1)[0] if "<tbody>" in html else ""

    return [" ".join(re.sub(r"<[^>]+>", " ", row).split()) for row in body.split("<tr>")[1:]]


# --- Quién la ve ---------------------------------------------------------------------------


@pytest.mark.parametrize("role", ["SOLICITANTE", "TECNICO", "SUPERVISOR"])
def test_only_the_administrator_reads_the_audit(client, make_user, role):
    login(client, make_user(role))

    for view in ("administrativa", "accesos", "tickets"):
        assert client.get(f"/admin/audit?vista={view}").status_code == 403


def test_the_hub_leads_to_the_audit(client, admin):
    login(client, admin)

    assert 'href="/admin/audit"' in client.get("/admin").get_data(as_text=True)


# --- Administrativa ------------------------------------------------------------------------


def test_the_administrative_tab_shows_who_did_what_newest_first(app, client, admin):
    _record(app, AuditAction.GRUPO_CREADO, actor_id=admin["id"], entity_type="grupo", entity_id=7, detail="Soporte Redes")
    _record(app, AuditAction.CAMBIO_ROL, actor_id=admin["id"], entity_type="usuario", entity_id=admin["id"], reason="Ascenso")
    login(client, admin)

    rows = _rows(client, "/admin/audit")

    assert len(rows) == 2
    assert "Cambio de rol" in rows[0] and "Ana Admin (admin_audit)" in rows[0]
    assert "Motivo: Ascenso" in rows[0]
    assert "Grupo creado" in rows[1] and "Soporte Redes" in rows[1]


def test_an_action_of_the_system_says_so(app, client, admin):
    _record(app, AuditAction.SLA_RECALCULADO, new_value={"tickets_recalculados": 3})
    login(client, admin)

    (row,) = _rows(client, "/admin/audit")

    assert "Sistema" in row and "SLA recalculado desde la consola" in row


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("tipo=GRUPO_CREADO", ["Grupo creado"]),
        ("entidad=usuario", ["Cambio de rol"]),
        ("entidad=grupo&entidad_id=7", ["Grupo creado"]),
        ("entidad=grupo&entidad_id=8", []),
        ("persona=nadie", []),
        ("persona=ANA", ["Cambio de rol", "Grupo creado"]),
        ("resultado=FALLIDO", []),
    ],
)
def test_the_administrative_filters(app, client, admin, query, expected):
    _record(app, AuditAction.GRUPO_CREADO, actor_id=admin["id"], entity_type="grupo", entity_id=7)
    _record(app, AuditAction.CAMBIO_ROL, actor_id=admin["id"], entity_type="usuario", entity_id=admin["id"])
    login(client, admin)

    rows = _rows(client, f"/admin/audit?vista=administrativa&{query}")
    found = [label for label in ("Cambio de rol", "Grupo creado") if any(label in r for r in rows)]

    assert found == expected


@pytest.mark.parametrize(
    "query",
    ["tipo=NO_EXISTE", "entidad=inventada", "desde=31-12-2026", "vista=otra", "page=abc"],
)
def test_an_invalid_filter_is_ignored(app, client, admin, query):
    _record(app, AuditAction.GRUPO_CREADO, actor_id=admin["id"], entity_type="grupo", entity_id=1)
    login(client, admin)

    response = client.get(f"/admin/audit?{query}")

    assert response.status_code == 200
    assert len(_rows(client, f"/admin/audit?{query}")) == 1


def test_the_dates_are_whole_local_days(app, client, admin):
    _record(app, AuditAction.GRUPO_CREADO, actor_id=admin["id"], entity_type="grupo", entity_id=1)
    login(client, admin)
    # «Hoy» en la zona de la aplicación, que es la que usan los filtros.
    today = datetime.now(UTC).astimezone(ZoneInfo(app.config["APP_TIMEZONE"])).date()

    def count(query):
        return len(_rows(client, f"/admin/audit?{query}"))

    tomorrow = (today + timedelta(days=1)).isoformat()
    yesterday = (today - timedelta(days=1)).isoformat()

    assert count(f"desde={yesterday}&hasta={tomorrow}") == 1
    # «Desde hoy hasta hoy» incluye lo de hoy: «hasta» abarca el día entero.
    assert count(f"desde={today.isoformat()}&hasta={today.isoformat()}") == 1
    assert count(f"desde={tomorrow}") == 0
    assert count(f"hasta={yesterday}") == 0


def test_whatever_was_recorded_is_escaped(app, client, admin):
    _record(
        app,
        AuditAction.GRUPO_CREADO,
        actor_id=admin["id"],
        entity_type="grupo",
        entity_id=1,
        detail="<script>alert('x')</script>",
        new_value={"nombre": "<img src=x onerror=alert(1)>"},
    )
    login(client, admin)

    html = client.get("/admin/audit").get_data(as_text=True)

    assert "<script>alert" not in html
    assert "<img src=x" not in html
    assert "&lt;script&gt;" in html


# --- Accesos -------------------------------------------------------------------------------


def _access(app, **values):
    with app.app_context():
        db.session.add(AuthEvent(**values))
        db.session.commit()


def test_the_access_tab_shows_attempts_with_their_cause(app, client, admin):
    _access(app, tipo_evento="LOGIN_FALLIDO", resultado="FALLIDO", detalle="USUARIO_DESCONOCIDO", identificador_intentado="pedro.gomez", ip_origen="10.0.0.66")
    login(client, admin)

    rows = _rows(client, "/admin/audit?vista=accesos")

    # El inicio de sesión del Administrador y el intento fallido, el más reciente primero.
    assert "Inicio de sesión" in rows[0] and "Ana Admin" in rows[0]
    assert "Escrito: pedro.gomez" in rows[1]
    assert "El usuario no existe" in rows[1] and "10.0.0.66" in rows[1]


@pytest.mark.parametrize(
    ("query", "count"),
    [
        ("ip=10.0.0.66", 1),
        ("ip=no-es-una-ip", 2),
        ("resultado=FALLIDO", 1),
        ("tipo=LOGIN_EXITOSO", 1),
        ("persona=pedro", 1),
        ("persona=admin_audit", 1),
    ],
)
def test_the_access_filters(app, client, admin, query, count):
    _access(app, tipo_evento="LOGIN_FALLIDO", resultado="FALLIDO", detalle="USUARIO_DESCONOCIDO", identificador_intentado="pedro.gomez", ip_origen="10.0.0.66")
    login(client, admin)

    assert len(_rows(client, f"/admin/audit?vista=accesos&{query}")) == count


# --- Tickets -------------------------------------------------------------------------------


def test_the_ticket_tab_shows_internal_events_too(app, client, admin, make_user, catalog):
    tech = make_user("TECNICO", username="tec_audit")
    number = make_ticket(app, catalog, tech["id"])

    with app.app_context():
        ticket = db.session.scalar(db.select(Ticket).where(Ticket.public_id == number))
        add_comment(ticket, actor=person(tech["id"]), content="Revisar el switch", kind=CommentType.INTERNO)
        db.session.commit()

    login(client, admin)
    rows = _rows(client, f"/admin/audit?vista=tickets&ticket=%23{number}")

    assert len(rows) == 2
    assert "Interno" in rows[0] and f"#{number}" in rows[0]
    assert "Ticket creado" in rows[1]
    assert _rows(client, "/admin/audit?vista=tickets&ticket=99999") == []


# --- Nombres y coste -----------------------------------------------------------------------


def test_every_audit_action_has_a_name():
    assert set(AUDIT_ACTION_LABELS) == set(AuditAction)


def test_every_entity_the_code_audits_has_a_name():
    """Los tipos de entidad que se auditan, sacados del propio código: los literales
    `entity_type="..."` y las constantes de cada módulo."""
    literals = set()

    for path in PACKAGE.rglob("*.py"):
        literals |= set(re.findall(r'entity_type="([a-z_]+)"', path.read_text(encoding="utf-8")))

    constants = {
        *CATALOG_ENTITY_TYPES.values(),
        GROUP_ENTITY_TYPE,
        ARTICLE_ENTITY_TYPE,
        POLICY_ENTITY_TYPE,
    }

    assert literals, "no se encontró ningún entity_type"
    assert literals | constants <= set(ENTITY_LABELS)


def test_a_full_page_costs_the_same_as_one_row(app, client, admin, make_user):
    """Cada fila nombra a una persona distinta: si las personas se cargaran una a una, la
    página llena costaría decenas de consultas más."""
    login(client, admin)

    def queries(url):
        seen = []

        def count(*_args):
            seen.append(1)

        with app.app_context():
            event.listen(db.engine, "before_cursor_execute", count)
            try:
                assert client.get(url).status_code == 200
            finally:
                event.remove(db.engine, "before_cursor_execute", count)

        return len(seen)

    _record(app, AuditAction.CAMBIO_ROL, actor_id=admin["id"], entity_type="usuario", entity_id=admin["id"])
    with_one = queries("/admin/audit")

    for index in range(60):
        other = make_user("TECNICO", username=f"tecnico_{index:02d}")
        _record(app, AuditAction.CAMBIO_ROL, actor_id=admin["id"], entity_type="usuario", entity_id=other["id"])

    assert queries("/admin/audit") == with_one
    assert queries("/admin/audit?page=2") == with_one
