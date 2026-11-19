"""Adjuntos de un ticket (docs/06, RN-160).

Los metadatos viven en `archivos` y el binario en el almacenamiento local
(`tickets/storage.py`). Un adjunto puede colgar de un comentario o nota
interna: entonces hereda su visibilidad.

Quién puede subir, ver y eliminar lo deciden las rutas y las políticas de
`security/authorization.py`; aquí viven las reglas de los datos. Nada hace
commit: si la transacción falla después de guardar los archivos, quien llama
debe borrar los físicos con `discard_files`.

Reglas:

- **El filtro de visibilidad está en la consulta** (`visible_attachments_condition`),
  igual que en los comentarios. Un adjunto de una nota interna nunca llega al
  Solicitante y deja de verse para todos si el comentario se elimina.
- Máximo de archivos activos por ticket (`UPLOAD_MAX_FILES_PER_TICKET`) y de
  tamaño por archivo (`UPLOAD_MAX_BYTES`), comprobados bajo el bloqueo del
  ticket.
- La eliminación es lógica: el archivo físico se conserva (docs/10, sección 69).
- No sube la versión del ticket ni cambia «Actualizado».
"""

from collections.abc import Iterable

from flask import current_app
from sqlalchemy import exists, false, func, or_
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models import (
    Attachment,
    Comment,
    CommentType,
    HistoryVisibility,
    Ticket,
    TicketEvent,
    User,
)
from ..security import RoleCode, can_view_internal_activity, has_any_role
from .comments import visible_comments_condition
from .service import TicketRuleError, record_ticket_event
from .storage import (
    MAX_FILES_PER_REQUEST,
    UploadError,
    absolute_path,
    remove_file,
    store_upload,
)
from .versioning import begin_ticket_operation

_GONE = "Ese archivo ya no existe."


# --- Consultas --------------------------------------------------------


def visible_attachments_condition(user):
    """Condición SQL con los adjuntos que `user` puede ver: activos y, si
    cuelgan de un comentario, solo si ese comentario también es visible para él
    (el Solicitante no ve los de una nota interna). Es el equivalente en SQL de
    `can_view_attachment`. Como las demás, no comprueba el acceso al ticket.
    """
    if not (
        can_view_internal_activity(user)
        or has_any_role(user, RoleCode.SOLICITANTE)
    ):
        return false()

    return Attachment.activo.is_(True) & or_(
        Attachment.comentario_id.is_(None),
        exists().where(
            Comment.id == Attachment.comentario_id,
            visible_comments_condition(user),
        ),
    )


def list_attachments(ticket: Ticket, viewer: User) -> list[Attachment]:
    """Adjuntos del ticket que `viewer` puede ver, del más antiguo al más
    reciente. `viewer` es obligatorio a propósito."""
    return list(
        db.session.scalars(
            db.select(Attachment)
            .where(
                Attachment.ticket_id == ticket.id,
                visible_attachments_condition(viewer),
            )
            .options(joinedload(Attachment.subido_por))
            .order_by(Attachment.fecha_subida, Attachment.id)
        )
    )


def get_attachment(
    ticket: Ticket,
    attachment_id: int,
    viewer: User,
) -> Attachment | None:
    """Un adjunto del ticket, solo si `viewer` puede verlo (si no, None: las
    rutas responden 404, como con un ticket ajeno)."""
    return db.session.scalar(
        db.select(Attachment)
        .where(
            Attachment.id == attachment_id,
            Attachment.ticket_id == ticket.id,
            visible_attachments_condition(viewer),
        )
        .options(joinedload(Attachment.subido_por))
    )


def attachment_path(attachment: Attachment):
    """Ruta física de un adjunto, resuelta contra la raíz configurada."""
    return absolute_path(
        current_app.config["UPLOADS_DIR"],
        attachment.ruta_archivo,
    )


# --- Subir y eliminar -------------------------------------------------


