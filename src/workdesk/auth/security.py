from datetime import datetime, timedelta

from ..models import User


def refresh_login_lock(user: User, now: datetime) -> bool:
    if user.bloqueado_hasta is None:
        return False

    if user.bloqueado_hasta > now:
        return True

    user.bloqueado_hasta = None
    user.intentos_fallidos = 0

    return False


def register_failed_login(
    user: User,
    max_attempts: int,
    lock_minutes: int,
    now: datetime,
) -> None:
    user.intentos_fallidos += 1

    if user.intentos_fallidos >= max_attempts:
        user.bloqueado_hasta = now + timedelta(minutes=lock_minutes)


def reset_login_failures(user: User) -> None:
    user.intentos_fallidos = 0
    user.bloqueado_hasta = None