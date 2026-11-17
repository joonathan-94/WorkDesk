from flask import Blueprint

# Grupos de atención. El Administrador los gestiona todos; el Supervisor ve
# solo los suyos y gestiona sus miembros (docs/03, sección 5).
bp = Blueprint("groups", __name__, url_prefix="/groups")

from . import routes as routes
