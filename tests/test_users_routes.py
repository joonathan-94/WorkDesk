import re

import pytest

from src.workdesk.extensions import db
from src.workdesk.models import AdminAuditLog, Role, User
from src.workdesk.security import hash_password, verify_password
from src.workdesk.users.service import PAGE_SIZE

NON_ADMIN_ROLES = ("SOLICITANTE", "TECNICO", "SUPERVISOR")
TEMPORARY_PASSWORD = "ClaveTemporal789xyz"
GENERATED_PASSWORD = re.compile(
    r'id="temporary-password"\s*>([^<]+)</code>'
)


def login(client, user_data, password=None):
    return client.post(
        "/login",
        data={
            "username": user_data["username"],
            "password": password or user_data["password"],
        },
    )


def admin_session(client, make_user):
    admin_data = make_user("ADMINISTRADOR")
    login(client, admin_data)

    return admin_data


def form_data(**overrides):
    data = {
        "nombre": "Ana",
        "apellido": "Pérez",
        "username": "ana.perez",
        "email": "ana.perez@workdesk.local",
        "telefono": "",
        "cargo": "",
        "departamento_area": "",
        "rol": "TECNICO",
        "password_mode": "generate",
        "temporary_password": "",
    }
    data.update(overrides)

    return data


def count_users(app) -> int:
    with app.app_context():
        return db.session.scalar(db.select(db.func.count()).select_from(User))


def audit_actions(app):
    with app.app_context():
        return list(
            db.session.scalars(
                db.select(AdminAuditLog.accion).order_by(AdminAuditLog.id)
            )
        )


def find_user(app, username):
    with app.app_context():
        user = db.session.scalar(
            db.select(User).where(User.username == username)
        )

        if user is None:
            return None

        return {
            "id": user.id,
            "hash": user.password_hash,
            "role": user.rol.codigo,
            "active": user.activo,
            "must_change": user.debe_cambiar_password,
            "created_by": user.usuario_creacion_id,
        }


def add_users(app, count, *, role_code="SOLICITANTE", prefix="usuario"):
    with app.app_context():
        role = db.session.scalar(
            db.select(Role).where(Role.codigo == role_code)
        )
        password_hash = hash_password(TEMPORARY_PASSWORD)

        for index in range(count):
            db.session.add(
                User(
                    nombre=f"Nombre{index:02d}",
                    apellido=f"Apellido{index:02d}",
                    username=f"{prefix}{index:02d}",
                    email=f"{prefix}{index:02d}@workdesk.local",
                    password_hash=password_hash,
                    rol_id=role.id,
                )
            )

        db.session.commit()


# --- Control de acceso ------------------------------------------------


@pytest.mark.parametrize("path", ["/users", "/users/new"])
def test_anonymous_user_is_redirected_to_login(client, path):
    response = client.get(path)

    assert response.status_code == 302
    assert "/login" in response.location


@pytest.mark.parametrize("path", ["/users", "/users/new"])
@pytest.mark.parametrize("role_code", NON_ADMIN_ROLES)
def test_non_admin_roles_are_forbidden(
    client,
    seeded_roles,
    make_user,
    role_code,
    path,
):
    login(client, make_user(role_code))

    assert client.get(path).status_code == 403


def test_non_admin_cannot_create_users_by_posting(
    client,
    app,
    seeded_roles,
    make_user,
):
    login(client, make_user("TECNICO"))
    before = count_users(app)

    response = client.post("/users/new", data=form_data())

    assert response.status_code == 403
    assert count_users(app) == before
    assert audit_actions(app) == []


def test_anonymous_user_cannot_create_users_by_posting(client, app):
    response = client.post("/users/new", data=form_data())

    assert response.status_code == 302
    assert count_users(app) == 0


def test_navigation_links_are_shown_only_to_administrators(
    client,
    app,
    seeded_roles,
    make_user,
):
    login(client, make_user("TECNICO"))
    technician_view = client.get("/dashboard").get_data(as_text=True)

    other_client = app.test_client()
    login(other_client, make_user("ADMINISTRADOR"))
    admin_view = other_client.get("/dashboard").get_data(as_text=True)

    assert "/users" not in technician_view
    assert "/users" in admin_view


def test_admin_area_links_to_users(client, seeded_roles, make_user):
    admin_session(client, make_user)

    content = client.get("/admin").get_data(as_text=True)

    assert 'href="/users"' in content


# --- Listado ----------------------------------------------------------


