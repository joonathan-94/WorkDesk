from flask import current_app, jsonify
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from . import bp


@bp.get("/health")
def health():
    try:
        with db.engine.connect() as connection:
            database_result = connection.execute(
                text("SELECT 1")
            ).scalar_one()
    except SQLAlchemyError:
        current_app.logger.exception(
            "Health check fallido: PostgreSQL no está disponible."
        )

        return _degraded()

    if database_result != 1:
        current_app.logger.error(
            "Health check recibió una respuesta inesperada de PostgreSQL."
        )

        return _degraded()

    return jsonify(
        status="ok",
        application="ok",
        database="ok",
    )


def _degraded():
    """La aplicación responde pero PostgreSQL no (503, sin detalles técnicos)."""
    return (
        jsonify(
            status="degraded",
            application="ok",
            database="unavailable",
        ),
        503,
    )