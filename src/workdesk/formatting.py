"""Formato de datos para las plantillas."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import current_app


def app_zone():
    """Zona horaria de la aplicación; UTC si la configurada no existe."""
    try:
        return ZoneInfo(current_app.config["APP_TIMEZONE"])
    except ZoneInfoNotFoundError:
        return UTC


def start_of_local_day(value: date) -> datetime:
    """Primer instante del día `value` en la zona horaria de la aplicación.

    Sirve para filtrar por fecha: quien elige "5 de marzo" piensa en su día
    local, no en el día UTC.
    """
    return datetime(value.year, value.month, value.day, tzinfo=app_zone())


def format_duration(minutes: int | None) -> str:
    """Una duración como la lee una persona: «30 min», «4 h» o «1 h 30 min».

    Sin valor (por ejemplo, un objetivo que no se definió) muestra «—». Una
    duración negativa es un error de quien llama, no algo que mostrar.
    """
    if minutes is None:
        return "—"

    if minutes < 0:
        raise ValueError("Una duración no puede ser negativa.")

    hours, rest = divmod(minutes, 60)

    if hours == 0:
        return f"{rest} min"

    if rest == 0:
        return f"{hours} h"

    return f"{hours} h {rest} min"


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

    return value.astimezone(app_zone()).strftime("%d-%m-%Y %H:%M")
