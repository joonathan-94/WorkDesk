from flask import Flask

from .auth.session import load_user
from .cli import register_commands
from .config import Config
from .extensions import db, login_manager, migrate


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.user_loader(load_user)
    
    register_commands(app)

    @app.get("/")
    def index():
        return f"{app.config['APP_NAME']} está funcionando"

    return app