"""La base de conocimiento (docs/12, fase 7): artículos reutilizables y su búsqueda.

`service.py` escribe (crear, editar, publicar, destacar, desactivar) y `queries.py` lee
(quién ve qué y la búsqueda). Las pantallas están en `routes.py` y `editor_routes.py`.
"""

from flask import Blueprint

bp = Blueprint("knowledge", __name__, url_prefix="/knowledge")

from . import editor_routes as editor_routes
from . import routes as routes