def test_list_shows_users_with_role_and_status(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    add_users(app, 2, role_code="TECNICO", prefix="tec")

    response = client.get("/users")
    content = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Nombre00 Apellido00" in content
    assert "tec01@workdesk.local" in content
    assert "Técnico" in content
    assert "Activo" in content
    assert "3 usuarios" in " ".join(content.split())


def test_list_marks_users_with_pending_password_change(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    client.post("/users/new", data=form_data())

    content = client.get("/users").get_data(as_text=True)

    assert "Cambio de contraseña pendiente" in content


def test_list_search_and_filters(client, app, seeded_roles, make_user):
    admin_session(client, make_user)
    add_users(app, 2, role_code="SOLICITANTE", prefix="sol")
    add_users(app, 2, role_code="TECNICO", prefix="tec")

    by_search = client.get("/users?q=TEC01").get_data(as_text=True)
    by_role = client.get("/users?rol=SOLICITANTE").get_data(as_text=True)

    assert "tec01@workdesk.local" in by_search
    assert "sol01@workdesk.local" not in by_search
    assert "sol01@workdesk.local" in by_role
    assert "tec01@workdesk.local" not in by_role


def test_list_ignores_invalid_filters_and_page(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    add_users(app, 2)

    response = client.get("/users?rol=HACKER&estado=raro&page=abc")
    content = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "usuario01@workdesk.local" in content


def test_list_shows_an_empty_state(client, seeded_roles, make_user):
    admin_session(client, make_user)

    content = client.get("/users?q=inexistente").get_data(as_text=True)

    assert "No se encontraron usuarios" in content


def test_list_paginates_and_keeps_the_filters_in_the_links(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    add_users(app, PAGE_SIZE + 5, role_code="TECNICO", prefix="tec")

    first = client.get("/users?rol=TECNICO").get_data(as_text=True)
    second = client.get("/users?rol=TECNICO&page=2").get_data(as_text=True)

    assert "Página 1 de 2" in " ".join(first.split())
    assert "Siguiente" in first
    assert "page=2" in first
    assert "rol=TECNICO" in first
    assert "Anterior" in second
    assert "tec24@workdesk.local" in second


def test_list_escapes_user_supplied_html(client, app, seeded_roles, make_user):
    admin_session(client, make_user)

    with app.app_context():
        role = db.session.scalar(
            db.select(Role).where(Role.codigo == "SOLICITANTE")
        )
        db.session.add(
            User(
                nombre="<script>alert(1)</script>",
                apellido="Prueba",
                username="xss.test",
                email="xss@workdesk.local",
                password_hash=hash_password(TEMPORARY_PASSWORD),
                rol_id=role.id,
            )
        )
        db.session.commit()

    content = client.get("/users").get_data(as_text=True)

    assert "<script>alert(1)</script>" not in content
    assert "&lt;script&gt;" in content


# --- Formulario de alta ----------------------------------------------


def test_new_user_form_shows_the_role_options_and_password_hint(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)

    response = client.get("/users/new")
    content = response.get_data(as_text=True)
    visible_text = " ".join(content.split())

    assert response.status_code == 200
    for role_name in ("Solicitante", "Técnico", "Supervisor", "Administrador"):
        assert role_name in content
    assert (
        f"Mínimo {app.config['PASSWORD_MIN_LENGTH']} caracteres."
        in visible_text
    )


def test_post_without_csrf_token_is_rejected(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    app.config["WTF_CSRF_ENABLED"] = True
    before = count_users(app)

    response = client.post("/users/new", data=form_data())

    assert response.status_code == 400
    assert count_users(app) == before


# --- Alta con contraseña generada ------------------------------------


def test_create_with_generated_password_shows_it_once(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_data = admin_session(client, make_user)

    response = client.post("/users/new", data=form_data())
    content = response.get_data(as_text=True)
    match = GENERATED_PASSWORD.search(content)

    assert response.status_code == 200
    assert "Usuario creado" in content
    assert match is not None
    assert len(match.group(1)) >= 12
    assert response.headers["Cache-Control"] == "no-store"

    saved = find_user(app, "ana.perez")

    assert saved["role"] == "TECNICO"
    assert saved["active"] is True
    assert saved["must_change"] is True
    assert saved["created_by"] == admin_data["id"]
    assert verify_password(saved["hash"], match.group(1))

    # La contraseña no se puede volver a consultar.
    assert match.group(1) not in client.get("/users").get_data(as_text=True)
    assert match.group(1) not in client.get("/users/new").get_data(
        as_text=True
    )


def test_generated_password_is_not_stored_in_the_audit_log(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)

    content = client.post("/users/new", data=form_data()).get_data(
        as_text=True
    )
    password = GENERATED_PASSWORD.search(content).group(1)

    with app.app_context():
        entry = db.session.scalar(
            db.select(AdminAuditLog).where(
                AdminAuditLog.accion == "USUARIO_CREADO"
            )
        )

        assert entry is not None
        assert password not in str(entry.valor_nuevo)
        assert password not in str(entry.detalle)


def test_new_user_can_login_and_is_forced_to_change_the_password(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)

    content = client.post("/users/new", data=form_data()).get_data(
        as_text=True
    )
    password = GENERATED_PASSWORD.search(content).group(1)

    new_client = app.test_client()
    login_response = login(
        new_client,
        {"username": "ana.perez"},
        password,
    )
    dashboard = new_client.get("/dashboard")

    assert login_response.status_code == 302
    assert dashboard.status_code == 302
    assert dashboard.location.endswith("/account/password")


def test_create_is_audited(client, app, seeded_roles, make_user):
    admin_session(client, make_user)

    client.post("/users/new", data=form_data())

    assert audit_actions(app) == ["USUARIO_CREADO"]


def test_created_user_appears_in_the_list(
    client,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)

    client.post("/users/new", data=form_data())
    content = client.get("/users").get_data(as_text=True)

    assert "Ana Pérez" in content
    assert "ana.perez@workdesk.local" in content


def test_admin_can_create_another_administrator(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)

    client.post("/users/new", data=form_data(rol="ADMINISTRADOR"))

    assert find_user(app, "ana.perez")["role"] == "ADMINISTRADOR"


# --- Alta con contraseña escrita -------------------------------------


def test_create_with_a_typed_password_does_not_display_it(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)

    response = client.post(
        "/users/new",
        data=form_data(
            password_mode="manual",
            temporary_password=TEMPORARY_PASSWORD,
        ),
    )
    content = response.get_data(as_text=True)
    saved = find_user(app, "ana.perez")

    assert response.status_code == 200
    assert "Usuario creado" in content
    assert TEMPORARY_PASSWORD not in content
    assert GENERATED_PASSWORD.search(content) is None
    assert saved["must_change"] is True
    assert verify_password(saved["hash"], TEMPORARY_PASSWORD)


def test_typed_password_below_the_minimum_is_rejected(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    before = count_users(app)

    response = client.post(
        "/users/new",
        data=form_data(password_mode="manual", temporary_password="corta"),
    )

    assert response.status_code == 200
    assert "al menos" in response.get_data(as_text=True)
    assert count_users(app) == before
    assert audit_actions(app) == []


def test_typed_password_is_required_in_manual_mode(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    before = count_users(app)

    response = client.post(
        "/users/new",
        data=form_data(password_mode="manual", temporary_password=""),
    )

    assert response.status_code == 200
    assert "Ingresa la contraseña temporal." in response.get_data(
        as_text=True
    )
    assert count_users(app) == before


def test_typed_password_is_ignored_in_generate_mode(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)

    response = client.post(
        "/users/new",
        data=form_data(temporary_password=TEMPORARY_PASSWORD),
    )
    saved = find_user(app, "ana.perez")

    assert response.status_code == 200
    assert not verify_password(saved["hash"], TEMPORARY_PASSWORD)


# --- Validaciones del formulario -------------------------------------


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"nombre": ""}, "Ingresa el nombre."),
        ({"apellido": ""}, "Ingresa el apellido."),
        ({"username": ""}, "Ingresa el nombre de usuario."),
        ({"username": "ab"}, "entre 3 y 50 caracteres"),
        ({"username": "ana perez"}, "letras minúsculas"),
        ({"username": "-ana"}, "letras minúsculas"),
        ({"username": "a" * 51}, "entre 3 y 50 caracteres"),
        ({"email": ""}, "Ingresa el correo electrónico."),
        ({"email": "sin-arroba"}, "correo electrónico válido"),
        ({"email": "a@b"}, "correo electrónico válido"),
        ({"telefono": "1" * 31}, "Máximo 30 caracteres."),
        ({"rol": ""}, "Selecciona un rol."),
        ({"rol": "SUPERADMIN"}, "Selecciona un rol válido."),
        ({"password_mode": "otro"}, "Elige cómo definir la contraseña."),
    ],
)
def test_invalid_form_data_is_rejected_with_a_message(
    client,
    app,
    seeded_roles,
    make_user,
    overrides,
    message,
):
    admin_session(client, make_user)
    before = count_users(app)

    response = client.post("/users/new", data=form_data(**overrides))

    assert response.status_code == 200
    assert message in response.get_data(as_text=True)
    assert count_users(app) == before
    assert audit_actions(app) == []


def test_form_keeps_the_entered_data_but_never_a_password(
    client,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)

    response = client.post(
        "/users/new",
        data=form_data(
            email="invalido",
            password_mode="manual",
            temporary_password=TEMPORARY_PASSWORD,
        ),
    )
    content = response.get_data(as_text=True)

    assert 'value="Ana"' in content
    assert 'value="ana.perez"' in content
    assert TEMPORARY_PASSWORD not in content


def test_username_and_email_are_stored_in_lowercase(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)

    client.post(
        "/users/new",
        data=form_data(
            username="Ana.Perez",
            email="ANA.PEREZ@WorkDesk.local",
        ),
    )

    assert find_user(app, "ana.perez") is not None


def test_duplicate_username_is_rejected(
    client,
    app,
    seeded_roles,
    make_user,
):
    admin_session(client, make_user)
    client.post("/users/new", data=form_data())

    response = client.post(
        "/users/new",
        data=form_data(email="otro@workdesk.local"),
    )

    assert response.status_code == 200
    assert "Ya existe un usuario con ese nombre." in response.get_data(
        as_text=True
    )
    assert count_users(app) == 2  # administrador + primer alta
    assert audit_actions(app) == ["USUARIO_CREADO"]


def test_duplicate_email_is_rejected(client, app, seeded_roles, make_user):
    admin_session(client, make_user)
    client.post("/users/new", data=form_data())

    response = client.post(
        "/users/new",
        data=form_data(username="otro.usuario"),
    )

    assert response.status_code == 200
    assert "Ya existe un usuario con ese correo." in response.get_data(
        as_text=True
    )
    assert count_users(app) == 2
