"""Definición única de los parámetros numéricos configurables de WorkDesk.

Cada parámetro tiene aquí su nombre, su valor por defecto y el rango en que tiene sentido.
Hasta `v0.7.0` el valor sale de una variable de entorno; con la tabla `configuracion` esas
variables pasan a ser solo el valor inicial, y esta lista sigue siendo la única fuente de
los nombres, los valores por defecto y los rangos (la pantalla de configuración y la
validación al iniciar leerán de aquí, sin repetir los números).

No usa Flask ni la base de datos: se importa desde `config.py` antes de que exista la
aplicación.
"""

import os
from dataclasses import dataclass

# Límites de la longitud mínima de contraseña. Viven aquí (y no en `security`) porque este
# módulo no puede depender de nada de la aplicación: `security` lee la configuración.
# Suelo absoluto: ninguna configuración puede exigir menos que esto.
PASSWORD_LENGTH_FLOOR = 8
# Tope para evitar que una entrada enorme encarezca el hashing sin motivo.
PASSWORD_LENGTH_CEILING = 128


@dataclass(frozen=True)
class IntSetting:
    """Un parámetro entero: su variable de entorno, su clave en la tabla, su valor inicial y su
    rango válido."""

    key: str
    # Nombre del parámetro en la tabla `configuracion` (docs/09, sección 26.1).
    table_key: str
    default: int
    minimum: int = 1
    maximum: int | None = None

    def problem(self, value: object) -> str | None:
        """Por qué `value` no es válido, o `None` si lo es."""
        # `bool` es un `int` para Python, pero `True` no es una cantidad.
        if not isinstance(value, int) or isinstance(value, bool):
            return f"{self.key} debe ser un entero."

        if self.maximum is not None and not self.minimum <= value <= self.maximum:
            return f"{self.key} debe estar entre {self.minimum} y {self.maximum}."

        if value < self.minimum:
            if self.minimum == 1:
                return f"{self.key} debe ser un entero mayor que cero."

            return f"{self.key} debe ser un entero mayor o igual que {self.minimum}."

        return None

    def from_environment(self) -> int:
        """El valor de la variable de entorno, o el de por defecto si no está definida."""
        raw = os.getenv(self.key)

        if raw is None or not raw.strip():
            return self.default

        try:
            return int(raw)
        except ValueError:
            raise RuntimeError(f"{self.key} debe ser un entero (se recibió «{raw}»).") from None


# Autenticación y sesión.
LOGIN_MAX_FAILED_ATTEMPTS = IntSetting("LOGIN_MAX_FAILED_ATTEMPTS", "autenticacion.max_intentos", 5)
LOGIN_LOCK_MINUTES = IntSetting("LOGIN_LOCK_MINUTES", "autenticacion.bloqueo_minutos", 15)
PASSWORD_MIN_LENGTH = IntSetting(
    "PASSWORD_MIN_LENGTH",
    "autenticacion.password_longitud_minima",
    12,
    PASSWORD_LENGTH_FLOOR,
    PASSWORD_LENGTH_CEILING,
)
SESSION_IDLE_MINUTES = IntSetting("SESSION_IDLE_MINUTES", "sesion.inactividad_minutos", 30)
SESSION_MAX_HOURS = IntSetting("SESSION_MAX_HOURS", "sesion.duracion_maxima_horas", 8)

# Tickets: comentarios, reapertura, cierre automático y bloqueo de edición.
COMMENT_EDIT_WINDOW_MINUTES = IntSetting(
    "COMMENT_EDIT_WINDOW_MINUTES", "comentarios.ventana_edicion_minutos", 30
)
REOPEN_WINDOW_DAYS = IntSetting("REOPEN_WINDOW_DAYS", "reapertura.ventana_dias", 30)
AUTO_CLOSE_HOURS = IntSetting("AUTO_CLOSE_HOURS", "cierre.auto_cierre_horas", 24)
EDIT_LOCK_TTL_SECONDS = IntSetting(
    "EDIT_LOCK_TTL_SECONDS", "edicion.bloqueo_duracion_segundos", 120
)
EDIT_LOCK_HEARTBEAT_SECONDS = IntSetting(
    "EDIT_LOCK_HEARTBEAT_SECONDS", "edicion.bloqueo_latido_segundos", 45
)

# Planificador y carga de trabajo (0 desactiva la marca de carga alta).
SCHEDULER_INTERVAL_SECONDS = IntSetting(
    "SCHEDULER_INTERVAL_SECONDS", "planificador.intervalo_segundos", 60
)
WORKLOAD_HIGH_ACTIVE_TICKETS = IntSetting(
    "WORKLOAD_HIGH_ACTIVE_TICKETS", "carga.tickets_activos_carga_alta", 10, minimum=0
)

# Archivos adjuntos (10 MB por archivo).
UPLOAD_MAX_BYTES = IntSetting(
    "UPLOAD_MAX_BYTES", "archivos.tamano_maximo_bytes", 10 * 1024 * 1024
)
UPLOAD_MAX_FILES_PER_TICKET = IntSetting(
    "UPLOAD_MAX_FILES_PER_TICKET", "archivos.cantidad_maxima_por_ticket", 20
)

INT_SETTINGS: tuple[IntSetting, ...] = (
    LOGIN_MAX_FAILED_ATTEMPTS,
    LOGIN_LOCK_MINUTES,
    PASSWORD_MIN_LENGTH,
    SESSION_IDLE_MINUTES,
    SESSION_MAX_HOURS,
    COMMENT_EDIT_WINDOW_MINUTES,
    REOPEN_WINDOW_DAYS,
    AUTO_CLOSE_HOURS,
    EDIT_LOCK_TTL_SECONDS,
    EDIT_LOCK_HEARTBEAT_SECONDS,
    SCHEDULER_INTERVAL_SECONDS,
    WORKLOAD_HIGH_ACTIVE_TICKETS,
    UPLOAD_MAX_BYTES,
    UPLOAD_MAX_FILES_PER_TICKET,
)


def settings_problems(config) -> list[str]:
    """Todo lo que está mal en los valores de `config` (vacío si todo es válido).

    `config` es cualquier mapeo de nombre de variable a valor: la configuración de la
    aplicación al iniciar o los valores vigentes con un cambio propuesto. Informa todos los
    problemas a la vez, no solo el primero.
    """
    problems = [
        message
        for setting in INT_SETTINGS
        if (message := setting.problem(config[setting.key]))
    ]

    # Con un latido igual o mayor que la duración, el bloqueo expiraría entre dos
    # renovaciones aunque la persona siga editando.
    if not problems and (
        config[EDIT_LOCK_HEARTBEAT_SECONDS.key] >= config[EDIT_LOCK_TTL_SECONDS.key]
    ):
        problems.append(
            f"{EDIT_LOCK_HEARTBEAT_SECONDS.key} debe ser menor que {EDIT_LOCK_TTL_SECONDS.key}."
        )

    return problems


def validate_settings(config) -> None:
    """Comprueba todos los parámetros de `config` y lanza `RuntimeError` con lo que falla.

    Informa todos los problemas a la vez para que quien configura no tenga que reiniciar la
    aplicación una vez por cada error.
    """
    if problems := settings_problems(config):
        raise RuntimeError(" ".join(problems))
