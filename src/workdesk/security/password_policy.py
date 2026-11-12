import secrets
import string

from .passwords import verify_password

# Suelo absoluto: ninguna configuración puede exigir menos que esto.
MIN_LENGTH_FLOOR = 8

# Tope para evitar que una entrada enorme encarezca el hashing sin motivo.
MAX_LENGTH = 128

TEMPORARY_PASSWORD_LENGTH = 16

# Sin caracteres que se confunden al leerlos o dictarlos (0/O/o, 1/l/I).
_AMBIGUOUS_CHARACTERS = "0Oo1lI"
_TEMPORARY_ALPHABET = "".join(
    character
    for character in string.ascii_letters + string.digits
    if character not in _AMBIGUOUS_CHARACTERS
)


class PasswordPolicyError(ValueError):
    """La contraseña no cumple la política de WorkDesk."""


def validate_password_policy(
    password: str,
    *,
    min_length: int,
    current_hash: str | None = None,
) -> None:
    """Valida una contraseña nueva o lanza PasswordPolicyError.

    La política prioriza la longitud y no impone reglas de composición
    (mayúsculas, números, símbolos). La contraseña no se recorta: los
    espacios iniciales y finales forman parte de ella.

    Si se indica `current_hash`, la nueva contraseña debe ser distinta
    de la actual.
    """
    if len(password) < min_length:
        raise PasswordPolicyError(
            f"La contraseña debe tener al menos {min_length} caracteres."
        )

    if len(password) > MAX_LENGTH:
        raise PasswordPolicyError(
            f"La contraseña no puede superar los {MAX_LENGTH} caracteres."
        )

    if not password.strip():
        raise PasswordPolicyError(
            "La contraseña no puede estar formada solo por espacios."
        )

    if current_hash is not None and verify_password(
        current_hash,
        password,
    ):
        raise PasswordPolicyError(
            "La nueva contraseña debe ser distinta de la actual."
        )


def generate_temporary_password(min_length: int) -> str:
    """Genera una contraseña temporal aleatoria y criptográficamente segura.

    Usa `secrets` (no `random`) y nunca es más corta que `min_length`.
    """
    length = min(
        max(TEMPORARY_PASSWORD_LENGTH, min_length),
        MAX_LENGTH,
    )

    return "".join(
        secrets.choice(_TEMPORARY_ALPHABET) for _ in range(length)
    )
