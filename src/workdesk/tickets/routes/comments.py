"""Comentarios públicos y notas internas (docs/06, RN-159).
"""

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm

from ...extensions import db
from ...models import CommentType
from ...models.comment import MAX_COMMENT_LENGTH
from ...security import (
    can_comment_publicly,
    can_delete_comment,
    can_edit_comment,
    can_write_internal_note,
    current_actor,
)
from .. import bp
from ..attachments import add_attachments, discard_files
from ..comments import add_comment, delete_comment, edit_comment, get_comment
from ..forms import CommentEditForm, CommentForm
from ..service import TicketRuleError
from ..versioning import TicketClosedError
from .common import (
    CLOSED_MODIFY_MESSAGE,
    closed_redirect,
    ticket_is_closed,
    visible_ticket_or_404,
)
from .detail import render_detail


@bp.post("/<public_id>/comments")
@login_required
def add_ticket_comment(public_id: str):
    """Publica un comentario o una nota interna (formulario del detalle)."""
    ticket = visible_ticket_or_404(public_id)

    if not can_comment_publicly(current_user, ticket):
        abort(403)

    form = CommentForm()

    if not form.validate_on_submit():
        # Se vuelve al detalle con los errores y lo que ya se había escrito.
        return render_detail(ticket, form)

    kind = CommentType(form.tipo.data)

    # Una nota interna es solo del personal: enviar el tipo a mano no basta.
    if kind is CommentType.INTERNO and not can_write_internal_note(current_user):
        abort(403)

    paths: list[str] = []

    try:
        comment = add_comment(
            ticket,
            actor=current_actor(),
            content=form.contenido.data,
            kind=kind,
        )
        # Los archivos del mismo envío cuelgan del comentario y heredan su
        # visibilidad. Si alguno falla, no se guarda ni el comentario.
        attachments = add_attachments(
            ticket,
            actor=current_actor(),
            uploads=request.files.getlist("archivos"),
            comment=comment,
        )
        paths = [attachment.ruta_archivo for attachment in attachments]
        db.session.commit()
    except TicketClosedError as error:
        db.session.rollback()
        flash(str(error), "error")

        return redirect(url_for("tickets.detail", public_id=public_id))
    except TicketRuleError as error:
        # Por ejemplo, un archivo no permitido: se vuelve al detalle con lo
        # escrito para no perderlo.
        db.session.rollback()
        flash(str(error), "error")

        return render_detail(ticket, form)
    except Exception:
        # Si la base de datos falla tras guardar los archivos, se borran.
        db.session.rollback()
        discard_files(paths)

        raise

    flash(
        "Nota interna registrada."
        if kind is CommentType.INTERNO
        else "Comentario publicado.",
        "success",
    )

    return redirect(
        url_for(
            "tickets.detail",
            public_id=public_id,
            _anchor=f"comentario-{comment.id}",
        )
    )


@bp.route("/<public_id>/comments/<int:comment_id>/edit", methods=["GET", "POST"])
@login_required
def edit_ticket_comment(public_id: str, comment_id: int):
    ticket = visible_ticket_or_404(public_id)
    comment = _visible_comment_or_404(ticket, comment_id)

    # Quien ve el comentario pero no puede editarlo (no es suyo, o venció el
    # plazo) recibe un 403.
    if not can_edit_comment(current_user, comment):
        abort(403)

    if ticket_is_closed(ticket):
        return closed_redirect(ticket, CLOSED_MODIFY_MESSAGE)

    initial = {"contenido": comment.contenido} if request.method == "GET" else {}
    form = CommentEditForm(**initial)

    if form.validate_on_submit():
        try:
            changed = edit_comment(
                ticket,
                comment_id,
                actor=current_actor(),
                content=form.contenido.data,
            )
            db.session.commit()
        except TicketRuleError as error:
            db.session.rollback()
            flash(str(error), "error")

            return redirect(url_for("tickets.detail", public_id=public_id))

        flash(
            "Comentario actualizado."
            if changed
            else "No había cambios que guardar.",
            "success" if changed else "warning",
        )

        return redirect(
            url_for(
                "tickets.detail",
                public_id=public_id,
                _anchor=f"comentario-{comment_id}",
            )
        )

    return render_template(
        "tickets/comment_edit.html",
        ticket=ticket,
        comment=comment,
        form=form,
        max_comment=MAX_COMMENT_LENGTH,
    )


@bp.route("/<public_id>/comments/<int:comment_id>/delete", methods=["GET", "POST"])
@login_required
def delete_ticket_comment(public_id: str, comment_id: int):
    """Confirmación para eliminar un comentario o nota (eliminación lógica)."""
    ticket = visible_ticket_or_404(public_id)
    comment = _visible_comment_or_404(ticket, comment_id)

    if not can_delete_comment(current_user, comment):
        abort(403)

    if ticket_is_closed(ticket):
        return closed_redirect(ticket, CLOSED_MODIFY_MESSAGE)

    form = FlaskForm()

    if form.validate_on_submit():
        was_note = comment.es_nota_interna

        try:
            delete_comment(ticket, comment_id, actor=current_actor())
            db.session.commit()
        except TicketRuleError as error:
            db.session.rollback()
            flash(str(error), "error")
        else:
            flash(
                "Nota interna eliminada." if was_note else "Comentario eliminado.",
                "success",
            )

        return redirect(url_for("tickets.detail", public_id=public_id))

    return render_template(
        "tickets/comment_delete.html",
        ticket=ticket,
        comment=comment,
        form=form,
    )


def _visible_comment_or_404(ticket, comment_id: int):
    """Comentario del ticket que el usuario puede ver; 404 en cualquier otro
    caso (no existe, es de otro ticket, está eliminado o es una nota interna
    y el usuario es un Solicitante)."""
    comment = get_comment(ticket, comment_id, current_actor())

    if comment is None:
        abort(404)

    return comment
