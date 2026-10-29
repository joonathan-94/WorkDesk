import os

import pytest
from sqlalchemy.engine import make_url

from src.workdesk import create_app
from src.workdesk.extensions import db
from src.workdesk.models import Role, User
from src.workdesk.security import hash_password

TEST_PASSWORD = "WorkDeskTest123!"


@pytest.fixture()
def app():
    test_database_url = os.getenv("TEST_DATABASE_URL")

    if not test_database_url:
        raise RuntimeError(
            "Falta TEST_DATABASE_URL para ejecutar los tests."
        )

    database_name = make_url(test_database_url).database

    if database_name != "workdesk_test":
        raise RuntimeError(
            "Los tests solo pueden ejecutarse sobre workdesk_test."
        )

    app = create_app(
        {
            "TESTING": True,
            "APP_ENV": "testing",
            "SECRET_KEY": "test-secret-key",
            "SQLALCHEMY_DATABASE_URI": test_database_url,
            "WTF_CSRF_ENABLED": False,
            "SESSION_COOKIE_SECURE": False,
        }
    )

    with app.app_context():
        db.drop_all()
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def admin_user(app):
    with app.app_context():
        admin_role = Role(
            codigo="ADMINISTRADOR",
            nombre="Administrador",
            descripcion="Rol administrativo para pruebas.",
        )

        db.session.add(admin_role)
        db.session.flush()

        user = User(
            nombre="Admin",
            apellido="Pruebas",
            username="admin_test",
            email="admin.test@workdesk.local",
            password_hash=hash_password(TEST_PASSWORD),
            rol_id=admin_role.id,
        )

        db.session.add(user)
        db.session.commit()

        return {
            "id": user.id,
            "username": user.username,
            "password": TEST_PASSWORD,
        }