from flask import Blueprint

# Administración de los catálogos de tickets. Cuelga de /admin porque son
# pantallas del área de administración (docs/11, UI-014).
bp = Blueprint("catalogs", __name__, url_prefix="/admin")

from . import routes as routes
