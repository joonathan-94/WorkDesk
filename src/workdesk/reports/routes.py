"""La pantalla de reportes (`GET /reports`, UI-012, RF-098).

Solo el personal: el Solicitante recibe 403 (RN-179). La autorización está dos veces: en
la ruta (`roles_required`) y en la política (`can_view_reports`), que además usa
`build_report`. Todo se lee de la URL y lo que no corresponde a ninguna opción se ignora,
como en el resto de filtros. La pantalla solo lee; la exportación (`/reports/export`) trae
las mismas cifras y deja constancia en la auditoría (RN-180).
"""

from dataclasses import dataclass
from datetime import date

from flask import abort, flash, redirect, render_template, request, url_for

from ..catalogs.service import list_categories, list_priorities
from ..dashboard.requester import local_today
from ..exports import (
    EXPORTS_BUSY_MESSAGE,
    ExportFormat,
    begin_consistent_read,
    export_response,
    export_slot,
    parse_format,
    record_export,
)
from ..extensions import db
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
from .export import report_long_table, report_tables
from .queries import (
    DEFAULT_PERIOD_DAYS,
    PERIOD_PRESETS,
    Report,
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


@dataclass(frozen=True)
class _ReportRequest:
    """Lo que la URL pide al reporte, ya validado: lo comparten la pantalla y la
    exportación, así que el archivo trae las cifras que se ven."""

    report: Report
    period_key: str
    options: dict

    @property
    def params(self) -> dict:
        """Los parámetros de la URL que reproducen este reporte."""
        filters = self.report.filters
        custom = self.period_key == CUSTOM_PERIOD

        return {
            "periodo": self.period_key,
            "desde": filters.period.first.isoformat() if custom else None,
            "hasta": filters.period.last.isoformat() if custom else None,
            "grupo": filters.group_id,
            "tecnico": filters.technician_id,
            "categoria": filters.category_id,
            "prioridad": filters.priority_id,
        }

    def filter_names(self) -> dict:
        """Los filtros aplicados, con sus nombres (para el resumen exportado)."""
        filters = self.report.filters
        chosen = {
            "Grupo": (self.options["groups"], filters.group_id),
            "Técnico": (self.options["technicians"], filters.technician_id),
            "Categoría": (self.options["categories"], filters.category_id),
            "Prioridad": (self.options["priorities"], filters.priority_id),
        }
        names = {}

        for label, (items, chosen_id) in chosen.items():
            for item in items:
                if item.id == chosen_id:
                    names[label] = (
                        f"{item.nombre} {item.apellido}" if label == "Técnico" else item.nombre
                    )

        return names


def _read_report() -> _ReportRequest:
    actor = current_actor()

    if not can_view_reports(actor):
        abort(403)

    every = can_view_every_technician_report(actor)
    options = {
        "groups": list_group_options(),
        # Un Técnico solo puede filtrar por sí mismo: la pantalla no compara personas.
        "technicians": list_technician_options() if every else [actor],
        "categories": list_categories(""),
        "priorities": list_priorities(""),
    }
    period_key, period = _period(local_today())

    report = build_report(
        actor,
        ReportFilters(
            period,
            group_id=choice_arg("grupo", options["groups"]),
            technician_id=choice_arg("tecnico", options["technicians"]),
            category_id=choice_arg("categoria", options["categories"]),
            priority_id=choice_arg("prioridad", options["priorities"]),
        ),
    )

    return _ReportRequest(report, period_key, options)


@bp.get("")
@staff_only
def reports_page():
    request_data = _read_report()
    report = request_data.report

    return render_template(
        "reports/index.html",
        report=report,
        period_key=request_data.period_key,
        period_labels=PERIOD_LABELS,
        custom_period=CUSTOM_PERIOD,
        export_params=request_data.params,
        **request_data.options,
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


@bp.get("/export")
@staff_only
def export_report():
    """El reporte que se ve, en CSV o XLSX (RF-099 a RF-101). Queda en la auditoría."""
    fmt = parse_format(request.args.get("formato"))

    if fmt is None:
        abort(404)

    with export_slot() as free:
        if not free:
            flash(EXPORTS_BUSY_MESSAGE, "warning")
            screen = {name: value for name, value in request.args.items() if name != "formato"}

            return redirect(url_for("reports.reports_page", **screen))

        # Las siete consultas del reporte con la misma foto de la base.
        begin_consistent_read()
        request_data = _read_report()
        report = request_data.report
        names = request_data.filter_names()
        tables = (
            [report_long_table(report, names)]
            if fmt is ExportFormat.CSV
            else report_tables(report, names)
        )
        period = report.filters.period

        record_export(
            current_actor(),
            what="reportes",
            label="Reportes",
            fmt=fmt,
            rows=sum(len(table.rows) for table in tables),
            filters=request_data.params,
        )
        response = export_response(
            fmt, tables, f"workdesk-reportes-{period.first.isoformat()}-a-{period.last.isoformat()}"
        )
        # La auditoría se confirma con el archivo ya escrito y antes de enviarlo.
        db.session.commit()

        return response


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
