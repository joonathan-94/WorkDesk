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


# Personal de soporte: ve y opera todos los tickets (docs/04, RF-011). El
# Solicitante, en cambio, solo accede a los tickets que le pertenecen.
STAFF_ROLES = (
    RoleCode.TECNICO,
    RoleCode.SUPERVISOR,
    RoleCode.ADMINISTRADOR,
)


def can_manage_users(user) -> bool:
    return has_any_role(user, RoleCode.ADMINISTRADOR)


def can_create_ticket(user) -> bool:
    """Los cuatro roles pueden crear tickets (docs/06, RN-09)."""
    return has_any_role(user, *RoleCode)


def can_choose_requesters(user) -> bool:
    """Crear un ticket a nombre de otras personas (docs/06, RN-10).

    El Solicitante no elige solicitantes: queda siempre como su propio
    solicitante.
    """
    return has_any_role(user, *STAFF_ROLES)


def can_view_ticket(user, ticket) -> bool:
    """Indica si el usuario puede ver el ticket.

    - El personal (Técnico, Supervisor y Administrador) ve todos.
    - El Solicitante ve los que creó y aquellos en los que es solicitante
      vigente (sin `fecha_retiro`). Un solicitante retirado deja de verlo.
    """
    if has_any_role(user, *STAFF_ROLES):
        return True

    if not has_any_role(user, RoleCode.SOLICITANTE):
        return False

    if ticket.creado_por_usuario_id == user.id:
        return True

    return any(
        requester.solicitante_id == user.id and requester.fecha_retiro is None
        for requester in ticket.solicitantes
    )


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
