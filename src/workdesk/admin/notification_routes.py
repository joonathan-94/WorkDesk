"""La pantalla de configuración de notificaciones (docs/11, UI-024), solo del
Administrador. El catálogo de avisos y sus reglas están en `notifications/preferences.py`."""

from flask import flash, redirect, render_template, request, url_for
from wtforms import HiddenField

from ..cleaning import MAX_REASON_LENGTH
from ..configuration import SettingConflictError, SettingRuleError
from ..extensions import db
from ..models.notificacion import NOTIFICATION_EVENT_LABELS
from ..notifications.preferences import (
    AUDIENCE_LABELS,
    RULES,
    Audience,
    disabled_keys,
    preferences_token,
    save_disabled_keys,
)
from ..security import admin_only, current_actor
from ..users.forms import ReasonForm
from . import bp

SCREEN_ENDPOINT = "admin.notification_settings"

# Los nombres de campo del formulario: una casilla por aviso, con su clave como valor.
CHECKBOX_NAME = "avisos"


class NotificationSettingsForm(ReasonForm):
    # Lo que se vio al abrir la pantalla, para detectar que otra persona lo cambió.
    base = HiddenField()


def _rows(enabled: set[str]) -> list[dict]:
    """Una fila por evento, en el orden del catálogo, con una celda por destinatario."""
    rows: dict = {}

    for rule in RULES:
        row = rows.setdefault(
            rule.event,
            {"label": NOTIFICATION_EVENT_LABELS[rule.event], "cells": {}},
        )
        row["cells"][rule.audience] = {
            "rule": rule,
            "checked": rule.locked is not None or rule.key in enabled,
        }

    return list(rows.values())


def _render(form, enabled: set[str], *, error: str | None = None):
    return render_template(
        "admin/notification_settings.html",
        form=form,
        rows=_rows(enabled),
        audiences=[(audience, AUDIENCE_LABELS[audience]) for audience in Audience],
        checkbox_name=CHECKBOX_NAME,
        reason_max=MAX_REASON_LENGTH,
        error=error,
    )


@bp.route("/notifications", methods=["GET", "POST"])
@admin_only
def notification_settings():
    if request.method == "GET":
        disabled = disabled_keys()
        form = NotificationSettingsForm(data={"base": preferences_token()})

        return _render(form, {rule.key for rule in RULES if rule.key not in disabled})

    form = NotificationSettingsForm()
    # Una casilla desmarcada no se envía: lo apagado es lo del catálogo que no llegó.
    enabled = set(request.form.getlist(CHECKBOX_NAME))

    if not form.validate_on_submit():
        return _render(form, enabled)

    try:
        changed = save_disabled_keys(
            (rule.key for rule in RULES if rule.key not in enabled),
            actor=current_actor(),
            reason=form.motivo.data,
            base_token=form.base.data or "",
        )
    except SettingConflictError as error:
        db.session.rollback()
        flash(str(error), "warning")

        return redirect(url_for(SCREEN_ENDPOINT))
    except SettingRuleError as error:
        db.session.rollback()

        return _render(form, enabled, error=str(error))

    db.session.commit()

    if changed:
        flash("La configuración de notificaciones se guardó correctamente.", "success")
    else:
        flash("No hay cambios que guardar.", "info")

    return redirect(url_for(SCREEN_ENDPOINT))
