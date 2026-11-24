import os

from flask import Flask

from .account import bp as account_bp
from .admin import bp as admin_bp
from .auth import bp as auth_bp
from .auth.session import load_user
from .catalogs import bp as catalogs_bp
from .cli import register_commands
from .config import Config
from .errors import register_error_handlers
from .extensions import csrf, db, login_manager, migrate
from .formatting import format_duration, local_datetime
from .groups import bp as groups_bp
from .logging_config import configure_logging
from .main import bp as main_bp
from .navigation import layout_context, user_initials
from .notifications import bp as notifications_bp
from .security import MAX_LENGTH, MIN_LENGTH_FLOOR, can_manage_users
from .security.headers import register_security_headers
from .sla import bp as sla_bp
from .system import bp as system_bp
from .tickets import bp as tickets_bp
from .tickets.storage import MAX_FILES_PER_REQUEST
from .users import bp as users_bp


def create_app(
    config_overrides: dict[str, object] | None = None,
) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    if config_overrides:
        app.config.update(config_overrides)

    _validate_required_config(app)
    _validate_session_limits(app)
    _validate_comment_edit_window(app)
    _validate_reopen_window(app)
    _validate_scheduler(app)
    _validate_workload(app)
    _validate_edit_lock(app)
    _configure_uploads(app)
    _validate_password_policy(app)
    configure_logging(app)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.session_protection = "strong"
    login_manager.user_loader(load_user)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Debes iniciar sesión para acceder."
    login_manager.login_message_category = "warning"

    register_commands(app)
    register_error_handlers(app)
    register_security_headers(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(catalogs_bp)
    app.register_blueprint(groups_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(sla_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(tickets_bp)
    app.register_blueprint(users_bp)

    app.add_template_filter(local_datetime, "local_datetime")
    # Minutos como «1 h 30 min» (los objetivos de SLA).
    app.add_template_filter(format_duration, "duration")
    # Iniciales de una persona para el avatar de un comentario.
    app.add_template_filter(user_initials, "initials")

    # Las plantillas consultan las políticas para decidir qué mostrar. Eso
    # es solo presentación: la autorización real se aplica en las rutas.
    app.context_processor(lambda: {"can_manage_users": can_manage_users})
    app.context_processor(layout_context)

    return app


def _validate_required_config(app: Flask) -> None:
    required_config = (
        "SECRET_KEY",
        "SQLALCHEMY_DATABASE_URI",
    )

    missing_config = [
        key
        for key in required_config
        if not app.config.get(key)
    ]

    if missing_config:
        missing_names = ", ".join(missing_config)

        raise RuntimeError(
            f"Falta configuración obligatoria: {missing_names}"
        )


def _validate_password_policy(app: Flask) -> None:
    # Una longitud mínima fuera de rango dejaría contraseñas débiles
    # (por debajo del suelo) o imposibles de cumplir (por encima del tope).
    min_length = app.config["PASSWORD_MIN_LENGTH"]

    if not MIN_LENGTH_FLOOR <= min_length <= MAX_LENGTH:
        raise RuntimeError(
            "PASSWORD_MIN_LENGTH debe estar entre "
            f"{MIN_LENGTH_FLOOR} y {MAX_LENGTH}."
        )


def _configure_uploads(app: Flask) -> None:
    for key in ("UPLOAD_MAX_BYTES", "UPLOAD_MAX_FILES_PER_TICKET"):
        if app.config[key] <= 0:
            raise RuntimeError(f"{key} debe ser un entero mayor que cero.")

    if not app.config.get("UPLOADS_DIR"):
        app.config["UPLOADS_DIR"] = os.path.join(app.instance_path, "uploads")

    # Flask rechaza con 413, antes de leer el cuerpo, una petición mayor que
    # esto: el máximo de archivos por envío más un margen para el formulario.
    app.config["MAX_CONTENT_LENGTH"] = (
        app.config["UPLOAD_MAX_BYTES"] * MAX_FILES_PER_REQUEST + 1024 * 1024
    )


def _validate_comment_edit_window(app: Flask) -> None:
    # Con 0 o menos nadie podría corregir un comentario recién escrito.
    if app.config["COMMENT_EDIT_WINDOW_MINUTES"] <= 0:
        raise RuntimeError(
            "COMMENT_EDIT_WINDOW_MINUTES debe ser un entero mayor que cero."
        )


def _validate_reopen_window(app: Flask) -> None:
    # Con 0 o menos ningún solicitante podría reabrir su ticket.
    if app.config["REOPEN_WINDOW_DAYS"] <= 0:
        raise RuntimeError(
            "REOPEN_WINDOW_DAYS debe ser un entero mayor que cero."
        )


def _validate_scheduler(app: Flask) -> None:
    # Con 0 o menos el cierre automático cerraría todo al instante o el bucle
    # no esperaría nada entre una revisión y otra.
    for name in ("AUTO_CLOSE_HOURS", "SCHEDULER_INTERVAL_SECONDS"):
        if app.config[name] <= 0:
            raise RuntimeError(f"{name} debe ser un entero mayor que cero.")


def _validate_workload(app: Flask) -> None:
    # 0 desactiva la marca de carga alta; un valor negativo no significa nada.
    if app.config["WORKLOAD_HIGH_ACTIVE_TICKETS"] < 0:
        raise RuntimeError(
            "WORKLOAD_HIGH_ACTIVE_TICKETS debe ser un entero mayor o igual que cero."
        )


def _validate_edit_lock(app: Flask) -> None:
    ttl = app.config["EDIT_LOCK_TTL_SECONDS"]
    heartbeat = app.config["EDIT_LOCK_HEARTBEAT_SECONDS"]

    if ttl <= 0 or heartbeat <= 0:
        raise RuntimeError(
            "EDIT_LOCK_TTL_SECONDS y EDIT_LOCK_HEARTBEAT_SECONDS deben ser "
            "enteros mayores que cero."
        )

    # Con un latido igual o mayor que la duración, el bloqueo expiraría entre
    # dos renovaciones aunque la persona siga editando.
    if heartbeat >= ttl:
        raise RuntimeError(
            "EDIT_LOCK_HEARTBEAT_SECONDS debe ser menor que "
            "EDIT_LOCK_TTL_SECONDS."
        )


def _validate_session_limits(app: Flask) -> None:
    # Un límite de 0 o negativo invalidaría todas las sesiones
    # en cada petición, por lo que se rechaza al iniciar.
    for key in ("SESSION_IDLE_MINUTES", "SESSION_MAX_HOURS"):
        if app.config[key] <= 0:
            raise RuntimeError(
                f"{key} debe ser un entero mayor que cero."
            )