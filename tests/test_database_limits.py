"""La conexión con PostgreSQL (`src/workdesk/database.py`): ninguna espera es indefinida.

Cada conexión recibe tiempos máximos para una consulta, para esperar un bloqueo y para quedar
en una transacción sin hacer nada; una petición que no consigue conexión también se rinde. En
todos esos casos la persona recibe «inténtalo en unos segundos» (503 con `Retry-After`) y no
una página colgada ni un error del programa. Estas pruebas provocan cada caso de verdad.
"""

import threading
import time

import psycopg
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError

from src.workdesk import create_app, settings
from src.workdesk.extensions import db
from src.workdesk.notifications import routes as notification_routes
from tests.ticket_helpers import login

LIMITS = ("statement_timeout", "lock_timeout", "idle_in_transaction_session_timeout")
BUSY = "Sistema ocupado"


def _limits(app) -> dict[str, str]:
    """Lo que PostgreSQL dice de los tres tiempos de la conexión (en milisegundos)."""
    with app.app_context():
        rows = db.session.execute(
            text("SELECT name, setting FROM pg_settings WHERE name = ANY(:names)"),
            {"names": list(LIMITS)},
        )

        return dict(rows.all())


def _engine(app):
    with app.app_context():
        return db.engine


# --- Los valores ------------------------------------------------------------------------


def test_every_connection_gets_the_three_limits(app):
    assert _limits(app) == {
        "statement_timeout": "30000",
        "lock_timeout": "10000",
        "idle_in_transaction_session_timeout": "60000",
    }


def test_the_limits_follow_the_configuration_and_zero_means_none(make_app):
    other = make_app(
        DATABASE_STATEMENT_TIMEOUT_SECONDS=0,
        DATABASE_LOCK_TIMEOUT_SECONDS=3,
        DATABASE_IDLE_TRANSACTION_TIMEOUT_SECONDS=0,
    )

    assert _limits(other) == {
        "statement_timeout": "0",
        "lock_timeout": "3000",
        "idle_in_transaction_session_timeout": "0",
    }


def test_the_pool_is_sized_and_checked_from_the_configuration(make_app):
    pool = _engine(make_app(DATABASE_POOL_SIZE=3, DATABASE_MAX_OVERFLOW=2)).pool

    assert pool.size() == 3
    assert pool._max_overflow == 2
    assert pool._pre_ping is True


@pytest.mark.parametrize(
    ("overrides", "variable"),
    [
        ({"DATABASE_POOL_SIZE": 0}, "DATABASE_POOL_SIZE"),
        ({"DATABASE_MAX_OVERFLOW": -1}, "DATABASE_MAX_OVERFLOW"),
        ({"DATABASE_POOL_TIMEOUT_SECONDS": 0}, "DATABASE_POOL_TIMEOUT_SECONDS"),
        ({"DATABASE_STATEMENT_TIMEOUT_SECONDS": 3601}, "DATABASE_STATEMENT_TIMEOUT_SECONDS"),
        # Una espera de bloqueo que no es más corta que la consulta nunca llegaría a cortar.
        (
            {"DATABASE_STATEMENT_TIMEOUT_SECONDS": 10, "DATABASE_LOCK_TIMEOUT_SECONDS": 10},
            "DATABASE_LOCK_TIMEOUT_SECONDS",
        ),
    ],
)
def test_the_application_does_not_start_with_limits_that_make_no_sense(overrides, variable):
    with pytest.raises(RuntimeError, match=variable):
        create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret-key",
                "SQLALCHEMY_DATABASE_URI": "postgresql+psycopg://u:p@localhost/workdesk_test",
                **overrides,
            }
        )


def test_every_default_is_valid():
    defaults = {setting.key: setting.default for setting in settings.ENGINE_SETTINGS}

    assert settings.engine_settings_problems(defaults) == []
    # Sin límite para la consulta, la espera del bloqueo puede ser cualquiera.
    assert settings.engine_settings_problems(
        defaults | {"DATABASE_STATEMENT_TIMEOUT_SECONDS": 0, "DATABASE_LOCK_TIMEOUT_SECONDS": 50}
    ) == []


# --- Cada límite corta de verdad ---------------------------------------------------------


def test_a_query_that_takes_too_long_is_cancelled(make_app):
    other = make_app(DATABASE_STATEMENT_TIMEOUT_SECONDS=1, DATABASE_LOCK_TIMEOUT_SECONDS=0)

    with other.app_context(), pytest.raises(OperationalError) as raised:
        db.session.execute(text("SELECT pg_sleep(3)"))

    assert isinstance(raised.value.orig, psycopg.errors.QueryCanceled)


