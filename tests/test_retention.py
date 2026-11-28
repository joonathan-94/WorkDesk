"""La retención (`retention.py`, RF-110 a RF-112, RN-105 a RN-110 y RN-183)."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, insert, select, text, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.workdesk import retention, settings
from src.workdesk.audit import AuditAction
from src.workdesk.backups.package import backup_name, checksum_path
from src.workdesk.extensions import db
from src.workdesk.models import (
    AdminAuditLog,
    Attachment,
    AuthEvent,
    Notificacion,
    Ticket,
    User,
)
from src.workdesk.scheduler import run_once
from tests.ticket_helpers import login

NOW = datetime.now(UTC)
OLD = NOW - timedelta(days=400)
RECENT = NOW - timedelta(days=5)

ALL_SWITCHES = (
    settings.RETENTION_NOTIFICATIONS_ENABLED,
    settings.RETENTION_AUTH_EVENTS_ENABLED,
    settings.RETENTION_DELETED_FILES_ENABLED,
    settings.RETENTION_BACKUPS_ENABLED,
)


def _enable(app, *switches):
    for switch in switches:
        app.config[switch.key] = True


def _run(app):
    with app.app_context():
        return retention.run_retention()


def _audits(app):
    with app.app_context():
        return db.session.scalars(
            select(AdminAuditLog).where(AdminAuditLog.accion == AuditAction.RETENCION_APLICADA)
        ).all()


@pytest.fixture()
def person(app, make_user):
    return make_user("SOLICITANTE", "con_avisos")["id"]


def _notification(app, user_id, *, created, read):
    with app.app_context():
        db.session.execute(
            insert(Notificacion.__table__).values(
                usuario_id=user_id,
                tipo_evento="ESTADO_CAMBIADO",
                mensaje="Tu ticket cambió de estado.",
                leida=read,
                fecha_creacion=created,
                fecha_lectura=created + timedelta(hours=1) if read else None,
            )
        )
        db.session.commit()


def _notifications(app):
    with app.app_context():
        return db.session.execute(
            select(Notificacion.leida, Notificacion.fecha_creacion).order_by(Notificacion.id)
        ).all()


def _auth_event(app, user_id, when):
    with app.app_context():
        db.session.execute(
            insert(AuthEvent.__table__).values(
                usuario_id=user_id, tipo_evento="LOGIN_EXITOSO", resultado="EXITOSO", fecha_hora=when
            )
        )
        db.session.commit()


def _count(app, model):
    with app.app_context():
        return db.session.scalar(select(func.count()).select_from(model))


# --- Nada sin una decisión explícita ----------------------------------------------------


def test_every_policy_starts_switched_off():
    assert all(switch.default is False for switch in ALL_SWITCHES)


def test_with_every_policy_off_nothing_is_deleted(app, person):
    _notification(app, person, created=OLD, read=True)
    _auth_event(app, person, OLD)

    result = _run(app)

    assert result.removed == 0
    assert _count(app, Notificacion) == 1
    assert _count(app, AuthEvent) == 1
    assert _audits(app) == []


# --- Cada política ----------------------------------------------------------------------


def test_only_old_read_notifications_are_deleted(app, person):
    _notification(app, person, created=OLD, read=True)
    _notification(app, person, created=OLD, read=False)
    _notification(app, person, created=RECENT, read=True)
    _enable(app, settings.RETENTION_NOTIFICATIONS_ENABLED)

    result = _run(app)

    assert result.notifications == 1
    remaining = _notifications(app)
    assert [read for read, _ in remaining] == [False, True]
    assert all(read is False or created > NOW - timedelta(days=90) for read, created in remaining)


def test_the_period_is_the_one_in_force(app, person):
    _notification(app, person, created=NOW - timedelta(days=40), read=True)
    _enable(app, settings.RETENTION_NOTIFICATIONS_ENABLED)

    assert _run(app).notifications == 0

    app.config[settings.RETENTION_NOTIFICATIONS_DAYS.key] = 30

    assert _run(app).notifications == 1


def test_old_access_events_are_deleted_and_recent_ones_kept(app, person):
    _auth_event(app, person, OLD)
    _auth_event(app, person, RECENT)
    _enable(app, settings.RETENTION_AUTH_EVENTS_ENABLED)

    assert _run(app).auth_events == 1

    with app.app_context():
        assert db.session.scalar(select(AuthEvent.fecha_hora)) > NOW - timedelta(days=365)


def test_access_events_are_kept_at_least_thirty_days():
    assert settings.RETENTION_AUTH_EVENTS_DAYS.problem(29)
    assert settings.RETENTION_AUTH_EVENTS_DAYS.problem(30) is None


@pytest.fixture()
def deleted_attachment(app, seeded):
    """Un adjunto de la demostración, eliminado hace 400 días, con su archivo en disco."""
    with app.app_context():
        attachment = db.session.scalars(select(Attachment).order_by(Attachment.id)).first()
        db.session.execute(
            update(Attachment.__table__)
            .where(Attachment.__table__.c.id == attachment.id)
            .values(activo=False, fecha_eliminacion=OLD)
        )
        db.session.commit()

        return attachment.id, Path(app.config["UPLOADS_DIR"]) / attachment.ruta_archivo


def test_the_file_of_an_old_deleted_attachment_is_removed_and_its_row_kept(app, deleted_attachment):
    attachment_id, path = deleted_attachment
    others = _count(app, Attachment)
    assert path.is_file()
    _enable(app, settings.RETENTION_DELETED_FILES_ENABLED)

    result = _run(app)

    assert result.files == 1
    assert not path.exists()

    with app.app_context():
        row = db.session.get(Attachment, attachment_id)
        assert row.fecha_purga_archivo is not None
        assert row.fecha_purga_archivo >= row.fecha_eliminacion

    # La fila sigue: el historial del ticket la nombra. Los adjuntos activos no se tocan.
    assert _count(app, Attachment) == others

    with app.app_context():
        for active in db.session.scalars(select(Attachment).where(Attachment.activo)):
            assert (Path(app.config["UPLOADS_DIR"]) / active.ruta_archivo).is_file()

    # Una segunda pasada no vuelve sobre él.
    assert _run(app).files == 0


def test_a_recently_deleted_attachment_keeps_its_file(app, deleted_attachment):
    attachment_id, path = deleted_attachment

    with app.app_context():
        db.session.execute(
            update(Attachment.__table__)
            .where(Attachment.__table__.c.id == attachment_id)
            .values(fecha_eliminacion=RECENT)
        )
        db.session.commit()

    _enable(app, settings.RETENTION_DELETED_FILES_ENABLED)

    assert _run(app).files == 0
    assert path.is_file()


def test_a_file_already_missing_is_still_marked(app, deleted_attachment):
    attachment_id, path = deleted_attachment
    path.unlink()
    _enable(app, settings.RETENTION_DELETED_FILES_ENABLED)

    assert _run(app).files == 1

    with app.app_context():
        assert db.session.get(Attachment, attachment_id).fecha_purga_archivo is not None


def test_the_database_refuses_a_purge_date_on_an_active_attachment(app, seeded):
    with app.app_context():
        table = Attachment.__table__

        with pytest.raises(IntegrityError, match="ck_archivos_purga_coherente"):
            db.session.execute(
                update(table)
                .where(table.c.id == db.session.scalar(select(func.min(table.c.id))))
                .values(fecha_purga_archivo=NOW)
            )

        db.session.rollback()


def _backup_files(app, count):
    folder = Path(app.config["BACKUPS_DIR"])
    folder.mkdir(parents=True, exist_ok=True)
    paths = []

    for days in range(count):
        path = folder / backup_name(NOW - timedelta(days=days))
        path.write_bytes(b"respaldo")
        checksum_path(path).write_text("huella", encoding="ascii")
        paths.append(path)

    (folder / "notas.txt").write_text("no es un respaldo", encoding="utf-8")

    return paths  # del más reciente al más antiguo


def test_only_the_newest_backups_are_kept(app):
    paths = _backup_files(app, 4)
    app.config[settings.RETENTION_BACKUPS_KEEP.key] = 2
    _enable(app, settings.RETENTION_BACKUPS_ENABLED)

    assert _run(app).backups == 2

    folder = Path(app.config["BACKUPS_DIR"])
    assert sorted(p.name for p in folder.iterdir()) == sorted(
        [paths[0].name, f"{paths[0].name}.sha256", paths[1].name, f"{paths[1].name}.sha256", "notas.txt"]
    )


def test_at_least_one_backup_is_always_kept():
    assert settings.RETENTION_BACKUPS_KEEP.problem(0)


# --- Cómo se aplica ---------------------------------------------------------------------


def test_a_large_backlog_is_deleted_in_batches(app, person, monkeypatch):
    for _ in range(5):
        _notification(app, person, created=OLD, read=True)

    monkeypatch.setattr(retention, "BATCH_SIZE", 2)
    _enable(app, settings.RETENTION_NOTIFICATIONS_ENABLED)

    assert [_run(app).notifications for _ in range(4)] == [2, 2, 1, 0]


def test_each_pass_that_deletes_is_audited_as_a_system_action(app, person):
    _notification(app, person, created=OLD, read=True)
    _auth_event(app, person, OLD)
    _enable(app, *ALL_SWITCHES)

    _run(app)
    (event,) = _audits(app)

    assert event.actor_usuario_id is None
    assert event.valor_nuevo == {"notificaciones": 1, "accesos": 1, "archivos": 0, "respaldos": 0}

    _run(app)

    assert len(_audits(app)) == 1


def test_a_failing_policy_does_not_stop_the_others(app, person, monkeypatch):
    _notification(app, person, created=OLD, read=True)
    _auth_event(app, person, OLD)
    _enable(app, *ALL_SWITCHES)
    real = retention._apply

    def fail_notifications(policy, now):
        if policy is retention.NOTIFICATIONS:
            raise SQLAlchemyError("la tabla no responde")
        return real(policy, now)

    monkeypatch.setattr(retention, "_apply", fail_notifications)

    result = _run(app)

    assert result.failures == 1
    assert result.auth_events == 1
    assert _count(app, Notificacion) == 1


def test_what_the_screen_announces_is_what_a_pass_deletes(app, person, deleted_attachment):
    """La vista previa y el borrado usan las mismas condiciones: lo anunciado es lo que se
    borra, política por política."""
    _notification(app, person, created=OLD, read=True)
    _notification(app, person, created=OLD, read=False)
    _auth_event(app, person, OLD)
    _auth_event(app, person, RECENT)
    _backup_files(app, 3)
    app.config[settings.RETENTION_BACKUPS_KEEP.key] = 1

    with app.app_context():
        announced = {state.policy.key: state.pending for state in retention.retention_overview()}

    _enable(app, *ALL_SWITCHES)
    result = _run(app)

    assert announced == {
        "notificaciones": result.notifications,
        "accesos": result.auth_events,
        "archivos": result.files,
        "respaldos": result.backups,
    } == {"notificaciones": 1, "accesos": 1, "archivos": 1, "respaldos": 2}


def test_tickets_history_and_audit_are_never_touched(app, seeded, person):
    _enable(app, *ALL_SWITCHES)

    with app.app_context():
        tickets = db.session.scalar(select(func.count()).select_from(Ticket))
        history = db.session.scalar(text("SELECT count(*) FROM historial_ticket"))
        users = db.session.scalar(select(func.count()).select_from(User))

    _run(app)

    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(Ticket)) == tickets
        assert db.session.scalar(text("SELECT count(*) FROM historial_ticket")) == history
        assert db.session.scalar(select(func.count()).select_from(User)) == users


def test_the_scheduler_applies_retention_in_each_pass(app, person):
    _notification(app, person, created=OLD, read=True)
    _enable(app, settings.RETENTION_NOTIFICATIONS_ENABLED)

    with app.app_context():
        result = run_once()

    assert result.retained == 1
    assert _count(app, Notificacion) == 0


def test_the_scheduler_command_reports_what_retention_deleted(app, person):
    _notification(app, person, created=OLD, read=True)
    _enable(app, settings.RETENTION_NOTIFICATIONS_ENABLED)

    output = app.test_cli_runner().invoke(args=["run-scheduler", "--once"]).output

    assert "Retención: 1 elemento eliminado." in output


# --- La pantalla ------------------------------------------------------------------------


@pytest.fixture()
def admin(client, make_user):
    login(client, make_user("ADMINISTRADOR", "admin_retencion"))
    return client


def test_the_screen_shows_each_policy_what_it_would_delete_and_what_is_always_kept(app, admin, person):
    _notification(app, person, created=OLD, read=True)

    page = admin.get("/admin/settings/retencion").get_data(as_text=True)

    for policy in retention.POLICIES:
        assert policy.label in page
    assert "Se eliminaría hoy" in page
    assert 'data-policy="notificaciones">1<' in page
    assert "Se conservan siempre" in page
    assert "Tickets, su historial y la auditoría" in page


def test_switching_a_policy_on_is_audited(app, admin):
    page = admin.get("/admin/settings/retencion").get_data(as_text=True)
    token = page.split('name="base" type="hidden" value="')[1].split('"')[0]
    data = {
        "base": token,
        settings.RETENTION_NOTIFICATIONS_ENABLED.key: "y",
        settings.RETENTION_NOTIFICATIONS_DAYS.key: "60",
        settings.RETENTION_AUTH_EVENTS_DAYS.key: "365",
        settings.RETENTION_DELETED_FILES_DAYS.key: "90",
        settings.RETENTION_BACKUPS_KEEP.key: "14",
        "motivo": "Limpieza trimestral",
    }

    response = admin.post("/admin/settings/retencion", data=data)

    assert response.status_code == 302

    with app.app_context():
        changed = db.session.scalars(
            select(AdminAuditLog.detalle).where(AdminAuditLog.accion == AuditAction.CONFIGURACION_MODIFICADA)
        ).all()

    assert set(changed) >= {
        settings.RETENTION_NOTIFICATIONS_ENABLED.table_key,
        settings.RETENTION_NOTIFICATIONS_DAYS.table_key,
    }
