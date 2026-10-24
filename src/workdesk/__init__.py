from flask import Flask

from .config import Config
from .extensions import db


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)

    @app.get("/")
    def index():
        return f"{app.config['APP_NAME']} está funcionando"

    return app