from functools import cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

# Los parámetros de Argon2id, escritos aquí y no tomados de los valores por defecto de
# argon2-cffi: una actualización de la librería no debe cambiar cuánto cuesta un hash sin
# que nadie lo decida. Son los valores de RFC 9106 que la librería usa hoy (64 MiB, 3
# pasadas, 4 hilos), muy por encima del mínimo de OWASP (19 MiB y 2 pasadas). Bajarlos
# hace fallar `tests/test_passwords.py`. Un hash guardado con otros parámetros se recalcula
# al iniciar sesión (`password_needs_rehash`).
TIME_COST = 3
MEMORY_COST_KIB = 64 * 1024
PARALLELISM = 4


def build_password_hasher() -> PasswordHasher:
    """El hasher de producción."""
    return PasswordHasher(
        time_cost=TIME_COST,
        memory_cost=MEMORY_COST_KIB,
        parallelism=PARALLELISM,
    )


password_hasher = build_password_hasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return password_hasher.check_needs_rehash(password_hash)


@cache
def _stand_in_hash() -> str:
    # Un hash válido de una contraseña que nadie conoce, calculado una sola vez.
    return password_hasher.hash("workdesk-stand-in-password")


def spend_verification_time(password: str) -> None:
    """Gasta el mismo tiempo que una verificación real, sin comprobar nada.

    El inicio de sesión lo llama cuando no hay una cuenta que verificar (usuario
    inexistente, inactivo o bloqueado). Sin esto, responder sin calcular el hash es mucho
    más rápido que responder tras comprobar una contraseña, y esa diferencia de tiempo
    delata qué usuarios existen aunque el mensaje de error sea idéntico.
    """
    verify_password(_stand_in_hash(), password)
