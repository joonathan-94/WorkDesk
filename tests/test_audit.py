import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from src.workdesk.audit import (
    AuditAction,
    AuditResult,
    record_admin_event,
)
from src.workdesk.extensions import db
from src.workdesk.models import AdminAuditLog, User
from src.workdesk.models.admin_audit_log import AuditLogImmutableError


def load_user(user_data):
    return db.session.get(User, user_data["id"])


def count_entries() -> int:
    return db.session.scalar(
        db.select(db.func.count()).select_from(AdminAuditLog)
    )


def test_records_event_performed_by_a_user(app, make_user):
    admin = make_user("ADMINISTRADOR")
    target = make_user("TECNICO")

    with app.app_context():
        entry = record_admin_event(
            AuditAction.CAMBIO_ROL,
            actor=load_user(admin),
            entity_type="usuario",
            entity_id=target["id"],
            old_value={"rol": "TECNICO"},
            new_value={"rol": "SUPERVISOR"},
            reason="Promoción interna.",
        )
        db.session.commit()

        saved = db.session.get(AdminAuditLog, entry.id)

        assert saved.actor_usuario_id == admin["id"]
        assert saved.actor_tipo == "USUARIO"
        assert saved.accion == "CAMBIO_ROL"
        assert saved.entidad_tipo == "usuario"
        assert saved.entidad_id == target["id"]
        assert saved.valor_anterior == {"rol": "TECNICO"}
        assert saved.valor_nuevo == {"rol": "SUPERVISOR"}
        assert saved.motivo == "Promoción interna."
        assert saved.resultado == "EXITOSO"
        assert saved.fecha_hora is not None


def test_records_event_performed_by_the_system(app):
    with app.app_context():
        entry = record_admin_event(
            AuditAction.USUARIO_DESACTIVADO,
            actor=None,
            entity_type="usuario",
            entity_id=1,
            result=AuditResult.FALLIDO,
        )
        db.session.commit()

        saved = db.session.get(AdminAuditLog, entry.id)

        assert saved.actor_tipo == "SISTEMA"
        assert saved.actor_usuario_id is None
        assert saved.resultado == "FALLIDO"


def test_captures_request_origin_when_inside_a_request(app):
    with app.test_request_context(
        "/",
        headers={"User-Agent": "pytest-agent"},
        environ_base={"REMOTE_ADDR": "10.0.0.5"},
    ):
        entry = record_admin_event(AuditAction.USUARIO_CREADO, actor=None)

        assert entry.ip_origen == "10.0.0.5"
        assert entry.user_agent == "pytest-agent"


def test_origin_is_empty_outside_a_request(app):
    with app.app_context():
        entry = record_admin_event(AuditAction.USUARIO_CREADO, actor=None)

        assert entry.ip_origen is None
        assert entry.user_agent is None


def test_user_agent_is_truncated_to_column_length(app):
    with app.test_request_context(
        "/",
        headers={"User-Agent": "a" * 1000},
    ):
        entry = record_admin_event(AuditAction.USUARIO_CREADO, actor=None)
        db.session.commit()

        assert len(entry.user_agent) == 255


def test_event_is_not_committed_by_the_service(app):
    with app.app_context():
        record_admin_event(AuditAction.USUARIO_CREADO, actor=None)
        db.session.rollback()

        assert count_entries() == 0


def test_rejects_actions_outside_the_controlled_vocabulary(app):
    with app.app_context():
        with pytest.raises(ValueError):
            record_admin_event("BORRAR_TODO", actor=None)

        assert count_entries() == 0


def test_rejects_entity_id_without_entity_type(app):
    with (
        app.app_context(),
        pytest.raises(ValueError, match="entity_type"),
    ):
        record_admin_event(
            AuditAction.USUARIO_MODIFICADO,
            actor=None,
            entity_id=7,
        )


@pytest.mark.parametrize(
    "sensitive_key",
    ["password", "password_hash", "contraseña", "access_token", "SECRET_KEY"],
)
def test_rejects_sensitive_keys_in_values(app, sensitive_key):
    with app.app_context():
        with pytest.raises(ValueError, match="datos sensibles"):
            record_admin_event(
                AuditAction.PASSWORD_RESTABLECIDA,
                actor=None,
                new_value={sensitive_key: "dato"},
            )

        assert count_entries() == 0


def test_rejects_sensitive_keys_in_nested_values(app):
    with (
        app.app_context(),
        pytest.raises(ValueError, match="datos sensibles"),
    ):
        record_admin_event(
            AuditAction.USUARIO_MODIFICADO,
            actor=None,
            old_value={"datos": [{"password": "x"}]},
        )


def test_allows_token_version_counter(app):
    with app.app_context():
        entry = record_admin_event(
            AuditAction.PASSWORD_RESTABLECIDA,
            actor=None,
            old_value={"token_version": 1},
            new_value={"token_version": 2},
        )

        assert entry.valor_nuevo == {"token_version": 2}


def test_audit_entries_cannot_be_updated(app):
    with app.app_context():
        entry = record_admin_event(AuditAction.USUARIO_CREADO, actor=None)
        db.session.commit()

        entry.detalle = "alterado"

        with pytest.raises(AuditLogImmutableError):
            db.session.commit()

        db.session.rollback()


def test_audit_entries_cannot_be_deleted(app):
    with app.app_context():
        entry = record_admin_event(AuditAction.USUARIO_CREADO, actor=None)
        db.session.commit()

        db.session.delete(entry)

        with pytest.raises(AuditLogImmutableError):
            db.session.commit()

        db.session.rollback()

        assert count_entries() == 1


@pytest.mark.parametrize(
    "invalid_fields",
    [
        {"actor_tipo": "OTRO"},
        {"actor_tipo": "USUARIO", "actor_usuario_id": None},
        {"actor_tipo": "SISTEMA", "actor_usuario_id": 1},
        {"actor_tipo": "SISTEMA", "resultado": "PENDIENTE"},
        {"actor_tipo": "SISTEMA", "entidad_id": 5, "entidad_tipo": None},
    ],
)
def test_database_rejects_inconsistent_entries(
    app,
    make_user,
    invalid_fields,
):
    make_user("ADMINISTRADOR")

    fields = {
        "actor_tipo": "SISTEMA",
        "accion": "USUARIO_CREADO",
        **invalid_fields,
    }

    with app.app_context():
        db.session.add(AdminAuditLog(**fields))

        with pytest.raises(IntegrityError):
            db.session.commit()

        db.session.rollback()


def test_actor_must_reference_an_existing_user(app):
    with app.app_context():
        db.session.add(
            AdminAuditLog(
                actor_tipo="USUARIO",
                actor_usuario_id=999999,
                accion="USUARIO_CREADO",
            )
        )

        with pytest.raises(IntegrityError):
            db.session.commit()

        db.session.rollback()


def test_table_has_the_documented_indexes(app):
    with app.app_context():
        index_names = {
            index["name"]
            for index in inspect(db.engine).get_indexes(
                "auditoria_administrativa"
            )
        }

    assert {
        "ix_auditoria_administrativa_fecha_hora",
        "ix_auditoria_administrativa_actor_fecha",
        "ix_auditoria_administrativa_entidad",
    } <= index_names
