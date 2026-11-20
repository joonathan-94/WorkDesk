"""Relaciones entre tickets y duplicados; solo para el personal (docs/06,
RN-162).
"""

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm

from ...extensions import db
from ...models import StateAction
from ...security import can_manage_relations, current_actor
from .. import bp
from ..forms import DuplicateForm, RelationForm
from ..lifecycle import available_actions
from ..relations import (
    KIND_DUPLICATE_OF,
    KIND_PRINCIPAL_OF,
    KIND_RELATED,
    MAX_RELATION_COMMENT_LENGTH,
    add_relation,
    list_relations,
    mark_duplicate,
    parse_ticket_number,
    remove_relation,
)
from ..service import TicketRuleError
from ..versioning import TicketClosedError, TicketConflictError
from .common import (
    CLOSED_MODIFY_MESSAGE,
    closed_redirect,
    run_ticket_operation,
    ticket_is_closed,
    visible_ticket_or_404,
)


@bp.get("/<public_id>/relations")
@login_required
def relations_page(public_id: str):
    """Relaciones del ticket: las vigentes, el formulario para relacionarlo con
    otro ticket y el acceso a «Marcar como duplicado». Solo el personal."""
    ticket = visible_ticket_or_404(public_id)

    if not can_manage_relations(current_user):
        abort(403)

    return _render_relations(ticket, RelationForm())


def _render_relations(ticket, form):
    return render_template(
        "tickets/relations.html",
        ticket=ticket,
        form=form,
        views=list_relations(ticket),
        is_closed=ticket_is_closed(ticket),
        max_comment=MAX_RELATION_COMMENT_LENGTH,
        KIND_DUPLICATE_OF=KIND_DUPLICATE_OF,
        KIND_PRINCIPAL_OF=KIND_PRINCIPAL_OF,
        KIND_RELATED=KIND_RELATED,
    )


@bp.post("/<public_id>/relations/add")
@login_required
def add_ticket_relation(public_id: str):
    ticket = visible_ticket_or_404(public_id)

    if not can_manage_relations(current_user):
        abort(403)

    form = RelationForm()

    if not form.validate_on_submit():
        flash(
            next(iter(form.ticket.errors or form.comentario.errors), None)
            or "No se pudo relacionar el ticket.",
            "error",
        )

        return redirect(url_for("tickets.relations_page", public_id=public_id))

    try:
        other = parse_ticket_number(form.ticket.data)
    except TicketRuleError as error:
        flash(str(error), "error")

        return redirect(url_for("tickets.relations_page", public_id=public_id))

    return run_ticket_operation(
        ticket,
        lambda: add_relation(
            ticket,
            other,
            actor=current_actor(),
            comment=form.comentario.data,
        ),
        f"El ticket #{public_id} quedó relacionado con el #{other}.",
        back="tickets.relations_page",
    )


@bp.route(
    "/<public_id>/relations/<int:relation_id>/remove",
    methods=["GET", "POST"],
)
@login_required
def remove_ticket_relation(public_id: str, relation_id: int):
    """Confirmación para quitar una relación. La de un duplicado que sigue
    cerrado no se quita."""
    ticket = visible_ticket_or_404(public_id)

    if not can_manage_relations(current_user):
        abort(403)

    if ticket_is_closed(ticket):
        return closed_redirect(ticket, CLOSED_MODIFY_MESSAGE)

    view = next(
        (
            v
            for v in list_relations(ticket)
            if v.relation.id == relation_id and v.removable
        ),
        None,
    )

    if view is None:
        flash("Esa relación ya no existe o no se puede quitar.", "error")

        return redirect(url_for("tickets.relations_page", public_id=public_id))

    form = FlaskForm()

    if form.validate_on_submit():
        return run_ticket_operation(
            ticket,
            lambda: remove_relation(ticket, relation_id, actor=current_actor()),
            f"Se quitó la relación con el ticket #{view.other.public_id}.",
            back="tickets.relations_page",
        )

    return render_template(
        "tickets/relation_remove.html",
        ticket=ticket,
        view=view,
        form=form,
    )


@bp.route("/<public_id>/duplicate", methods=["GET", "POST"])
@login_required
def mark_ticket_duplicate(public_id: str):
    """Marca el ticket como duplicado de otro: crea la relación y lo cierra con
    el motivo «Duplicado». Es una pantalla de confirmación (cierra el ticket)."""
    ticket = visible_ticket_or_404(public_id)

    if not can_manage_relations(current_user):
        abort(403)

    if ticket_is_closed(ticket):
        return closed_redirect(ticket, CLOSED_MODIFY_MESSAGE)

    # Se comprueba también en GET: un ticket Resuelto no se cierra de forma
    # directa, así que no tiene sentido ofrecer la pantalla. De paso se
    # obtiene el estado al que pasará (el nombre lo puede cambiar el
    # Administrador).
    close_option = next(
        (
            option
            for option in available_actions(ticket, current_user)
            if option.info.action is StateAction.CIERRE_DIRECTO
        ),
        None,
    )

    if close_option is None:
        flash(
            "Este ticket no se puede cerrar como duplicado desde su estado "
            "actual.",
            "error",
        )

        return redirect(url_for("tickets.relations_page", public_id=public_id))

    initial = {"version": ticket.version} if request.method == "GET" else {}
    form = DuplicateForm(**initial)

    if form.validate_on_submit():
        try:
            principal = parse_ticket_number(form.ticket.data)

            mark_duplicate(
                ticket,
                principal,
                actor=current_actor(),
                expected_version=form.version.data,
                comment=form.comentario.data,
            )
            db.session.commit()
        except TicketConflictError as error:
            db.session.rollback()
            flash(str(error), "error")

            return redirect(
                url_for("tickets.mark_ticket_duplicate", public_id=public_id)
            )
        except TicketClosedError as error:
            db.session.rollback()
            flash(str(error), "error")

            return redirect(url_for("tickets.detail", public_id=public_id))
        except TicketRuleError as error:
            db.session.rollback()
            flash(str(error), "error")
        else:
            flash(
                f"El ticket #{public_id} quedó cerrado como duplicado del "
                f"#{principal}.",
                "success",
            )

            return redirect(url_for("tickets.detail", public_id=public_id))

    return render_template(
        "tickets/duplicate.html",
        ticket=ticket,
        form=form,
        destination=close_option.destination,
        max_comment=MAX_RELATION_COMMENT_LENGTH,
    )
