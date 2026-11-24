import os

from dotenv import load_dotenv

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

    LOGIN_MAX_FAILED_ATTEMPTS = int(
        os.getenv("LOGIN_MAX_FAILED_ATTEMPTS", "5")
    )

    LOGIN_LOCK_MINUTES = int(
        os.getenv("LOGIN_LOCK_MINUTES", "15")
    )

    PASSWORD_MIN_LENGTH = int(
        os.getenv("PASSWORD_MIN_LENGTH", "12")
    )

    SESSION_IDLE_MINUTES = int(
        os.getenv("SESSION_IDLE_MINUTES", "30")
    )

    SESSION_MAX_HOURS = int(
        os.getenv("SESSION_MAX_HOURS", "8")
    )

    # Minutos durante los que el autor de un comentario puede editarlo o
    # eliminarlo (docs/09, 17.1). Pasará a la tabla `configuracion` cuando
    # exista la administración (`v0.7.0`).
    COMMENT_EDIT_WINDOW_MINUTES = int(
        os.getenv("COMMENT_EDIT_WINDOW_MINUTES", "30")
    )

    # Días, desde el cierre, durante los que un solicitante puede reabrir su
    # ticket (docs/06, RN-73). El personal puede reabrir siempre. Pasará a la
    # tabla `configuracion` cuando exista la administración (`v0.7.0`).
    REOPEN_WINDOW_DAYS = int(
        os.getenv("REOPEN_WINDOW_DAYS", "30")
    )

    # Horas que un ticket puede estar en `Resuelto` sin que ningún solicitante
    # lo valide antes de que el planificador lo cierre solo (docs/06, RN-58 y
    # RN-59: también aplica a los tickets sin solicitante). Se cuentan en horas
    # corridas desde la resolución. Pasará a la tabla `configuracion` cuando
    # exista la administración (`v0.7.0`).
    AUTO_CLOSE_HOURS = int(
        os.getenv("AUTO_CLOSE_HOURS", "24")
    )

    # Cada cuántos segundos revisa el planificador (`run-scheduler`) los avisos
    # de SLA y los cierres automáticos cuando se deja en marcha como bucle.
    SCHEDULER_INTERVAL_SECONDS = int(
        os.getenv("SCHEDULER_INTERVAL_SECONDS", "60")
    )

    # Carga de trabajo (docs/06, RN-26 y docs/12, fase 6): a partir de cuántos tickets
    # activos (ni Resueltos ni Cerrados) se marca a un técnico con «carga alta». Es solo
    # informativo: nunca bloquea ni impide asignar. 0 desactiva la marca. Pasará a la
    # tabla `configuracion` cuando exista la administración (`v0.7.0`).
    WORKLOAD_HIGH_ACTIVE_TICKETS = int(
        os.getenv("WORKLOAD_HIGH_ACTIVE_TICKETS", "10")
    )

    # Bloqueo temporal de edición (docs/10, secciones 71 a 74). Segundos que
    # dura un bloqueo sin renovarse y cada cuánto lo renueva la pantalla de
    # edición mientras está abierta; el latido debe ser menor que la duración.
    # Pasarán a la tabla `configuracion` cuando exista la administración
    # (`v0.7.0`).
    EDIT_LOCK_TTL_SECONDS = int(
        os.getenv("EDIT_LOCK_TTL_SECONDS", "120")
    )
    EDIT_LOCK_HEARTBEAT_SECONDS = int(
        os.getenv("EDIT_LOCK_HEARTBEAT_SECONDS", "45")
    )

    # Adjuntos (docs/10, secciones 61 a 69). Pasarán a la tabla
    # `configuracion` cuando exista la administración (`v0.7.0`).
    # Tamaño máximo de cada archivo, en bytes (10 MB por defecto).
    UPLOAD_MAX_BYTES = int(
        os.getenv("UPLOAD_MAX_BYTES", str(10 * 1024 * 1024))
    )
    # Cantidad máxima de archivos activos por ticket.
    UPLOAD_MAX_FILES_PER_TICKET = int(
        os.getenv("UPLOAD_MAX_FILES_PER_TICKET", "20")
    )
    # Raíz del almacenamiento. Si no se define, `instance/uploads`.
    UPLOADS_DIR = os.getenv("UPLOADS_DIR")

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