from flask import Blueprint

bp = Blueprint("admin", __name__, url_prefix="/admin")

from . import audit_routes as audit_routes
from . import notification_routes as notification_routes
from . import routes as routes
from . import settings_routes as settings_routes
