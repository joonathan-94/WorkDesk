"""El log técnico: un archivo por proceso (ver `src/workdesk/logging_config.py`).

El servidor web y el planificador viven a la vez. Si escribieran el mismo archivo, en
Windows la rotación fallaría con `PermissionError` (otro proceso lo tiene abierto) y el log
crecería sin límite. Estas pruebas no dependen del sistema operativo: comprueban la causa,
que cada proceso escribe en su propio archivo y que ninguno lo abre antes de escribir.
"""

from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

from src.workdesk.cli import scheduling
from src.workdesk.logging_config import (
    APP_LOG_FILE,
    SCHEDULER_LOG_FILE,
    configure_logging,
    use_log_file,
)


def _file_handlers(app):
    return [h for h in app.logger.handlers if isinstance(h, RotatingFileHandler)]


@pytest.fixture()
def real_logging(app, tmp_path):
    """La aplicación como fuera de los tests (con log a archivo), en un directorio
    temporal. `app.logger` es global por nombre: al terminar se retiran los manejadores
    para no tocar a los demás tests."""
    app.config["TESTING"] = False
    app.instance_path = str(tmp_path)

    yield app

    for handler in _file_handlers(app):
        app.logger.removeHandler(handler)
        handler.close()

    app.config["TESTING"] = True


def test_the_tests_never_write_a_log_file(app):
    configure_logging(app)

    assert _file_handlers(app) == []


def test_the_web_application_writes_workdesk_log(real_logging, tmp_path):
    configure_logging(real_logging)
    real_logging.logger.warning("mensaje de prueba")

    log_file = tmp_path / "logs" / APP_LOG_FILE
    assert "mensaje de prueba" in log_file.read_text(encoding="utf-8")


def test_the_file_is_not_opened_until_something_is_written(real_logging, tmp_path):
    # Un comando de un momento crea la aplicación pero casi nunca escribe: así no
    # mantiene abierto el archivo que el servidor web necesita rotar.
    configure_logging(real_logging)

    (handler,) = _file_handlers(real_logging)
    assert handler.stream is None
    assert not (tmp_path / "logs" / APP_LOG_FILE).exists()


def test_switching_the_file_leaves_exactly_one_handler(real_logging, tmp_path):
    configure_logging(real_logging)
    use_log_file(real_logging, SCHEDULER_LOG_FILE)
    use_log_file(real_logging, SCHEDULER_LOG_FILE)

    (handler,) = _file_handlers(real_logging)
    assert Path(handler.baseFilename) == (tmp_path / "logs" / SCHEDULER_LOG_FILE).resolve()


def test_the_scheduler_writes_its_own_file(app, monkeypatch):
    chosen = []
    monkeypatch.setattr(scheduling, "use_log_file", lambda _app, name: chosen.append(name))
    monkeypatch.setattr(scheduling, "run_once", lambda: scheduling.SchedulerResult())

    result = app.test_cli_runner().invoke(args=["run-scheduler", "--once"])

    assert result.exit_code == 0, result.output
    assert chosen == [SCHEDULER_LOG_FILE]
    assert SCHEDULER_LOG_FILE != APP_LOG_FILE
