"""Lectura de los parámetros de la URL que comparten las pantallas con filtros."""

from flask import request


def choice_arg(name: str, options) -> int | None:
    """El id recibido en `name` si corresponde a una de las opciones; si no, None (un
    valor inválido se ignora, como en todos los filtros)."""
    value = request.args.get(name, type=int)

    return value if value in {option.id for option in options} else None
