from flask import Blueprint

# Reasignación masiva: pasar los tickets de un técnico a otros. Solo el Supervisor y el
# Administrador (docs/04, RF-034 y RF-035; docs/11, UI-007).
bp = Blueprint("reassignment", __name__, url_prefix="/reassign")

from . import routes as routes
