from flask import Blueprint

# La carga de trabajo del equipo: solo el personal (docs/12, fase 6; UI-006).
bp = Blueprint("workload", __name__, url_prefix="/workload")

from . import routes as routes
from .queries import GroupLoad as GroupLoad
from .queries import TechnicianLoad as TechnicianLoad
from .queries import WorkloadFilters as WorkloadFilters
from .queries import WorkloadOverview as WorkloadOverview
from .queries import WorkloadSummary as WorkloadSummary
from .queries import is_high_load as is_high_load
from .queries import workload_overview as workload_overview
