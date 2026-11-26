"""Las reglas de forma de la identidad de un usuario (RN-148), en un único lugar.

Las aplican el formulario web (para mostrar cada error junto a su campo), el servicio
de usuarios (para que ningún camino de alta se las salte) y el comando `create-admin`.
Antes vivían solo en el formulario y `create-admin` aceptaba, por ejemplo, un username
con espacios o mayúsculas que después no se podía escribir en la pantalla de login.

No consultan la base de datos: la unicidad la comprueba el servicio.
"""

import re

USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 50
EMAIL_MAX_LENGTH = 254
NAME_MAX_LENGTH = 100

# Minúsculas, números, punto, guion y guion bajo; empieza por letra o número.
USERNAME_PATTERN = r"^[a-z0-9][a-z0-9._-]*$"

# Comprobación de forma deliberadamente simple (algo@dominio.tld). La
# validez real de una dirección solo se confirma enviándole un correo.
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

USERNAME_LENGTH_MESSAGE = (
    f"Debe tener entre {USERNAME_MIN_LENGTH} y {USERNAME_MAX_LENGTH} caracteres."
)
USERNAME_FORMAT_MESSAGE = (
    "Usa solo letras minúsculas, números, punto, guion y guion bajo, "
    "empezando por una letra o un número."
)
EMAIL_FORMAT_MESSAGE = "Ingresa un correo electrónico válido."

_USERNAME = re.compile(USERNAME_PATTERN)
_EMAIL = re.compile(EMAIL_PATTERN)


def normalize_username(username: str) -> str:
    return username.strip().lower()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def username_problem(username: str) -> str | None:
    """Lo que está mal en un username ya normalizado, o None."""
    if not USERNAME_MIN_LENGTH <= len(username) <= USERNAME_MAX_LENGTH:
        return USERNAME_LENGTH_MESSAGE

    # `fullmatch` y no `match`: `$` aceptaría un salto de línea final.
    if not _USERNAME.fullmatch(username):
        return USERNAME_FORMAT_MESSAGE

    return None


def email_problem(email: str) -> str | None:
    """Lo que está mal en un correo ya normalizado, o None."""
    if not email:
        return "Ingresa el correo electrónico."

    if len(email) > EMAIL_MAX_LENGTH:
        return f"Máximo {EMAIL_MAX_LENGTH} caracteres."

    if not _EMAIL.fullmatch(email):
        return EMAIL_FORMAT_MESSAGE

    return None


def name_problem(value: str, label: str) -> str | None:
    """Lo que está mal en un nombre o apellido ya recortado, o None."""
    if not value:
        return f"Ingresa el {label}."

    if len(value) > NAME_MAX_LENGTH:
        return f"Máximo {NAME_MAX_LENGTH} caracteres."

    return None


def identity_problems(
    *, nombre: str, apellido: str, username: str | None, email: str
) -> dict[str, str]:
    """Todos los problemas de forma de una identidad, por campo.

    Recibe los valores ya normalizados. `username` es None cuando no se valida (en una
    edición, que no puede cambiarlo).
    """
    problems = {
        "nombre": name_problem(nombre, "nombre"),
        "apellido": name_problem(apellido, "apellido"),
        "email": email_problem(email),
    }

    if username is not None:
        problems["username"] = username_problem(username)

    return {field: message for field, message in problems.items() if message}
