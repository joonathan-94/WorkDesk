from flask import Flask

from .config import Config


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    @app.get("/")
    def index():
        return f"{app.config['APP_NAME']} está funcionando"

    return app