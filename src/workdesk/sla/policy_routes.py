"""Pantallas de los objetivos de SLA por prioridad (docs/11, UI-022). Las reglas
están en `sla/policies.py`; aquí solo se orquesta. El listado vive en la propia
pantalla «SLA» (`sla.index`) y cada acción tiene su pantalla, sin modales, como el
resto del área de administración. Todas las rutas son exclusivas del
Administrador y la autorización se comprueba en backend.

Se identifica la política por su **prioridad** (`/admin/sla/priorities/<id>/...`):
hay una por prioridad y una prioridad sin política también tiene su pantalla, la de
definirla.
"""

from flask import abort, flash, redirect, render_template, request, url_for

from ..extensions import db
from ..security import admin_only, current_actor
from ..users.forms import ReasonForm
from . import bp
from .policies import (
    PolicyConflictError,
    PolicyRuleError,
    SaveOutcome,
    activate_policy,
    deactivate_policy,
    get_policy,
    get_priority,
    on_hold_state_name,
    save_policy,
)
from .policy_forms import PolicyForm, policy_form_data

INDEX_ENDPOINT = "sla.index"
EDIT_ENDPOINT = "sla.policy_edit"


@bp.route("/priorities/<int:priority_id>/edit", methods=["GET", "POST"])
@admin_only
def policy_edit(priority_id: int):
    """Define u edita los objetivos de SLA de la prioridad."""
    priority = _priority_or_404(priority_id)
    policy = get_policy(priority)

    # Los valores vigentes rellenan el formulario solo al abrirlo. En un envío
    # manda lo que llegó: si faltara la marca de la política, no debe completarse
    # sola con la vigente, porque entonces no se detectaría que la pantalla estaba
    # desactualizada.
    if request.method == "POST":
        form = PolicyForm()
    else:
        form = PolicyForm(data=policy_form_data(policy))

    if form.validate_on_submit():
        try:
            result = save_policy(
                priority,
                actor=current_actor(),
                base_token=form.base.data,
                response_minutes=form.response_minutes,
                resolution_minutes=form.resolution_minutes,
                warning_percent=form.umbral_aviso.data,
                pause_on_hold=form.pausa_en_espera.data,
                reason=form.motivo.data,
            )
            db.session.commit()
        except PolicyConflictError as error:
            db.session.rollback()
            flash(str(error), "error")

            # Se vuelve al formulario con lo vigente. Lo escrito se pierde a
            # propósito: reenviarlo pisaría un cambio que no se ha visto.
            return redirect(url_for(EDIT_ENDPOINT, priority_id=priority_id))
        except PolicyRuleError as error:
            db.session.rollback()
            _show_rule_error(form, error)
        else:
            _flash_saved(result.outcome, priority.nombre)

            return redirect(url_for(INDEX_ENDPOINT))

    return render_template(
        "sla/policy_form.html",
        form=form,
        priority=priority,
        policy=policy,
        on_hold_name=on_hold_state_name(),
    )


@bp.route("/priorities/<int:priority_id>/deactivate", methods=["GET", "POST"])
@admin_only
def policy_deactivate(priority_id: int):
    return _status_page(priority_id, deactivate=True)


@bp.route("/priorities/<int:priority_id>/activate", methods=["GET", "POST"])
@admin_only
def policy_activate(priority_id: int):
    return _status_page(priority_id, deactivate=False)


# --- Piezas comunes -----------------------------------------------------------


def _status_page(priority_id: int, *, deactivate: bool):
    """Confirmación y ejecución de desactivar o reactivar una política."""
    priority = _priority_or_404(priority_id)
    policy = get_policy(priority)

    # Se comprueba también en GET para no mostrar una confirmación de algo que no
    # se puede hacer.
    if policy is None:
        return _blocked("Esta prioridad todavía no tiene una política de SLA.")

    if deactivate and not policy.activo:
        return _blocked("La política ya está desactivada.")

    if not deactivate and policy.activo:
        return _blocked("La política ya está activa.")

    form = ReasonForm()

    if form.validate_on_submit():
        name = priority.nombre
        operation = deactivate_policy if deactivate else activate_policy

        try:
            operation(priority, actor=current_actor(), reason=form.motivo.data)
            db.session.commit()
        except PolicyRuleError as error:
            return _blocked(str(error))

        verb = "desactivado" if deactivate else "reactivado"
        flash(f"SLA de la prioridad «{name}» {verb}.", "success")

        return redirect(url_for(INDEX_ENDPOINT))

    return render_template(
        "sla/policy_status.html",
        form=form,
        priority=priority,
        deactivating=deactivate,
    )


def _blocked(message: str):
    """Una regla impide la acción: avisa y vuelve a la pantalla «SLA»."""
    db.session.rollback()
    flash(message, "error")

    return redirect(url_for(INDEX_ENDPOINT))


def _flash_saved(outcome: SaveOutcome, name: str) -> None:
    if outcome is SaveOutcome.CREATED:
        flash(f"SLA de la prioridad «{name}» definido.", "success")
    elif outcome is SaveOutcome.UPDATED:
        flash(f"SLA de la prioridad «{name}» actualizado.", "success")
    else:
        flash("No había cambios que guardar.", "warning")


def _show_rule_error(form: PolicyForm, error: PolicyRuleError) -> None:
    """Deja el error junto a su campo; si no es de un campo, como aviso."""
    field = getattr(form, error.field, None) if error.field else None

    if field is None:
        flash(str(error), "error")
    else:
        field.errors = [*field.errors, str(error)]


def _priority_or_404(priority_id: int):
    priority = get_priority(priority_id)

    if priority is None:
        abort(404)

    return priority
