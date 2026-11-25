from flask import Blueprint

bp = Blueprint("admin", __name__, url_prefix="/admin")

from . import routes as routes
from . import settings_routes as settings_routes
