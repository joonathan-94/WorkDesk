import pytest
from sqlalchemy.exc import SQLAlchemyError

from src.workdesk import create_app
from src.workdesk.extensions import db


def test_bad_request_uses_custom_error_page(app):
    app.config["WTF_CSRF_ENABLED"] = True

    client = app.test_client()
    response = client.post("/logout")

    content = response.get_data(as_text=True)

    assert response.status_code == 400
    assert "Solicitud no válida" in content


def test_health_returns_503_when_database_is_unavailable(
    app,
    client,
    monkeypatch,
):
    def fail_connect():
        raise SQLAlchemyError("Database unavailable")

    with app.app_context():
        engine = db.engine

    monkeypatch.setattr(
        engine,
        "connect",
        fail_connect,
    )

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json == {
        "application": "ok",
        "database": "unavailable",
        "status": "degraded",
    }


@pytest.mark.parametrize(
    "missing_config",
    [
        "SECRET_KEY",
        "SQLALCHEMY_DATABASE_URI",
    ],
)
def test_app_rejects_missing_required_configuration(
    missing_config,
):
    config = {
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    }

    config[missing_config] = ""

    with pytest.raises(
        RuntimeError,
        match=missing_config,
    ):
        create_app(config)