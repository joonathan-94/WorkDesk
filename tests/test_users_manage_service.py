from datetime import UTC, datetime, timedelta

import pytest

from src.workdesk.auth.session import load_user
from src.workdesk.extensions import db
from src.workdesk.models import AdminAuditLog, User
from src.workdesk.security import PasswordPolicyError, verify_password
from src.workdesk.users import service
from src.workdesk.users.service import (
    DuplicateUserError,
    LastAdministratorError,
    NothingToChangeError,
    SelfProtectionError,
    UnknownRoleError,
    activate_user,
    change_role,
    deactivate_user,
    reset_user_password,
    update_profile,
)

TEMPORARY_PASSWORD = "ClaveTemporal789xyz"


def get(user_data) -> User:
    return db.session.get(User, user_data["id"])


def audit_entries() -> list[AdminAuditLog]:
    return list(
        db.session.scalars(db.select(AdminAuditLog).order_by(AdminAuditLog.id))
    )


def profile_data(user: User, **overrides):
    data = {
        "nombre": user.nombre,
        "apellido": user.apellido,
        "email": user.email,
        "telefono": user.telefono,
        "cargo": user.cargo,
        "departamento_area": user.departamento_area,
    }
    data.update(overrides)

    return data


# --- Datos personales -------------------------------------------------


