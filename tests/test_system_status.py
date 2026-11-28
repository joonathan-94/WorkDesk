"""Estado del sistema y pantalla de respaldos (UI-028, UI-029, RF-130, RNF-037)."""

import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.exc import OperationalError

from src.workdesk.backups import create_backup
from src.workdesk.extensions import db
from src.workdesk.scheduler import run_once
from src.workdesk.system import status
from src.workdesk.system.heartbeat import read_heartbeat, record_heartbeat
from src.workdesk.system.migrations import code_heads, known_revisions
from src.workdesk.system.status import Health, system_status
from tests.backup_helpers import (
    MOMENT,
    install_alembic_version,
    members,
    needs_tools,
    rewrite,
)
from tests.ticket_helpers import login

NOW = MOMENT + timedelta(hours=1)
HEAD = ",".join(sorted(code_heads()))


def _component(app, name, now=NOW):
    with app.app_context():
        return next(component for component in system_status(now) if component.name == name)


def _heartbeat_file(app) -> Path:
    return Path(app.config["SCHEDULER_HEARTBEAT_FILE"])


@pytest.fixture()
def admin(app, client, make_user):
    login(client, make_user("ADMINISTRADOR", "admin_estado"))
    return client


@pytest.fixture()
def at_head(app):
    put_back = install_alembic_version(app, HEAD)
    yield
    put_back()


# --- Piezas sueltas ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("seconds", "text"),
    [(5, "hace menos de un minuto"), (180, "hace 3 min"), (7200, "hace 2 h"), (86400, "hace 1 día"), (3 * 86400, "hace 3 días")],
)
def test_elapsed_time_reads_like_a_person_says_it(seconds, text):
    assert status.ago(NOW - timedelta(seconds=seconds), NOW) == text


def test_a_heartbeat_is_written_whole_and_read_back(tmp_path):
    path = tmp_path / "latido.json"
    record_heartbeat(path, failures=2, moment=MOMENT)

    beat = read_heartbeat(path)

    assert beat.last_pass == MOMENT
    assert beat.failures == 2
    assert [p.name for p in tmp_path.iterdir()] == ["latido.json"]


@pytest.mark.parametrize("content", ["", "no es json", '{"fallos": 0}', '{"ultima_pasada": "2026-11-27T10:00:00", "fallos": 0}'])
def test_an_unreadable_heartbeat_counts_as_none(tmp_path, content):
    path = tmp_path / "latido.json"
    path.write_text(content, encoding="utf-8")

    assert read_heartbeat(path) is None


def test_every_scheduler_pass_leaves_its_heartbeat(app):
    with app.app_context():
        run_once(now=MOMENT)

    beat = read_heartbeat(_heartbeat_file(app))

    assert beat is not None
    assert beat.failures == 0
    assert abs(datetime.now(UTC) - beat.last_pass) < timedelta(minutes=1)


# --- Cada pieza -------------------------------------------------------------------------


def test_the_database_answers_with_its_version_and_size(app):
    component = _component(app, "Base de datos")

    assert component.health is Health.BIEN
    assert "responde en" in component.summary
    assert dict(component.details)["Base"] == "workdesk_test"


