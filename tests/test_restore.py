"""Restaurar un respaldo (`backups/restore.py`, RF-128, RNF-041, RNF-042, RN-182).

Restaura de verdad, con `pg_restore` y `psql`, sobre el esquema de la base de pruebas: borra
sus tablas y las vuelve a crear desde el volcado. Por eso cada test empieza con un respaldo
real y comprueba lo que queda en la base y en el disco.
"""

import json
import shutil
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select, text

from src.workdesk.audit import AuditAction, AuditResult
from src.workdesk.backups import BackupError, create_backup, package, restore
from src.workdesk.backups.package import Signature
from src.workdesk.backups.restore import RestoreRefused, plan_restore, restore_backup
from src.workdesk.extensions import db
from src.workdesk.models import AdminAuditLog, Attachment, Ticket, User
from src.workdesk.system.migrations import RevisionMatch, code_heads, known_revisions
from tests.backup_helpers import (
    MOMENT,
    install_alembic_version,
    members,
    needs_tools,
    resigned,
    rewrite,
)
from tests.ticket_helpers import login

pytestmark = needs_tools

HEAD = ",".join(sorted(code_heads()))
LATER = MOMENT + timedelta(minutes=5)


@pytest.fixture()
def at_head(app):
    """La base como la deja `db upgrade`: con la revisión que espera el código."""
    put_back = install_alembic_version(app, HEAD)
    yield
    put_back()


def _backup(app, moment=MOMENT):
    with app.app_context():
        return create_backup(now=moment)


def _plan(app, path, **options):
    with app.app_context():
        return plan_restore(path, **options)


def _restore(app, path, *, plan_options=None, **options):
    options.setdefault("ignore_connections", True)

    with app.app_context():
        plan = plan_restore(path, **(plan_options or {}))
        return restore_backup(plan, now=LATER, **options)


def _state(app):
    """Lo que la restauración debe devolver: filas de la base y archivos del disco."""
    uploads = Path(app.config["UPLOADS_DIR"])

    with app.app_context():
        return {
            "tickets": db.session.scalar(select(func.count()).select_from(Ticket)),
            "usernames": sorted(db.session.scalars(select(User.username))),
            "attachments": sorted(db.session.scalars(select(Attachment.ruta_archivo))),
            "files": sorted(p.relative_to(uploads).as_posix() for p in uploads.rglob("*") if p.is_file()),
        }


def _change_everything(app, make_user):
    """Lo que pasa después del respaldo: una cuenta nueva, un adjunto que se pierde y un
    archivo suelto en el disco."""
    make_user("SOLICITANTE", "despues_del_respaldo")
    uploads = Path(app.config["UPLOADS_DIR"])

    with app.app_context():
        first = db.session.scalars(select(Attachment.ruta_archivo).order_by(Attachment.id)).first()

    (uploads / first).unlink()
    (uploads / "suelto.txt").write_bytes(b"llegado despues")


def test_a_restore_brings_back_the_database_and_the_attachments_exactly(app, seeded, at_head, make_user):
    backup = _backup(app)
    before = _state(app)
    _change_everything(app, make_user)
    assert _state(app) != before

    result = _restore(app, backup.path)

    assert _state(app) == before
    assert result.attachments == len(before["attachments"])
    assert result.safety_backup is not None
    assert not result.plan.needs_upgrade

    with app.app_context():
        assert db.session.scalar(text("SELECT version_num FROM alembic_version")) == HEAD


def _restore_events(app):
    with app.app_context():
        return db.session.scalars(
            select(AdminAuditLog)
            .where(AdminAuditLog.accion == AuditAction.RESPALDO_RESTAURADO)
            .order_by(AdminAuditLog.id)
        ).all()


def _dot_folders(app) -> list[str]:
    """Las carpetas de trabajo de una restauración que quedaron junto a los adjuntos."""
    return [p.name for p in Path(app.config["UPLOADS_DIR"]).parent.iterdir() if p.name.startswith(".")]


def test_every_session_ends_because_accounts_now_are_the_backup_ones(app, client, seeded, at_head, make_user):
    person = make_user("SOLICITANTE", "con_sesion_abierta")
    login(client, person)
    assert client.get("/dashboard").status_code == 200
    backup = _backup(app)

    with app.app_context():
        versions = dict(db.session.execute(select(User.username, User.token_version)).all())

    _restore(app, backup.path)

    with app.app_context():
        after = dict(db.session.execute(select(User.username, User.token_version)).all())

    assert after == {username: version + 1 for username, version in versions.items()}
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_the_restore_is_audited_and_the_previous_state_is_kept_in_a_backup(app, seeded, at_head, make_user):
    backup = _backup(app)
    _change_everything(app, make_user)
    changed = _state(app)

    result = _restore(app, backup.path)
    (event,) = _restore_events(app)

    assert event.resultado == AuditResult.EXITOSO
    assert event.actor_usuario_id is None
    assert event.detalle == backup.path.name
    assert event.valor_nuevo["sha256"] == backup.sha256
    assert event.valor_nuevo["firma"] == Signature.VALIDA
    assert event.valor_nuevo["respaldo_previo"] == result.safety_backup.path.name
    assert event.valor_nuevo["adjuntos_restaurados"] == result.attachments
    assert "usuario_sistema" in event.valor_nuevo

    # El respaldo previo trae lo que había justo antes de restaurar.
    previous = json.loads(members(result.safety_backup.path)[package.MANIFEST_MEMBER])
    assert previous["contenido"]["usuarios"] == len(changed["usernames"])

    # No quedan carpetas de trabajo ni los adjuntos anteriores (están en el respaldo previo).
    assert _dot_folders(app) == []
    assert not any(p.name.startswith(restore.WORKSPACE_PREFIX) for p in Path(app.config["BACKUPS_DIR"]).iterdir())