def test_update_profile_changes_only_what_was_modified(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")
    target_data = make_user("TECNICO")

    with app.app_context():
        admin = get(admin_data)
        target = get(target_data)
        username = target.username

        changed = update_profile(
            target,
            actor=admin,
            **profile_data(target, nombre="Silvio", cargo="Consigliere"),
        )
        db.session.commit()

        target = get(target_data)

        assert changed is True
        assert target.nombre == "Silvio"
        assert target.cargo == "Consigliere"
        assert target.username == username
        assert target.usuario_modificacion_id == admin.id
        assert target.fecha_modificacion is not None

        (entry,) = audit_entries()

        assert entry.accion == "USUARIO_MODIFICADO"
        assert entry.actor_usuario_id == admin.id
        assert entry.entidad_id == target.id
        assert entry.valor_anterior == {
            "nombre": "Tecnico",
            "cargo": None,
        }
        assert entry.valor_nuevo == {
            "nombre": "Silvio",
            "cargo": "Consigliere",
        }


def test_update_profile_without_changes_does_nothing(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")
    target_data = make_user("TECNICO")

    with app.app_context():
        target = get(target_data)

        changed = update_profile(
            target,
            actor=get(admin_data),
            **profile_data(target),
        )
        db.session.commit()

        assert changed is False
        assert get(target_data).fecha_modificacion is None
        assert audit_entries() == []


def test_update_profile_normalizes_the_input(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")
    target_data = make_user("TECNICO")

    with app.app_context():
        target = get(target_data)
        target.telefono = "123"
        db.session.commit()

        update_profile(
            target,
            actor=get(admin_data),
            **profile_data(
                target,
                nombre="  Tony  ",
                email="  TONY@WorkDesk.Local ",
                telefono="   ",
            ),
        )

        assert target.nombre == "Tony"
        assert target.email == "tony@workdesk.local"
        assert target.telefono is None


def test_update_profile_rejects_the_email_of_another_user(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")
    target_data = make_user("TECNICO")

    with app.app_context():
        admin = get(admin_data)
        target = get(target_data)
        original_email = target.email

        with pytest.raises(DuplicateUserError) as error:
            update_profile(
                target,
                actor=admin,
                **profile_data(target, email=admin.email.upper()),
            )

        assert error.value.field == "email"
        assert target.email == original_email
        assert audit_entries() == []


def test_update_profile_allows_keeping_the_own_email_in_other_case(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")
    target_data = make_user("TECNICO")

    with app.app_context():
        target = get(target_data)

        update_profile(
            target,
            actor=get(admin_data),
            **profile_data(target, email=target.email.upper(), cargo="X"),
        )

        assert target.cargo == "X"


def test_update_profile_recovers_from_an_email_race(
    app,
    seeded_roles,
    make_user,
    monkeypatch,
):
    """Si dos ediciones pasan la comprobación, gana la restricción UNIQUE."""
    admin_data = make_user("ADMINISTRADOR")
    target_data = make_user("TECNICO")

    with app.app_context():
        admin = get(admin_data)
        target = get(target_data)

        monkeypatch.setattr(
            service,
            "_is_in_use",
            lambda column, value, *, exclude_id=None: False,
        )

        with pytest.raises(DuplicateUserError) as error:
            update_profile(
                target,
                actor=admin,
                **profile_data(target, email=admin.email),
            )

        assert error.value.field == "email"

        # La sesión sigue siendo utilizable y no quedó auditoría.
        monkeypatch.undo()
        db.session.rollback()

        assert audit_entries() == []


# --- Cambio de rol ----------------------------------------------------


def test_change_role_updates_role_and_invalidates_sessions(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")
    target_data = make_user("TECNICO")

    with app.app_context():
        admin = get(admin_data)
        target = get(target_data)
        old_session_id = target.get_id()
        previous_version = target.token_version

        change_role(
            target,
            "SUPERVISOR",
            actor=admin,
            reason="  Ascenso interno.  ",
        )
        db.session.commit()

        target = get(target_data)

        assert target.rol.codigo == "SUPERVISOR"
        assert target.token_version == previous_version + 1
        assert target.usuario_modificacion_id == admin.id
        assert load_user(old_session_id) is None
        assert load_user(target.get_id()) is not None

        (entry,) = audit_entries()

        assert entry.accion == "CAMBIO_ROL"
        assert entry.valor_anterior == {"rol": "TECNICO"}
        assert entry.valor_nuevo == {"rol": "SUPERVISOR"}
        assert entry.motivo == "Ascenso interno."


def test_change_role_blank_reason_is_stored_as_none(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")
    target_data = make_user("TECNICO")

    with app.app_context():
        change_role(
            get(target_data),
            "SOLICITANTE",
            actor=get(admin_data),
            reason="   ",
        )

        (entry,) = audit_entries()

        assert entry.motivo is None


def test_change_role_cannot_target_oneself(app, seeded_roles, make_user):
    admin_data = make_user("ADMINISTRADOR")

    with app.app_context():
        admin = get(admin_data)

        with pytest.raises(SelfProtectionError):
            change_role(admin, "TECNICO", actor=admin)

        assert admin.rol.codigo == "ADMINISTRADOR"
        assert audit_entries() == []


def test_change_role_rejects_the_current_role(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")
    target_data = make_user("TECNICO")

    with app.app_context(), pytest.raises(NothingToChangeError):
        change_role(get(target_data), "TECNICO", actor=get(admin_data))


def test_change_role_rejects_an_unknown_role(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")
    target_data = make_user("TECNICO")

    with app.app_context(), pytest.raises(UnknownRoleError):
        change_role(get(target_data), "SUPERADMIN", actor=get(admin_data))


def test_change_role_protects_the_last_active_administrator(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")
    supervisor_data = make_user("SUPERVISOR")

    with app.app_context():
        admin = get(admin_data)

        with pytest.raises(LastAdministratorError):
            change_role(
                admin,
                "TECNICO",
                actor=get(supervisor_data),
            )

        assert admin.rol.codigo == "ADMINISTRADOR"
        assert audit_entries() == []


def test_change_role_allows_demoting_an_administrator_if_another_remains(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")
    other_data = make_user("ADMINISTRADOR", username="admin_dos")

    with app.app_context():
        change_role(get(other_data), "TECNICO", actor=get(admin_data))

        assert get(other_data).rol.codigo == "TECNICO"


def test_inactive_administrators_do_not_count_as_remaining(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")
    make_user("ADMINISTRADOR", username="admin_inactivo", activo=False)
    supervisor_data = make_user("SUPERVISOR")

    with app.app_context(), pytest.raises(LastAdministratorError):
        change_role(
            get(admin_data),
            "TECNICO",
            actor=get(supervisor_data),
        )


def test_change_role_can_promote_to_administrator(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")
    target_data = make_user("TECNICO")

    with app.app_context():
        change_role(
            get(target_data),
            "ADMINISTRADOR",
            actor=get(admin_data),
        )

        assert get(target_data).rol.codigo == "ADMINISTRADOR"


# --- Desactivación y reactivación -------------------------------------


def test_deactivate_user_blocks_access_and_keeps_history(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")
    target_data = make_user("TECNICO")

    with app.app_context():
        admin = get(admin_data)
        target = get(target_data)
        old_session_id = target.get_id()
        previous_version = target.token_version

        deactivate_user(target, actor=admin, reason="Dejó la empresa.")
        db.session.commit()

        target = get(target_data)

        assert target.activo is False
        assert target.fecha_desactivacion is not None
        assert target.usuario_desactivacion_id == admin.id
        assert target.token_version == previous_version + 1
        assert load_user(old_session_id) is None

        (entry,) = audit_entries()

        assert entry.accion == "USUARIO_DESACTIVADO"
        assert entry.valor_anterior == {"activo": True}
        assert entry.valor_nuevo == {"activo": False}
        assert entry.motivo == "Dejó la empresa."


def test_deactivate_user_cannot_target_oneself(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")

    with app.app_context():
        admin = get(admin_data)

        with pytest.raises(SelfProtectionError):
            deactivate_user(admin, actor=admin)

        assert admin.activo is True
        assert audit_entries() == []


def test_deactivate_user_rejects_an_inactive_user(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")
    target_data = make_user("TECNICO", activo=False)

    with app.app_context(), pytest.raises(NothingToChangeError):
        deactivate_user(get(target_data), actor=get(admin_data))


def test_deactivate_user_protects_the_last_active_administrator(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")
    supervisor_data = make_user("SUPERVISOR")

    with app.app_context():
        admin = get(admin_data)

        with pytest.raises(LastAdministratorError):
            deactivate_user(admin, actor=get(supervisor_data))

        assert admin.activo is True
        assert audit_entries() == []


def test_deactivate_user_allows_an_administrator_if_another_remains(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")
    other_data = make_user("ADMINISTRADOR", username="admin_dos")

    with app.app_context():
        deactivate_user(get(other_data), actor=get(admin_data))

        assert get(other_data).activo is False


def test_activate_user_restores_access_and_clears_the_lock(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")
    target_data = make_user("TECNICO")

    with app.app_context():
        admin = get(admin_data)
        target = get(target_data)

        deactivate_user(target, actor=admin)
        target.intentos_fallidos = 5
        target.bloqueado_hasta = datetime.now(UTC) + timedelta(minutes=10)
        db.session.commit()

        activate_user(get(target_data), actor=admin, reason="Regresó.")
        db.session.commit()

        target = get(target_data)

        assert target.activo is True
        assert target.fecha_desactivacion is None
        assert target.usuario_desactivacion_id is None
        assert target.intentos_fallidos == 0
        assert target.bloqueado_hasta is None

        entry = audit_entries()[-1]

        assert entry.accion == "USUARIO_ACTIVADO"
        assert entry.valor_nuevo == {"activo": True}
        assert entry.motivo == "Regresó."


def test_activate_user_rejects_an_active_user(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")
    target_data = make_user("TECNICO")

    with app.app_context(), pytest.raises(NothingToChangeError):
        activate_user(get(target_data), actor=get(admin_data))


def test_reactivation_does_not_revive_old_sessions(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")
    target_data = make_user("TECNICO")

    with app.app_context():
        admin = get(admin_data)
        target = get(target_data)
        old_session_id = target.get_id()

        deactivate_user(target, actor=admin)
        db.session.commit()
        activate_user(get(target_data), actor=admin)
        db.session.commit()

        assert load_user(old_session_id) is None
        assert load_user(get(target_data).get_id()) is not None


# --- Restablecimiento de contraseña ----------------------------------


def test_reset_user_password_applies_the_security_measures(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")
    target_data = make_user("TECNICO")

    with app.app_context():
        admin = get(admin_data)
        target = get(target_data)
        target.intentos_fallidos = 3
        target.bloqueado_hasta = datetime.now(UTC) + timedelta(minutes=10)
        previous_version = target.token_version

        reset_user_password(target, TEMPORARY_PASSWORD, actor=admin)
        db.session.commit()

        target = get(target_data)

        assert verify_password(target.password_hash, TEMPORARY_PASSWORD)
        assert target.debe_cambiar_password is True
        assert target.token_version == previous_version + 1
        assert target.bloqueado_hasta is None

        (entry,) = audit_entries()

        assert entry.accion == "PASSWORD_RESTABLECIDA"
        assert entry.actor_usuario_id == admin.id
        assert TEMPORARY_PASSWORD not in str(entry.valor_nuevo)


def test_reset_user_password_cannot_target_oneself(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")

    with app.app_context():
        admin = get(admin_data)
        original_hash = admin.password_hash

        with pytest.raises(SelfProtectionError):
            reset_user_password(admin, TEMPORARY_PASSWORD, actor=admin)

        assert admin.password_hash == original_hash
        assert audit_entries() == []


def test_reset_user_password_rejects_a_weak_password(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")
    target_data = make_user("TECNICO")

    with app.app_context():
        target = get(target_data)
        original_hash = target.password_hash

        with pytest.raises(PasswordPolicyError):
            reset_user_password(target, "corta", actor=get(admin_data))

        assert target.password_hash == original_hash
        assert audit_entries() == []
