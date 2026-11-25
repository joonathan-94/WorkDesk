"""Detalle de un ticket (docs/11, UI-005).

`render_detail` arma todo lo que muestra la pantalla. Lo comparten el GET
del detalle y las rutas que vuelven a mostrarlo con errores (por ejemplo, un
comentario que no pasa la validación).
"""

from datetime import UTC, datetime

from flask import render_template
from flask_login import current_user, login_required

from ... import settings
from ...catalogs.service import list_priorities
from ...configuration import value_of
from ...models import StateAction
from ...models.comment import MAX_COMMENT_LENGTH
from ...security import (
    STAFF_ROLES,
    can_assign_self,
    can_attach_files,
    can_change_priority,
    can_comment_publicly,
    can_delete_attachment,
    can_delete_comment,
    can_edit_comment,
    can_edit_ticket,
    can_link_articles,
    can_manage_assignments,
    can_manage_relations,
    can_manage_requesters,
    can_revoke_edit_lock,
    can_write_internal_note,
    current_actor,
    has_any_role,
)
from ...sla.periods import evaluate_ticket_sla, list_periods
from .. import bp
from ..attachments import list_attachments
from ..comments import list_comments
from ..forms import CommentForm
from ..history import describe_history_changes
from ..knowledge_links import list_links
from ..lifecycle import available_actions
from ..locking import current_edit_lock
from ..relations import KIND_DUPLICATE_OF, KIND_PRINCIPAL_OF, list_relations
from ..service import list_ticket_history
from ..storage import MAX_FILES_PER_REQUEST, allowed_extensions
from .common import my_assignment, ticket_is_closed, visible_ticket_or_404


@bp.get("/<public_id>")
@login_required
def detail(public_id: str):
    return render_detail(visible_ticket_or_404(public_id), CommentForm())


def render_detail(ticket, comment_form):
    """Muestra el detalle del ticket. Lo comparten el GET del detalle y el
    envío de un comentario que no pasa la validación (para mostrar los errores
    sin perder lo escrito).

    Solo reúne lo que la plantilla necesita: qué ve cada rol lo deciden las
    consultas y las políticas, nunca la plantilla, y cada ruta vuelve a
    comprobar la autorización de lo que ofrece.
    """
    is_staff = has_any_role(current_user, *STAFF_ROLES)
    is_closed = ticket_is_closed(ticket)
    now = datetime.now(UTC)

    files = _attachment_rows(ticket, now)
    files_by_comment = _group_by_comment(files)
    header_actions, validation_actions = _split_state_actions(
        available_actions(ticket, current_user)
    )
    show_relations = can_manage_relations(current_user)

    return render_template(
        "tickets/detail.html",
        ticket=ticket,
        history=_history_rows(ticket, is_staff),
        is_staff=is_staff,
        is_closed=is_closed,
        # Solo para decidir qué botones mostrar; las rutas de edición
        # comprueban la autorización por sí mismas.
        show_edit=can_edit_ticket(current_user) and not is_closed,
        show_priority=can_change_priority(current_user) and not is_closed,
        state_actions=header_actions,
        validation_actions=validation_actions,
        # Asignación: lo que se ofrece según el rol (cada ruta lo comprueba).
        can_self_assign=can_assign_self(current_user) and not is_closed,
        my_assignment=my_assignment(ticket),
        show_assignment=can_manage_assignments(current_user) and not is_closed,
        show_requesters=can_manage_requesters(current_user) and not is_closed,
        # Comentarios: el formulario se ofrece mientras el ticket esté abierto y
        # el selector de nota interna solo al personal.
        comments=_comment_rows(ticket, now),
        files_by_comment=files_by_comment,
        ticket_files=files_by_comment.get(None, []),
        show_uploader=can_attach_files(current_user, ticket) and not is_closed,
        max_files=MAX_FILES_PER_REQUEST,
        max_upload_mb=value_of(settings.UPLOAD_MAX_BYTES) // (1024 * 1024),
        allowed_extensions=allowed_extensions(),
        # Relaciones: solo el personal las ve (el Solicitante no recibe ni la
        # consulta).
        show_relations=show_relations,
        relation_views=list_relations(ticket) if show_relations else [],
        other_editor=_other_editor(ticket, is_closed),
        can_revoke_lock=can_revoke_edit_lock(current_user),
        can_edit_relations=show_relations and not is_closed,
        KIND_DUPLICATE_OF=KIND_DUPLICATE_OF,
        KIND_PRINCIPAL_OF=KIND_PRINCIPAL_OF,
        comment_form=comment_form,
        show_composer=can_comment_publicly(current_user, ticket) and not is_closed,
        can_write_note=can_write_internal_note(current_user),
        max_comment=MAX_COMMENT_LENGTH,
        # El SLA es solo del personal: el Solicitante no recibe ni la consulta.
        sla=evaluate_ticket_sla(ticket.id) if is_staff else None,
        # Artículos vinculados que esta persona puede leer (el filtro está en la consulta).
        article_links=list_links(ticket, current_user),
        can_link_articles=can_link_articles(current_user),
        sla_period_rows=_sla_period_rows(ticket) if is_staff else [],
    )


