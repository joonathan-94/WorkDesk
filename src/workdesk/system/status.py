"""El estado de WorkDesk y de sus piezas (UI-029, RF-130, RNF-037).

Cada pieza da un estado (bien, atención o fallo), una frase y unos datos. Se comprueban por
separado: que la base no responda no impide ver el disco, el planificador o los respaldos.
Ninguna comprobación escribe nada; la de la base mide cuánto tarda en contestar.

Solo lo ve el Administrador. `/health` sigue siendo la comprobación pública y mínima, sin
detalles, para un monitor externo.
"""

import platform
import re
import shutil
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path

from flask import current_app
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .. import settings
from ..backups.package import Signature, list_backups
from ..configuration import initial_value, value_of
from ..extensions import db
from ..formatting import format_size, local_datetime
from ..logging_config import APP_LOG_FILE, SCHEDULER_LOG_FILE, log_directory
from .heartbeat import read_heartbeat
from .migrations import (
    RevisionMatch,
    compare_revision,
    database_revision,
)

# El planificador se da por activo si pasó en los últimos tres intervalos, o en los últimos 15
# minutos si se programa con `--once` cada pocos minutos.
SCHEDULER_MISSED_PASSES = 3
SCHEDULER_MIN_WINDOW = timedelta(minutes=15)
BACKUP_MAX_AGE = timedelta(days=7)
LOW_DISK_RATIO = 0.10
# Del final de cada log: errores de las últimas 24 horas. Con el tope no se lee un log entero.
LOG_TAIL_BYTES = 2 * 1024 * 1024
LOG_WINDOW = timedelta(hours=24)
_LOG_ERROR = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ \| (?:ERROR|CRITICAL) \|", re.MULTILINE)


class Health(StrEnum):
    BIEN = "BIEN"
    ATENCION = "ATENCION"
    FALLO = "FALLO"


HEALTH_LABELS = {Health.BIEN: "Operativo", Health.ATENCION: "Requiere atención", Health.FALLO: "Con fallos"}


@dataclass
class Component:
    name: str
    health: Health
    summary: str
    details: list[tuple[str, str]] = field(default_factory=list)


def ago(moment: datetime, now: datetime) -> str:
    """«hace 3 min», «hace 5 h» o «hace 2 días»."""
    seconds = max(0, int((now - moment).total_seconds()))

    if seconds < 60:
        return "hace menos de un minuto"

    if seconds < 3600:
        return f"hace {seconds // 60} min"

    if seconds < 86400:
        return f"hace {seconds // 3600} h"

    days = seconds // 86400

    return f"hace {days} {'día' if days == 1 else 'días'}"


def _application() -> Component:
    config = current_app.config

    return Component(
        "Aplicación",
        Health.BIEN,
        "Responde.",
        [
            ("Entorno", config["APP_ENV"]),
            ("Zona horaria", config["APP_TIMEZONE"]),
            ("Python", platform.python_version()),
        ],
    )


def _database() -> tuple[Component, str | None]:
    """El estado de la base y su revisión de migraciones (o `None` si no responde)."""
    try:
        started = time.perf_counter()

        with db.engine.connect() as connection:
            connection.scalar(text("SELECT 1"))
            milliseconds = (time.perf_counter() - started) * 1000
            name, version, size = connection.execute(
                text(
                    "SELECT current_database(), current_setting('server_version'), "
                    "pg_database_size(current_database())"
                )
            ).one()
            revision = database_revision(connection)
    except SQLAlchemyError:
        current_app.logger.exception("Estado del sistema: PostgreSQL no responde.")
        return Component("Base de datos", Health.FALLO, "PostgreSQL no responde."), None

    component = Component(
        "Base de datos",
        Health.BIEN,
        "PostgreSQL responde en menos de 1 ms." if milliseconds < 1 else f"PostgreSQL responde en {milliseconds:.0f} ms.",
        [("Base", name), ("Versión", version), ("Tamaño", format_size(size))],
    )

    return component, revision or ""


_MIGRATION_HEALTH = {
    RevisionMatch.AL_DIA: (Health.BIEN, "El esquema está al día con el código."),
    RevisionMatch.ANTERIOR: (Health.ATENCION, "Hay migraciones pendientes: ejecuta «db upgrade»."),
    RevisionMatch.DESCONOCIDA: (Health.FALLO, "La base es de una versión de WorkDesk que este código no conoce."),
    RevisionMatch.SIN_REVISION: (Health.ATENCION, "La base no se creó con las migraciones."),
}


def _migrations(revision: str | None) -> Component:
    if revision is None:
        return Component("Migraciones", Health.FALLO, "No se puede saber: la base no responde.")

    match = compare_revision(revision)
    health, summary = _MIGRATION_HEALTH[match]

    return Component("Migraciones", health, summary, [("Revisión de la base", revision or "—")])


