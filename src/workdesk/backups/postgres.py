"""Las herramientas de PostgreSQL (`pg_dump` y `pg_restore`) y cómo se les pasa la conexión.

- **Dónde están.** En `PG_BIN_DIR` si se definió; si no, en el PATH. Sin ellas no se puede
  respaldar ni comprobar un respaldo, así que su ausencia es un error con instrucciones.
- **La contraseña nunca va en la línea de comandos** (cualquier usuario del equipo puede ver
  los argumentos de un proceso) ni en `PGPASSWORD` (la documentación de PostgreSQL lo
  desaconseja por lo mismo). Va en un archivo de contraseñas temporal, privado del usuario,
  que el proceso hijo lee con `PGPASSFILE` y que se borra al terminar. El hijo tampoco
  hereda `DATABASE_URL` ni `SECRET_KEY`.
- **Nunca se queda esperando.** `--no-password` hace que falle en lugar de preguntar por
  consola, y `PGCONNECT_TIMEOUT` limita la espera por un servidor que no responde.
"""

import contextlib
import os
import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import URL, make_url

CONNECT_TIMEOUT_SECONDS = "10"
APPLICATION_NAME = "workdesk-backup"
# Lo último que escribió la herramienta al fallar: lo que sirve para entender el error.
ERROR_TAIL_LINES = 5
# Lo que nunca debe llegar a las herramientas (ver `tool_environment`).
SECRET_VARIABLES = frozenset(
    {"PGPASSWORD", "SECRET_KEY", "DATABASE_URL", "TEST_DATABASE_URL", "WORKDESK_DEMO_PASSWORD"}
)


class BackupError(Exception):
    """Un respaldo no se pudo crear o comprobar. El mensaje es para quien lo ejecuta."""


@dataclass(frozen=True)
class Connection:
    """Los datos de conexión de libpq, sin la contraseña, y la contraseña aparte."""

    conninfo: str
    password: str | None


def find_tool(name: str, bin_dir: str | None) -> str:
    """La ruta de `pg_dump` o `pg_restore`, o un `BackupError` que dice cómo resolverlo."""
    if bin_dir:
        executable = Path(bin_dir) / (f"{name}.exe" if os.name == "nt" else name)

        if executable.is_file():
            return str(executable)

        raise BackupError(f"No se encontró {name} en PG_BIN_DIR ({bin_dir}).")

    found = shutil.which(name)

    if found is None:
        raise BackupError(
            f"No se encontró {name}. Instala las herramientas de cliente de PostgreSQL o "
            "define PG_BIN_DIR con la carpeta que las contiene."
        )

    return found


def _quote(value: str) -> str:
    """Un valor de una cadena de conexión de libpq, entre comillas simples."""
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def connection_for(database_url: str | URL) -> Connection:
    """La conexión de `DATABASE_URL` para las herramientas de PostgreSQL."""
    url = make_url(database_url)

    if url.get_backend_name() != "postgresql":
        raise BackupError("Los respaldos necesitan una base de datos PostgreSQL.")

    if not url.database:
        raise BackupError("DATABASE_URL no indica la base de datos.")

    fields = {
        "host": url.host,
        "port": None if url.port is None else str(url.port),
        "dbname": url.database,
        "user": url.username,
        "application_name": APPLICATION_NAME,
    }
    # Opciones de la URL como `sslmode=require` (las de libpq tienen el mismo nombre).
    for key, value in url.query.items():
        fields.setdefault(key, value if isinstance(value, str) else value[-1])

    conninfo = " ".join(f"{key}={_quote(value)}" for key, value in fields.items() if value)

    return Connection(conninfo=conninfo, password=url.password)


def _passfile_line(password: str) -> str:
    """La línea del archivo de contraseñas: vale para cualquier servidor, base y usuario
    (el archivo solo existe para este proceso) y escapa `\\` y `:` como pide libpq."""
    escaped = password.replace("\\", "\\\\").replace(":", "\\:")

    return f"*:*:*:*:{escaped}\n"


@contextlib.contextmanager
def tool_environment(connection: Connection) -> Iterator[dict[str, str]]:
    """El entorno del proceso hijo, con la contraseña en un archivo temporal privado.

    El hijo hereda el entorno (en Windows lo necesita para arrancar), pero sin los secretos de
    WorkDesk: `python-dotenv` carga el `.env` en el entorno del proceso, así que
    `DATABASE_URL` (con la contraseña dentro) y `SECRET_KEY` llegarían a `pg_dump` sin que
    las use. Tampoco pasa ninguna variable cuyo valor contenga la contraseña, ni
    `PGPASSWORD`, que además ganaría al archivo. Las demás variables de libpq (los
    certificados de SSL, por ejemplo) se respetan, y la cadena de conexión manda sobre el
    servidor, la base y el usuario.
    """
    password = connection.password
    environment = {
        key: value
        for key, value in os.environ.items()
        if key not in SECRET_VARIABLES and not (password and password in value)
    }
    environment.setdefault("PGCONNECT_TIMEOUT", CONNECT_TIMEOUT_SECONDS)
    passfile = None

    try:
        if connection.password:
            # `mkstemp` crea el archivo solo para este usuario (0600 en Linux; en Windows,
            # en su carpeta temporal privada).
            descriptor, passfile = tempfile.mkstemp(prefix="workdesk-pg-", suffix=".pass")

            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(_passfile_line(connection.password))

            environment["PGPASSFILE"] = passfile

        yield environment
    finally:
        if passfile is not None:
            with contextlib.suppress(OSError):
                os.remove(passfile)


def run_tool(arguments: list[str], environment: dict[str, str] | None = None, *, timeout=None):
    """Ejecuta una herramienta y devuelve su salida; si falla, un `BackupError` con el final
    de lo que escribió (nunca contiene la contraseña: no está en los argumentos)."""
    try:
        result = subprocess.run(
            arguments,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise BackupError(f"{Path(arguments[0]).stem} no terminó a tiempo.") from error
    except OSError as error:
        raise BackupError(f"No se pudo ejecutar {Path(arguments[0]).stem}: {error}") from error

    if result.returncode != 0:
        tail = "\n".join(result.stderr.strip().splitlines()[-ERROR_TAIL_LINES:])
        raise BackupError(f"{Path(arguments[0]).stem} falló: {tail or 'sin mensaje'}")

    return result.stdout


def tool_version(executable: str) -> str:
    """La versión de una herramienta, como «18.6»."""
    output = run_tool([executable, "--version"], timeout=30).strip()

    return output.rsplit(" ", 1)[-1]
