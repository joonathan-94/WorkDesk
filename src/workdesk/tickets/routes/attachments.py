"""Archivos adjuntos: subir, descargar y eliminar (docs/06, RN-160).
"""

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required
from flask_wtf import FlaskForm

from ...extensions import db
from ...security import can_attach_files, can_delete_attachment, current_actor
from .. import bp
from ..attachments import (
    add_attachments,
    attachment_path,
    delete_attachment,
    discard_files,
    get_attachment,
)
from ..service import TicketRuleError
from .common import (
    CLOSED_MODIFY_MESSAGE,
    closed_redirect,
    ticket_is_closed,
    visible_ticket_or_404,
)


@bp.post("/<public_id>/attachments")
@login_required
def add_ticket_attachments(public_id: str):
    """Sube archivos al ticket (tarjeta «Archivos»)."""
    ticket = visible_ticket_or_404(public_id)

    if not can_attach_files(current_user, ticket):
        abort(403)

    form = FlaskForm()

    if not form.validate_on_submit():
        abort(400)

    paths: list[str] = []
    back = url_for("tickets.detail", public_id=public_id, _anchor="archivos")

    try:
        attachments = add_attachments(
            ticket,
            actor=current_actor(),
            uploads=request.files.getlist("archivos"),
        )
        paths = [attachment.ruta_archivo for attachment in attachments]
        db.session.commit()
    except TicketRuleError as error:
        db.session.rollback()
        flash(str(error), "error")

        return redirect(back)
    except Exception:
        db.session.rollback()
        discard_files(paths)

        raise

    if not attachments:
        flash("Elige al menos un archivo.", "warning")
    else:
        flash(
            "Archivo adjuntado."
            if len(attachments) == 1
            else f"{len(attachments)} archivos adjuntados.",
            "success",
        )

    return redirect(back)


@bp.get("/<public_id>/attachments/<int:attachment_id>/download")
@login_required
def download_ticket_attachment(public_id: str, attachment_id: int):
    """Descarga autenticada: se comprueba el acceso al ticket y al adjunto, y
    el archivo se envía siempre como descarga (nunca se interpreta en el
    navegador)."""
    ticket = visible_ticket_or_404(public_id)
    attachment = _visible_attachment_or_404(ticket, attachment_id)

    try:
        path = attachment_path(attachment)
    except ValueError:
        abort(404)

    if not path.is_file():
        current_app.logger.error(
            "Adjunto sin archivo físico: archivo_id=%s", attachment.id
        )
        abort(404)

    response = send_file(
        path,
        mimetype=attachment.mime_type,
        as_attachment=True,
        download_name=attachment.nombre_original,
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "private, no-store"

    return response


@bp.route(
    "/<public_id>/attachments/<int:attachment_id>/delete",
    methods=["GET", "POST"],
)
@login_required
def delete_ticket_attachment(public_id: str, attachment_id: int):
    """Confirmación para eliminar un adjunto (eliminación lógica)."""
    ticket = visible_ticket_or_404(public_id)
    attachment = _visible_attachment_or_404(ticket, attachment_id)

    if not can_delete_attachment(current_user, attachment):
        abort(403)

    if ticket_is_closed(ticket):
        return closed_redirect(ticket, CLOSED_MODIFY_MESSAGE)

    form = FlaskForm()

    if form.validate_on_submit():
        try:
            delete_attachment(ticket, attachment_id, actor=current_actor())
            db.session.commit()
        except TicketRuleError as error:
            db.session.rollback()
            flash(str(error), "error")
        else:
            flash("Archivo eliminado.", "success")

        return redirect(url_for("tickets.detail", public_id=public_id))

    return render_template(
        "tickets/attachment_delete.html",
        ticket=ticket,
        attachment=attachment,
        form=form,
    )


def _visible_attachment_or_404(ticket, attachment_id: int):
    """Adjunto del ticket que el usuario puede ver; 404 en cualquier otro caso
    (no existe, es de otro ticket, está eliminado o cuelga de una nota
    interna que no puede ver)."""
    attachment = get_attachment(ticket, attachment_id, current_actor())

    if attachment is None:
        abort(404)

    return attachment
