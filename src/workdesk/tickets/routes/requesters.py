"""Solicitantes de un ticket ya creado: agregar y retirar (docs/06, RN-158).
"""

from flask import abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from ...cleaning import MAX_REASON_LENGTH
from ...security import can_manage_requesters, current_actor
from ...users.forms import ReasonForm
from .. import bp
from ..forms import RequesterPickForm
from ..requesters import add_requester, list_addable_requesters, remove_requester
from .common import (
    CLOSED_MODIFY_MESSAGE,
    closed_redirect,
    requester_choices,
    run_ticket_operation,
    ticket_is_closed,
    visible_ticket_or_404,
)


@bp.get("/<public_id>/requesters")
@login_required
def requesters_page(public_id: str):
    """Solicitantes del ticket: el personal los ve, agrega y retira."""
    ticket = visible_ticket_or_404(public_id)

    if not can_manage_requesters(current_user):
        abort(403)

    if ticket_is_closed(ticket):
        return closed_redirect(ticket, CLOSED_MODIFY_MESSAGE)

    return render_template(
        "tickets/requesters.html",
        ticket=ticket,
        requester_form=RequesterPickForm(
            choices=requester_choices(list_addable_requesters(ticket))
        ),
    )


@bp.post("/<public_id>/requesters/add")
@login_required
def add_ticket_requester(public_id: str):
    ticket = visible_ticket_or_404(public_id)

    if not can_manage_requesters(current_user):
        abort(403)

    form = RequesterPickForm(
        choices=requester_choices(list_addable_requesters(ticket))
    )

    if not form.validate_on_submit():
        flash(
            form.solicitante.errors[0]
            if form.solicitante.errors
            else "No se pudo agregar al solicitante.",
            "error",
        )

        return redirect(url_for("tickets.requesters_page", public_id=public_id))

    return run_ticket_operation(
        ticket,
        lambda: add_requester(ticket, form.solicitante.data, actor=current_actor()),
        "Solicitante agregado.",
        back="tickets.requesters_page",
    )


@bp.route(
    "/<public_id>/requesters/<int:participation_id>/remove",
    methods=["GET", "POST"],
)
@login_required
def remove_ticket_requester(public_id: str, participation_id: int):
    """Confirmación (con motivo opcional) para retirar a un solicitante.

    Retirarlo le quita el acceso al ticket, así que no es un clic sin más (a
    diferencia de quitar un técnico, que es solo organizativo).
    """
    ticket = visible_ticket_or_404(public_id)

    if not can_manage_requesters(current_user):
        abort(403)

    if ticket_is_closed(ticket):
        return closed_redirect(ticket, CLOSED_MODIFY_MESSAGE)

    link = next(
        (r for r in ticket.solicitantes_vigentes if r.id == participation_id),
        None,
    )

    if link is None:
        flash("Esa persona ya no es solicitante del ticket.", "error")

        return redirect(url_for("tickets.requesters_page", public_id=public_id))

    form = ReasonForm()

    if form.validate_on_submit():
        name = f"{link.solicitante.nombre} {link.solicitante.apellido}"

        return run_ticket_operation(
            ticket,
            lambda: remove_requester(
                ticket,
                participation_id,
                actor=current_actor(),
                reason=form.motivo.data,
            ),
            f"{name} dejó de ser solicitante del ticket.",
            back="tickets.requesters_page",
        )

    return render_template(
        "tickets/requester_remove.html",
        ticket=ticket,
        link=link,
        form=form,
        max_reason=MAX_REASON_LENGTH,
    )
