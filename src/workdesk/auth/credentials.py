from datetime import UTC, datetime

from flask import current_app

from ..audit import AuditAction, record_admin_event
from ..models import User
from ..security import (
    hash_password,
    validate_password_policy,
    verify_password,
)
from .security import invalidate_user_sessions, reset_login_failures


class CurrentPasswordError(ValueError):
    """La contraseña actual indicada no es correcta."""


def _min_length() -> int:
    return current_app.config["PASSWORD_MIN_LENGTH"]


def change_own_password(
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    """Cambia la contraseña del propio usuario.

    Lanza `CurrentPasswordError` si la contraseña actual no es correcta y
    `PasswordPolicyError` si la nueva no cumple la política. En ambos casos
    el usuario no se modifica.

    Al cambiarla se sube `token_version`, lo que invalida **todas** las
    sesiones del usuario, incluida la actual: quien llama debe volver a
    iniciar la sesión actual para que el usuario no quede desconectado.

    No hace commit; tampoco cuenta el intento fallido de contraseña
    actual, algo que debe resolver quien llama (la ruta).
    """
    if not verify_password(user.password_hash, current_password):
        raise CurrentPasswordError("La contraseña actual no es correcta.")

    validate_password_policy(
        new_password,
        min_length=_min_length(),
        current_hash=user.password_hash,
    )

    previous_version = user.token_version

    user.password_hash = hash_password(new_password)
    user.debe_cambiar_password = False
    invalidate_user_sessions(user)
    _mark_modified(user, actor=user)

    record_admin_event(
        AuditAction.PASSWORD_CAMBIADA,
        actor=user,
        entity_type="usuario",
        entity_id=user.id,
        old_value={"token_version": previous_version},
        new_value={"token_version": user.token_version},
    )


def set_temporary_password(user: User, temporary_password: str) -> None:
    """Asigna una contraseña temporal y marca el cambio obligatorio.

    Pensada para crear un usuario: no invalida sesiones ni audita (la
    creación del usuario ya se audita como un único evento). Para un
    usuario existente se usa `reset_password`.

    No hace commit.
    """
    validate_password_policy(
        temporary_password,
        min_length=_min_length(),
    )

    user.password_hash = hash_password(temporary_password)
    user.debe_cambiar_password = True


def reset_password(
    user: User,
    temporary_password: str,
    *,
    actor: User,
) -> None:
    """Restablece la contraseña de un usuario existente (acción de Admin).

    Asigna una contraseña temporal, exige su cambio en el siguiente inicio
    de sesión, invalida las sesiones del usuario y limpia sus intentos
    fallidos y su bloqueo temporal.

    No hace commit.
    """
    previous_version = user.token_version

    set_temporary_password(user, temporary_password)
    invalidate_user_sessions(user)
    reset_login_failures(user)
    _mark_modified(user, actor=actor)

    record_admin_event(
        AuditAction.PASSWORD_RESTABLECIDA,
        actor=actor,
        entity_type="usuario",
        entity_id=user.id,
        old_value={"token_version": previous_version},
        new_value={
            "token_version": user.token_version,
            "cambio_obligatorio": True,
        },
    )


def _mark_modified(user: User, *, actor: User) -> None:
    user.fecha_modificacion = datetime.now(UTC)
    user.usuario_modificacion_id = actor.id
