"""La base de datos de la suite: su protección, su esquema y su limpieza.

**Protección crítica.** `checked_database_url` es la única puerta de entrada a la base
de pruebas: se niega a devolver una URL que no apunte a `workdesk_test`, y todo lo que
borra o crea tablas (los fixtures de `conftest.py` y `empty_tables`) la llama antes de
tocar nada. Así ninguna operación destructiva de la suite puede alcanzar `workdesk_dev`.
No se debe debilitar ni saltarse.

**Por qué el esquema no se recrea en cada test.** Medido sobre una muestra de 237 tests,
el 83 % del tiempo se iba en preparar y limpiar fixtures (`drop_all` + `create_all` +
`drop_all` en cada test, unos 330 ms) y solo el 17 % en los tests. Ahora:

- el esquema se crea **una vez por sesión** (una vez por proceso con `pytest-xdist`) y se
  elimina al terminar;
- entre un test y el siguiente solo se **vacían las tablas que quedaron con filas** y se
  reinician las secuencias (`empty_tables`, unos pocos milisegundos): cada test sigue
  empezando con la base vacía y con los identificadores en 1, como si fuera recién creada.

Se vacían las tablas (y no se envuelve cada test en una transacción que se deshace)
porque la aplicación y los tests dependen de confirmaciones reales: `now()` cambia entre
transacciones (el orden por fecha), y los tests con hilos usan conexiones distintas que
solo ven lo ya confirmado.

**Instantáneas.** Algunos tests parten de un estado caro de construir (por ejemplo, los 108
tickets de demostración, unos 6 s). `take_snapshot` guarda una copia de los datos en un
esquema auxiliar y `restore_snapshot` la restaura en unas decenas de milisegundos: el
estado se construye una vez por proceso y cada test parte de una copia exacta (mismas
filas y mismas secuencias). La instantánea solo cubre la base de datos: lo que un test
deja en disco (como los adjuntos) lo copia quien la usa.

**Ejecución en paralelo.** Con `pytest-xdist` cada proceso trabaja en su propio esquema de
PostgreSQL (`wd_test_gw0`, `wd_test_gw1`...) dentro de la misma base `workdesk_test`: no
hace falta crear bases ni permisos nuevos, y la protección anterior sigue valiendo.

**Conexiones reutilizadas entre tests.** Cada test crea su aplicación y su motor de
SQLAlchemy, y antes cada uno abría conexiones nuevas: en Windows PostgreSQL crea un proceso
por conexión y cada una costaba unos 54 ms, en miles de tests. Ahora los motores reciben
sus conexiones de una reserva del proceso (`reusable_engine_options`): al cerrar el motor,
la conexión vuelve a la reserva limpia (sin transacción, con la configuración de sesión
restablecida y sin bloqueos consultivos) y el test siguiente la reutiliza. Cada test sigue
teniendo su aplicación y su motor propios; solo se ahorra abrir la conexión.
"""

import os
import threading
from dataclasses import dataclass
from functools import cache

import psycopg
from psycopg.pq import TransactionStatus
from sqlalchemy import text
from sqlalchemy.engine import make_url

from src.workdesk.extensions import db

TEST_DATABASE_NAME = "workdesk_test"


def checked_database_url() -> str:
    """La URL de la base de pruebas; `RuntimeError` si no es `workdesk_test`."""
    test_database_url = os.getenv("TEST_DATABASE_URL")

    if not test_database_url:
        raise RuntimeError(
            "Falta TEST_DATABASE_URL para ejecutar los tests."
        )

    database_name = make_url(test_database_url).database

    if database_name != TEST_DATABASE_NAME:
        raise RuntimeError(
            "Los tests solo pueden ejecutarse sobre workdesk_test."
        )

    return test_database_url


def worker_schema() -> str | None:
    """El esquema propio de este proceso con `pytest-xdist`, o None sin paralelismo
    (entonces se usa el esquema por defecto, como siempre)."""
    worker = os.getenv("PYTEST_XDIST_WORKER")

    return f"wd_test_{worker}" if worker else None


