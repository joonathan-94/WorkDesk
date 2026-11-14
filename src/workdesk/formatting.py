"""Formato de datos para las plantillas."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import current_app


def local_datetime(value: datetime | None) -> str:
    """Muestra una fecha y hora en la zona horaria de la aplicación.

    La base de datos guarda las fechas con zona horaria (UTC); aquí se
    convierten a `APP_TIMEZONE` (docs/10, sección 79) para mostrarlas, con el
    formato día-mes-año hora:minuto. Si la zona configurada no existe, se
    muestra en UTC en lugar de fallar.
    """
    if value is None:
        return "—"

    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)

    try:
        zone = ZoneInfo(current_app.config["APP_TIMEZONE"])
    except ZoneInfoNotFoundError:
        zone = UTC

    return value.astimezone(zone).strftime("%d-%m-%Y %H:%M")
