"""Las pantallas de configuración (`/admin/settings/<grupo>`), solo del Administrador.

Una pantalla guarda todos sus campos a la vez (así dos parámetros relacionados se cambian
juntos) y solo escribe y audita los que cambiaron. Las reglas están en `configuration.py`;
aquí se traduce a la pantalla.
"""

from flask import abort, flash, redirect, render_template, request, url_for
from wtforms import BooleanField, HiddenField
from wtforms.validators import InputRequired

from ..catalogs.forms import OptionalIntegerField
from ..cleaning import MAX_REASON_LENGTH
from ..configuration import (
    SettingConflictError,
    SettingRuleError,
    has_own_value,
    initial_value,
    reset_setting,
    save_settings,
    state_token,
    value_of,
)
from ..extensions import db
from ..retention import retention_overview
from ..security import admin_only, current_actor
from ..tickets.storage import allowed_extensions
from ..users.forms import ReasonForm
from . import bp
from .settings_screens import GROUPS_BY_SLUG, SettingsGroup

SCREEN_ENDPOINT = "admin.settings_screen"


def _group_or_404(slug: str) -> SettingsGroup:
    group = GROUPS_BY_SLUG.get(slug)

    if group is None:
        abort(404)

    return group


def _form_class(group: SettingsGroup):
    """Un formulario con un campo por parámetro (nombrado como su variable) más la marca de
    lo que se vio al abrirlo y el motivo opcional."""
    attributes = {
        "base": HiddenField(),
    }

    for field in group.fields:
        if field.is_switch:
            attributes[field.setting.key] = BooleanField(field.label)
        else:
            attributes[field.setting.key] = OptionalIntegerField(
                field.label,
                validators=[InputRequired(message="Ingresa un número entero.")],
            )

    return type("SettingsForm", (ReasonForm,), attributes)


def _humanize(group: SettingsGroup, message: str) -> str:
    """Cambia los nombres de variable de un mensaje del servicio por los de la pantalla."""
    for field in group.fields:
        message = message.replace(field.setting.key, f"«{field.label}»")

    return message


def _changes(group: SettingsGroup, form) -> dict:
    """Los parámetros que la persona cambió. Marca en el campo los valores fuera de rango.

    Se compara con lo que se mostraba, no con el valor guardado: un valor que no es múltiplo
    de la unidad de pantalla (un tope de bytes definido por entorno) no se reescribe si la
    persona no lo tocó.
    """
    changes = {}

    for field in group.fields:
        control = form[field.setting.key]
        submitted = control.data

        if submitted == field.to_display(value_of(field.setting)):
            continue

        if not field.is_switch:
            lowest, highest = field.limits()

            if not lowest <= submitted <= highest:
                control.errors = [
                    *control.errors,
                    f"Ingresa un valor entre {lowest} y {highest} {field.unit}.",
                ]
                continue

        changes[field.setting] = field.from_display(submitted)

    return changes


def _rows(group: SettingsGroup) -> list[dict]:
    rows = []

    for field in group.fields:
        initial = initial_value(field.setting)
        rows.append(
            {
                "field": field,
                "has_own_value": has_own_value(field.setting),
                "initial": field.to_display(initial),
                "limits": None if field.is_switch else field.limits(),
            }
        )

    return rows


def _render(group: SettingsGroup, form, *, error: str | None = None, status: int = 200):
    return (
        render_template(
            "admin/settings.html",
            group=group,
            form=form,
            rows=_rows(group),
            error=error,
            reason_max=MAX_REASON_LENGTH,
            extensions=allowed_extensions() if group.slug == "archivos" else None,
            # Antes de encender una política, lo que borraría hoy (RN-106).
            retention=retention_overview() if group.slug == "retencion" else None,
        ),
        status,
    )


@bp.route("/settings/<slug>", methods=["GET", "POST"])
@admin_only
def settings_screen(slug: str):
    group = _group_or_404(slug)

    if request.method == "GET":
        current = {
            field.setting.key: field.to_display(value_of(field.setting))
            for field in group.fields
        }
        form = _form_class(group)(data={**current, "base": state_token(group.settings)})

        return _render(group, form)

    # En un envío manda lo que llegó: nada se completa con lo vigente, o una petición sin la
    # marca de lo que se vio podría saltarse la comprobación.
    form = _form_class(group)()

    if not form.validate_on_submit():
        return _render(group, form)

    changes = _changes(group, form)

    if any(form[field.setting.key].errors for field in group.fields):
        return _render(group, form)

    try:
        saved = save_settings(
            changes,
            actor=current_actor(),
            reason=form.motivo.data,
            base_token=form.base.data or "",
            group=group.settings,
        )
    except SettingConflictError as error:
        db.session.rollback()
        flash(str(error), "warning")

        return redirect(url_for(SCREEN_ENDPOINT, slug=group.slug))
    except SettingRuleError as error:
        db.session.rollback()

        return _render(group, form, error=_humanize(group, str(error)))

    db.session.commit()

    if saved:
        flash("La configuración se guardó correctamente.", "success")
    else:
        flash("No hay cambios que guardar.", "info")

    return redirect(url_for(SCREEN_ENDPOINT, slug=group.slug))


@bp.post("/settings/<slug>/reset/<key>")
@admin_only
def settings_reset(slug: str, key: str):
    group = _group_or_404(slug)
    field = next((f for f in group.fields if f.setting.key == key), None)

    if field is None:
        abort(404)

    try:
        changed = reset_setting(
            field.setting,
            actor=current_actor(),
            reason=request.form.get("motivo"),
        )
    except SettingRuleError as error:
        db.session.rollback()
        flash(_humanize(group, str(error)), "error")

        return redirect(url_for(SCREEN_ENDPOINT, slug=group.slug))

    db.session.commit()

    if changed:
        flash(f"«{field.label}» volvió a su valor inicial.", "success")
    else:
        flash(f"«{field.label}» ya usaba su valor inicial.", "info")

    return redirect(url_for(SCREEN_ENDPOINT, slug=group.slug))
