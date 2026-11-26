"""Las páginas de error: una sola plantilla para cualquier error HTTP.

Cada código conocido tiene su texto; **cualquier otro** (un 405 por usar un método que la
ruta no admite, por ejemplo) recibe igualmente la página de WorkDesk, nunca la genérica
de Werkzeug. Ninguna dice nada técnico: ni la excepción, ni la ruta interna, ni la pila
(eso va al log). Un error de servidor conserva su código (500, 503...) con un texto genérico.
"""

from flask import Flask, make_response, render_template
from werkzeug.exceptions import HTTPException

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


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(HTTPException)
    def http_error(error: HTTPException):
        status = error.code if error.code and 400 <= error.code < 600 else 500

        if status >= 500:
            # Cualquier fallo del servidor dice lo mismo: el detalle va al log.
            title, message = PAGES[500]
        else:
            title, message = PAGES.get(status, OTHER_CLIENT_ERROR)

        response = make_response(
            render_template(
                "errors/error.html",
                status_code=status,
                title=title,
                message=message,
            ),
            status,
        )

        for name, value in error.get_headers():
            if name in KEPT_HEADERS:
                response.headers[name] = value

        return response
