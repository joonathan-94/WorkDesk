import functools
import shutil
from pathlib import Path

import pytest

from src.workdesk import create_app
from src.workdesk.extensions import db
from src.workdesk.models import Categoria, Prioridad, Role, Ubicacion, User
from src.workdesk.security import hash_password
from src.workdesk.seeds import seed_catalogs, seed_demo_tickets, seed_roles
from src.workdesk.sla import periods
from tests.areas import AREA_BY_MODULE
from tests.database import (
    checked_database_url,
    create_schema,
    drop_schema,
    empty_tables,
    engine_options,
    has_snapshot,
    restore_snapshot,
    take_snapshot,
)
from tests.demo_data import NOW, prepare
from tests.sla_helpers import FakeClock

TEST_PASSWORD = "WorkDeskTest123!"


@functools.cache
def _test_password_hash() -> str:
    """El hash Argon2id de `TEST_PASSWORD`, calculado una sola vez por proceso.

    Cada usuario de prueba usa el mismo: calcularlo de nuevo costaría unos 50 ms por
    usuario. Es un hash real de Argon2id con los parámetros por defecto, así que el
    login de los tests sigue verificándolo con el código de producción.
    """
    return hash_password(TEST_PASSWORD)


def _app_config(uploads_dir) -> dict:
    # `checked_database_url` es la protección crítica: se llama siempre antes de
    # construir una aplicación que pueda borrar o crear tablas.
    config = {
        "TESTING": True,
        "APP_ENV": "testing",
        "SECRET_KEY": "test-secret-key",
        "SQLALCHEMY_DATABASE_URI": checked_database_url(),
        "WTF_CSRF_ENABLED": False,
        "SESSION_COOKIE_SECURE": False,
        # Los adjuntos de los tests van a un directorio temporal: nunca
        # tocan `instance/uploads`.
        "UPLOADS_DIR": str(uploads_dir),
    }
    options = engine_options()

    if options:
        config["SQLALCHEMY_ENGINE_OPTIONS"] = options

    return config


def pytest_collection_modifyitems(items):
    """Marca cada test con su área y, si no usa la base de datos, como `unit`.

    Permite ejecutar solo una parte de la suite (`pytest -m sla`, `pytest -m unit`...).
    Ver `tests/areas.py`.
    """
    for item in items:
        module = item.path.stem
        area = AREA_BY_MODULE.get(module)

        if area is None:
            raise pytest.UsageError(
                f"El módulo de tests «{module}» no pertenece a ningún área: "
                "añádelo a AREAS en tests/areas.py."
            )

        item.add_marker(getattr(pytest.mark, area))

        if "app" not in item.fixturenames:
            item.add_marker(pytest.mark.unit)


@pytest.fixture(scope="session")
def _schema(tmp_path_factory):
    """El esquema de la base de pruebas: se crea una vez y se elimina al terminar."""
    app = create_app(_app_config(tmp_path_factory.mktemp("schema")))

    with app.app_context():
        create_schema()

    yield

    with app.app_context():
        drop_schema()
        db.engine.dispose()


@pytest.fixture()
def app(tmp_path, _schema):
    app = create_app(_app_config(tmp_path / "uploads"))

    yield app

    with app.app_context():
        db.session.remove()
        # Cada test empieza con la base vacía (ver `tests/database.py`).
        empty_tables()

        # Cada test crea su propia app y su propio engine. Sin cerrar su
        # pool, las conexiones se acumulan hasta agotar max_connections de
        # PostgreSQL a medida que crece la suite.
        db.engine.dispose()


@pytest.fixture()
def clock(app, monkeypatch):
    """«La hora» que ven los períodos de SLA: noviembre de 2026 en Santiago, y se mueve a
    mano (`clock.set(...)`). Las pruebas de SLA llaman a las funciones con esa hora y las
    ayudas de `tests/sla_helpers.py` arman los momentos."""
    app.config["APP_TIMEZONE"] = "America/Santiago"
    fake = FakeClock()
    monkeypatch.setattr(periods, "current_time", lambda: fake.now)

    return fake


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def seeded_roles(app):
    """Carga los cuatro roles estructurales en la base de pruebas."""
    with app.app_context():
        seed_roles()


