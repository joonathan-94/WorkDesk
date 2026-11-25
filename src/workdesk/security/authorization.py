from datetime import UTC, datetime, timedelta
from enum import StrEnum
from functools import wraps

from flask import abort, current_app, request
from flask_login import current_user

from .. import settings
from ..configuration import value_of


class RoleCode(StrEnum):
    """Códigos estables de los cuatro roles estructurales (tabla roles)."""

    SOLICITANTE = "SOLICITANTE"
    TECNICO = "TECNICO"
    SUPERVISOR = "SUPERVISOR"
    ADMINISTRADOR = "ADMINISTRADOR"


def current_actor():
    """El usuario autenticado como objeto real, no como el proxy de
    Flask-Login.

    Es lo que se pasa a los servicios como `actor`: se guarda en la sesión de
    SQLAlchemy y se compara por identidad, cosa que el proxy no permite.
    """
    return current_user._get_current_object()


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


def can_manage_settings(user) -> bool:
    """Solo el Administrador cambia los parámetros de la aplicación (docs/03, RF-113)."""
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


# Códigos de estado que las políticas necesitan. Repiten los de `Estado` para
# que este módulo no dependa de los modelos; un test comprueba que coinciden.
CLOSED_STATE = "CERRADO"
RESOLVED_STATE = "RESUELTO"


def can_resolve_ticket(user) -> bool:
    """Marcar un ticket como Resuelto (docs/04, RF-046; docs/03, sección 5):
    el personal. El Solicitante nunca resuelve; solo valida la solución."""
    return has_any_role(user, *STAFF_ROLES)


def can_close_directly(user) -> bool:
    """Cerrar un ticket sin pasar por Resuelto (docs/06, RN-60 y RN-61): el
    Técnico, el Supervisor y el Administrador."""
    return has_any_role(user, *STAFF_ROLES)


def can_close_exceptionally(user) -> bool:
    """Cierre excepcional de un ticket Resuelto (docs/04, RF-054): solo el
    Supervisor y el Administrador."""
    return has_any_role(user, RoleCode.SUPERVISOR, RoleCode.ADMINISTRADOR)


def is_current_requester(user, ticket) -> bool:
    """Un Solicitante activo que figura como solicitante vigente del ticket
    (sin `fecha_retiro`). El creador que fue retirado como solicitante deja de
    serlo: puede seguir viendo el ticket, pero ya no responde por él."""
    if not has_any_role(user, RoleCode.SOLICITANTE):
        return False

    return any(
        requester.solicitante_id == user.id and requester.fecha_retiro is None
        for requester in ticket.solicitantes
    )


def can_validate_resolution(user, ticket) -> bool:
    """Confirmar o rechazar la solución de un ticket Resuelto (docs/06, RN-53
    a RN-55): cualquiera de sus solicitantes vigentes. La confirmación de uno
    solo basta para cerrar el ticket. Que el ticket esté en Resuelto lo decide
    `tickets.lifecycle`."""
    return is_current_requester(user, ticket)


def can_reopen_ticket(user, ticket, *, now=None, window_days=None) -> bool:
    """Reabrir un ticket (docs/06, RN-66, RN-69, RN-70 y RN-73).

    - El personal reabre un ticket Resuelto o Cerrado sin límite de tiempo.
    - Un solicitante vigente solo reabre un ticket **Cerrado**, dentro de
      `REOPEN_WINDOW_DAYS` desde el cierre (30 por defecto). Si está Resuelto
      no reabre: rechaza la solución.

    Que el ticket esté en un estado desde el que se puede reabrir lo decide
    `tickets.lifecycle`. `now` y `window_days` permiten comprobarlo sin reloj
    ni configuración.
    """
    if has_any_role(user, *STAFF_ROLES):
        return True

    if not is_current_requester(user, ticket):
        return False

    if ticket.estado.codigo != CLOSED_STATE or ticket.fecha_cierre is None:
        return False

    if window_days is None:
        window_days = value_of(settings.REOPEN_WINDOW_DAYS)

    now = datetime.now(UTC) if now is None else now

    return now - ticket.fecha_cierre <= timedelta(days=window_days)


def can_manage_relations(user) -> bool:
    """Ver y gestionar las relaciones entre tickets: relacionar tickets y
    marcar un ticket como duplicado de otro (docs/06, RN-162). Solo el
    personal; el Solicitante no ve las relaciones. Que el ticket esté abierto
    lo aplica el servicio."""
    return has_any_role(user, *STAFF_ROLES)


def can_view_workload(user) -> bool:
    """Ver la carga de trabajo del equipo (docs/12, fase 6). Es información de
    todo el equipo —no solo de lo propio—, así que es solo del personal: un
    Técnico ve la carga de sus compañeros, el Solicitante no ve nada de esto."""
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


