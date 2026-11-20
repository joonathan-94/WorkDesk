"""Pantallas de administración de los estados y las transiciones del flujo
(docs/11, UI-021). Las reglas están en `catalogs/flow.py`; aquí solo se
orquesta. Como el resto del área de administración, todas las rutas son
exclusivas del Administrador y la autorización se comprueba en backend."""

from flask import abort, flash, redirect, render_template, url_for

from ..extensions import db
from ..security import admin_only, current_actor
from ..users.forms import ReasonForm
from . import bp
from .flow import (
    ALREADY_DISABLED,
    ALREADY_ENABLED,
    activate_transition,
    count_tickets_by_state,
    deactivate_transition,
    describe_transition,
    get_state,
    get_transition,
    group_by_origin,
    list_states,
    list_transitions,
    transition_blocker,
    update_state,
)
from .forms import MAX_STATE_DESCRIPTION_LENGTH, MAX_STATE_NAME_LENGTH, StateForm
from .service import CatalogRuleError, DuplicateNameError

STATES_ENDPOINT = "catalogs.states_page"


@bp.get("/states")
@admin_only
def states_page():
    return render_template(
        "catalogs/states.html",
        states=list_states(),
        ticket_counts=count_tickets_by_state(),
        groups=group_by_origin(list_transitions()),
    )


@bp.route("/states/<int:state_id>/edit", methods=["GET", "POST"])
@admin_only
def state_edit(state_id: int):
    state = get_state(state_id)

    if state is None:
        abort(404)

    # En GET rellena el formulario con los datos actuales; en POST manda lo
    # enviado.
    form = StateForm(obj=state)

    if form.validate_on_submit():
        try:
            changed = update_state(
                state,
                actor=current_actor(),
                nombre_visible=form.nombre_visible.data,
                descripcion=form.descripcion.data,
            )
            db.session.commit()
        except DuplicateNameError as error:
            db.session.rollback()
            form.nombre_visible.errors.append(str(error))
        except CatalogRuleError as error:
            db.session.rollback()
            flash(str(error), "error")
        else:
            if changed:
                flash(f"El estado «{state.nombre_visible}» se actualizó.", "success")
            else:
                flash("No había cambios que guardar.", "warning")

            return redirect(url_for(STATES_ENDPOINT))

    return render_template(
        "catalogs/state_form.html",
        state=state,
        form=form,
        max_name=MAX_STATE_NAME_LENGTH,
        max_description=MAX_STATE_DESCRIPTION_LENGTH,
    )


@bp.route("/transitions/<int:transition_id>/deactivate", methods=["GET", "POST"])
@admin_only
def transition_deactivate(transition_id: int):
    return _transition_status_page(transition_id, deactivate=True)


@bp.route("/transitions/<int:transition_id>/activate", methods=["GET", "POST"])
@admin_only
def transition_activate(transition_id: int):
    return _transition_status_page(transition_id, deactivate=False)


def _transition_status_page(transition_id: int, *, deactivate: bool):
    """Confirmación y ejecución de habilitar o deshabilitar una transición."""
    transition = get_transition(transition_id)

    if transition is None:
        abort(404)

    # Se comprueba también en GET para no mostrar una confirmación de algo que
    # no se puede hacer.
    if deactivate:
        if not transition.activa:
            return _blocked(ALREADY_DISABLED)

        blocker = transition_blocker(transition)

        if blocker is not None:
            return _blocked(blocker)
    elif transition.activa:
        return _blocked(ALREADY_ENABLED)

    form = ReasonForm()
    description = describe_transition(transition)

    if form.validate_on_submit():
        operation = deactivate_transition if deactivate else activate_transition

        try:
            operation(transition, actor=current_actor(), reason=form.motivo.data)
            db.session.commit()
        except CatalogRuleError as error:
            return _blocked(str(error))

        flash(
            f"La transición «{description}» fue "
            f"{'deshabilitada' if deactivate else 'habilitada'}.",
            "success",
        )

        return redirect(url_for(STATES_ENDPOINT))

    return render_template(
        "catalogs/transition_confirm.html",
        transition=transition,
        description=description,
        form=form,
        deactivating=deactivate,
    )


def _blocked(message: str):
    """Una regla impide la acción: avisa y vuelve a la pantalla de estados."""
    db.session.rollback()
    flash(message, "error")

    return redirect(url_for(STATES_ENDPOINT))
