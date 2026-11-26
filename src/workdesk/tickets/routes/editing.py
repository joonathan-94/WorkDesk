"""Edición de los datos y de la prioridad de un ticket (docs/06, RN-155) y
bloqueo temporal de edición (RN-163).

El bloqueo reserva el ticket mientras alguien lo edita. Es una mejora de la
experiencia: la barrera de integridad sigue siendo la versión del ticket,
que se comprueba siempre al guardar.
"""

from flask import (
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from ... import settings
from ...catalogs.service import list_locations, list_priorities
from ...cleaning import MAX_REASON_LENGTH
from ...configuration import value_of
from ...extensions import db
from ...models.ticket import MAX_DESCRIPTION_LENGTH, MAX_TITLE_LENGTH
from ...responses import json_error
from ...security import (
    can_change_priority,
    can_edit_ticket,
    can_revoke_edit_lock,
    current_actor,
)
from ...sla.evaluation import evaluate_ticket_sla
from ...users.forms import ReasonForm
from .. import bp
from ..editing import change_priority, update_ticket
from ..forms import PriorityChangeForm, TicketEditForm
from ..locking import (
    EditLockRevokedError,
    acquire_edit_lock,
    current_edit_lock,
    release_edit_lock,
    renew_edit_lock,
    revoke_edit_lock,
)
from ..service import TicketRuleError, categories_for_selection, location_required
from ..versioning import TicketClosedError, TicketConflictError
from .common import (
    catalog_label,
    choices_with_current,
    closed_redirect,
    ticket_is_closed,
    visible_ticket_or_404,
)


@bp.route("/<public_id>/edit", methods=["GET", "POST"])
@login_required
def edit_ticket(public_id: str):
    ticket = visible_ticket_or_404(public_id)

    # Quien ve el ticket pero no puede editarlo recibe un 403: la existencia
    # del ticket no es un secreto para él.
    if not can_edit_ticket(current_user):
        abort(403)

    if ticket_is_closed(ticket):
        return closed_redirect(ticket)

    # El ticket queda reservado para quien lo edita (RN-115): si otra persona
    # lo tiene, solo se puede consultar. La versión sigue siendo la barrera
    # final al guardar.
    holder = _hold_edit_lock(ticket)

    if holder is not None:
        return _render_locked(
            ticket,
            holder,
            title="Editar ticket",
            retry_url=url_for("tickets.edit_ticket", public_id=public_id),
            saved_nothing=request.method == "POST",
        )

    # Solo al abrir el formulario se rellena con los datos actuales; al
    # enviarlo manda lo que se envió.
    initial = _edit_initial_values(ticket) if request.method == "GET" else {}

    form = TicketEditForm(
        category_choices=[
            (category.id, catalog_label(category))
            for category in choices_with_current(
                categories_for_selection(),
                ticket.categoria,
            )
        ],
        location_choices=[
            (location.id, catalog_label(location))
            for location in choices_with_current(
                list_locations("activo"),
                ticket.ubicacion,
            )
        ],
        # Un ticket que ya tiene ubicación no puede quedarse sin ella si es obligatoria;
        # uno antiguo sin ubicación se sigue pudiendo editar tal cual.
        location_required=ticket.ubicacion_id is not None and location_required(),
        **initial,
    )

    if form.validate_on_submit():
        try:
            changed = update_ticket(
                ticket,
                actor=current_actor(),
                expected_version=form.version.data,
                title=form.titulo.data,
                description=form.descripcion.data,
                category_id=form.categoria.data,
                location_id=form.ubicacion.data,
            )
            # Terminó de editar: otra persona ya puede hacerlo.
            release_edit_lock(ticket, current_actor())
            db.session.commit()
        except TicketConflictError as error:
            # Otra persona lo modificó: se vuelven a mostrar los datos
            # actuales para no pisar su cambio sin haberlo visto.
            db.session.rollback()
            flash(str(error), "error")

            return redirect(url_for("tickets.edit_ticket", public_id=public_id))
        except TicketClosedError as error:
            db.session.rollback()
            flash(str(error), "error")

            return redirect(url_for("tickets.detail", public_id=public_id))
        except TicketRuleError as error:
            db.session.rollback()
            flash(str(error), "error")
        else:
            if changed:
                flash(f"Ticket #{public_id} actualizado.", "success")
            else:
                flash("No había cambios que guardar.", "warning")

            return redirect(url_for("tickets.detail", public_id=public_id))

    return render_template(
        "tickets/edit.html",
        ticket=ticket,
        form=form,
        max_title=MAX_TITLE_LENGTH,
        max_description=MAX_DESCRIPTION_LENGTH,
        **_lock_context(ticket),
    )


@bp.route("/<public_id>/priority", methods=["GET", "POST"])
@login_required
def change_ticket_priority(public_id: str):
    ticket = visible_ticket_or_404(public_id)

    if not can_change_priority(current_user):
        abort(403)

    if ticket_is_closed(ticket):
        return closed_redirect(ticket)

    holder = _hold_edit_lock(ticket)

    if holder is not None:
        return _render_locked(
            ticket,
            holder,
            title="Cambiar prioridad",
            retry_url=url_for("tickets.change_ticket_priority", public_id=public_id),
            saved_nothing=request.method == "POST",
        )

    initial = {"version": ticket.version} if request.method == "GET" else {}

    form = PriorityChangeForm(
        priority_choices=[
            (
                priority.id,
                f"{priority.nombre} (actual)"
                if priority.id == ticket.prioridad_id
                else priority.nombre,
            )
            for priority in choices_with_current(
                list_priorities("activo"),
                ticket.prioridad,
            )
        ],
        **initial,
    )

    if form.validate_on_submit():
        try:
            changed = change_priority(
                ticket,
                actor=current_actor(),
                expected_version=form.version.data,
                priority_id=form.prioridad.data,
                reason=form.motivo.data,
            )
            release_edit_lock(ticket, current_actor())
            db.session.commit()
        except TicketConflictError as error:
            db.session.rollback()
            flash(str(error), "error")

            return redirect(
                url_for("tickets.change_ticket_priority", public_id=public_id)
            )
        except TicketClosedError as error:
            db.session.rollback()
            flash(str(error), "error")

            return redirect(url_for("tickets.detail", public_id=public_id))
        except TicketRuleError as error:
            db.session.rollback()
            flash(str(error), "error")
        else:
            if changed:
                flash(
                    f"La prioridad del ticket #{public_id} se actualizó.",
                    "success",
                )
            else:
                flash("El ticket ya tiene esa prioridad.", "warning")

            return redirect(url_for("tickets.detail", public_id=public_id))

    return render_template(
        "tickets/priority.html",
        ticket=ticket,
        form=form,
        max_reason=MAX_REASON_LENGTH,
        # Para advertir antes de confirmar si el SLA está en riesgo (RN-88).
        sla=evaluate_ticket_sla(ticket.id),
        **_lock_context(ticket),
    )


def _hold_edit_lock(ticket):
    """Adquiere (o renueva) el bloqueo de edición para el usuario actual y lo
    confirma. Devuelve el bloqueo de **otra persona** si ella lo tiene, o None
    si ya es del usuario (RN-115)."""
    status = acquire_edit_lock(ticket, current_actor())
    db.session.commit()

    return None if status.mine else status.lock


def _render_locked(ticket, lock, *, title, retry_url, saved_nothing=False):
    """Pantalla de solo lectura: otra persona está editando el ticket (RN-116).
    Se puede consultar, pero no editar hasta que termine o el bloqueo expire."""
    if saved_nothing:
        flash(
            "No se guardó nada: otra persona está editando este ticket.",
            "warning",
        )

    return render_template(
        "tickets/edit_locked.html",
        ticket=ticket,
        lock=lock,
        can_revoke=can_revoke_edit_lock(current_user),
        title=title,
        retry_url=retry_url,
    )


def _lock_context(ticket) -> dict:
    """Lo que necesita la pantalla de edición para renovar y liberar el
    bloqueo mientras está abierta (mejora progresiva con JavaScript)."""
    return {
        "lock_renew_url": url_for("tickets.renew_ticket_lock", public_id=ticket.public_id),
        "lock_release_url": url_for(
            "tickets.release_ticket_lock", public_id=ticket.public_id
        ),
        "lock_heartbeat": value_of(settings.EDIT_LOCK_HEARTBEAT_SECONDS),
        "lock_ttl_minutes": max(
            1, round(value_of(settings.EDIT_LOCK_TTL_SECONDS) / 60)
        ),
    }


@bp.post("/<public_id>/lock/renew")
@login_required
def renew_ticket_lock(public_id: str):
    """Renueva el bloqueo de edición (latido de la pantalla de edición). Solo
    afecta al bloqueo del usuario; responde JSON. 409 si otra persona lo tiene."""
    ticket = visible_ticket_or_404(public_id)

    if not can_edit_ticket(current_user):
        abort(403)

    if ticket_is_closed(ticket):
        return json_error("ticket_closed", "El ticket está cerrado.", 409)

    try:
        status = renew_edit_lock(ticket, current_actor())
    except EditLockRevokedError as error:
        db.session.rollback()

        return json_error("lock_revoked", str(error), 409)

    db.session.commit()
    holder = None if status.mine else status.lock

    if holder is not None:
        return json_error(
            "lock_held",
            f"{holder.usuario.nombre} {holder.usuario.apellido} "
            "está editando este ticket.",
            409,
        )

    return jsonify(ok=True)


@bp.route("/<public_id>/lock/revoke", methods=["GET", "POST"])
@login_required
def revoke_ticket_lock(public_id: str):
    """Confirmación para liberar el bloqueo de edición de otra persona (RN-176)."""
    ticket = visible_ticket_or_404(public_id)

    if not can_revoke_edit_lock(current_user):
        abort(403)

    back = url_for("tickets.detail", public_id=ticket.public_id)
    lock = current_edit_lock(ticket)

    if lock is None or lock.usuario_id == current_user.id:
        flash("Ya no hay un bloqueo de otra persona que liberar.", "info")

        return redirect(back)

    form = ReasonForm()

    if form.validate_on_submit():
        try:
            holder = revoke_edit_lock(ticket, current_actor(), form.motivo.data)
        except TicketRuleError as error:
            db.session.rollback()
            flash(str(error), "info")

            return redirect(back)

        db.session.commit()
        flash(
            f"Se liberó el bloqueo de {holder.nombre} {holder.apellido}.", "success"
        )

        return redirect(back)

    return render_template(
        "tickets/lock_revoke.html",
        ticket=ticket,
        lock=lock,
        form=form,
        max_reason=MAX_REASON_LENGTH,
    )


@bp.post("/<public_id>/lock/release")
@login_required
def release_ticket_lock(public_id: str):
    """Libera el bloqueo del usuario (al cancelar o salir de la pantalla). Nunca
    toca el de otra persona; liberar sin tener bloqueo no es un error."""
    ticket = visible_ticket_or_404(public_id)

    if not can_edit_ticket(current_user):
        abort(403)

    released = release_edit_lock(ticket, current_actor())
    db.session.commit()

    return jsonify(ok=True, released=released)


def _edit_initial_values(ticket) -> dict:
    """Valores con los que arranca el formulario de edición."""
    return {
        "titulo": ticket.titulo,
        "descripcion": ticket.descripcion,
        "categoria": ticket.categoria_id,
        "ubicacion": ticket.ubicacion_id,
        "version": ticket.version,
    }
