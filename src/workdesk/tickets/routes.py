from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..catalogs.service import list_locations, list_priorities
from ..extensions import db
from ..models.ticket import MAX_DESCRIPTION_LENGTH, MAX_TITLE_LENGTH
from ..security import (
    STAFF_ROLES,
    can_choose_requesters,
    can_create_ticket,
    can_view_ticket,
    has_any_role,
)
from . import bp
from .forms import TicketForm
from .service import (
    TicketRuleError,
    categories_for_selection,
    create_ticket,
    get_ticket_by_public_id,
    list_requester_candidates,
    list_ticket_history,
)

# Prioridad que se ofrece preseleccionada al crear un ticket (docs/11, UI-004).
DEFAULT_PRIORITY_CODE = "MEDIA"


# --- Creación ---------------------------------------------------------


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new_ticket():
    # La autorización se comprueba en backend; ocultar el enlace no basta.
    if not can_create_ticket(current_user):
        abort(403)

    choose_requesters = can_choose_requesters(current_user)
    priorities = list_priorities("activo")

    form = TicketForm(
        category_choices=[
            (category.id, category.nombre)
            for category in categories_for_selection()
        ],
        priority_choices=[
            (priority.id, priority.nombre) for priority in priorities
        ],
        location_choices=[
            (location.id, location.nombre)
            for location in list_locations("activo")
        ],
        requester_choices=(
            [
                (user.id, f"{user.apellido}, {user.nombre} ({user.username})")
                for user in list_requester_candidates()
            ]
            if choose_requesters
            else None
        ),
        # Solo al abrir el formulario: un envío sin prioridad debe fallar en
        # lugar de quedar en Media sin que nadie la haya elegido.
        **_initial_values(priorities, is_new_form=request.method == "GET"),
    )

    if form.validate_on_submit():
        # El Solicitante siempre es su propio solicitante; el personal
        # elige a quién (puede ser nadie).
        requester_ids = (
            form.solicitantes.data if choose_requesters else [current_user.id]
        )

        try:
            ticket = create_ticket(
                actor=_actor(),
                title=form.titulo.data,
                description=form.descripcion.data,
                category_id=form.categoria.data,
                priority_id=form.prioridad.data,
                location_id=form.ubicacion.data,
                requester_ids=requester_ids,
            )
            db.session.commit()
        except TicketRuleError as error:
            # Por ejemplo, un valor de catálogo desactivado mientras se
            # rellenaba el formulario.
            db.session.rollback()
            flash(str(error), "error")
        else:
            flash(f"Ticket #{ticket.public_id} creado correctamente.", "success")

            return redirect(
                url_for("tickets.detail", public_id=ticket.public_id)
            )

    return render_template(
        "tickets/new.html",
        form=form,
        choose_requesters=choose_requesters,
        max_title=MAX_TITLE_LENGTH,
        max_description=MAX_DESCRIPTION_LENGTH,
    )


# --- Detalle ----------------------------------------------------------


@bp.get("/<public_id>")
@login_required
def detail(public_id: str):
    # Un identificador que no sea un número no puede existir.
    if not (public_id.isascii() and public_id.isdecimal()):
        abort(404)

    ticket = get_ticket_by_public_id(public_id)

    # Un ticket ajeno responde igual que uno inexistente (404): los números
    # son correlativos y, con un 403, cualquiera podría descubrir cuáles
    # existen.
    if ticket is None or not can_view_ticket(current_user, ticket):
        abort(404)

    return render_template(
        "tickets/detail.html",
        ticket=ticket,
        history=list_ticket_history(ticket),
        is_staff=has_any_role(current_user, *STAFF_ROLES),
    )


# --- Utilidades -------------------------------------------------------


def _initial_values(priorities, *, is_new_form: bool) -> dict:
    """Valores con los que arranca el formulario recién abierto."""
    if not is_new_form:
        return {}

    default = next(
        (p for p in priorities if p.codigo == DEFAULT_PRIORITY_CODE),
        None,
    )

    return {} if default is None else {"prioridad": default.id}


def _actor():
    return current_user._get_current_object()
