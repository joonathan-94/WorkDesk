from flask import Blueprint

# Centro de notificaciones (docs/11, UI-008). Las ven todos los roles, cada uno
# las suyas.
bp = Blueprint("notifications", __name__, url_prefix="/notifications")

from . import routes as routes
