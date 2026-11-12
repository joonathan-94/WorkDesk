import os

import pytest
from sqlalchemy.engine import make_url

from src.workdesk import create_app
from src.workdesk.extensions import db
from src.workdesk.models import Role, User
from src.workdesk.security import hash_password
from src.workdesk.seeds import seed_roles

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

        # Cada test crea su propia app y su propio engine. Sin cerrar su
        # pool, las conexiones se acumulan hasta agotar max_connections de
        # PostgreSQL a medida que crece la suite.
        db.engine.dispose()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def seeded_roles(app):
    """Carga los cuatro roles estructurales en la base de pruebas."""
    with app.app_context():
        seed_roles()


@pytest.fixture()
def make_user(app):
    """Crea un usuario de pruebas con el rol indicado por su código."""

    def _make_user(role_code: str):
        with app.app_context():
            role = db.session.scalar(
                db.select(Role).where(Role.codigo == role_code)
            )

            if role is None:
                role = Role(
                    codigo=role_code,
                    nombre=role_code.capitalize(),
                    descripcion="Rol para pruebas.",
                )
                db.session.add(role)
                db.session.flush()

            username = f"{role_code.lower()}_test"

            user = User(
                nombre=role_code.capitalize(),
                apellido="Pruebas",
                username=username,
                email=f"{username}@workdesk.local",
                password_hash=hash_password(TEST_PASSWORD),
                rol_id=role.id,
            )

            db.session.add(user)
            db.session.commit()

            return {
                "id": user.id,
                "username": user.username,
                "password": TEST_PASSWORD,
            }

    return _make_user


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