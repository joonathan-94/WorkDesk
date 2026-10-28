from flask import Flask, render_template


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(400)
    def bad_request(error: Exception):
        return (
            render_template(
                "errors/error.html",
                status_code=400,
                title="Solicitud no válida",
                message=(
                    "La solicitud no pudo ser procesada. "
                    "Verifica la información e inténtalo nuevamente."
                ),
            ),
            400,
        )

    @app.errorhandler(404)
    def not_found(error: Exception):
        return (
            render_template(
                "errors/error.html",
                status_code=404,
                title="Página no encontrada",
                message=(
                    "La página que intentas abrir no existe "
                    "o ya no está disponible."
                ),
            ),
            404,
        )

    @app.errorhandler(500)
    def internal_server_error(error: Exception):
        return (
            render_template(
                "errors/error.html",
                status_code=500,
                title="Error interno",
                message=(
                    "Ocurrió un problema inesperado. "
                    "Inténtalo nuevamente más tarde."
                ),
            ),
            500,
        )