def test_if_anything_fails_the_database_and_the_files_stay_as_they_were(app, seeded, at_head, make_user, monkeypatch):
    """Los borrados, el volcado y el cierre de sesiones van en una sola transacción: un fallo
    en la última sentencia deshace también las primeras."""
    backup = _backup(app)
    _change_everything(app, make_user)
    changed = _state(app)
    monkeypatch.setattr(restore, "post_restore_sql", lambda schema: "SELECT 1 / 0;\n")

    with pytest.raises(BackupError, match="No se restauró nada"):
        _restore(app, backup.path)

    assert _state(app) == changed
    assert _dot_folders(app) == []
    assert [event.resultado for event in _restore_events(app)] == [AuditResult.FALLIDO]


def test_a_package_changed_after_checking_it_is_not_restored(app, seeded, at_head, make_user):
    backup = _backup(app)
    _change_everything(app, make_user)
    changed = _state(app)
    plan = _plan(app, backup.path)

    contents = members(backup.path)
    name = next(n for n in contents if n.startswith("uploads/"))
    contents[name] = contents[name][:-1] + bytes([contents[name][-1] ^ 1])
    rewrite(backup.path, list(contents.items()))

    with app.app_context(), pytest.raises(BackupError, match="cambió desde que se comprobó"):
        restore_backup(plan, now=LATER, ignore_connections=True)

    assert _state(app) == changed
    assert _dot_folders(app) == []


def test_an_altered_backup_is_refused_before_touching_anything(app, seeded, at_head, make_user):
    backup = _backup(app)
    contents = members(backup.path)
    name = next(n for n in contents if n.startswith("uploads/"))
    contents[name] += b"!"
    rewrite(backup.path, list(contents.items()))
    _change_everything(app, make_user)
    changed = _state(app)

    with pytest.raises(RestoreRefused) as refused:
        _plan(app, backup.path)

    assert any("tamaño" in problem for problem in refused.value.problems)
    assert _state(app) == changed
    assert sorted(p.name for p in Path(app.config["BACKUPS_DIR"]).iterdir()) == [
        backup.path.name,
        f"{backup.path.name}.sha256",
    ]


def test_a_backup_signed_with_another_key_needs_to_be_accepted_expressly(app, seeded, at_head, monkeypatch):
    backup = _backup(app)
    monkeypatch.setitem(app.config, "SECRET_KEY", "la-clave-nueva-tras-rotarla")

    with pytest.raises(RestoreRefused, match="firma no corresponde"):
        _plan(app, backup.path)

    result = _restore(app, backup.path, plan_options={"accept_other_key": True})

    assert result.plan.signature is Signature.OTRA_CLAVE
    assert _restore_events(app)[-1].valor_nuevo["firma"] == Signature.OTRA_CLAVE


def test_a_backup_without_signature_is_never_restored(app, seeded, at_head):
    backup = _backup(app)
    contents = members(backup.path)
    del contents[package.SIGNATURE_MEMBER]
    rewrite(backup.path, list(contents.items()))

    with pytest.raises(RestoreRefused, match="No tiene firma"):
        _plan(app, backup.path, accept_other_key=True)


@pytest.fixture()
def unknown_revision(app):
    put_back = install_alembic_version(app, "abc123def456")
    yield
    put_back()


def test_a_backup_from_a_newer_version_is_refused(app, unknown_revision):
    backup = _backup(app)

    with pytest.raises(RestoreRefused, match="no conoce"):
        _plan(app, backup.path)


@pytest.fixture()
def without_revision(app):
    put_back = install_alembic_version(app, None)
    yield
    put_back()


def test_a_backup_without_migrations_is_refused(app, without_revision):
    backup = _backup(app)

    with pytest.raises(RestoreRefused, match="no tiene revisión"):
        _plan(app, backup.path)


@pytest.fixture()
def older_revision(app):
    older = min(known_revisions() - code_heads())
    put_back = install_alembic_version(app, older)
    yield older
    put_back()


def test_a_backup_from_an_older_version_is_restored_and_asks_for_db_upgrade(app, older_revision):
    backup = _backup(app)

    result = _restore(app, backup.path)

    assert result.plan.revision is RevisionMatch.ANTERIOR
    assert result.plan.needs_upgrade

    with app.app_context():
        assert db.session.scalar(text("SELECT version_num FROM alembic_version")) == older_revision