def engine_options() -> dict:
    """Opciones del motor de SQLAlchemy: dirige las conexiones al esquema del proceso."""
    schema = worker_schema()

    if schema is None:
        return {}

    return {"connect_args": {"options": f"-csearch_path={schema}"}}


# --- Conexiones reutilizadas -------------------------------------------------------

# Las conexiones que esperan al próximo test. Los tests con hilos devuelven conexiones
# desde otros hilos, de ahí el candado.
_IDLE: list["_ReusableConnection"] = []
_IDLE_LOCK = threading.Lock()

# Lo que deja una conexión como recién abierta: la configuración de sesión vuelve a la de
# su arranque (el `search_path` del esquema del proceso) y se sueltan los bloqueos
# consultivos de sesión. Los de transacción ya se soltaron con el `ROLLBACK`.
_RESET_SESSION = "RESET ALL; SELECT pg_advisory_unlock_all()"


class _ReusableConnection(psycopg.Connection):
    """Una conexión de psycopg que, al cerrarla, vuelve a la reserva en vez de cerrarse."""

    def close(self) -> None:
        if self.closed:
            return

        try:
            if self.info.transaction_status != TransactionStatus.IDLE:
                self.rollback()

            self.execute(_RESET_SESSION)
            self.commit()
        except psycopg.Error:
            # Rota o a medio usar: no se reutiliza.
            self.close_for_real()
            return

        with _IDLE_LOCK:
            _IDLE.append(self)

    def close_for_real(self) -> None:
        super().close()


def reusable_engine_options(database_url: str) -> dict:
    """Opciones del motor para que tome sus conexiones de la reserva del proceso.

    `database_url` debe venir de `checked_database_url`: la reserva nunca abre una
    conexión a otra base que `workdesk_test`.
    """
    url = make_url(database_url)

    if url.database != TEST_DATABASE_NAME:
        raise RuntimeError("Las conexiones reutilizadas solo pueden apuntar a workdesk_test.")

    conninfo = url.set(drivername="postgresql").render_as_string(hide_password=False)
    connect_kwargs = engine_options().get("connect_args", {})

    def creator():
        with _IDLE_LOCK:
            while _IDLE:
                connection = _IDLE.pop()

                if not connection.closed:
                    return connection

        return _ReusableConnection.connect(conninfo, **connect_kwargs)

    return {"creator": creator}


def close_idle_connections() -> None:
    """Cierra de verdad las conexiones en espera (al terminar la sesión)."""
    with _IDLE_LOCK:
        while _IDLE:
            _IDLE.pop().close_for_real()


def create_schema() -> None:
    """Deja un esquema nuevo y vacío. Necesita el contexto de una aplicación de pruebas
    (cuya URL ya pasó por `checked_database_url`)."""
    schema = worker_schema()

    if schema is None:
        db.drop_all()
    else:
        with db.engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))

    db.create_all()


def drop_schema() -> None:
    """Elimina el esquema de pruebas (y sus instantáneas) al terminar la sesión, y cierra
    las conexiones que esperaban al próximo test."""
    drop_snapshots()
    schema = worker_schema()

    if schema is None:
        db.drop_all()
    else:
        with db.engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))

    db.engine.dispose()
    close_idle_connections()


@cache
def _non_empty_tables_query(table_names: tuple[str, ...]) -> str:
    """Una sola consulta que devuelve el nombre de las tablas que tienen alguna fila."""
    return " UNION ALL ".join(
        f"SELECT '{name}' AS name WHERE EXISTS (SELECT 1 FROM \"{name}\")"
        for name in table_names
    )


# Todas las secuencias del esquema vuelven a 1: los ids de un test no dependen de los
# que usaron los tests anteriores.
_RESET_SEQUENCES = text(
    "SELECT setval(c.oid::regclass, 1, false) FROM pg_class c "
    "WHERE c.relkind = 'S' AND c.relnamespace = current_schema()::regnamespace"
)


