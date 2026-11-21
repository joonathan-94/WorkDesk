"""Pantallas de la configuración del SLA (docs/11, UI-022). Las reglas están en
`sla/work_calendar.py`; aquí solo se orquesta. Como el resto del área de
administración, todas las rutas son exclusivas del Administrador y la
autorización se comprueba en backend."""

from datetime import datetime

from flask import flash, redirect, render_template, request, url_for

from ..extensions import db
from ..formatting import app_zone
from ..security import admin_only, current_actor
from . import bp
from .forms import (
    MAX_HOLIDAYS_TEXT_LENGTH,
    WorkCalendarForm,
    calendar_form_data,
)
from .work_calendar import (
    MAX_REASON_LENGTH,
    CalendarConflictError,
    CalendarRuleError,
    NothingToChangeError,
    available_zone_names,
    describe_calendar,
    list_calendar_versions,
    resolve_work_calendar,
    save_work_calendar,
)

INDEX_ENDPOINT = "sla.index"
CALENDAR_ENDPOINT = "sla.calendar_edit"

# Cuántos feriados próximos se muestran en el resumen.
UPCOMING_HOLIDAYS = 5


@bp.get("")
@admin_only
def index():
    view = describe_calendar(resolve_work_calendar())
    today = datetime.now(app_zone()).date()
    upcoming = [holiday for holiday in view.holidays if holiday.fecha >= today]

    return render_template(
        "sla/index.html",
        calendar=view,
        upcoming_holidays=upcoming[:UPCOMING_HOLIDAYS],
        versions=list_calendar_versions(),
    )


@bp.route("/calendar", methods=["GET", "POST"])
@admin_only
def calendar_edit():
    view = describe_calendar(resolve_work_calendar())

    # Los valores vigentes rellenan el formulario solo al abrirlo. En un envío
    # manda lo que llegó: si faltara la versión base, no debe completarse sola con
    # la vigente, porque entonces no se detectaría que la pantalla estaba
    # desactualizada.
    if request.method == "POST":
        form = WorkCalendarForm()
    else:
        form = WorkCalendarForm(data=calendar_form_data(view))

    if form.validate_on_submit():
        try:
            saved = save_work_calendar(
                actor=current_actor(),
                base_version=form.version_base.data,
                zone_name=form.zona_horaria.data,
                franjas=form.franjas,
                holidays=form.holidays,
                reason=form.motivo.data,
            )
            db.session.commit()
        except NothingToChangeError as error:
            db.session.rollback()
            flash(str(error), "warning")

            return redirect(url_for(INDEX_ENDPOINT))
        except CalendarConflictError as error:
            db.session.rollback()
            flash(str(error), "error")

            # Se vuelve al formulario con lo vigente. Lo escrito se pierde a
            # propósito: reenviarlo pisaría un cambio que no se ha visto.
            return redirect(url_for(CALENDAR_ENDPOINT))
        except CalendarRuleError as error:
            db.session.rollback()
            form.general_errors.append(str(error))
        else:
            flash(f"Calendario laboral guardado: versión {saved.version}.", "success")

            return redirect(url_for(INDEX_ENDPOINT))

    return render_template(
        "sla/calendar_form.html",
        form=form,
        calendar=view,
        zone_names=sorted(available_zone_names()),
        max_holidays=MAX_HOLIDAYS_TEXT_LENGTH,
        max_reason=MAX_REASON_LENGTH,
    )
