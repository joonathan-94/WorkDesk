"""La exportación de los reportes (RF-099 a RF-101).

Exporta el mismo `Report` que muestra la pantalla, así que trae los mismos filtros y
permisos: un Técnico exporta su fila de la tabla por técnico y nada más (RN-179).

- **XLSX:** una hoja por sección (resumen con el período y los filtros, estados,
  categorías, prioridades, semanas y técnicos).
- **CSV:** un archivo es una sola tabla, así que va en formato «largo»: una fila por cifra,
  con su sección, su elemento, su medida, su valor y, si la tiene, la del período anterior.
  Es la forma que mejor se filtra o se convierte en tabla dinámica.

Los tiempos van en horas con dos decimales (un número con el que se puede calcular), no
como texto.
"""

from ..exports import Table
from .queries import Duration, Report

HOURS = 3600


def hours(seconds: float | None) -> float | None:
    return None if seconds is None else round(seconds / HOURS, 2)


def _person(user) -> str:
    return "Sin asignar" if user is None else f"{user.nombre} {user.apellido} ({user.username})"


def _summary_rows(report: Report, filter_names: dict) -> list[list]:
    """El resumen: el período, los filtros y las cifras principales con las anteriores."""
    period = report.filters.period
    before = period.previous()
    rows = [
        ["Período", f"{period.first.isoformat()} a {period.last.isoformat()}", f"{before.first.isoformat()} a {before.last.isoformat()}"],
        *[[name, value, None] for name, value in filter_names.items()],
        ["Tickets creados", report.created.current.value, report.created.previous.value],
        ["Tickets resueltos", report.resolved.current.value, report.resolved.previous.value],
        [
            "Tiempo medio de resolución (horas)",
            hours(report.resolution.current.mean_seconds),
            hours(report.resolution.previous.mean_seconds),
        ],
        [
            "Mediana del tiempo de resolución (horas)",
            hours(report.resolution.current.median_seconds),
            hours(report.resolution.previous.median_seconds),
        ],
    ]

    if report.breached is not None:
        rows.append(["Fuera de SLA", report.breached.current.value, report.breached.previous.value])

    return rows


def _technician_rows(report: Report) -> list[list]:
    rows = list(report.technicians)

    if report.unassigned is not None:
        rows.append(report.unassigned)

    def line(row):
        values = [
            _person(row.user),
            row.handled.value,
            row.in_work.value,
            row.resolution.resolved.value,
            hours(row.resolution.mean_seconds),
            hours(row.resolution.median_seconds),
        ]

        return values + ([row.breached.value] if report.sla_enabled else [])

    return [line(row) for row in rows]


def _week_rows(report: Report) -> list[list]:
    def line(week):
        resolution: Duration = week.resolution
        return [
            week.first,
            week.last,
            resolution.resolved.value,
            hours(resolution.mean_seconds),
            hours(resolution.median_seconds),
        ]

    return [line(week) for week in report.weeks]


def report_tables(report: Report, filter_names: dict) -> list[Table]:
    """Las hojas del XLSX. `filter_names` son los filtros aplicados, con nombres."""
    technician_headers = ["Técnico", "Gestionados", "En trabajo", "Resueltos", "Tiempo medio (horas)", "Mediana (horas)"]

    if report.sla_enabled:
        technician_headers.append("Fuera de SLA")

    return [
        Table("Resumen", ["Medida", "Período", "Período anterior"], _summary_rows(report, filter_names)),
        Table("Por estado", ["Estado", "Tickets creados"], [[r.label, r.count.value] for r in report.by_state]),
        Table("Por categoría", ["Categoría", "Tickets creados"], [[r.label, r.count.value] for r in report.by_category]),
        Table("Por prioridad", ["Prioridad", "Tickets creados"], [[r.label, r.count.value] for r in report.by_priority]),
        Table(
            "Por semana",
            ["Desde", "Hasta", "Resueltos", "Tiempo medio (horas)", "Mediana (horas)"],
            _week_rows(report),
        ),
        Table("Por técnico", technician_headers, _technician_rows(report)),
    ]


def report_long_table(report: Report, filter_names: dict) -> Table:
    """El CSV: todas las cifras de las hojas, una por fila."""
    rows = []

    for measure, value, previous in _summary_rows(report, filter_names):
        rows.append(["Resumen", None, measure, value, previous])

    for section, items in (
        ("Por estado", report.by_state),
        ("Por categoría", report.by_category),
        ("Por prioridad", report.by_priority),
    ):
        rows += [[section, item.label, "Tickets creados", item.count.value, None] for item in items]

    for first, last, resolved, mean, median in _week_rows(report):
        element = f"{first.isoformat()} a {last.isoformat()}"
        rows += [
            ["Por semana", element, "Resueltos", resolved, None],
            ["Por semana", element, "Tiempo medio (horas)", mean, None],
            ["Por semana", element, "Mediana (horas)", median, None],
        ]

    measures = ["Gestionados", "En trabajo", "Resueltos", "Tiempo medio (horas)", "Mediana (horas)"]

    if report.sla_enabled:
        measures.append("Fuera de SLA")

    for who, *values in _technician_rows(report):
        rows += [["Por técnico", who, measure, value, None] for measure, value in zip(measures, values, strict=True)]

    return Table("Reporte", ["Sección", "Elemento", "Medida", "Valor", "Período anterior"], rows)
