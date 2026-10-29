import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import Flask


def configure_logging(app: Flask) -> None:
    if app.config.get("TESTING"):
        return

    log_directory = Path(app.instance_path) / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)

    log_file = log_directory / "workdesk.log"

    log_level_name = app.config["LOG_LEVEL"]
    log_level = getattr(logging, log_level_name, logging.INFO)

    log_file_path = log_file.resolve()

    for handler in app.logger.handlers:
        if (
            isinstance(handler, RotatingFileHandler)
            and Path(handler.baseFilename) == log_file_path
        ):
            return

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=app.config["LOG_MAX_BYTES"],
        backupCount=app.config["LOG_BACKUP_COUNT"],
        encoding="utf-8",
    )

    file_handler.setLevel(log_level)

    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
    )

    app.logger.setLevel(log_level)
    app.logger.addHandler(file_handler)

    app.logger.info(
        "Logging configurado para WorkDesk. Entorno: %s",
        app.config["APP_ENV"],
    )