import ast
from pathlib import Path

import click
import pytest

from src.workdesk.extensions import db
from src.workdesk.models import AdminAuditLog, Role, User
from src.workdesk.security import verify_password

VALID_PASSWORD = "ClaveInicialSegura123"


def seed_admin_role(app):
    with app.app_context():
        db.session.add(
            Role(
                codigo="ADMINISTRADOR",
                nombre="Administrador",
                descripcion="Rol administrativo para pruebas.",
            )
        )
        db.session.commit()


def run_create_admin(app, password):
    runner = app.test_cli_runner()

    return runner.invoke(
        args=["create-admin"],
        input=(
            "Ana\nPérez\nana_admin\nana@workdesk.local\n"
            f"{password}\n{password}\n"
        ),
    )


def find_admin(app):
    with app.app_context():
        return db.session.scalar(
            db.select(User).where(User.username == "ana_admin")
        )


def test_create_admin_creates_the_initial_administrator(app):
    seed_admin_role(app)

    result = run_create_admin(app, VALID_PASSWORD)

    assert result.exit_code == 0
    assert "creado correctamente" in result.output

    admin = find_admin(app)

    assert admin is not None
    assert verify_password(admin.password_hash, VALID_PASSWORD)
    assert admin.debe_cambiar_password is False


def test_create_admin_holds_no_transaction_while_the_person_types(app, monkeypatch):
    """Mientras la persona escribe, la conexión no queda en una transacción abierta: la
    retendría sin hacer nada y PostgreSQL la cortaría pasado el tiempo máximo de inactividad
    (`database.py`)."""
    seed_admin_role(app)
    open_while_typing = []
    real_prompt = click.prompt

    def prompt(*args, **kwargs):
        open_while_typing.append(db.session().in_transaction())

        return real_prompt(*args, **kwargs)

    monkeypatch.setattr(click, "prompt", prompt)
    result = run_create_admin(app, VALID_PASSWORD)

    assert result.exit_code == 0
    assert open_while_typing and not any(open_while_typing)


def test_create_admin_rejects_a_password_below_the_minimum(app):
    seed_admin_role(app)

    result = run_create_admin(app, "corta123")

    assert result.exit_code != 0
    assert "al menos 12 caracteres" in result.output
    assert find_admin(app) is None


def test_create_admin_uses_the_configured_minimum_length(app):
    seed_admin_role(app)
    app.config["PASSWORD_MIN_LENGTH"] = 14

    result = run_create_admin(app, VALID_PASSWORD[:12])

    assert result.exit_code != 0
    assert "al menos 14 caracteres" in result.output
    assert find_admin(app) is None


def _create_admin_with(app, *, username="ana_admin", email="ana@workdesk.local"):
    return app.test_cli_runner().invoke(
        args=["create-admin"],
        input=(
            f"Ana\nPérez\n{username}\n{email}\n"
            f"{VALID_PASSWORD}\n{VALID_PASSWORD}\n"
        ),
    )


def _user_count(app):
    with app.app_context():
        return db.session.scalar(db.select(db.func.count(User.id)))


@pytest.mark.parametrize(
    "username",
    ["ana admin", "ab", "_ana", "ana@admin", "a" * 51],
    ids=["espacio", "corto", "empieza-con-guion", "arroba", "largo"],
)
def test_create_admin_applies_the_same_username_rule_as_the_screen(app, username):
    # Antes, el comando solo recortaba y pasaba a minúsculas: aceptaba un username
    # que la pantalla de alta rechaza (RN-148).
    seed_admin_role(app)

    result = _create_admin_with(app, username=username)

    assert result.exit_code != 0
    assert "Username:" in result.output
    assert _user_count(app) == 0


def test_create_admin_rejects_an_email_without_the_shape_of_an_address(app):
    seed_admin_role(app)

    result = _create_admin_with(app, email="ana-sin-dominio")

    assert result.exit_code != 0
    assert "Email: Ingresa un correo electrónico válido." in result.output
    assert _user_count(app) == 0


def test_create_admin_normalizes_like_the_screen(app):
    seed_admin_role(app)

    result = _create_admin_with(app, username="  Ana_Admin ", email=" ANA@WorkDesk.local ")

    assert result.exit_code == 0
    admin = find_admin(app)
    assert admin.email == "ana@workdesk.local"


def test_create_admin_is_audited_as_an_action_of_the_system(app):
    seed_admin_role(app)

    _create_admin_with(app)

    with app.app_context():
        admin = db.session.scalar(db.select(User).where(User.username == "ana_admin"))
        event = db.session.scalar(db.select(AdminAuditLog))

        assert event.accion == "USUARIO_CREADO"
        assert event.actor_tipo == "SISTEMA"
        assert event.actor_usuario_id is None
        assert event.entidad_id == admin.id
        assert event.valor_nuevo["rol"] == "ADMINISTRADOR"
        assert event.valor_nuevo["cambio_obligatorio"] is False


def test_create_admin_refuses_a_second_administrator(app):
    seed_admin_role(app)
    assert _create_admin_with(app).exit_code == 0

    result = _create_admin_with(app, username="otro_admin", email="otro@workdesk.local")

    assert result.exit_code != 0
    assert "Ya existe un usuario con rol ADMINISTRADOR." in result.output
    assert _user_count(app) == 1


PACKAGE = Path(__file__).resolve().parent.parent / "src" / "workdesk"


def _texts_of(path: Path):
    """Las cadenas del módulo, sin los docstrings (que nunca se imprimen)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = {
        id(node.body[0].value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef)
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
    }

    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
    ]


def test_command_output_can_be_written_to_a_windows_console():
    """La consola de Windows, al redirigir la salida a un archivo o a otro programa, escribe
    en cp1252: un carácter fuera de ella (como «→») hacía fallar el comando entero."""
    modules = [
        *(PACKAGE / "cli").glob("*.py"),
        *(PACKAGE / "seeds").rglob("*.py"),
        PACKAGE / "scheduler.py",
    ]
    unwritable = sorted(
        f"{path.relative_to(PACKAGE).as_posix()}: {text[:60]!r}"
        for path in modules
        for text in _texts_of(path)
        if text.encode("cp1252", "replace").decode("cp1252") != text
    )

    assert len(modules) > 10
    assert unwritable == []
