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


def can_manage_requesters(user) -> bool:
    """Agregar y retirar solicitantes de un ticket ya creado (docs/06, RN-11).

    Es la misma regla que elegirlos al crear (`can_choose_requesters`): el
    personal puede; el Solicitante no decide quiénes más figuran en un
    ticket. Que el ticket esté cerrado es una regla del ticket, no del rol, y
    la aplica el servicio.
    """
    return has_any_role(user, *STAFF_ROLES)


def can_edit_ticket(user) -> bool:
    """Editar título, descripción, categoría y ubicación de un ticket.

    Es una política de rol: el personal puede; el Solicitante solo lee. Que
    el ticket esté cerrado (no se edita sin reabrirlo) es una regla del
    ticket, no del rol, y la aplica el servicio.
    """
    return has_any_role(user, *STAFF_ROLES)


def can_change_priority(user) -> bool:
    """Cambiar la prioridad de un ticket ya creado (docs/06, RN-22)."""
    return has_any_role(user, *STAFF_ROLES)


def can_change_state(user) -> bool:
    """Ejecutar los cambios de estado operativos: iniciar el trabajo, poner
    en espera y reactivar (docs/03, sección 5; docs/08, sección 33).

    Es una política de rol: el personal puede; el Solicitante no cambia
    estados operativos. Si la transición es válida desde el estado actual
    del ticket lo decide `tickets.lifecycle`.
    """
    return has_any_role(user, *STAFF_ROLES)


def can_assign_self(user) -> bool:
    """Asignarse (y dejar de estar asignado) a un ticket (docs/03, sección 5).

    Solo un Técnico: es el único rol que puede figurar como técnico de un
    ticket. El Supervisor y el Administrador asignan a otras personas, pero
    no se asignan a sí mismos.
    """
    return has_any_role(user, RoleCode.TECNICO)


def can_manage_assignments(user) -> bool:
    """Asignar, quitar y reasignar técnicos a cualquier persona, fijar el
    grupo del ticket y escalarlo: Supervisor y Administrador (docs/03,
    sección 5). El Técnico solo se asigna a sí mismo (`can_assign_self`)."""
    return has_any_role(user, RoleCode.SUPERVISOR, RoleCode.ADMINISTRADOR)


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


def can_view_internal_activity(user) -> bool:
    """Ver lo interno de un ticket: notas internas y eventos internos.

    Solo el personal. El Solicitante nunca accede a ello (docs/03, sección
    5): ni en el detalle, ni en el historial, ni en los conteos.
    """
    return has_any_role(user, *STAFF_ROLES)


def can_access_groups(user) -> bool:
    """Entrar al área de grupos: el Administrador y los Supervisores.

    El Técnico y el Solicitante no tienen pantalla de grupos (la pertenencia
    de un técnico a un grupo no limita lo que ve ni lo que hace).
    """
    return has_any_role(user, RoleCode.ADMINISTRADOR, RoleCode.SUPERVISOR)


def can_manage_groups(user) -> bool:
    """Crear, editar, activar y desactivar grupos, y designar a sus
    supervisores responsables (docs/03, sección 5): solo el Administrador."""
    return has_any_role(user, RoleCode.ADMINISTRADOR)


def is_responsible_supervisor(user, group) -> bool:
    """Indica si el usuario es un Supervisor activo con designación vigente
    (sin `fecha_fin`) como responsable del grupo."""
    if not has_any_role(user, RoleCode.SUPERVISOR):
        return False

    return any(
        designation.supervisor_id == user.id
        for designation in group.supervisores_vigentes
    )


def can_view_group(user, group) -> bool:
    """El Administrador ve todos los grupos; el Supervisor, solo aquellos de
    los que es responsable. Cualquier otro rol, ninguno."""
    return can_manage_groups(user) or is_responsible_supervisor(user, group)


def can_manage_group_members(user, group) -> bool:
    """Agregar y retirar técnicos de un grupo (docs/09, 10.2): el
    Administrador en cualquiera y el Supervisor solo en los suyos."""
    return can_view_group(user, group)


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
