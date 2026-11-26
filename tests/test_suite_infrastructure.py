"""La infraestructura de la propia suite: la protección de la base de pruebas, la
limpieza entre tests, el esquema por proceso y la organización por áreas.

Es lo que permite correr tests destructivos sin riesgo y rápido (ver `tests/database.py`),
así que se comprueba como cualquier otra pieza del proyecto.
"""

import configparser
from pathlib import Path

import pytest
from sqlalchemy import text

from src.workdesk.extensions import db
from src.workdesk.models import Role, Ticket
from tests.areas import AREA_BY_MODULE, AREAS
from tests.database import (
    TEST_DATABASE_NAME,
    checked_database_url,
    drop_snapshot,
    empty_tables,
    engine_options,
    has_snapshot,
    restore_snapshot,
    reusable_engine_options,
    take_snapshot,
    worker_schema,
)
from tests.ticket_helpers import make_ticket

TESTS_DIR = Path(__file__).parent
ROOT = TESTS_DIR.parent


def url_for(database: str) -> str:
    # Una URL de mentira: estos tests solo miran el nombre de la base.
    return f"postgresql+psycopg://usuario:clave@localhost:5432/{database}"


# --- La protección crítica de `workdesk_test` ------------------------------------


@pytest.mark.parametrize(
    "database",
    [
        "workdesk_dev",
        "workdesk",
        "postgres",
        "workdesk_test2",
        "workdesk_testing",
        "WORKDESK_TEST",
        "workdesk_dev_test",
    ],
)
def test_the_guard_rejects_any_database_that_is_not_workdesk_test(monkeypatch, database):
    monkeypatch.setenv("TEST_DATABASE_URL", url_for(database))

    with pytest.raises(RuntimeError, match="solo pueden ejecutarse sobre workdesk_test"):
        checked_database_url()


