"""Las páginas de error: una sola plantilla para cualquier error HTTP.

Cada código conocido tiene su texto; **cualquier otro** (un 405 por usar un método que la
ruta no admite, por ejemplo) recibe igualmente la página de WorkDesk, nunca la genérica
de Werkzeug. Ninguna dice nada técnico: ni la excepción, ni la ruta interna, ni la pila
(eso va al log). Un error de servidor conserva su código (500, 503...) con un texto genérico.

**La base de datos ocupada o sin respuesta** (una consulta o una espera de bloqueo que pasó de
su tiempo máximo, ninguna conexión libre, PostgreSQL caído: ver `database.py`) no es un fallo
del programa: responde 503 con `Retry-After` y un texto que invita a reintentar. A las
consultas del propio JavaScript (piden JSON) les responde en JSON, para que la campana siga
consultando en el ciclo siguiente.

La página de error se dibuja **sin los procesadores de contexto** (solo usa `url_for`): ellos
calculan la persona, el menú y la campana, que consultarían la base en balde y, si el error
vino de ella, para volver a fallar dentro del propio manejador.
"""

import logging

from flask import Flask, current_app, make_response, request
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError
from werkzeug.exceptions import HTTPException

from .responses import json_error

logger = logging.getLogger(__name__)

PAGES: dict[int, tuple[str, str]] = {
    400: (
        "Solicitud no válida",
        "La solicitud no pudo ser procesada. Verifica la información e inténtalo nuevamente.",
    ),
    403: ("Acceso denegado", "No tienes permiso para acceder a esta página."),
    404: (
        "Página no encontrada",
        "La página que intentas abrir no existe o ya no está disponible.",
    ),
    405: (
        "Acción no permitida",
        (
            "Esta dirección no admite esa acción. Vuelve a la página anterior e "
            "inténtalo desde allí."
        ),
    ),
    413: (
        "Archivo demasiado grande",
        (
            "Lo que intentaste enviar supera el tamaño permitido. Reduce el tamaño de "
            "los archivos e inténtalo de nuevo."
        ),
    ),
    500: ("Error interno", "Ocurrió un problema inesperado. Inténtalo nuevamente más tarde."),
}

# Un error de la petición sin texto propio (por ejemplo, 409 o 429).
OTHER_CLIENT_ERROR = (
    "Solicitud no atendida",
    "No se pudo completar la solicitud. Vuelve a la página anterior e inténtalo nuevamente.",
)

# Cabeceras del error original que la respuesta debe conservar (el protocolo exige
# `Allow` en un 405 y `Retry-After` tiene sentido en un 429 o un 503).
KEPT_HEADERS = ("Allow", "Retry-After")

# La base de datos no atendió a tiempo: se puede reintentar enseguida.
BUSY_PAGE = (
    "Sistema ocupado",
    "WorkDesk no pudo atender tu solicitud a tiempo. Espera unos segundos e inténtalo de nuevo.",
)
BUSY_RETRY_SECONDS = 5


def render_error_page(status: int, title: str, message: str):
    """La página de error común, sin procesadores de contexto (ver el comentario del módulo)."""
    template = current_app.jinja_env.get_template("errors/error.html")

    return make_response(
        template.render(status_code=status, title=title, message=message), status
    )


def _wants_json() -> bool:
    return request.accept_mimetypes.best_match(("text/html", "application/json")) == "application/json"


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(HTTPException)
    def http_error(error: HTTPException):
        status = error.code if error.code and 400 <= error.code < 600 else 500

        if status >= 500:
            # Cualquier fallo del servidor dice lo mismo: el detalle va al log.
            title, message = PAGES[500]
        else:
            title, message = PAGES.get(status, OTHER_CLIENT_ERROR)

        response = render_error_page(status, title, message)

        for name, value in error.get_headers():
            if name in KEPT_HEADERS:
                response.headers[name] = value

        return response

    @app.errorhandler(OperationalError)
    @app.errorhandler(PoolTimeoutError)
    def database_busy(error):
        # Solo el tipo de error y dónde: ni la sentencia ni la dirección completa (su consulta
        # puede llevar lo que alguien buscó).
        cause = getattr(error, "orig", None) or error
        logger.warning(
            "La base de datos no atendió a tiempo (%s, SQLSTATE %s) en %s %s.",
            type(cause).__name__,
            getattr(cause, "sqlstate", None) or "-",
            request.method,
            request.path,
        )
        title, message = BUSY_PAGE

        if _wants_json():
            response = json_error("database_busy", message, 503)
        else:
            response = render_error_page(503, title, message)

        response.headers["Retry-After"] = str(BUSY_RETRY_SECONDS)

        return response
