"""Cambios de estado: iniciar, poner en espera, reactivar, resolver, cerrar,
confirmar, rechazar y reabrir (docs/06, RN-156 y RN-161).

Una sola ruta (`/tickets/<n>/status/<acción>`) para todas las acciones: qué
pide cada una y quién la ejecuta está declarado en
`tickets/state_actions.py`.
"""

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ...catalogs.service import list_wait_reasons
from ...extensions import db
from ...models import StateAction
from ...security import current_actor
from .. import bp
from ..forms import StateChangeForm
from ..lifecycle import (
    StateTransitionError,
    available_actions,
    change_state,
    list_close_reasons,
)
from ..service import TicketRuleError
from ..state_actions import ACTION_BY_SLUG
from ..versioning import TicketClosedError, TicketConflictError
from .common import (
    CLOSED_MODIFY_MESSAGE,
    closed_redirect,
    ticket_is_closed,
    visible_ticket_or_404,
)


@bp.route("/<public_id>/status/<action_slug>", methods=["GET", "POST"])
@login_required
def change_ticket_state(public_id: str, action_slug: str):
    ticket = visible_ticket_or_404(public_id)
    info = ACTION_BY_SLUG.get(action_slug)

    # Una acción que no existe es un 404; una que existe pero el rol no
    # puede ejecutar, un 403 (quien ve el ticket no necesita que se le oculte).
    if info is None:
        abort(404)

    if not info.policy(current_user, ticket):
        abort(403)

    # Un ticket cerrado solo admite reabrirlo.
    if ticket_is_closed(ticket) and info.action is not StateAction.REABRIR:
        return closed_redirect(ticket, CLOSED_MODIFY_MESSAGE)

    # Se comprueba también en GET: una pantalla abierta antes de que otra
    # persona cambiara el estado ya no corresponde al ticket.
    option = next(
        (a for a in available_actions(ticket, current_user) if a.info is info),
        None,
    )

    if option is None:
        flash(
            "Esta acción no está disponible para el estado actual del ticket.",
            "error",
        )

        return redirect(url_for("tickets.detail", public_id=public_id))

    wait_reasons = list_wait_reasons("activo") if info.allows_wait_reason else []
    close_reasons = list_close_reasons(info)
    initial = {"version": ticket.version} if request.method == "GET" else {}

    form = StateChangeForm(
        wait_reason_choices=[(reason.id, reason.nombre) for reason in wait_reasons],
        close_reason_choices=[(reason.id, reason.nombre) for reason in close_reasons],
        text_max=info.text_max,
        text_required=info.text_required,
        text_required_message=info.text_required_message,
        **initial,
    )

    if form.validate_on_submit():
        try:
            new_state = change_state(
                ticket,
                actor=current_actor(),
                action=info.action,
                expected_version=form.version.data,
                wait_reason_id=form.motivo_espera.data,
                close_reason_id=form.motivo_cierre.data,
                text=form.texto.data,
            )
            db.session.commit()
        except TicketConflictError as error:
            # Otra persona lo modificó: se vuelve a abrir la pantalla con los
            # datos actuales (si la acción ya no corresponde, avisa).
            db.session.rollback()
            flash(str(error), "error")

            return redirect(
                url_for(
                    "tickets.change_ticket_state",
                    public_id=public_id,
                    action_slug=action_slug,
                )
            )
        except TicketClosedError as error:
            db.session.rollback()
            flash(str(error), "error")

            return redirect(url_for("tickets.detail", public_id=public_id))
        except StateTransitionError as error:
            db.session.rollback()
            flash(str(error), "error")

            return redirect(url_for("tickets.detail", public_id=public_id))
        except TicketRuleError as error:
            db.session.rollback()
            flash(str(error), "error")
        else:
            flash(
                info.success_message.format(
                    number=public_id,
                    state=new_state.nombre_visible,
                ),
                "success",
            )

            return redirect(url_for("tickets.detail", public_id=public_id))

    return render_template(
        "tickets/state_change.html",
        ticket=ticket,
        form=form,
        info=info,
        destination=option.destination,
        wait_reasons=wait_reasons,
        close_reasons=close_reasons,
        max_text=info.text_max,
    )
