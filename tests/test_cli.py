from src.workdesk.extensions import db
from src.workdesk.models import Role, User
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