def _sla_period_rows(ticket) -> list[dict]:
    """Los períodos de SLA del ticket con el nombre de su prioridad (solo personal)."""
    names = {priority.id: priority.nombre for priority in list_priorities("")}

    return [
        {"period": period, "priority": names.get(period.prioridad_id, "—")}
        for period in list_periods(ticket.id)
    ]


def _comment_rows(ticket, now) -> list[dict]:
    """Comentarios del ticket con lo que la plantilla necesita de cada uno.

    La lista sale de una consulta que ya filtra por tipo: la nota interna no
    llega nunca al Solicitante (docs/10, sección 57). Los permisos de editar y
    eliminar solo deciden qué enlaces se muestran; cada ruta vuelve a
    comprobarlos.
    """
    return [
        {
            "comment": comment,
            "can_edit": can_edit_comment(current_user, comment, now=now),
            "can_delete": can_delete_comment(current_user, comment, now=now),
        }
        for comment in list_comments(ticket, current_actor())
    ]


def _attachment_rows(ticket, now) -> list[dict]:
    """Archivos del ticket (ya filtrados por la consulta, igual que los
    comentarios) con si el usuario puede eliminarlos."""
    return [
        {
            "file": attachment,
            "can_delete": can_delete_attachment(current_user, attachment, now=now),
        }
        for attachment in list_attachments(ticket, current_actor())
    ]


def _group_by_comment(files: list[dict]) -> dict:
    """Los archivos agrupados por el comentario del que cuelgan. Los del ticket
    (sin comentario) quedan bajo la clave `None` y van en la tarjeta «Archivos»;
    los demás se muestran bajo su comentario."""
    grouped: dict = {}

    for row in files:
        grouped.setdefault(row["file"].comentario_id, []).append(row)

    return grouped


def _history_rows(ticket, is_staff: bool) -> list[dict]:
    """Eventos del historial con lo que cada rol puede ver de ellos.

    Las filas internas ya las descarta la consulta. Aquí solo se decide qué
    motivos acompañan a un evento visible:

    - el motivo de un cambio de prioridad, de una espera o de un cierre es una
      nota interna del equipo: el Solicitante ve qué cambió, pero no por qué
      (docs/06, RN-155);
    - el motivo de un rechazo es del propio solicitante: lo ve quien ve el
      ticket.
    """
    return [
        {
            "entry": entry,
            "changes": describe_history_changes(entry),
            "reason": (entry.contexto or {}).get("motivo") if is_staff else None,
            "wait_reason": (
                entry.motivo_espera.nombre
                if is_staff and entry.motivo_espera is not None
                else None
            ),
            "rejection": (entry.contexto or {}).get("motivo_rechazo"),
        }
        for entry in list_ticket_history(ticket, current_actor())
    ]


def _split_state_actions(actions):
    """Separa las acciones de estado en las de la cabecera y las de validación.

    Confirmar o rechazar la solución no son botones de la cabecera: se muestran
    en el aviso de «Resuelto» (docs/11, UI-005A), en este orden. Las acciones
    ya llegan filtradas por transición activa y por política; cada ruta vuelve
    a comprobarlas.
    """
    order = (StateAction.RECHAZAR, StateAction.CONFIRMAR)
    validation = sorted(
        (a for a in actions if a.info.action in order),
        key=lambda a: order.index(a.info.action),
    )
    header = [a for a in actions if a not in validation]

    return header, validation


def _other_editor(ticket, is_closed: bool):
    """La persona que está editando el ticket ahora (RN-116), o None.

    Solo se muestra al personal que podría editar y nunca a quien tiene el
    bloqueo.
    """
    if is_closed or not can_edit_ticket(current_user):
        return None

    lock = current_edit_lock(ticket)

    if lock is None or lock.usuario_id == current_user.id:
        return None

    return lock.usuario
