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
from .reassignment import bp as reassignment_bp
from .security import can_manage_users
from .security.headers import register_security_headers
from .settings import validate_settings
from .sla import bp as sla_bp
from .system import bp as system_bp
from .tickets import bp as tickets_bp
from .tickets.storage import MAX_FILES_PER_REQUEST
from .users import bp as users_bp
from .workload import bp as workload_bp


def create_app(
    config_overrides: dict[str, object] | None = None,
) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    if config_overrides:
        app.config.update(config_overrides)

    _validate_required_config(app)
    validate_settings(app.config)
    _configure_uploads(app)
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
    app.register_blueprint(workload_bp)
    app.register_blueprint(reassignment_bp)
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


def _configure_uploads(app: Flask) -> None:
    if not app.config.get("UPLOADS_DIR"):
        app.config["UPLOADS_DIR"] = os.path.join(app.instance_path, "uploads")

    # Flask rechaza con 413, antes de leer el cuerpo, una petición mayor que
    # esto: el máximo de archivos por envío más un margen para el formulario.
    app.config["MAX_CONTENT_LENGTH"] = (
        app.config["UPLOAD_MAX_BYTES"] * MAX_FILES_PER_REQUEST + 1024 * 1024
    )
