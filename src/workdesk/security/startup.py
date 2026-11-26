"""Comprobaciones de seguridad al arrancar: qué configuración no se acepta.

WorkDesk prefiere no arrancar a arrancar inseguro. En producción (`APP_ENV=production`):

- **La `SECRET_KEY` debe ser larga** (al menos 32 caracteres). Firma la cookie de sesión:
  quien la adivine puede fabricar una sesión de cualquier usuario, también de un
  Administrador. El README explica cómo generar una de 64.
- **El modo depuración está prohibido.** El depurador de Werkzeug permite ejecutar código
  Python desde el navegador; en producción sería una puerta abierta.
- **Sin cookies seguras se avisa** (no se impide): en una intranet se puede servir por HTTP,
  pero la contraseña y la cookie viajarían sin cifrar.

En cualquier entorno se rechaza el texto de ejemplo del README como clave, y una clave
corta fuera de producción solo se avisa, para no impedir arrancar en desarrollo.
"""

MIN_SECRET_KEY_LENGTH = 32

# El texto que el README pone de ejemplo: si llegó tal cual al `.env`, no hay clave.
PLACEHOLDER_SECRET_KEYS = frozenset({"pega-aqui-la-clave-generada", "change-me", "changeme"})

# Sin el nombre por defecto de Flask (`session`), que delata con qué está hecha la
# aplicación. Por HTTPS lleva el prefijo `__Host-`: el navegador solo la acepta con
# `Secure`, `Path=/` y sin dominio, así que ningún subdominio puede plantarla ni pisarla.
SESSION_COOKIE = "workdesk_session"
SECURE_SESSION_COOKIE = "__Host-workdesk_session"

GENERATE_HINT = (
    'Genera una con: python -c "import secrets; print(secrets.token_hex(32))"'
)


def is_production(config) -> bool:
    return config.get("APP_ENV") == "production"


def startup_problems(config, *, debug: bool) -> list[str]:
    """Lo que impide arrancar (lista vacía si nada)."""
    problems = []
    secret_key = config.get("SECRET_KEY") or ""

    if secret_key.strip().lower() in PLACEHOLDER_SECRET_KEYS:
        problems.append(f"SECRET_KEY tiene el valor de ejemplo. {GENERATE_HINT}")

    if is_production(config):
        if len(secret_key) < MIN_SECRET_KEY_LENGTH:
            problems.append(
                f"En producción SECRET_KEY debe tener al menos {MIN_SECRET_KEY_LENGTH} "
                f"caracteres. {GENERATE_HINT}"
            )

        if debug:
            problems.append(
                "El modo depuración no se puede usar en producción: el depurador permite "
                "ejecutar código desde el navegador. Quita --debug y FLASK_DEBUG."
            )

    return problems


def startup_warnings(config) -> list[str]:
    """Lo que se permite pero conviene corregir; va al log al arrancar."""
    warnings = []
    secret_key = config.get("SECRET_KEY") or ""

    if not is_production(config) and len(secret_key) < MIN_SECRET_KEY_LENGTH:
        warnings.append(
            f"SECRET_KEY tiene menos de {MIN_SECRET_KEY_LENGTH} caracteres: en producción "
            f"no se aceptaría. {GENERATE_HINT}"
        )

    if is_production(config) and not config.get("SESSION_COOKIE_SECURE"):
        warnings.append(
            "SESSION_COOKIE_SECURE=false en producción: la cookie de sesión y las "
            "contraseñas viajan sin cifrar. Sirve WorkDesk por HTTPS y actívala."
        )

    return warnings


def session_cookie_name(secure: bool) -> str:
    return SECURE_SESSION_COOKIE if secure else SESSION_COOKIE
