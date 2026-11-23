"""Respuestas JSON de los endpoints internos (renovar el bloqueo de edición, el
contador de la campana...).

WorkDesk no tiene una API pública: son consultas que hace su propio JavaScript.
Aun así comparten una forma de error, para que quien las consuma (hoy dos scripts)
pueda distinguir qué pasó sin adivinar:

    {"ok": false, "error": "<código>", "message": "<texto para mostrar>"}

El código es estable (`session_expired`, `lock_held`, `ticket_closed`...) y el mensaje
está pensado para la persona. Las respuestas correctas conservan su forma propia
(`{"ok": true}`, `{"unread": 3}`...). Ninguna se guarda en caché.
"""

from flask import jsonify


def json_error(code: str, message: str, status: int):
    """Una respuesta de error JSON con la forma común."""
    response = jsonify(ok=False, error=code, message=message)
    response.status_code = status
    response.headers["Cache-Control"] = "no-store"

    return response
