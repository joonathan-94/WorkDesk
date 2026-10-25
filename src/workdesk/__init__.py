from flask import Flask

from .auth import bp as auth_bp
from .auth.session import load_user
from .cli import register_commands
from .config import Config
from .extensions import db, login_manager, migrate
from .main import bp as main_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    login_manager.user_loader(load_user)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Debes iniciar sesión para acceder."
    login_manager.login_message_category = "warning"

    register_commands(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    return app