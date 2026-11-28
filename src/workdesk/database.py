"""La conexión con PostgreSQL: la reserva de conexiones y los tiempos máximos.

Con muchas personas a la vez, lo que deja colgada a una aplicación web no suele ser una
consulta lenta sino una espera que **no termina**: una transacción abierta que retiene un
bloqueo, una consulta desbocada o una petición que aguarda para siempre una conexión libre.
Cada hilo que se queda esperando es uno menos para atender a los demás, y en pocos minutos no
queda ninguno. Por eso:

- **Ninguna espera es indefinida.** PostgreSQL corta la consulta que pasa de
  `DATABASE_STATEMENT_TIMEOUT_SECONDS`, la espera de un bloqueo que pasa de
  `DATABASE_LOCK_TIMEOUT_SECONDS` y la transacción que lleva más de
  `DATABASE_IDLE_TRANSACTION_TIMEOUT_SECONDS` abierta sin hacer nada (así suelta sus
  bloqueos). Una petición que no consigue conexión en `DATABASE_POOL_TIMEOUT_SECONDS` también
  se rinde. En todos los casos la persona ve «inténtalo en unos segundos» (503, `errors.py`)
  y las demás peticiones siguen atendidas.
- **Una conexión rota no se entrega:** antes de usar una conexión de la reserva se comprueba
  que siga viva (`pool_pre_ping`), así que tras reiniciar PostgreSQL ninguna petición falla
  por una conexión que ya no existe.
- **Los errores no copian datos:** el texto de un error de SQL lleva la sentencia pero no sus
  valores (`hide_parameters`), así que el log nunca recibe un hash ni un dato personal.

Los tiempos se fijan en cada conexión nueva (evento `connect`) y no en la URL: valen igual con
cualquier forma de abrir la conexión, también la reserva de la suite de tests. Lo que necesita
más tiempo (la foto de un respaldo mientras `pg_dump` trabaja, una migración) lo levanta solo
para su transacción con `SET LOCAL`.
"""

from flask import Flask
from sqlalchemy import event
from sqlalchemy.engine import make_url

from . import settings
from .extensions import db


def engine_options(config) -> dict:
    """Las opciones del motor de SQLAlchemy que salen de la configuración."""
    recycle = config[settings.DATABASE_POOL_RECYCLE_SECONDS.key]

    return {
        "pool_size": config[settings.DATABASE_POOL_SIZE.key],
        "max_overflow": config[settings.DATABASE_MAX_OVERFLOW.key],
        "pool_timeout": config[settings.DATABASE_POOL_TIMEOUT_SECONDS.key],
        # Para SQLAlchemy, -1 es «nunca».
        "pool_recycle": recycle if recycle > 0 else -1,
        "pool_pre_ping": True,
        "hide_parameters": True,
    }


def session_limits(config) -> dict[str, str]:
    """Los parámetros de PostgreSQL que recibe cada conexión («0s» es sin límite)."""
    return {
        "statement_timeout": f"{config[settings.DATABASE_STATEMENT_TIMEOUT_SECONDS.key]}s",
        "lock_timeout": f"{config[settings.DATABASE_LOCK_TIMEOUT_SECONDS.key]}s",
        "idle_in_transaction_session_timeout": (
            f"{config[settings.DATABASE_IDLE_TRANSACTION_TIMEOUT_SECONDS.key]}s"
        ),
    }


def configure_database(app: Flask) -> None:
    """Valida los parámetros de la conexión, crea el motor y le pone los tiempos máximos.

    Las opciones que ya traiga `SQLALCHEMY_ENGINE_OPTIONS` mandan sobre las de aquí: los tests
    entregan su propia forma de abrir conexiones. Todo esto es de PostgreSQL, la base de
    WorkDesk: con otra URL (las pruebas que solo comprueban la configuración usan una de
    SQLite que nunca se abre) el motor se crea sin más.
    """
    if problems := settings.engine_settings_problems(app.config):
        raise RuntimeError(" ".join(problems))

    if make_url(app.config["SQLALCHEMY_DATABASE_URI"]).get_backend_name() != "postgresql":
        db.init_app(app)
        return

    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_options(app.config) | app.config.get(
        "SQLALCHEMY_ENGINE_OPTIONS", {}
    )
    db.init_app(app)

    with app.app_context():
        for engine in db.engines.values():
            _limit_each_connection(engine, session_limits(app.config))


def _limit_each_connection(engine, limits: dict[str, str]) -> None:
    # `set_config(nombre, valor, false)` es `SET` para toda la sesión, con los valores como
    # parámetros (nada se escribe dentro del SQL).
    statement = "SELECT " + ", ".join("set_config(%s, %s, false)" for _ in limits)
    values = tuple(item for pair in limits.items() for item in pair)

    @event.listens_for(engine, "connect")
    def set_limits(dbapi_connection, _connection_record):
        # Fuera de una transacción: dentro, el `ROLLBACK` con que la reserva devuelve cada
        # conexión desharía el `SET`.
        autocommit = dbapi_connection.autocommit
        dbapi_connection.autocommit = True

        try:
            with dbapi_connection.cursor() as cursor:
                cursor.execute(statement, values)
        finally:
            dbapi_connection.autocommit = autocommit