@pytest.mark.parametrize("value", [None, ""])
def test_the_guard_requires_the_url(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("TEST_DATABASE_URL", value)

    with pytest.raises(RuntimeError, match="Falta TEST_DATABASE_URL"):
        checked_database_url()


def test_the_guard_accepts_workdesk_test_and_returns_the_url_unchanged(monkeypatch):
    url = url_for(TEST_DATABASE_NAME)
    monkeypatch.setenv("TEST_DATABASE_URL", url)

    assert checked_database_url() == url
    assert TEST_DATABASE_NAME == "workdesk_test"


def test_the_guard_looks_at_the_database_name_not_at_the_whole_url(monkeypatch):
    # Un nombre de usuario o de servidor que contiene `workdesk_test` no cuenta.
    monkeypatch.setenv(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://workdesk_test:clave@workdesk_test:5432/workdesk_dev",
    )

    with pytest.raises(RuntimeError):
        checked_database_url()


# --- Un esquema por proceso con pytest-xdist ---------------------------------------


def test_without_xdist_the_default_schema_is_used(monkeypatch):
    monkeypatch.delenv("PYTEST_XDIST_WORKER", raising=False)

    assert worker_schema() is None
    assert engine_options() == {}


def test_each_xdist_worker_gets_its_own_schema(monkeypatch):
    monkeypatch.setenv("PYTEST_XDIST_WORKER", "gw3")

    assert worker_schema() == "wd_test_gw3"
    assert engine_options() == {
        "connect_args": {"options": "-csearch_path=wd_test_gw3"}
    }


# --- Conexiones reutilizadas entre tests ---------------------------------------------


def test_the_reused_connections_only_reach_workdesk_test():
    with pytest.raises(RuntimeError, match="workdesk_test"):
        reusable_engine_options("postgresql+psycopg://u:p@localhost:5432/workdesk_dev")


def _backend_pid():
    return db.session.scalar(text("SELECT pg_backend_pid()"))


def test_the_next_test_reuses_the_connection_and_finds_it_clean(app):
    """Lo que un test deja en su conexión (una transacción a medias, un parámetro de
    sesión, un bloqueo consultivo) no llega al siguiente, aunque la conexión sea la misma."""
    with app.app_context():
        pid = _backend_pid()
        # Confirmado: un SET dentro de una transacción que se deshace ya se deshace solo.
        db.session.execute(text("SET statement_timeout = '7s'"))
        db.session.execute(text("SELECT pg_advisory_lock(424242)"))
        db.session.commit()
        db.session.execute(text("SELECT 1"))  # transacción abierta, sin confirmar
        # Igual que al terminar un test (fixture `app`): se suelta la sesión y se cierra
        # el pool.
        db.session.remove()
        db.engine.dispose()

    with app.app_context():
        db.session.remove()
        assert _backend_pid() == pid, "la conexión no se reutilizó"
        assert db.session.scalar(text("SHOW statement_timeout")) == "0"
        assert db.session.scalar(text("SHOW search_path")) == (worker_schema() or '"$user", public')
        locks = db.session.scalar(
            text(
                "SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' "
                "AND pid = pg_backend_pid()"
            )
        )
        assert locks == 0


# --- Cada test empieza con la base vacía ---------------------------------------------


def test_emptying_the_tables_leaves_the_database_as_a_new_one(app, catalog, make_user):
    staff = make_user("TECNICO", username="tecnico")
    first = make_ticket(app, catalog, staff["id"])

    with app.app_context():
        # Hay filas en muchas tablas (roles, catálogos, usuarios, tickets, historial...).
        assert db.session.scalar(db.select(db.func.count(Ticket.id))) == 1
        db.session.remove()

        empty_tables()

        rows = {
            table.name: db.session.scalar(
                db.select(db.func.count()).select_from(table)
            )
            for table in db.metadata.sorted_tables
        }

        assert {name: count for name, count in rows.items() if count} == {}

        # Y los identificadores vuelven a empezar: el primer ticket es de nuevo el 1.
        assert db.session.scalar(text("SELECT nextval('tickets_public_id_seq')")) == 1
        db.session.add(Role(codigo="NUEVO", nombre="Nuevo", descripcion="Uno."))
        db.session.commit()

        assert db.session.scalar(db.select(Role.id)) == 1

    assert first == "1"


def test_emptying_an_already_empty_database_changes_nothing(app):
    with app.app_context():
        empty_tables()
        empty_tables()

        assert db.session.scalar(db.select(db.func.count(Role.id))) == 0


# --- Las instantáneas ------------------------------------------------------------------


def test_a_snapshot_restores_the_rows_and_the_sequences_exactly(app, catalog, make_user):
    staff = make_user("TECNICO", username="tecnico")
    first = make_ticket(app, catalog, staff["id"])

    with app.app_context():
        take_snapshot("prueba", extra={"ticket": first})

        assert has_snapshot("prueba")

    second = make_ticket(app, catalog, staff["id"])
    make_ticket(app, catalog, staff["id"])

    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(Ticket.id))) == 3

        # Devuelve lo que se guardó con ella y descarta todo lo posterior.
        assert restore_snapshot("prueba") == {"ticket": first}
        assert db.session.scalar(db.select(db.func.count(Ticket.id))) == 1

    # Las secuencias siguen donde estaban al tomarla: el siguiente ticket vuelve a ser el 2.
    assert make_ticket(app, catalog, staff["id"]) == second == "2"

    with app.app_context():
        drop_snapshot("prueba")

        assert not has_snapshot("prueba")


def test_restoring_a_snapshot_twice_gives_the_same_database(app, catalog):
    with app.app_context():
        take_snapshot("doble")
        restore_snapshot("doble")
        before = db.session.scalar(db.select(db.func.count(Role.id)))
        restore_snapshot("doble")

        assert db.session.scalar(db.select(db.func.count(Role.id))) == before > 0
        drop_snapshot("doble")


# --- La organización por áreas ----------------------------------------------------------


def test_every_test_module_belongs_to_an_area():
    modules = {path.stem for path in TESTS_DIR.glob("test_*.py")}

    assert modules - set(AREA_BY_MODULE) == set()


def test_no_area_lists_a_module_that_does_not_exist():
    modules = {path.stem for path in TESTS_DIR.glob("test_*.py")}

    assert set(AREA_BY_MODULE) - modules == set()


def test_no_module_is_in_two_areas():
    listed = [module for modules in AREAS.values() for module in modules]

    assert len(listed) == len(set(listed))


def test_every_area_is_a_declared_marker():
    config = configparser.ConfigParser()
    config.read(ROOT / "pytest.ini", encoding="utf-8")
    declared = {
        line.split(":")[0].strip()
        for line in config["pytest"]["markers"].splitlines()
        if line.strip()
    }

    assert set(AREAS) | {"unit"} == declared


def test_each_test_gets_its_area_marker_and_unit_when_it_does_not_use_the_database(request):
    assert request.node.get_closest_marker("platform") is not None
    # Este test no pide el fixture `app`: no usa la base de datos.
    assert request.node.get_closest_marker("unit") is not None


def test_a_test_that_uses_the_database_is_not_marked_unit(request, app):
    assert request.node.get_closest_marker("platform") is not None
    assert request.node.get_closest_marker("unit") is None
