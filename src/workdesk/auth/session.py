from datetime import datetime

from flask import session
from sqlalchemy.orm import joinedload

from .. import settings
from ..configuration import value_of
from ..extensions import db
from ..models import User

SESSION_STARTED_KEY = "session_started_at"
SESSION_ACTIVITY_KEY = "session_last_activity"

# Rutas técnicas que no cuentan como actividad del usuario
# ni deben provocar la expiración de su sesión.
EXEMPT_ENDPOINTS = frozenset({"static", "system.health"})

# Consultas que el navegador hace solo, sin que la persona haga nada (hoy, el contador de
# la campana de notificaciones, cada 30 segundos). Se comprueban como cualquier petición:
# una sesión expirada no recibe datos. Pero no cuentan como actividad: si contaran, una
# pestaña abandonada renovaría la sesión sin parar y el límite de inactividad nunca se
# aplicaría (RNF-013).
PASSIVE_ENDPOINTS = frozenset({"notifications.unread_count"})

# Pantalla donde se cambia la contraseña. Un usuario con cambio obligatorio
# pendiente solo puede acceder a ella, cerrar sesión y a las rutas técnicas.
PASSWORD_CHANGE_ENDPOINT = "account.change_password"
PASSWORD_CHANGE_ALLOWED_ENDPOINTS = EXEMPT_ENDPOINTS | {
    PASSWORD_CHANGE_ENDPOINT,
    "auth.logout",
}


def load_user(session_id: str) -> User | None:
    user_id, separator, token_version = session_id.partition(":")

    if not separator:
        return None

    try:
        user_pk = int(user_id)
        session_token_version = int(token_version)
    except (TypeError, ValueError):
        return None

    # El rol se trae en la misma consulta: casi toda pantalla lo consulta (menú, políticas)
    # y cargarlo aparte costaba una consulta más en cada petición. Solo aquí y no en el
    # modelo, para no cambiar las consultas de usuarios que bloquean filas o filtran por rol.
    user = db.session.get(User, user_pk, options=[joinedload(User.rol)])

    if user is None or not user.activo:
        return None

    if user.token_version != session_token_version:
        return None

    return user


def start_session_clock(now: datetime) -> None:
    """Registra el inicio de la sesión y su primera actividad."""
    timestamp = now.timestamp()

    session[SESSION_STARTED_KEY] = timestamp
    session[SESSION_ACTIVITY_KEY] = timestamp


def touch_session(now: datetime) -> None:
    session[SESSION_ACTIVITY_KEY] = now.timestamp()


def session_has_expired(now: datetime) -> bool:
    """Indica si la sesión superó la inactividad o la duración máxima.

    Una sesión autenticada sin marcas de tiempo válidas se considera
    expirada: se prefiere pedir un nuevo login a aceptar una sesión
    cuya antigüedad no se puede comprobar.
    """
    started_at = session.get(SESSION_STARTED_KEY)
    last_activity = session.get(SESSION_ACTIVITY_KEY)

    if not isinstance(started_at, (int, float)):
        return True

    if not isinstance(last_activity, (int, float)):
        return True

    idle_limit = value_of(settings.SESSION_IDLE_MINUTES) * 60
    max_limit = value_of(settings.SESSION_MAX_HOURS) * 3600

    current = now.timestamp()

    return (
        current - last_activity > idle_limit
        or current - started_at > max_limit
    )