def add_attachments(
    ticket: Ticket,
    *,
    actor: User,
    uploads: Iterable,
    comment: Comment | None = None,
) -> list[Attachment]:
    """Guarda los archivos subidos y los asocia al ticket (o a `comment`).

    Se ignoran las partes vacías del formulario (el navegador las envía cuando
    no se elige ningún archivo). Valida cada archivo (tipo, firma y tamaño),
    la cantidad por envío y el máximo de archivos del ticket. Si algo falla, no
    queda ningún archivo físico de este envío. Registra `ARCHIVO_ADJUNTADO` por
    cada uno, con la visibilidad del comentario del que cuelga. Un ticket
    cerrado lanza `TicketClosedError`.
    """
    begin_ticket_operation(ticket, actor)

    files = [upload for upload in uploads if getattr(upload, "filename", "")]

    if not files:
        return []

    if len(files) > MAX_FILES_PER_REQUEST:
        raise TicketRuleError(
            f"Puedes adjuntar hasta {MAX_FILES_PER_REQUEST} archivos a la vez."
        )

    config = current_app.config
    current = db.session.scalar(
        db.select(func.count(Attachment.id)).where(
            Attachment.ticket_id == ticket.id,
            Attachment.activo.is_(True),
        )
    )

    if current + len(files) > config["UPLOAD_MAX_FILES_PER_TICKET"]:
        raise TicketRuleError(
            "Un ticket admite hasta "
            f"{config['UPLOAD_MAX_FILES_PER_TICKET']} archivos y este ya "
            f"tiene {current}."
        )

    stored = []
    attachments = []

    try:
        for upload in files:
            try:
                stored.append(
                    store_upload(
                        upload,
                        config["UPLOADS_DIR"],
                        config["UPLOAD_MAX_BYTES"],
                    )
                )
            except UploadError as error:
                raise TicketRuleError(str(error)) from error

        for item in stored:
            attachment = Attachment(
                ticket_id=ticket.id,
                comentario_id=None if comment is None else comment.id,
                nombre_original=item.original_name,
                nombre_interno=item.internal_name,
                ruta_archivo=item.relative_path,
                mime_type=item.mime_type,
                tamano_bytes=item.size,
                hash=item.sha256,
                usuario_subida_id=actor.id,
            )
            db.session.add(attachment)
            attachments.append(attachment)

        db.session.flush()
    except BaseException:
        # Lo ya guardado de este envío no debe quedar disponible.
        for item in stored:
            remove_file(config["UPLOADS_DIR"], item.relative_path)

        raise

    for attachment in attachments:
        record_ticket_event(
            ticket,
            TicketEvent.ARCHIVO_ADJUNTADO,
            actor=actor,
            detail=f"Archivo adjuntado: {attachment.nombre_original}.",
            new_value={
                "archivo_id": attachment.id,
                "nombre": attachment.nombre_original,
                "tamano_bytes": attachment.tamano_bytes,
                "comentario_id": attachment.comentario_id,
            },
            context={"archivo_id": attachment.id},
            visibility=_event_visibility(comment),
        )

    return attachments


def delete_attachment(ticket: Ticket, attachment_id: int, *, actor: User) -> None:
    """Elimina lógicamente un adjunto: deja de mostrarse y descargarse, pero el
    registro y el archivo físico se conservan. Registra `ARCHIVO_ELIMINADO`."""
    begin_ticket_operation(ticket, actor)

    attachment = db.session.scalar(
        db.select(Attachment)
        .where(Attachment.id == attachment_id, Attachment.ticket_id == ticket.id)
        .options(joinedload(Attachment.comentario))
        .execution_options(populate_existing=True)
    )

    if attachment is None or not attachment.activo:
        raise TicketRuleError(_GONE)

    attachment.activo = False
    attachment.fecha_eliminacion = func.now()
    attachment.usuario_eliminacion_id = actor.id
    db.session.flush()

    record_ticket_event(
        ticket,
        TicketEvent.ARCHIVO_ELIMINADO,
        actor=actor,
        detail=f"Archivo eliminado: {attachment.nombre_original}.",
        old_value={
            "archivo_id": attachment.id,
            "nombre": attachment.nombre_original,
            "comentario_id": attachment.comentario_id,
        },
        context={"archivo_id": attachment.id},
        visibility=_event_visibility(attachment.comentario),
    )


def discard_files(relative_paths: Iterable[str]) -> None:
    """Borra los archivos físicos de adjuntos cuya transacción no se confirmó
    (compensación, docs/10, sección 67). Recibe las rutas relativas, porque tras
    un rollback los objetos ya no se pueden leer."""
    root = current_app.config["UPLOADS_DIR"]

    for relative in relative_paths:
        remove_file(root, relative)


def _event_visibility(comment: Comment | None) -> HistoryVisibility:
    if comment is not None and comment.tipo == CommentType.INTERNO.value:
        return HistoryVisibility.INTERNO

    return HistoryVisibility.PUBLICO