# Tipo de comentario que solo ve el personal (`CommentType.INTERNO`). Se repite
# aquí para que este módulo no dependa de los modelos; un test comprueba que
# coincide con el del modelo.
INTERNAL_COMMENT_TYPE = "INTERNO"


def can_comment_publicly(user, ticket) -> bool:
    """Escribir un comentario público (docs/03, sección 5): el personal en
    cualquier ticket y el Solicitante solo en los suyos, es decir, quien puede
    ver el ticket. Que el ticket esté cerrado es una regla del ticket y la
    aplica el servicio.
    """
    return can_view_ticket(user, ticket)


def can_write_internal_note(user) -> bool:
    """Escribir una nota interna: solo el personal. El Solicitante nunca,
    ni en sus propios tickets."""
    return has_any_role(user, *STAFF_ROLES)


def can_view_comment(user, comment) -> bool:
    """Ver un comentario del ticket: el personal ve todos; el Solicitante, solo
    los públicos. Como `can_view_ticket`, no comprueba el acceso al ticket:
    quien llama debe haberlo comprobado antes. `visible_comments_condition`
    (`tickets/comments.py`) es su equivalente en SQL y deben coincidir.
    """
    if can_view_internal_activity(user):
        return True

    return (
        has_any_role(user, RoleCode.SOLICITANTE)
        and comment.tipo != INTERNAL_COMMENT_TYPE
    )


def can_edit_comment(user, comment, *, now=None, window_minutes=None) -> bool:
    """Editar un comentario o nota (docs/09, 17.1).

    - El Supervisor y el Administrador pueden editar cualquier comentario que
      puedan ver, también los de otras personas y fuera de plazo.
    - Cualquier otra persona solo edita los suyos, dentro de
      `COMMENT_EDIT_WINDOW_MINUTES` desde que los publicó (30 por defecto).

    `now` y `window_minutes` permiten comprobarlo sin reloj ni configuración.
    """
    if not can_view_comment(user, comment):
        return False

    if has_any_role(user, RoleCode.SUPERVISOR, RoleCode.ADMINISTRADOR):
        return True

    if comment.autor_usuario_id != user.id:
        return False

    if window_minutes is None:
        window_minutes = value_of(settings.COMMENT_EDIT_WINDOW_MINUTES)

    now = datetime.now(UTC) if now is None else now

    return now - comment.fecha_creacion <= timedelta(minutes=window_minutes)


def can_delete_comment(user, comment, *, now=None, window_minutes=None) -> bool:
    """Eliminar (lógicamente) un comentario o nota. Hoy sigue la misma regla
    que editarlo; se separa porque los documentos los nombran aparte."""
    return can_edit_comment(
        user,
        comment,
        now=now,
        window_minutes=window_minutes,
    )


def can_attach_files(user, ticket) -> bool:
    """Adjuntar archivos a un ticket: quien puede comentar en él (el personal
    en cualquiera y el Solicitante en los suyos). Que el ticket esté cerrado
    lo aplica el servicio."""
    return can_view_ticket(user, ticket)


def can_view_attachment(user, attachment) -> bool:
    """Ver o descargar un adjunto (docs/06, RN-82). Un adjunto del ticket lo ve
    quien ve el ticket; uno que cuelga de un comentario o nota hereda su
    visibilidad (el Solicitante no ve los de una nota interna) y deja de verse
    si el comentario se elimina. Como `can_view_ticket`, no comprueba el acceso
    al ticket. `visible_attachments_condition` es su equivalente en SQL.
    """
    if not (
        can_view_internal_activity(user)
        or has_any_role(user, RoleCode.SOLICITANTE)
    ):
        return False

    comment = attachment.comentario

    if comment is None:
        return True

    return bool(comment.activo) and can_view_comment(user, comment)


def can_delete_attachment(user, attachment, *, now=None, window_minutes=None) -> bool:
    """Eliminar (lógicamente) un adjunto. Misma regla que editar un comentario:
    el Supervisor y el Administrador, cualquiera que puedan ver; el resto, solo
    los que subieron ellos, dentro de `COMMENT_EDIT_WINDOW_MINUTES`."""
    if not can_view_attachment(user, attachment):
        return False

    if has_any_role(user, RoleCode.SUPERVISOR, RoleCode.ADMINISTRADOR):
        return True

    if attachment.usuario_subida_id != user.id:
        return False

    if window_minutes is None:
        window_minutes = value_of(settings.COMMENT_EDIT_WINDOW_MINUTES)

    now = datetime.now(UTC) if now is None else now

    return now - attachment.fecha_subida <= timedelta(minutes=window_minutes)


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


# Exclusivo del Administrador. Es el decorador que usan todas las pantallas de
# administración; como cualquier autorización, se comprueba en backend.
admin_only = roles_required(RoleCode.ADMINISTRADOR)
