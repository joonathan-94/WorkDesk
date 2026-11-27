"""La pantalla de reportes (`GET /reports`, UI-012, RF-098).

Solo el personal: el Solicitante recibe 403 (RN-179). La autorización está dos veces: en
la ruta (`roles_required`) y en la política (`can_view_reports`), que además usa
`build_report`. Todo se lee de la URL y lo que no corresponde a ninguna opción se ignora,
como en el resto de filtros. Es una pantalla de solo lectura: no cambia nada.
"""

from datetime import date

from flask import abort, render_template, request

from ..catalogs.service import list_categories, list_priorities
from ..dashboard.requester import local_today
from ..query_params import choice_arg
from ..security import (
    STAFF_ROLES,
    can_view_every_technician_report,
    can_view_reports,
    current_actor,
    roles_required,
)
from ..tickets.queries import list_group_options, list_technician_options
from . import bp
from .charts import (
    PRIORITY_TONES,
    STATE_TONES,
    bars,
    count_change,
    resolution_line,
    time_change,
)
from .queries import (
    DEFAULT_PERIOD_DAYS,
    PERIOD_PRESETS,
    ReportFilters,
    build_report,
    preset_period,
    resolve_period,
)

staff_only = roles_required(*STAFF_ROLES)

CUSTOM_PERIOD = "personalizado"
PERIOD_LABELS = {
    "7": "Últimos 7 días",
    "30": "Últimos 30 días",
    "90": "Últimos 90 días",
    "365": "Último año",
    CUSTOM_PERIOD: "Personalizado",
}


@bp.get("")
@staff_only
def reports_page():
    actor = current_actor()

    if not can_view_reports(actor):
        abort(403)

    every = can_view_every_technician_report(actor)
    groups = list_group_options()
    # Un Técnico solo puede filtrar por sí mismo: la pantalla no compara personas.
    technicians = list_technician_options() if every else [actor]
    categories = list_categories("")
    priorities = list_priorities("")
    period_key, period = _period(local_today())

    report = build_report(
        actor,
        ReportFilters(
            period,
            group_id=choice_arg("grupo", groups),
            technician_id=choice_arg("tecnico", technicians),
            category_id=choice_arg("categoria", categories),
            priority_id=choice_arg("prioridad", priorities),
        ),
    )

    return render_template(
        "reports/index.html",
        report=report,
        period_key=period_key,
        period_labels=PERIOD_LABELS,
        custom_period=CUSTOM_PERIOD,
        groups=groups,
        technicians=technicians,
        categories=categories,
        priorities=priorities,
        state_bars=bars(report.by_state, STATE_TONES),
        category_bars=bars(report.by_category),
        priority_bars=bars(report.by_priority, PRIORITY_TONES),
        line=resolution_line(report.weeks),
        created_change=count_change(report.created),
        resolved_change=count_change(report.resolved),
        breached_change=count_change(report.breached) if report.breached else "",
        resolution_change=time_change(
            report.resolution.current.mean_seconds,
            report.resolution.previous.mean_seconds,
        ),
    )


def _period(today: date):
    """El período elegido y su clave para el formulario. «Personalizado» usa las fechas
    (corregidas si no tienen sentido); cualquier otro valor, uno de los predefinidos."""
    choice = request.args.get("periodo", "")

    if choice == CUSTOM_PERIOD:
        return CUSTOM_PERIOD, resolve_period(_date_arg("desde"), _date_arg("hasta"), today)

    days = int(choice) if choice in {str(days) for days in PERIOD_PRESETS} else DEFAULT_PERIOD_DAYS

    return str(days), preset_period(days, today)


def _date_arg(name: str) -> date | None:
    try:
        return date.fromisoformat(request.args.get(name, ""))
    except ValueError:
        return None