def empty_tables() -> None:
    """Deja la base como recién creada: sin filas y con las secuencias en 1.

    Borra solo las tablas que tienen filas, de las que dependen hacia las que no, y lo
    hace con `DELETE` (no `TRUNCATE`, que en esta base cuesta más que recrear el
    esquema). Necesita el contexto de una aplicación de pruebas y que no haya una
    sesión abierta con cambios sin confirmar (`db.session.remove()` antes).
    """
    tables = db.metadata.sorted_tables
    query = _non_empty_tables_query(tuple(table.name for table in tables))

    with db.engine.begin() as connection:
        non_empty = set(connection.execute(text(query)).scalars())

        for table in reversed(tables):
            if table.name in non_empty:
                connection.execute(table.delete())

        connection.execute(_RESET_SEQUENCES)


# --- Instantáneas -------------------------------------------------------------------


@dataclass(frozen=True)
class _Snapshot:
    schema: str
    # Las tablas que tenían filas, y las secuencias usadas con su último valor.
    tables: frozenset[str]
    sequences: tuple[tuple[str, int, bool], ...]
    extra: object


_SNAPSHOTS: dict[str, _Snapshot] = {}


def _snapshot_schema(name: str) -> str:
    return f"{worker_schema() or 'wd_test'}_snap_{name}"


def has_snapshot(name: str) -> bool:
    return name in _SNAPSHOTS


def take_snapshot(name: str, extra: object = None) -> None:
    """Guarda una copia de los datos de todas las tablas con el nombre `name`.

    `extra` es un valor cualquiera que `restore_snapshot` devuelve (por ejemplo, el
    resultado de la carga que produjo los datos). No debe haber cambios sin confirmar.
    """
    schema = _snapshot_schema(name)
    tables = db.metadata.sorted_tables
    query = _non_empty_tables_query(tuple(table.name for table in tables))
    db.session.remove()

    with db.engine.begin() as connection:
        connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        non_empty = set(connection.execute(text(query)).scalars())

        for table in tables:
            if table.name in non_empty:
                connection.execute(
                    text(f'CREATE TABLE "{schema}"."{table.name}" AS TABLE "{table.name}"')
                )

        sequence_names = connection.execute(
            text(
                "SELECT c.relname FROM pg_class c WHERE c.relkind = 'S' "
                "AND c.relnamespace = current_schema()::regnamespace"
            )
        ).scalars().all()
        sequences = []

        for sequence in sequence_names:
            last_value, is_called = connection.execute(
                text(f'SELECT last_value, is_called FROM "{sequence}"')
            ).one()

            if is_called:
                sequences.append((sequence, last_value, is_called))

    _SNAPSHOTS[name] = _Snapshot(
        schema=schema,
        tables=frozenset(non_empty),
        sequences=tuple(sequences),
        extra=extra,
    )


def restore_snapshot(name: str) -> object:
    """Deja la base exactamente como estaba al tomar la instantánea `name` (filas y
    secuencias) y devuelve su `extra`. Descarta cualquier cambio posterior."""
    snapshot = _SNAPSHOTS[name]
    db.session.remove()
    empty_tables()

    with db.engine.begin() as connection:
        for table in db.metadata.sorted_tables:
            if table.name in snapshot.tables:
                connection.execute(
                    text(f'INSERT INTO "{table.name}" SELECT * FROM "{snapshot.schema}"."{table.name}"')
                )

        for sequence, last_value, is_called in snapshot.sequences:
            connection.execute(
                text("SELECT setval(CAST(:name AS regclass), :value, :called)"),
                {"name": f'"{sequence}"', "value": last_value, "called": is_called},
            )

    return snapshot.extra


def drop_snapshot(name: str) -> None:
    """Elimina la instantánea `name` (si existe)."""
    snapshot = _SNAPSHOTS.pop(name, None)

    if snapshot is not None:
        with db.engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{snapshot.schema}" CASCADE'))


def drop_snapshots() -> None:
    """Elimina todas las instantáneas de este proceso."""
    for name in list(_SNAPSHOTS):
        drop_snapshot(name)
