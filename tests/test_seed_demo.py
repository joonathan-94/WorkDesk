import re

from src.workdesk.extensions import db
from src.workdesk.models import AdminAuditLog, Role, User
from src.workdesk.security import hash_password, verify_password
from src.workdesk.seeds import seed_roles
from src.workdesk.seeds.demo import DEMO_USERS
from src.workdesk.users.forms import EMAIL_PATTERN, USERNAME_PATTERN

DEMO_PASSWORD = "ClaveDemoSegura2026"


def run_seed(app, *, password=DEMO_PASSWORD, confirmation=None, env=None):
    runner = app.test_cli_runner()
    confirmation = password if confirmation is None else confirmation

    if env is not None:
        return runner.invoke(args=["seed-demo"], env=env)

    return runner.invoke(
        args=["seed-demo"],
        input=f"{password}\n{confirmation}\n",
    )


def users(app):
    with app.app_context():
        return list(
            db.session.scalars(db.select(User).order_by(User.username))
        )


def count_by_role(app):
    with app.app_context():
        rows = db.session.execute(
            db.select(Role.codigo, db.func.count(User.id))
            .join(User, User.rol_id == Role.id)
            .group_by(Role.codigo)
        )

        return dict(rows.all())


# --- Datos --------------------------------------------------------------


def test_demo_data_is_consistent_with_the_data_rules():
    usernames = [demo.username for demo in DEMO_USERS]
    emails = [demo.email for demo in DEMO_USERS]

    assert len(set(usernames)) == len(usernames)
    assert len(set(emails)) == len(emails)

    for demo in DEMO_USERS:
        assert re.fullmatch(USERNAME_PATTERN, demo.username)
        assert 3 <= len(demo.username) <= 50
        assert re.fullmatch(EMAIL_PATTERN, demo.email)
        assert demo.email.endswith("@workdesk.local")
        assert len(demo.nombre) <= 100
        assert len(demo.apellido) <= 100
        assert len(demo.cargo) <= 100
        assert len(demo.departamento_area) <= 100
        assert len(demo.telefono) <= 30


def test_demo_data_covers_the_operational_roles_without_administrators():
    roles = {demo.rol for demo in DEMO_USERS}

    assert roles == {"SUPERVISOR", "TECNICO", "SOLICITANTE"}


# --- Comando ------------------------------------------------------------


def test_seed_demo_creates_the_team_and_loads_the_roles(app):
    result = run_seed(app)

    assert result.exit_code == 0
    assert f"Usuarios demo creados: {len(DEMO_USERS)}." in result.output
    assert count_by_role(app) == {
        "SUPERVISOR": 2,
        "TECNICO": 4,
        "SOLICITANTE": 6,
    }


def test_seed_demo_never_shows_the_password(app):
    result = run_seed(app)

    assert DEMO_PASSWORD not in result.output


def test_seed_demo_users_are_active_and_can_login_directly(app):
    run_seed(app)
    client = app.test_client()

    for user in users(app):
        assert user.activo is True
        assert user.debe_cambiar_password is False
        assert verify_password(user.password_hash, DEMO_PASSWORD)

    response = client.post(
        "/login",
        data={"username": "camila.rojas", "password": DEMO_PASSWORD},
    )

    assert response.status_code == 302
    assert client.get("/dashboard").status_code == 200


def test_seed_demo_does_not_create_administrators(app):
    run_seed(app)

    assert "ADMINISTRADOR" not in count_by_role(app)
    assert "No se creó ningún Administrador" in run_seed(app).output


def test_seed_demo_audits_each_creation_as_a_system_action(app):
    run_seed(app)

    with app.app_context():
        entries = list(db.session.scalars(db.select(AdminAuditLog)))

        assert len(entries) == len(DEMO_USERS)

        for entry in entries:
            assert entry.accion == "USUARIO_CREADO"
            assert entry.actor_tipo == "SISTEMA"
            assert entry.actor_usuario_id is None
            assert DEMO_PASSWORD not in str(entry.valor_nuevo)


def test_seed_demo_is_idempotent(app):
    run_seed(app)
    second = run_seed(app)

    assert second.exit_code == 0
    assert "Usuarios demo creados: 0." in second.output
    assert f"Omitidos (ya existían): {len(DEMO_USERS)}." in second.output
    assert len(users(app)) == len(DEMO_USERS)


def test_seed_demo_does_not_modify_users_that_already_exist(app):
    run_seed(app, password="PrimeraClaveDemo2026")
    original_hashes = {user.username: user.password_hash for user in users(app)}

    result = run_seed(app, password="SegundaClaveDemo2026")

    assert "Usuarios demo creados: 0." in result.output
    assert {
        user.username: user.password_hash for user in users(app)
    } == original_hashes


def test_seed_demo_skips_a_user_whose_email_is_already_taken(app):
    run_seed(app)
    first = DEMO_USERS[0]

    # Se libera el username del primero, pero su correo sigue ocupado.
    with app.app_context():
        user = db.session.scalar(
            db.select(User).where(User.username == first.username)
        )
        user.username = "otro.nombre"
        db.session.commit()

    result = run_seed(app)

    assert "Usuarios demo creados: 0." in result.output
    assert len(users(app)) == len(DEMO_USERS)


def test_seed_demo_works_without_interaction_using_the_environment(app):
    result = run_seed(app, env={"WORKDESK_DEMO_PASSWORD": DEMO_PASSWORD})

    assert result.exit_code == 0
    assert len(users(app)) == len(DEMO_USERS)
    assert DEMO_PASSWORD not in result.output


def test_seed_demo_refuses_to_run_in_production(app):
    app.config["APP_ENV"] = "production"

    result = run_seed(app)

    assert result.exit_code != 0
    assert "no se cargan en producción" in result.output
    assert users(app) == []


def test_seed_demo_rejects_a_password_below_the_minimum(app):
    result = run_seed(app, password="corta")

    assert result.exit_code != 0
    assert "al menos" in result.output
    assert users(app) == []


def test_seed_demo_rejects_a_weak_password_from_the_environment(app):
    result = run_seed(app, env={"WORKDESK_DEMO_PASSWORD": "corta"})

    assert result.exit_code != 0
    assert users(app) == []


def test_seed_demo_rejects_a_mismatched_confirmation(app):
    result = run_seed(app, confirmation="OtraClaveDistinta2026")

    assert result.exit_code != 0
    assert users(app) == []


def test_seed_demo_keeps_an_existing_administrator_untouched(app):
    with app.app_context():
        seed_roles()
        role = db.session.scalar(
            db.select(Role).where(Role.codigo == "ADMINISTRADOR")
        )
        db.session.add(
            User(
                nombre="Admin",
                apellido="Real",
                username="admin.real",
                email="admin.real@workdesk.local",
                password_hash=hash_password("ClaveAdminReal2026"),
                rol_id=role.id,
            )
        )
        db.session.commit()

    run_seed(app)

    assert count_by_role(app)["ADMINISTRADOR"] == 1
    assert len(users(app)) == len(DEMO_USERS) + 1
