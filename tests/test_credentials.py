from datetime import UTC, datetime, timedelta

import pytest

from src.workdesk.auth.credentials import (
    CurrentPasswordError,
    change_own_password,
    reset_password,
    set_temporary_password,
)
from src.workdesk.auth.session import load_user
from src.workdesk.extensions import db
from src.workdesk.models import AdminAuditLog, User
from src.workdesk.security import PasswordPolicyError, verify_password

NEW_PASSWORD = "NuevaClaveSegura456!"
TEMPORARY_PASSWORD = "ClaveTemporal789xyz"


def get_user(user_data) -> User:
    return db.session.get(User, user_data["id"])


def audit_entries() -> list[AdminAuditLog]:
    return list(
        db.session.scalars(
            db.select(AdminAuditLog).order_by(AdminAuditLog.id)
        )
    )


def test_change_own_password_updates_credentials(app, make_user):
    user_data = make_user("TECNICO")

    with app.app_context():
        user = get_user(user_data)
        user.debe_cambiar_password = True
        previous_version = user.token_version

        change_own_password(user, user_data["password"], NEW_PASSWORD)
        db.session.commit()

        user = get_user(user_data)

        assert verify_password(user.password_hash, NEW_PASSWORD)
        assert not verify_password(
            user.password_hash,
            user_data["password"],
        )
        assert user.debe_cambiar_password is False
        assert user.token_version == previous_version + 1
        assert user.usuario_modificacion_id == user.id
        assert user.fecha_modificacion is not None


def test_change_own_password_invalidates_existing_sessions(
    app,
    make_user,
):
    user_data = make_user("TECNICO")

    with app.app_context():
        user = get_user(user_data)
        old_session_id = user.get_id()

        change_own_password(user, user_data["password"], NEW_PASSWORD)
        db.session.commit()

        assert load_user(old_session_id) is None
        assert load_user(get_user(user_data).get_id()) is not None


def test_change_own_password_is_audited_without_secrets(app, make_user):
    user_data = make_user("TECNICO")

    with app.app_context():
        user = get_user(user_data)

        change_own_password(user, user_data["password"], NEW_PASSWORD)
        db.session.commit()

        (entry,) = audit_entries()
        stored = f"{entry.valor_anterior} {entry.valor_nuevo} {entry.detalle}"

        assert entry.accion == "PASSWORD_CAMBIADA"
        assert entry.actor_usuario_id == user_data["id"]
        assert entry.entidad_tipo == "usuario"
        assert entry.entidad_id == user_data["id"]
        assert NEW_PASSWORD not in stored
        assert user_data["password"] not in stored
        assert user.password_hash not in stored


def test_change_own_password_rejects_wrong_current_password(
    app,
    make_user,
):
    user_data = make_user("TECNICO")

    with app.app_context():
        user = get_user(user_data)
        original_hash = user.password_hash
        original_version = user.token_version

        with pytest.raises(CurrentPasswordError):
            change_own_password(user, "ClaveIncorrecta000", NEW_PASSWORD)

        assert user.password_hash == original_hash
        assert user.token_version == original_version
        assert audit_entries() == []


def test_change_own_password_rejects_too_short_new_password(
    app,
    make_user,
):
    user_data = make_user("TECNICO")

    with app.app_context():
        user = get_user(user_data)
        original_hash = user.password_hash
        original_version = user.token_version

        with pytest.raises(PasswordPolicyError, match="al menos"):
            change_own_password(user, user_data["password"], "corta")

        assert user.password_hash == original_hash
        assert user.token_version == original_version
        assert audit_entries() == []


def test_change_own_password_rejects_the_same_password(app, make_user):
    user_data = make_user("TECNICO")

    with app.app_context():
        user = get_user(user_data)
        original_hash = user.password_hash
        original_version = user.token_version

        with pytest.raises(PasswordPolicyError, match="distinta"):
            change_own_password(
                user,
                user_data["password"],
                user_data["password"],
            )

        assert user.password_hash == original_hash
        assert user.token_version == original_version
        assert audit_entries() == []


def test_set_temporary_password_marks_mandatory_change(app, make_user):
    user_data = make_user("SOLICITANTE")

    with app.app_context():
        user = get_user(user_data)
        previous_version = user.token_version

        set_temporary_password(user, TEMPORARY_PASSWORD)
        db.session.commit()

        user = get_user(user_data)

        assert verify_password(user.password_hash, TEMPORARY_PASSWORD)
        assert user.debe_cambiar_password is True
        assert user.token_version == previous_version
        assert audit_entries() == []


def test_set_temporary_password_rejects_weak_password(app, make_user):
    user_data = make_user("SOLICITANTE")

    with app.app_context():
        user = get_user(user_data)
        original_hash = user.password_hash

        with pytest.raises(PasswordPolicyError):
            set_temporary_password(user, "corta")

        assert user.password_hash == original_hash
        assert user.debe_cambiar_password is False


def test_reset_password_applies_security_measures(app, make_user):
    admin_data = make_user("ADMINISTRADOR")
    user_data = make_user("TECNICO")

    with app.app_context():
        admin = get_user(admin_data)
        user = get_user(user_data)
        user.intentos_fallidos = 4
        user.bloqueado_hasta = datetime.now(UTC) + timedelta(minutes=10)
        old_session_id = user.get_id()
        previous_version = user.token_version

        reset_password(user, TEMPORARY_PASSWORD, actor=admin)
        db.session.commit()

        user = get_user(user_data)

        assert verify_password(user.password_hash, TEMPORARY_PASSWORD)
        assert user.debe_cambiar_password is True
        assert user.token_version == previous_version + 1
        assert user.intentos_fallidos == 0
        assert user.bloqueado_hasta is None
        assert user.usuario_modificacion_id == admin.id
        assert load_user(old_session_id) is None


def test_reset_password_is_audited_without_secrets(app, make_user):
    admin_data = make_user("ADMINISTRADOR")
    user_data = make_user("TECNICO")

    with app.app_context():
        admin = get_user(admin_data)
        user = get_user(user_data)

        reset_password(user, TEMPORARY_PASSWORD, actor=admin)
        db.session.commit()

        (entry,) = audit_entries()
        stored = f"{entry.valor_anterior} {entry.valor_nuevo} {entry.detalle}"

        assert entry.accion == "PASSWORD_RESTABLECIDA"
        assert entry.actor_usuario_id == admin_data["id"]
        assert entry.entidad_id == user_data["id"]
        assert TEMPORARY_PASSWORD not in stored
        assert user.password_hash not in stored


def test_reset_password_rejects_weak_password_without_changes(
    app,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")
    user_data = make_user("TECNICO")

    with app.app_context():
        admin = get_user(admin_data)
        user = get_user(user_data)
        original_hash = user.password_hash
        original_version = user.token_version

        with pytest.raises(PasswordPolicyError):
            reset_password(user, "corta", actor=admin)

        assert user.password_hash == original_hash
        assert user.token_version == original_version
        assert user.debe_cambiar_password is False
        assert audit_entries() == []
