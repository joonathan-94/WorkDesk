"""El bloqueo temporal por intentos fallidos (RNF-015).

**Por qué se bloquea la fila del usuario.** El contador de intentos se lee, se
compara y se escribe: si dos intentos llegan a la vez, los dos leen el mismo valor
y cada uno escribe «uno más», así que el contador pierde actualizaciones. Medido
antes de este arreglo: 20 intentos simultáneos con la contraseña equivocada dejaban
el contador en 2 y la cuenta sin bloquear (el límite era 5), es decir, quien enviara
ráfagas en paralelo podía probar muchas más contraseñas de las permitidas.

Por eso el login y el cambio de contraseña leen al usuario con `SELECT ... FOR
UPDATE` antes de mirar el bloqueo y de verificar la contraseña: los intentos sobre
una misma cuenta se atienden de uno en uno, cada uno ve lo que dejó el anterior y,
alcanzado el límite, el resto encuentra la cuenta bloqueada sin llegar a verificar
nada. Solo se esperan entre sí los intentos sobre la misma cuenta; el bloqueo dura
lo que tarda la petición en confirmar.
"""

from datetime import datetime, timedelta

from sqlalchemy import select

from ..extensions import db
from ..models import User


def find_user_for_login(username: str) -> User | None:
    """El usuario con ese username, con su fila bloqueada hasta el fin de la
    transacción (o None si no existe)."""
    return db.session.scalar(
        select(User)
        .where(User.username == username)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def lock_user_row(user: User) -> User:
    """Bloquea la fila de un usuario ya cargado y refresca sus valores.

    `populate_existing` es imprescindible: sin él, la sesión devolvería la copia que
    cargó la petición antes de esperar al bloqueo, con un contador ya viejo.
    """
    return db.session.scalar(
        select(User)
        .where(User.id == user.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def refresh_login_lock(user: User, now: datetime) -> bool:
    """Indica si la cuenta sigue bloqueada; si el bloqueo ya venció, lo levanta."""
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
    """Suma un intento fallido y bloquea la cuenta al llegar al límite.

    Quien llama debe tener la fila bloqueada (`find_user_for_login` o
    `lock_user_row`): si no, dos intentos simultáneos se pisan el contador.
    """
    user.intentos_fallidos += 1

    if user.intentos_fallidos >= max_attempts:
        user.bloqueado_hasta = now + timedelta(minutes=lock_minutes)


def reset_login_failures(user: User) -> None:
    user.intentos_fallidos = 0
    user.bloqueado_hasta = None


def invalidate_user_sessions(user: User) -> None:
    user.token_version += 1
