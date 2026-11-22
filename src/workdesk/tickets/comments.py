"""Comentarios públicos y notas internas de un ticket (docs/06, RN-159).

Una única entidad (`comentarios`) representa ambos tipos. Un **comentario
público** lo ven el personal y los Solicitantes con acceso al ticket; una
**nota interna**, solo el personal. El tipo se fija al crear y no cambia
nunca (cambiarlo alteraría retroactivamente quién lo ve).

Quién puede escribir, editar y eliminar lo deciden la capa de rutas y las
políticas de `security/authorization.py`; aquí viven las reglas de los datos.
Nada hace commit: el comentario y su evento de historial se confirman o se
revierten juntos.

Reglas que conviene tener presentes:

- **El filtro por tipo está en la consulta** (`visible_comments_condition`),
  nunca en la plantilla ni en JavaScript (docs/10, sección 57). Toda lista de
  comentarios, y cualquier conteo futuro, debe salir de ella.
- La eliminación es lógica: el comentario se conserva (con quién y cuándo lo
  eliminó) y deja de mostrarse a todos. El contenido anterior de una edición o
  una eliminación queda en el historial del ticket.
- Escribir, editar o eliminar no sube la versión del ticket ni cambia
  «Actualizado»: no toca ninguno de sus datos. Igualmente cada operación
  bloquea la fila del ticket antes de validar y rechaza un ticket cerrado.
- Los eventos del historial siguen la visibilidad del comentario: los de una
  nota interna son internos y los de un comentario público, públicos. El
  historial nunca muestra el texto; solo indica qué ocurrió.
"""

from sqlalchemy import false, func
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models import (
    Comment,
    CommentType,
    HistoryVisibility,
    Ticket,
    TicketEvent,
    User,
)
from ..models.comment import MAX_COMMENT_LENGTH
from ..notifications.events import notify_comment
from ..security import RoleCode, can_view_internal_activity, has_any_role
from .service import TicketRuleError, record_ticket_event
from .versioning import begin_ticket_operation

_GONE = "Ese comentario ya no existe."


# --- Consultas --------------------------------------------------------


def visible_comments_condition(user):
    """Condición SQL con los comentarios que `user` puede ver.

    - El personal ve todos, notas internas incluidas.
    - El Solicitante ve solo los públicos.
    - Cualquier otro caso (anónimo, inactivo, sin rol): ninguno.

    Es el equivalente en SQL de `can_view_comment` y un test comprueba que
    coinciden. Como `visible_tickets_condition`, no comprueba el acceso al
    ticket: quien llama debe haber aplicado antes `can_view_ticket`. Solo
    incluye los comentarios activos (los eliminados no se muestran a nadie).
    """
    active = Comment.activo.is_(True)

    if can_view_internal_activity(user):
        return active

    if has_any_role(user, RoleCode.SOLICITANTE):
        return active & (Comment.tipo == CommentType.PUBLICO.value)

    return false()


def list_comments(ticket: Ticket, viewer: User) -> list[Comment]:
    """Comentarios del ticket que `viewer` puede ver, del más antiguo al más
    reciente.

    `viewer` es obligatorio a propósito: así ninguna pantalla puede listar los
    comentarios sin decidir para quién. Carga de una vez al autor y su rol.
    """
    return list(
        db.session.scalars(
            db.select(Comment)
            .where(
                Comment.ticket_id == ticket.id,
                visible_comments_condition(viewer),
            )
            .options(joinedload(Comment.autor).joinedload(User.rol))
            .order_by(Comment.fecha_creacion, Comment.id)
        )
    )


def get_comment(ticket: Ticket, comment_id: int, viewer: User) -> Comment | None:
    """Un comentario del ticket, solo si `viewer` puede verlo.

    Devuelve None si no existe, es de otro ticket, está eliminado o es una nota
    interna que `viewer` no puede ver: las rutas responden 404 en todos los
    casos, igual que con un ticket ajeno (RN-153).
    """
    return db.session.scalar(
        db.select(Comment)
        .where(
            Comment.id == comment_id,
            Comment.ticket_id == ticket.id,
            visible_comments_condition(viewer),
        )
        .options(joinedload(Comment.autor).joinedload(User.rol))
    )


# --- Agregar, editar y eliminar ---------------------------------------


def add_comment(
    ticket: Ticket,
    *,
    actor: User,
    content: str,
    kind: CommentType | str,
) -> Comment:
    """Publica un comentario o una nota interna en el ticket.

    `kind` debe ser un `CommentType`. El contenido es obligatorio y admite hasta
    `MAX_COMMENT_LENGTH` caracteres. Registra `COMENTARIO_AGREGADO` con la
    visibilidad del comentario. Un ticket cerrado lanza `TicketClosedError`.

    No comprueba que `actor` pueda escribir ese tipo: lo hace la ruta (una nota
    interna exige `can_write_internal_note`).
    """
    begin_ticket_operation(ticket, actor)

    kind = _clean_kind(kind)
    content = clean_comment_content(content)

    comment = Comment(
        ticket_id=ticket.id,
        autor_usuario_id=actor.id,
        tipo=kind.value,
        contenido=content,
    )
    db.session.add(comment)
    db.session.flush()

    record_ticket_event(
        ticket,
        TicketEvent.COMENTARIO_AGREGADO,
        actor=actor,
        detail=_detail(kind, "agregad"),
        new_value={"comentario_id": comment.id, "tipo": kind.value},
        context={"comentario_id": comment.id},
        visibility=_event_visibility(kind),
    )

    notify_comment(ticket, actor, internal=kind is CommentType.INTERNO)

    return comment