@pytest.fixture()
def seeded_catalogs(app):
    """Carga los catálogos iniciales de tickets en la base de pruebas."""
    with app.app_context():
        seed_catalogs()


@pytest.fixture()
def ticket_catalog_ids(app, seeded_roles, seeded_catalogs):
    """Identificadores de catálogos listos para crear tickets.

    Incluye una ubicación de prueba, porque el seed no crea ninguna.
    """
    with app.app_context():
        location = Ubicacion(nombre="Oficina central", tipo="OFICINA")
        db.session.add(location)
        db.session.commit()

        return {
            "category_id": db.session.scalar(
                db.select(Categoria.id).where(
                    Categoria.codigo == "SIN_CLASIFICAR"
                )
            ),
            "priority_id": db.session.scalar(
                db.select(Prioridad.id).where(Prioridad.codigo == "MEDIA")
            ),
            "location_id": location.id,
        }


@pytest.fixture()
def make_user(app):
    """Crea un usuario de pruebas con el rol indicado por su código."""

    def _make_user(role_code: str, username: str | None = None, **extra):
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

            username = username or f"{role_code.lower()}_test"

            # `extra` puede sobrescribir cualquier valor por defecto
            # (nombre, apellido, activo...).
            values = {
                "nombre": role_code.capitalize(),
                "apellido": "Pruebas",
                "username": username,
                "email": f"{username}@workdesk.local",
                "password_hash": _test_password_hash(),
                "rol_id": role.id,
            }
            values.update(extra)

            user = User(**values)

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
            password_hash=_test_password_hash(),
            rol_id=admin_role.id,
        )

        db.session.add(user)
        db.session.commit()

        return {
            "id": user.id,
            "username": user.username,
            "password": TEST_PASSWORD,
        }


@pytest.fixture()
def catalog(app, seeded_roles, seeded_catalogs):
    """Categorías, una ubicación y las prioridades ya cargadas."""
    with app.app_context():
        hardware = Categoria(nombre="Hardware", orden=1)
        networks = Categoria(nombre="Redes", orden=2)
        location = Ubicacion(nombre="Casa matriz", tipo="SUCURSAL")
        db.session.add_all([hardware, networks, location])
        db.session.commit()

        return {
            "hardware": hardware.id,
            "networks": networks.id,
            "fallback": db.session.scalar(
                db.select(Categoria.id).where(
                    Categoria.codigo == "SIN_CLASIFICAR"
                )
            ),
            "location": location.id,
            "medium": db.session.scalar(
                db.select(Prioridad.id).where(Prioridad.codigo == "MEDIA")
            ),
            "high": db.session.scalar(
                db.select(Prioridad.id).where(Prioridad.codigo == "ALTA")
            ),
        }

# --- Los 108 tickets de demostración (ver `tests/demo_data.py`) ---------------------------
#
# Cargarlos cuesta unos 2,6 s y casi la mitad de los tests parten de ellos: se cargan una
# vez por proceso y cada test restaura una copia exacta de la base (ver `tests/database.py`)
# y de los adjuntos que dejó la carga.


@pytest.fixture()
def prepared(app):
    """La base como la tendría quien siguió el README hasta antes del seed."""
    if has_snapshot("demo_prepared"):
        app.config["APP_TIMEZONE"] = "America/Santiago"

        with app.app_context():
            restore_snapshot("demo_prepared")

        return

    prepare(app)

    with app.app_context():
        take_snapshot("demo_prepared")


@pytest.fixture(scope="session")
def seeded_uploads(tmp_path_factory):
    """Los adjuntos que deja la carga de los tickets de demostración."""
    return tmp_path_factory.mktemp("seeded-uploads")


@pytest.fixture()
def seeded(app, prepared, seeded_uploads):
    uploads = Path(app.config["UPLOADS_DIR"])

    if has_snapshot("demo_seeded"):
        with app.app_context():
            result = restore_snapshot("demo_seeded")

        shutil.copytree(seeded_uploads, uploads, dirs_exist_ok=True)

        return result

    with app.app_context():
        result = seed_demo_tickets(now=NOW)
        take_snapshot("demo_seeded", extra=result)

    if uploads.exists():
        shutil.copytree(uploads, seeded_uploads, dirs_exist_ok=True)

    return result
