import os

from flask import Flask, request

from .account import bp as account_bp
from .admin import bp as admin_bp
from .auth import bp as auth_bp
from .auth.session import load_user
from .catalogs import bp as catalogs_bp
from .cli import register_commands
from .config import Config
from .configuration import forget_cached_settings
from .errors import register_error_handlers
from .extensions import csrf, db, login_manager, migrate
from .formatting import format_duration, format_size, local_datetime
from .groups import bp as groups_bp
from .knowledge import bp as knowledge_bp
from .logging_config import configure_logging
from .main import bp as main_bp
from .navigation import layout_context, user_initials
from .notifications import bp as notifications_bp
from .reassignment import bp as reassignment_bp
from .security import can_manage_users
from .security.headers import register_security_headers
from .security.startup import session_cookie_name, startup_problems, startup_warnings
from .settings import validate_settings
from .sla import bp as sla_bp
from .sla.periods import sla_enabled
from .system import bp as system_bp
from .tickets import bp as tickets_bp
from .tickets.attachments import upload_request_limit
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
    _check_startup_safety(app, config_overrides or {})
    validate_settings(app.config)
    _configure_uploads(app)
    configure_logging(app)
    _warn_about_risky_config(app)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    # Cada petición empieza sin lo que otra leyó de la configuración. Con un app context por
    # petición (producción) no haría falta, pero `g` pertenece al app context: si hay uno
    # abierto durante varias peticiones (los tests, un proceso largo), la caché sobreviviría.
    app.before_request(forget_cached_settings)
    # Antes que la protección CSRF: ella lee el formulario, y con él el cuerpo entero, así
    # que el tope de la subida debe estar puesto antes de que llegue.
    _limit_upload_requests(app)
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
    app.register_blueprint(knowledge_bp)
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
    app.add_template_filter(format_size, "filesize")
    # Iniciales de una persona para el avatar de un comentario.
    app.add_template_filter(user_initials, "initials")

    # Las plantillas consultan las políticas para decidir qué mostrar. Eso
    # es solo presentación: la autorización real se aplica en las rutas.
    app.context_processor(lambda: {"can_manage_users": can_manage_users})
    # Como función y no como valor: solo las pantallas que muestran el SLA consultan
    # la configuración (el inicio de sesión o una página de error, no).
    app.context_processor(lambda: {"sla_enabled": sla_enabled})
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


def _check_startup_safety(app: Flask, overrides: dict) -> None:
    """No arranca con una configuración insegura (ver `security/startup.py`)."""
    problems = startup_problems(app.config, debug=app.debug)

    if problems:
        raise RuntimeError(" ".join(problems))

    if "SESSION_COOKIE_NAME" not in overrides:
        app.config["SESSION_COOKIE_NAME"] = session_cookie_name(
            bool(app.config.get("SESSION_COOKIE_SECURE"))
        )


def _warn_about_risky_config(app: Flask) -> None:
    if app.config.get("TESTING"):
        return

    for warning in startup_warnings(app.config):
        app.logger.warning(warning)


def _configure_uploads(app: Flask) -> None:
    if not app.config.get("UPLOADS_DIR"):
        app.config["UPLOADS_DIR"] = os.path.join(app.instance_path, "uploads")

    # Tope general de cualquier petición, calculado con el valor inicial. Las que suben
    # archivos usan el valor vigente de la configuración (`_limit_upload_requests`).
    app.config["MAX_CONTENT_LENGTH"] = (
        app.config["UPLOAD_MAX_BYTES"] * MAX_FILES_PER_REQUEST + 1024 * 1024
    )


def _limit_upload_requests(app: Flask) -> None:
    """Pone a las peticiones que suben archivos el tope del tamaño vigente.

    El Administrador puede cambiar el tamaño máximo de un archivo sin reiniciar la
    aplicación, así que el tope de Flask (que se fija al iniciar) no basta: un máximo bajado
    de 10 MB a 2 MB seguiría dejando entrar cuerpos de 51 MB. Solo se consulta la
    configuración en las peticiones `multipart`, las únicas que llevan archivos.
    """

    @app.before_request
    def limit_upload_size():
        if request.method == "POST" and request.mimetype == "multipart/form-data":
            request.max_content_length = upload_request_limit()
