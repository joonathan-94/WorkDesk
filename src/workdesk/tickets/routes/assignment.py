"""Asignación de técnicos, grupo del ticket y escalamiento (docs/06, RN-157).
"""

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ...extensions import db
from ...security import can_assign_self, can_manage_assignments, current_actor
from .. import bp
from ..assignment import (
    assign_technician,
    escalate_ticket,
    list_assignable_technicians,
    list_escalation_technicians,
    list_groups_for_ticket,
    set_group,
    unassign_technician,
)
from ..editing import MAX_REASON_LENGTH
from ..forms import EscalationForm, GroupChangeForm, TechnicianPickForm
from ..service import TicketRuleError
from ..versioning import TicketClosedError, TicketConflictError
from .common import (
    CLOSED_MODIFY_MESSAGE,
    closed_redirect,
    my_assignment,
    run_ticket_operation,
    ticket_is_closed,
    visible_ticket_or_404,
)


@bp.post("/<public_id>/assign-me")
@login_required
def assign_me(public_id: str):
    """Un Técnico se asigna a sí mismo el ticket."""
    ticket = visible_ticket_or_404(public_id)

    if not can_assign_self(current_user):
        abort(403)

    return run_ticket_operation(
        ticket,
        lambda: assign_technician(ticket, current_user.id, actor=current_actor()),
        f"Te asignaste el ticket #{public_id}.",
        back="tickets.detail",
    )


@bp.post("/<public_id>/unassign-me")
@login_required
def unassign_me(public_id: str):
    """Un Técnico deja de estar asignado al ticket."""
    ticket = visible_ticket_or_404(public_id)

    if not can_assign_self(current_user):
        abort(403)

    mine = my_assignment(ticket)

    if mine is None:
        flash("No estás asignado a este ticket.", "warning")

        return redirect(url_for("tickets.detail", public_id=public_id))

    return run_ticket_operation(
        ticket,
        lambda: unassign_technician(ticket, mine.id, actor=current_actor()),
        f"Dejaste de estar asignado al ticket #{public_id}.",
        back="tickets.detail",
    )


@bp.get("/<public_id>/assignment")
@login_required
def assignment_page(public_id: str):
    """Técnicos y grupo del ticket (Supervisor y Administrador)."""
    ticket = visible_ticket_or_404(public_id)

    if not can_manage_assignments(current_user):
        abort(403)

    if ticket_is_closed(ticket):
        return closed_redirect(ticket, CLOSED_MODIFY_MESSAGE)

    technician_form = TechnicianPickForm(
        choices=_people(list_assignable_technicians(ticket))
    )
    group_form = GroupChangeForm(
        choices=_group_choices(ticket),
        version=ticket.version,
        grupo=ticket.grupo_id,
    )

    return render_template(
        "tickets/assignment.html",
        ticket=ticket,
        technician_form=technician_form,
        group_form=group_form,
    )


@bp.post("/<public_id>/assignment/technicians/add")
@login_required
def add_ticket_technician(public_id: str):
    ticket = visible_ticket_or_404(public_id)

    if not can_manage_assignments(current_user):
        abort(403)

    form = TechnicianPickForm(
        choices=_people(list_assignable_technicians(ticket))
    )

    if not form.validate_on_submit():
        flash(
            form.tecnico.errors[0]
            if form.tecnico.errors
            else "No se pudo asignar.",
            "error",
        )

        return redirect(url_for("tickets.assignment_page", public_id=public_id))

    return run_ticket_operation(
        ticket,
        lambda: assign_technician(ticket, form.tecnico.data, actor=current_actor()),
        "Técnico asignado.",
        back="tickets.assignment_page",
    )


@bp.post("/<public_id>/assignment/technicians/<int:assignment_id>/remove")
@login_required
def remove_ticket_technician(public_id: str, assignment_id: int):
    ticket = visible_ticket_or_404(public_id)
    assignment = next(
        (a for a in ticket.tecnicos_vigentes if a.id == assignment_id),
        None,
    )

    # Supervisor y Administrador quitan a cualquiera; un Técnico, solo a sí
    # mismo.
    is_own = (
        assignment is not None
        and can_assign_self(current_user)
        and assignment.tecnico_id == current_user.id
    )

    if not (can_manage_assignments(current_user) or is_own):
        abort(403)

    return run_ticket_operation(
        ticket,
        lambda: unassign_technician(
            ticket,
            assignment_id,
            actor=current_actor(),
            reason=request.form.get("motivo"),
        ),
        "Técnico desasignado.",
        back=(
            "tickets.assignment_page"
            if can_manage_assignments(current_user)
            else "tickets.detail"
        ),
    )


@bp.post("/<public_id>/assignment/group")
@login_required
def set_ticket_group(public_id: str):
    ticket = visible_ticket_or_404(public_id)

    if not can_manage_assignments(current_user):
        abort(403)

    form = GroupChangeForm(choices=_group_choices(ticket))

    if not form.validate_on_submit():
        flash(
            (form.grupo.errors or form.version.errors or ["No se pudo cambiar."])[0],
            "error",
        )

        return redirect(url_for("tickets.assignment_page", public_id=public_id))

    holder = {}

    def run():
        holder["changed"] = set_group(
            ticket,
            form.grupo.data,
            actor=current_actor(),
            expected_version=form.version.data,
        )

    response = run_ticket_operation(
        ticket,
        run,
        "El grupo del ticket se actualizó.",
        back="tickets.assignment_page",
        quiet=True,
    )

    if holder.get("changed") is False:
        flash("El ticket ya tiene ese grupo.", "warning")
    elif holder.get("changed"):
        flash("El grupo del ticket se actualizó.", "success")

    return response


@bp.route("/<public_id>/escalate", methods=["GET", "POST"])
@login_required
def escalate(public_id: str):
    ticket = visible_ticket_or_404(public_id)

    if not can_manage_assignments(current_user):
        abort(403)

    if ticket_is_closed(ticket):
        return closed_redirect(ticket, CLOSED_MODIFY_MESSAGE)

    initial = {"version": ticket.version} if request.method == "GET" else {}

    form = EscalationForm(
        group_choices=_group_choices(ticket, active_only=True),
        technician_choices=_people(list_escalation_technicians()),
        **initial,
    )

    if form.validate_on_submit():
        try:
            escalate_ticket(
                ticket,
                actor=current_actor(),
                expected_version=form.version.data,
                group_id=form.grupo.data,
                technician_id=form.tecnico.data,
                reason=form.motivo.data,
            )
            db.session.commit()
        except TicketConflictError as error:
            db.session.rollback()
            flash(str(error), "error")

            return redirect(url_for("tickets.escalate", public_id=public_id))
        except TicketClosedError as error:
            db.session.rollback()
            flash(str(error), "error")

            return redirect(url_for("tickets.detail", public_id=public_id))
        except TicketRuleError as error:
            db.session.rollback()
            flash(str(error), "error")
        else:
            flash(f"El ticket #{public_id} fue escalado.", "success")

            return redirect(url_for("tickets.detail", public_id=public_id))

    return render_template(
        "tickets/escalate.html",
        ticket=ticket,
        form=form,
        max_reason=MAX_REASON_LENGTH,
    )


def _people(users) -> list[tuple[int, str]]:
    return [(user.id, f"{user.nombre} {user.apellido}") for user in users]


def _group_choices(ticket, *, active_only=False) -> list[tuple[int, str]]:
    groups = list_groups_for_ticket(ticket)

    if active_only:
        groups = [g for g in groups if g.activo]

    return [(g.id, g.nombre if g.activo else f"{g.nombre} (inactivo)") for g in groups]