def test_when_the_database_does_not_answer_the_rest_is_still_shown(app, monkeypatch):
    def refuse(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    with app.app_context():
        monkeypatch.setattr(db.engine, "connect", refuse)
        components = {component.name: component for component in system_status(NOW)}

    assert components["Base de datos"].health is Health.FALLO
    assert components["Migraciones"].health is Health.FALLO
    assert "connection refused" not in components["Base de datos"].summary
    assert {"Aplicación", "Planificador", "Almacenamiento", "Respaldos", "Errores"} <= components.keys()


def test_migrations_at_the_code_revision_are_up_to_date(app, at_head):
    assert _component(app, "Migraciones").health is Health.BIEN


def test_an_older_revision_asks_for_db_upgrade(app):
    put_back = install_alembic_version(app, min(known_revisions() - code_heads()))

    try:
        component = _component(app, "Migraciones")
    finally:
        put_back()

    assert component.health is Health.ATENCION
    assert "db upgrade" in component.summary


def test_a_revision_unknown_to_the_code_is_a_failure(app):
    put_back = install_alembic_version(app, "abc123def456")

    try:
        component = _component(app, "Migraciones")
    finally:
        put_back()

    assert component.health is Health.FALLO


def test_a_database_created_without_migrations_needs_attention(app):
    put_back = install_alembic_version(app, None)

    try:
        assert _component(app, "Migraciones").health is Health.ATENCION
    finally:
        put_back()


def test_without_heartbeat_the_scheduler_needs_attention(app):
    component = _component(app, "Planificador")

    assert component.health is Health.ATENCION
    assert "avisos de SLA" in component.summary


def test_a_recent_pass_means_the_scheduler_is_running(app):
    record_heartbeat(_heartbeat_file(app), failures=0, moment=NOW - timedelta(seconds=50))

    component = _component(app, "Planificador")

    assert component.health is Health.BIEN
    assert component.summary == "En marcha: pasó hace menos de un minuto."


def test_a_pass_older_than_the_window_means_it_stopped(app):
    # Con el intervalo de 60 s, la ventana es la mínima: 15 minutos.
    record_heartbeat(_heartbeat_file(app), failures=0, moment=NOW - timedelta(minutes=14))
    assert _component(app, "Planificador").health is Health.BIEN

    record_heartbeat(_heartbeat_file(app), failures=0, moment=NOW - timedelta(minutes=16))
    component = _component(app, "Planificador")

    assert component.health is Health.ATENCION
    assert "parece detenido" in component.summary


def test_a_pass_with_failures_needs_attention(app):
    record_heartbeat(_heartbeat_file(app), failures=3, moment=NOW - timedelta(seconds=30))

    component = _component(app, "Planificador")

    assert component.health is Health.ATENCION
    assert "con fallos" in component.summary


def test_a_disk_almost_full_needs_attention(app, monkeypatch):
    assert _component(app, "Almacenamiento").health is Health.BIEN

    monkeypatch.setattr(status.shutil, "disk_usage", lambda path: shutil._ntuple_diskusage(100, 95, 5))

    assert _component(app, "Almacenamiento").health is Health.ATENCION


def test_without_backups_there_is_a_warning(app):
    component = _component(app, "Respaldos")

    assert component.health is Health.ATENCION
    assert "backup-create" in component.summary


@needs_tools
def test_a_recent_backup_is_fine_and_an_old_one_is_not(app, at_head):
    with app.app_context():
        create_backup(now=MOMENT)

    assert _component(app, "Respaldos", now=MOMENT + timedelta(days=1)).health is Health.BIEN

    old = _component(app, "Respaldos", now=MOMENT + timedelta(days=8))
    assert old.health is Health.ATENCION
    assert "hace 8 días" in old.summary


@needs_tools
def test_a_backup_with_another_signature_needs_attention(app, at_head, monkeypatch):
    with app.app_context():
        create_backup(now=MOMENT)

    monkeypatch.setitem(app.config, "SECRET_KEY", "otra-clave")

    assert "firma" in _component(app, "Respaldos", now=MOMENT).summary


def _write_log(app, name, lines):
    folder = Path(app.config["LOG_DIR"])
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text("".join(line + "\n" for line in lines), encoding="utf-8")


def _log_line(moment, level):
    return f"{moment.astimezone():%Y-%m-%d %H:%M:%S},123 | {level} | workdesk | algo pasó"


def test_only_recent_errors_of_both_logs_are_counted(app):
    assert _component(app, "Errores").health is Health.BIEN

    _write_log(app, "workdesk.log", [
        _log_line(NOW - timedelta(hours=30), "ERROR"),
        _log_line(NOW - timedelta(hours=2), "ERROR"),
        _log_line(NOW - timedelta(hours=1), "WARNING"),
        "Traceback (most recent call last): | ERROR | no es una línea del log",
    ])
    _write_log(app, "scheduler.log", [_log_line(NOW - timedelta(minutes=5), "CRITICAL")])

    component = _component(app, "Errores")

    assert component.health is Health.ATENCION
    assert component.summary.startswith("2 errores registrados")
    assert dict(component.details)["workdesk.log"] == "1"
    assert dict(component.details)["scheduler.log"] == "1"


def test_the_overall_state_is_the_worst_one():
    parts = [status.Component("a", Health.BIEN, ""), status.Component("b", Health.ATENCION, "")]

    assert status.overall(parts) is Health.ATENCION
    assert status.overall([*parts, status.Component("c", Health.FALLO, "")]) is Health.FALLO
    assert status.overall(parts[:1]) is Health.BIEN


# --- Las pantallas ----------------------------------------------------------------------


def test_the_system_screen_shows_every_component(app, admin):
    response = admin.get("/admin/system")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    for name in ("Aplicación", "Base de datos", "Migraciones", "Planificador", "Almacenamiento", "Respaldos", "Errores"):
        assert name in page
    assert "Requiere atención" in page
    assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize("role", ["SUPERVISOR", "TECNICO", "SOLICITANTE"])
@pytest.mark.parametrize("url", ["/admin/system", "/admin/backups"])
def test_only_the_administrator_sees_them(app, client, make_user, role, url):
    login(client, make_user(role, f"{role.lower()}_estado"))

    assert client.get(url).status_code == 403


def test_the_backups_screen_without_backups_says_how_to_make_one(app, admin):
    page = admin.get("/admin/backups").get_data(as_text=True)

    assert "Todavía no hay respaldos" in page
    assert "backup-restore NOMBRE" in page
    assert "La auditoría no registra respaldos ni restauraciones." in page


@needs_tools
def test_the_backups_screen_lists_backups_and_what_the_audit_says(app, admin, at_head):
    with app.app_context():
        good = create_backup(now=MOMENT)

    broken = Path(app.config["BACKUPS_DIR"]) / "workdesk-respaldo-20261120-000000Z.zip"
    broken.write_bytes(b"roto")
    contents = members(good.path)
    del contents["manifest.sig"]
    unsigned = rewrite(Path(app.config["BACKUPS_DIR"]) / "workdesk-respaldo-20261126-000000Z.zip", list(contents.items()))
    (Path(app.config["BACKUPS_DIR"]) / ".tmp-respaldo-cortado").mkdir()

    page = admin.get("/admin/backups").get_data(as_text=True)

    assert page.index(good.path.name) < page.index(unsigned.name) < page.index(broken.name)
    assert "De esta instalación" in page
    assert "No tiene" in page
    assert "Al día" in page
    assert "No se puede leer" in page
    assert ".tmp-respaldo-cortado" in page
    assert "Respaldo creado" in page
    assert "Correcto" in page


def test_the_administration_hub_links_both_screens(app, admin):
    page = admin.get("/admin").get_data(as_text=True)

    assert 'href="/admin/backups"' in page
    assert 'href="/admin/system"' in page