def _scheduler(now: datetime) -> Component:
    heartbeat = read_heartbeat(Path(current_app.config["SCHEDULER_HEARTBEAT_FILE"]))

    if heartbeat is None:
        return Component(
            "Planificador",
            Health.ATENCION,
            "No hay constancia de que se haya ejecutado: sin él no hay avisos de SLA ni cierre automático.",
        )

    try:
        interval = value_of(settings.SCHEDULER_INTERVAL_SECONDS)
    except SQLAlchemyError:
        db.session.rollback()
        interval = initial_value(settings.SCHEDULER_INTERVAL_SECONDS)

    window = max(timedelta(seconds=interval * SCHEDULER_MISSED_PASSES), SCHEDULER_MIN_WINDOW)
    details = [("Última pasada", local_datetime(heartbeat.last_pass)), ("Fallos en esa pasada", str(heartbeat.failures))]

    if now - heartbeat.last_pass > window:
        return Component(
            "Planificador",
            Health.ATENCION,
            f"La última pasada fue {ago(heartbeat.last_pass, now)}: parece detenido.",
            details,
        )

    if heartbeat.failures:
        return Component(
            "Planificador",
            Health.ATENCION,
            f"Pasó {ago(heartbeat.last_pass, now)}, con fallos: revisa {SCHEDULER_LOG_FILE}.",
            details,
        )

    return Component("Planificador", Health.BIEN, f"En marcha: pasó {ago(heartbeat.last_pass, now)}.", details)


def _folder_details(label: str, folder: Path) -> tuple[list[tuple[str, str]], bool]:
    """Los datos de una carpeta y si su disco anda escaso de espacio."""
    probe = folder if folder.exists() else folder.parent

    try:
        usage = shutil.disk_usage(probe)
    except OSError:
        return [(label, f"{folder} (no se puede leer)")], True

    low = usage.free < usage.total * LOW_DISK_RATIO

    return [(label, str(folder)), ("Libre en su disco", f"{format_size(usage.free)} de {format_size(usage.total)}")], low


def _storage() -> Component:
    config = current_app.config
    uploads, backups = Path(config["UPLOADS_DIR"]), Path(config["BACKUPS_DIR"])
    uploads_details, uploads_low = _folder_details("Adjuntos", uploads)
    backups_details, backups_low = _folder_details("Respaldos", backups)
    details = uploads_details + backups_details

    if uploads.exists() and not uploads.is_dir():
        return Component("Almacenamiento", Health.FALLO, "La carpeta de adjuntos no es una carpeta.", details)

    if uploads_low or backups_low:
        percent = int(LOW_DISK_RATIO * 100)
        return Component("Almacenamiento", Health.ATENCION, f"Queda menos del {percent} % libre en un disco.", details)

    return Component("Almacenamiento", Health.BIEN, "Hay espacio en disco.", details)


def _backups(now: datetime) -> Component:
    config = current_app.config
    backups = list_backups(Path(config["BACKUPS_DIR"]), config["SECRET_KEY"])

    if not backups:
        return Component("Respaldos", Health.ATENCION, "Todavía no hay respaldos: crea uno con «backup-create».")

    latest = backups[0]
    created = latest.created_at
    details = [("Último", latest.name), ("Tamaño", format_size(latest.size)), ("Respaldos guardados", str(len(backups)))]

    if latest.manifest is None or created is None:
        return Component("Respaldos", Health.ATENCION, "El último respaldo no se puede leer.", details)

    if latest.signature is not Signature.VALIDA:
        return Component("Respaldos", Health.ATENCION, "La firma del último respaldo no es de esta instalación.", details)

    if now - created > BACKUP_MAX_AGE:
        return Component("Respaldos", Health.ATENCION, f"El último respaldo es de {ago(created, now)}.", details)

    return Component("Respaldos", Health.BIEN, f"El último respaldo es de {ago(created, now)}.", details)


def _log_errors(path: Path, since: datetime) -> tuple[int, datetime | None]:
    """Cuántos errores escribió un log desde `since`, y cuándo el último."""
    try:
        with path.open("rb") as handle:
            handle.seek(max(0, path.stat().st_size - LOG_TAIL_BYTES))
            tail = handle.read().decode("utf-8", errors="replace")
    except OSError:
        return 0, None

    # El log escribe la hora local del equipo, sin zona: `astimezone()` le pone la del equipo.
    moments = [datetime.strptime(match, "%Y-%m-%d %H:%M:%S").astimezone() for match in _LOG_ERROR.findall(tail)]
    recent = [moment for moment in moments if moment >= since]

    return len(recent), max(recent, default=None)


def _errors(now: datetime) -> Component:
    folder = log_directory(current_app)
    since = now - LOG_WINDOW
    details, total, latest = [], 0, None

    for name in (APP_LOG_FILE, SCHEDULER_LOG_FILE):
        count, last = _log_errors(folder / name, since)
        total += count
        latest = max(filter(None, (latest, last)), default=None)
        details.append((name, str(count)))

    if not total:
        return Component("Errores", Health.BIEN, "Ningún error registrado en las últimas 24 horas.", details)

    details.append(("El más reciente", local_datetime(latest)))

    return Component(
        "Errores",
        Health.ATENCION,
        f"{total} {'error registrado' if total == 1 else 'errores registrados'} en las últimas 24 horas: "
        f"el detalle está en {folder}.",
        details,
    )


def system_status(now: datetime | None = None) -> list[Component]:
    now = (now or datetime.now(UTC)).astimezone(UTC)
    database, revision = _database()

    return [
        _application(),
        database,
        _migrations(revision),
        _scheduler(now),
        _storage(),
        _backups(now),
        _errors(now),
    ]


def overall(components: list[Component]) -> Health:
    healths = {component.health for component in components}

    return Health.FALLO if Health.FALLO in healths else Health.ATENCION if Health.ATENCION in healths else Health.BIEN
