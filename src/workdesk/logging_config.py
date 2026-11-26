"""El log técnico de WorkDesk (`instance/logs`), con rotación por tamaño.

**Un archivo por proceso.** El servidor web y el planificador (`run-scheduler`) son dos
procesos que viven a la vez. Si escribieran el mismo archivo, en Windows la rotación
fallaría: renombrar un archivo que otro proceso tiene abierto da `PermissionError`, el
log seguiría creciendo sin límite (RNF-036) y se perderían archivos de la rotación
(reproducido: dos procesos escribiendo a la vez provocaron 16 rotaciones fallidas). Por
eso el servidor web escribe `workdesk.log` y el planificador `scheduler.log`.

**El archivo se abre al escribir, no al arrancar** (`delay=True`). Los comandos de un
momento (`seed-roles`, `sla-status`...) crean la aplicación y casi nunca escriben en el
log: así no lo mantienen abierto mientras el servidor web intenta rotarlo.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import Flask

APP_LOG_FILE = "workdesk.log"
SCHEDULER_LOG_FILE = "scheduler.log"

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def configure_logging(app: Flask) -> None:
    """Envía el log de la aplicación a `instance/logs/workdesk.log`."""
    use_log_file(app, APP_LOG_FILE)


def use_log_file(app: Flask, file_name: str) -> None:
    """Hace que este proceso escriba su log en `instance/logs/<file_name>`.

    Reemplaza el archivo anterior (si lo había) y es idempotente. En los tests no hace
    nada: la suite no escribe en `instance/`.
    """
    if app.config.get("TESTING"):
        return

    log_file = (log_directory(app) / file_name).resolve()

    for handler in list(app.logger.handlers):
        if not isinstance(handler, RotatingFileHandler):
            continue

        if Path(handler.baseFilename) == log_file:
            return

        app.logger.removeHandler(handler)
        handler.close()

    log_level = getattr(logging, app.config["LOG_LEVEL"], logging.INFO)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=app.config["LOG_MAX_BYTES"],
        backupCount=app.config["LOG_BACKUP_COUNT"],
        encoding="utf-8",
        delay=True,
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    app.logger.setLevel(log_level)
    app.logger.addHandler(file_handler)


def log_directory(app: Flask) -> Path:
    directory = Path(app.instance_path) / "logs"
    directory.mkdir(parents=True, exist_ok=True)

    return directory
