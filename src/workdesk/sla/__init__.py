from flask import Blueprint

# Configuración del SLA (docs/11, UI-022): por ahora, el calendario laboral.
# Cuelga de /admin/sla porque es una pantalla del área de administración
# (docs/11, UI-014).
bp = Blueprint("sla", __name__, url_prefix="/admin/sla")

from . import routes as routes
