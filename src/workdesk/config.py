import os

from dotenv import load_dotenv

from . import settings

load_dotenv()


def get_bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


class Config:
    APP_NAME = "WorkDesk"
    APP_ENV = os.getenv("APP_ENV", "development")
    APP_TIMEZONE = os.getenv("APP_TIMEZONE", "America/Santiago")

    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")

    # Parámetros numéricos: su nombre, valor por defecto y rango viven en `settings.py`
    # (la única definición); aquí solo se leen del entorno. Se validan al iniciar la
    # aplicación (`settings.validate_settings`) y son el valor inicial: rigen mientras el
    # Administrador no guarde otro en la tabla `configuracion` (`configuration.py`).
    #
    # - Sesión y autenticación: intentos fallidos, minutos de bloqueo, longitud mínima de
    #   contraseña, inactividad y duración máxima de la sesión.
    # - Tickets: ventana de edición de comentarios, días para reabrir, horas hasta el cierre
    #   automático de un ticket resuelto, y duración y latido del bloqueo de edición (el
    #   latido debe ser menor que la duración).
    # - Planificador: segundos entre revisiones. Carga de trabajo: tickets activos desde los
    #   que se marca «carga alta» (solo informativo; 0 la desactiva).
    # - Adjuntos: bytes por archivo y archivos activos por ticket.
    LOGIN_MAX_FAILED_ATTEMPTS = settings.LOGIN_MAX_FAILED_ATTEMPTS.from_environment()
    LOGIN_MAX_FAILED_PER_IP = settings.LOGIN_MAX_FAILED_PER_IP.from_environment()
    LOGIN_LOCK_MINUTES = settings.LOGIN_LOCK_MINUTES.from_environment()
    PASSWORD_MIN_LENGTH = settings.PASSWORD_MIN_LENGTH.from_environment()
    SESSION_IDLE_MINUTES = settings.SESSION_IDLE_MINUTES.from_environment()
    SESSION_MAX_HOURS = settings.SESSION_MAX_HOURS.from_environment()
    COMMENT_EDIT_WINDOW_MINUTES = settings.COMMENT_EDIT_WINDOW_MINUTES.from_environment()
    REOPEN_WINDOW_DAYS = settings.REOPEN_WINDOW_DAYS.from_environment()
    AUTO_CLOSE_HOURS = settings.AUTO_CLOSE_HOURS.from_environment()
    SCHEDULER_INTERVAL_SECONDS = settings.SCHEDULER_INTERVAL_SECONDS.from_environment()
    WORKLOAD_HIGH_ACTIVE_TICKETS = settings.WORKLOAD_HIGH_ACTIVE_TICKETS.from_environment()
    EDIT_LOCK_TTL_SECONDS = settings.EDIT_LOCK_TTL_SECONDS.from_environment()
    EDIT_LOCK_HEARTBEAT_SECONDS = settings.EDIT_LOCK_HEARTBEAT_SECONDS.from_environment()
    UPLOAD_MAX_BYTES = settings.UPLOAD_MAX_BYTES.from_environment()
    UPLOAD_MAX_FILES_PER_TICKET = settings.UPLOAD_MAX_FILES_PER_TICKET.from_environment()
    DUPLICATE_WINDOW_DAYS = settings.DUPLICATE_WINDOW_DAYS.from_environment()
    DUPLICATE_MIN_WORDS = settings.DUPLICATE_MIN_WORDS.from_environment()
    # Interruptores (también en `settings.py`): el SLA, el cierre automático y la ubicación
    # obligatoria al crear un ticket.
    SLA_ENABLED = settings.SLA_ENABLED.from_environment()
    AUTO_CLOSE_ENABLED = settings.AUTO_CLOSE_ENABLED.from_environment()
    LOCATION_REQUIRED = settings.LOCATION_REQUIRED.from_environment()

    # Raíz del almacenamiento de adjuntos. Si no se define, `instance/uploads`.
    UPLOADS_DIR = os.getenv("UPLOADS_DIR")
    # Carpeta de los respaldos (`backup-create`). Si no se define, `instance/backups`.
    # Conviene que esté en otro disco que la base y los adjuntos (RNF-043).
    BACKUPS_DIR = os.getenv("BACKUPS_DIR")
    # Carpeta de `pg_dump` y `pg_restore` si no están en el PATH (por ejemplo,
    # `C:\Program Files\PostgreSQL\18\bin`).
    PG_BIN_DIR = os.getenv("PG_BIN_DIR")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = get_bool_env(
        "SESSION_COOKIE_SECURE",
        default=False,
    )

    LOG_LEVEL = os.getenv(
        "LOG_LEVEL",
        "DEBUG" if APP_ENV == "development" else "INFO",
    ).upper()

    LOG_MAX_BYTES = int(
        os.getenv("LOG_MAX_BYTES", str(5 * 1024 * 1024))
    )

    LOG_BACKUP_COUNT = int(
        os.getenv("LOG_BACKUP_COUNT", "5")
    )
