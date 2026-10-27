from flask import Flask

from .auth import bp as auth_bp
from .auth.session import load_user
from .cli import register_commands
from .config import Config
from .extensions import csrf, db, login_manager, migrate
from .main import bp as main_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    _validate_required_config(app)

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

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

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