def test_a_transaction_left_idle_is_cut_and_releases_its_locks(make_app, make_user):
    other = make_app(DATABASE_IDLE_TRANSACTION_TIMEOUT_SECONDS=1)
    user = make_user("SOLICITANTE", "olvidada")
    engine = _engine(other)

    forgotten = engine.connect()

    # Si la prueba falla, la conexión no debe quedarse con la fila bloqueada: la limpieza de
    # la base esperaría por ella para siempre.
    try:
        forgotten.execute(text("SELECT id FROM usuarios WHERE id = :id FOR UPDATE"), {"id": user["id"]})
        time.sleep(1.5)

        # La fila quedó libre: otra transacción la bloquea sin esperar.
        with engine.connect() as connection:
            locked = connection.execute(
                text("SELECT id FROM usuarios WHERE id = :id FOR UPDATE NOWAIT"), {"id": user["id"]}
            ).scalar()

        assert locked == user["id"]

        with pytest.raises(DBAPIError):
            forgotten.execute(text("SELECT 1"))
    finally:
        forgotten.close()


def test_a_broken_connection_in_the_pool_is_replaced_before_use(app):
    """Tras reiniciar PostgreSQL, las conexiones de la reserva están muertas: la siguiente
    petición no debe fallar por eso (`pool_pre_ping`)."""
    with app.app_context():
        pid = db.session.scalar(text("SELECT pg_backend_pid()"))
        db.session.remove()

    with psycopg.connect(_engine(app).url.set(drivername="postgresql").render_as_string(hide_password=False)) as killer:
        killer.execute("SELECT pg_terminate_backend(%s)", (pid,))

    with app.app_context():
        assert db.session.scalar(text("SELECT pg_backend_pid()")) != pid


def test_an_sql_error_never_carries_the_values_of_the_query(app):
    """El log recibe el texto de los errores de SQL: no debe llevar los valores (un hash, un
    dato personal)."""
    with app.app_context(), pytest.raises(DBAPIError) as raised:
        db.session.execute(text("SELECT CAST(:marca AS text), 1 / 0"), {"marca": "dato-que-no-debe-salir"})

    assert "dato-que-no-debe-salir" not in str(raised.value)


# --- Lo que ve la persona -----------------------------------------------------------------


def test_a_lock_that_does_not_come_free_answers_busy_and_not_a_hanging_page(make_app, make_user):
    """Alguien retiene la fila de la cuenta (el login la bloquea para contar los intentos):
    la petición se rinde al pasar la espera máxima, con la página de «ocupado»."""
    other = make_app(DATABASE_LOCK_TIMEOUT_SECONDS=1)
    user = make_user("SOLICITANTE", "retenida")
    client = other.test_client()
    locked, done = threading.Event(), threading.Event()

    def hold_the_row():
        # Desde otro hilo, y la suelta sola a los 8 s: sin el límite, la prueba falla en vez
        # de quedarse esperando para siempre.
        with _engine(other).connect() as holder:
            holder.execute(text("SELECT id FROM usuarios WHERE id = :id FOR UPDATE"), {"id": user["id"]})
            locked.set()
            done.wait(timeout=8)
            holder.rollback()

    holder = threading.Thread(target=hold_the_row)
    holder.start()
    assert locked.wait(timeout=10)

    try:
        started = time.monotonic()
        response = login(client, user)
        elapsed = time.monotonic() - started
    finally:
        done.set()
        holder.join()

    body = response.get_data(as_text=True)

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "5"
    assert BUSY in body
    assert "LockNotAvailable" not in body
    assert elapsed < 5

    # La cuenta no quedó tocada: con la fila libre, entra.
    assert login(client, user).status_code == 302


def test_no_free_connection_answers_busy_and_the_error_page_does_not_ask_the_database(
    make_app, make_user
):
    """Con todas las conexiones ocupadas, la petición se rinde. La página de error no usa la
    base (ni la persona, ni el menú, ni la campana): si la usara, volvería a esperar y
    fallaría dentro del propio manejador."""
    other = make_app(
        DATABASE_POOL_SIZE=1, DATABASE_MAX_OVERFLOW=0, DATABASE_POOL_TIMEOUT_SECONDS=1
    )
    user = make_user("TECNICO", "sin_conexion")
    client = other.test_client()
    assert login(client, user).status_code == 302

    held = _engine(other).connect()

    try:
        response = client.get("/dashboard")
    finally:
        held.close()

    assert response.status_code == 503
    assert BUSY in response.get_data(as_text=True)
    assert client.get("/dashboard").status_code == 200


def test_the_bell_gets_its_busy_answer_in_json(app, client, make_user, monkeypatch):
    user = make_user("SOLICITANTE", "campana")
    login(client, user)

    def busy(_user):
        raise OperationalError("SELECT ...", {}, psycopg.errors.QueryCanceled())

    monkeypatch.setattr(notification_routes, "count_unread", busy)
    response = client.get("/notifications/unread-count", headers={"Accept": "application/json"})

    data = response.get_json()

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "5"
    assert (data["ok"], data["error"]) == (False, "database_busy")
    assert "inténtalo de nuevo" in data["message"]
