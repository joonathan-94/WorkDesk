from enum import StrEnum
from functools import wraps

from flask import abort, current_app, request
from flask_login import current_user


class RoleCode(StrEnum):
    """Códigos estables de los cuatro roles estructurales (tabla roles)."""

    SOLICITANTE = "SOLICITANTE"
    TECNICO = "TECNICO"
    SUPERVISOR = "SUPERVISOR"
    ADMINISTRADOR = "ADMINISTRADOR"


def has_any_role(user, *role_codes: RoleCode) -> bool:
    """Indica si el usuario está autenticado, activo y tiene uno de los roles.

    Es la única función que lee el rol del usuario; las políticas y el
    decorador se apoyan en ella para no duplicar la comprobación.
    """
    if not (user.is_authenticated and user.is_active):
        return False

    return user.rol.codigo in role_codes


def can_manage_users(user) -> bool:
    return has_any_role(user, RoleCode.ADMINISTRADOR)


def can_view_audit(user) -> bool:
    return has_any_role(user, RoleCode.ADMINISTRADOR)


def roles_required(*role_codes: RoleCode):
    """Restringe una vista a los roles indicados, comprobado en backend.

    - Sin sesión: se delega en Flask-Login (redirige al login).
    - Con sesión pero sin el rol necesario: responde 403.
    """

    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return current_app.login_manager.unauthorized()

            if not has_any_role(current_user, *role_codes):
                current_app.logger.warning(
                    "Acceso denegado: usuario_id=%s endpoint=%s",
                    current_user.id,
                    request.endpoint,
                )
                abort(403)

            return view(*args, **kwargs)

        return wrapped_view

    return decorator
