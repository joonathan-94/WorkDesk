"""Reportes operativos (RF-098, UI-012): las consultas en `queries.py`, los gráficos en
`charts.py` y la pantalla en `routes.py`. Solo para el personal."""

from flask import Blueprint

bp = Blueprint("reports", __name__, url_prefix="/reports")

from . import routes as routes
from .queries import Period as Period
from .queries import ReportFilters as ReportFilters
from .queries import build_report as build_report
from .queries import default_filters as default_filters
from .queries import preset_period as preset_period
from .queries import report_listing_params as report_listing_params
from .queries import resolve_period as resolve_period