def test_a_backup_of_another_schema_is_refused(app, at_head):
    backup = _backup(app)
    contents = members(backup.path)
    manifest = json.loads(contents[package.MANIFEST_MEMBER])
    manifest["base_de_datos"]["esquema"] = "otro_esquema"
    rewrite(backup.path, list(resigned(contents, manifest).items()))

    with pytest.raises(RestoreRefused, match="otro_esquema"):
        _plan(app, backup.path)


def test_nobody_else_may_be_connected(app, at_head):
    backup = _backup(app)

    with app.app_context():
        plan = plan_restore(backup.path)

        with db.engine.connect() as somebody_else:
            somebody_else.execute(text("SELECT 1"))

            with pytest.raises(RestoreRefused, match="conexiones más"):
                restore_backup(plan, now=LATER)

    assert _restore_events(app) == []


def test_without_a_safety_backup_the_previous_attachments_are_kept_aside(app, seeded, at_head, make_user):
    backup = _backup(app)
    _change_everything(app, make_user)

    result = _restore(app, backup.path, safety_backup=False)

    uploads = Path(app.config["UPLOADS_DIR"])
    kept = [p for p in uploads.parent.iterdir() if p.name.startswith(restore.PREVIOUS_PREFIX)]

    assert result.safety_backup is None
    assert len(kept) == 1
    assert (kept[0] / "suelto.txt").read_bytes() == b"llegado despues"
    assert any(str(kept[0]) in warning for warning in result.warnings)
    assert sorted(p.name for p in Path(app.config["BACKUPS_DIR"]).iterdir()) == [
        backup.path.name,
        f"{backup.path.name}.sha256",
    ]
    shutil.rmtree(kept[0])


def test_the_schema_itself_is_not_recreated_only_what_is_inside():
    listing = (
        ";\n"
        "; Selected TOC Entries:\n"
        "4; 2615 2200 SCHEMA - public pg_database_owner\n"
        "5614; 0 0 COMMENT - SCHEMA public pg_database_owner\n"
        "219; 1259 16390 TABLE public alembic_version workdesk_app\n"
        "258; 1259 10974819 TABLE public archivos workdesk_app\n"
    )
    kept = [line for line in listing.splitlines() if not restore._SCHEMA_ENTRY.match(line)]

    assert not any("SCHEMA" in line for line in kept)
    assert sum("TABLE" in line for line in kept) == 2


def test_the_sessions_statement_quotes_the_schema():
    expected = 'UPDATE "raro""; DROP".usuarios SET token_version = token_version + 1;\n'

    assert restore.post_restore_sql('raro"; DROP') == expected


# --- El comando -------------------------------------------------------------------------


def _run(app, *arguments, input=None):
    return app.test_cli_runner().invoke(args=list(arguments), input=input)


def _database(app) -> str:
    with app.app_context():
        return db.session.scalar(text("SELECT current_database()"))


def test_the_command_asks_for_the_database_name_before_anything(app, seeded, at_head, make_user):
    backup = _backup(app)
    _change_everything(app, make_user)
    changed = _state(app)

    result = _run(app, "backup-restore", backup.path.name, "--ignore-connections", input="workdesk_dev\n")

    assert result.exit_code == 1
    assert "Se reemplazará" in result.output
    assert "El nombre no coincide. No se restauró nada." in result.output
    assert _state(app) == changed


def test_the_command_restores_after_confirming(app, seeded, at_head, make_user):
    backup = _backup(app)
    before = _state(app)
    _change_everything(app, make_user)

    result = _run(app, "backup-restore", backup.path.name, "--ignore-connections", input=f"{_database(app)}\n")

    assert result.exit_code == 0, result.output
    assert "Antes se creará un respaldo de lo actual." in result.output
    assert "Respaldo previo de lo que había:" in result.output
    assert "Todas las sesiones se cerraron" in result.output
    assert _state(app) == before


def test_the_command_lists_why_a_backup_cannot_be_restored(app, at_head):
    backup = _backup(app)
    contents = members(backup.path)
    del contents[package.SIGNATURE_MEMBER]
    rewrite(backup.path, list(contents.items()))

    result = _run(app, "backup-restore", backup.path.name)

    assert result.exit_code == 1
    assert "Problema: No tiene firma" in result.output
    assert "No se restauró nada." in result.output

def test_an_empty_attachments_folder_is_not_kept_aside(app, seeded, at_head):
    """Una instalación nueva no tiene adjuntos que conservar: ni carpeta apartada ni aviso."""
    backup = _backup(app)
    uploads = Path(app.config["UPLOADS_DIR"])
    shutil.rmtree(uploads)
    uploads.mkdir()

    result = _restore(app, backup.path, safety_backup=False)

    assert result.warnings == []
    assert _dot_folders(app) == []
    assert result.attachments == len([p for p in uploads.rglob("*") if p.is_file()])