def edit_comment(
    ticket: Ticket,
    comment_id: int,
    *,
    actor: User,
    content: str,
) -> bool:
    """Edita el contenido de un comentario o nota. El tipo no cambia.

    Devuelve False, sin tocar nada, si el contenido es el mismo. Registra
    `COMENTARIO_EDITADO` con el contenido anterior y el nuevo (en el historial,
    para quien deba auditarlo; la pantalla del historial nunca lo muestra).
    """
    begin_ticket_operation(ticket, actor)

    comment = _get_active_comment(ticket, comment_id)
    content = clean_comment_content(content)

    if content == comment.contenido:
        return False

    old_content = comment.contenido
    kind = CommentType(comment.tipo)

    comment.contenido = content
    comment.editado = True
    # La hora la pone la base de datos, como `fecha_creacion`.
    comment.fecha_modificacion = func.now()
    comment.usuario_modificacion_id = actor.id
    db.session.flush()

    record_ticket_event(
        ticket,
        TicketEvent.COMENTARIO_EDITADO,
        actor=actor,
        detail=_detail(kind, "editad"),
        old_value={"contenido": old_content},
        new_value={"contenido": content},
        context={"comentario_id": comment.id, "tipo": kind.value},
        visibility=_event_visibility(kind),
    )

    return True


def delete_comment(ticket: Ticket, comment_id: int, *, actor: User) -> None:
    """Elimina lógicamente un comentario o nota: deja de mostrarse, pero la
    fila se conserva con quién y cuándo la eliminó.

    Registra `COMENTARIO_ELIMINADO` con el contenido y el tipo anteriores.
    """
    begin_ticket_operation(ticket, actor)

    comment = _get_active_comment(ticket, comment_id)
    kind = CommentType(comment.tipo)
    old_content = comment.contenido

    comment.activo = False
    comment.fecha_eliminacion = func.now()
    comment.usuario_eliminacion_id = actor.id
    db.session.flush()

    record_ticket_event(
        ticket,
        TicketEvent.COMENTARIO_ELIMINADO,
        actor=actor,
        detail=_detail(kind, "eliminad"),
        old_value={"contenido": old_content, "tipo": kind.value},
        context={"comentario_id": comment.id, "tipo": kind.value},
        visibility=_event_visibility(kind),
    )


def clean_comment_content(content: str | None) -> str:
    """Recorta y valida el contenido de un comentario.

    Unifica los saltos de línea (los navegadores envían CRLF y el límite debe
    coincidir con el contador que ve la persona). Lanza `TicketRuleError` con un
    mensaje para el usuario.
    """
    content = (content or "").replace("\r\n", "\n").replace("\r", "\n").strip()

    if not content:
        raise TicketRuleError("Escribe el comentario.")

    if len(content) > MAX_COMMENT_LENGTH:
        raise TicketRuleError(
            f"El comentario no puede superar los {MAX_COMMENT_LENGTH} caracteres."
        )

    return content


# --- Piezas comunes ---------------------------------------------------


def _get_active_comment(ticket: Ticket, comment_id: int) -> Comment:
    """El comentario activo del ticket, leído de nuevo de la base de datos.

    La fila del ticket ya está bloqueada: si otra persona acaba de editarlo o
    eliminarlo, aquí se ve su resultado (`populate_existing` evita usar una
    copia anterior que la sesión pudiera tener).
    """
    comment = db.session.scalar(
        db.select(Comment)
        .where(Comment.id == comment_id, Comment.ticket_id == ticket.id)
        .execution_options(populate_existing=True)
    )

    if comment is None or not comment.activo:
        raise TicketRuleError(_GONE)

    return comment


def _clean_kind(kind: CommentType | str) -> CommentType:
    try:
        return CommentType(kind)
    except ValueError as error:
        raise TicketRuleError("El tipo de comentario no es válido.") from error


def _event_visibility(kind: CommentType) -> HistoryVisibility:
    """Los eventos de una nota interna son internos: nunca llegan al
    Solicitante."""
    if kind is CommentType.INTERNO:
        return HistoryVisibility.INTERNO

    return HistoryVisibility.PUBLICO


def _detail(kind: CommentType, stem: str) -> str:
    """Texto del evento con la concordancia de género: «Nota interna
    agregada.» y «Comentario público agregado.»."""
    if kind is CommentType.INTERNO:
        return f"Nota interna {stem}a."

    return f"Comentario público {stem}o."
