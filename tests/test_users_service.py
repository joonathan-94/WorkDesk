import pytest
from sqlalchemy import event

from src.workdesk.extensions import db
from src.workdesk.models import AdminAuditLog, Role, User
from src.workdesk.security import (
    PasswordPolicyError,
    hash_password,
    verify_password,
)
from src.workdesk.users import service
from src.workdesk.users.service import (
    PAGE_SIZE,
    DuplicateUserError,
    UnknownRoleError,
    create_user,
    list_users,
)

TEMPORARY_PASSWORD = "ClaveTemporal789xyz"


def default_data(**overrides):
    data = {
        "nombre": "Ana",
        "apellido": "Pérez",
        "username": "ana.perez",
        "email": "ana.perez@workdesk.local",
        "role_code": "TECNICO",
        "temporary_password": TEMPORARY_PASSWORD,
    }
    data.update(overrides)

    return data


def get_admin(admin_data):
    return db.session.get(User, admin_data["id"])


def audit_entries():
    return list(
        db.session.scalars(db.select(AdminAuditLog).order_by(AdminAuditLog.id))
    )


def count_users() -> int:
    return db.session.scalar(db.select(db.func.count()).select_from(User))


def add_users(count, *, role_code="SOLICITANTE", prefix="usuario", **extra):
    """Inserta usuarios directamente (reutiliza un único hash por rapidez)."""
    role = db.session.scalar(db.select(Role).where(Role.codigo == role_code))
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
                **extra,
            )
        )

    db.session.commit()


# --- Creación ---------------------------------------------------------


def test_create_user_persists_the_expected_data(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")

    with app.app_context():
        admin = get_admin(admin_data)

        user = create_user(
            actor=admin,
            telefono="+56 9 1234 5678",
            cargo="Analista",
            departamento_area="Soporte",
            **default_data(),
        )
        db.session.commit()

        saved = db.session.get(User, user.id)

        assert saved.nombre == "Ana"
        assert saved.apellido == "Pérez"
        assert saved.username == "ana.perez"
        assert saved.email == "ana.perez@workdesk.local"
        assert saved.telefono == "+56 9 1234 5678"
        assert saved.cargo == "Analista"
        assert saved.departamento_area == "Soporte"
        assert saved.rol.codigo == "TECNICO"
        assert saved.activo is True
        assert saved.debe_cambiar_password is True
        assert saved.usuario_creacion_id == admin.id
        assert verify_password(saved.password_hash, TEMPORARY_PASSWORD)


def test_create_user_normalizes_and_cleans_the_input(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")

    with app.app_context():
        user = create_user(
            actor=get_admin(admin_data),
            telefono="   ",
            cargo="  ",
            **default_data(
                nombre="  Ana  ",
                apellido=" Pérez ",
                username="  Ana.Perez ",
                email="  ANA.PEREZ@WorkDesk.local ",
            ),
        )

        assert user.nombre == "Ana"
        assert user.apellido == "Pérez"
        assert user.username == "ana.perez"
        assert user.email == "ana.perez@workdesk.local"
        assert user.telefono is None
        assert user.cargo is None


def test_create_user_is_audited_without_secrets(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")

    with app.app_context():
        admin = get_admin(admin_data)

        user = create_user(actor=admin, **default_data())
        db.session.commit()

        (entry,) = audit_entries()
        stored = f"{entry.valor_nuevo} {entry.valor_anterior} {entry.detalle}"

        assert entry.accion == "USUARIO_CREADO"
        assert entry.actor_usuario_id == admin.id
        assert entry.entidad_tipo == "usuario"
        assert entry.entidad_id == user.id
        assert entry.valor_nuevo == {
            "username": "ana.perez",
            "email": "ana.perez@workdesk.local",
            "rol": "TECNICO",
            "activo": True,
            "cambio_obligatorio": True,
        }
        assert TEMPORARY_PASSWORD not in stored
        assert user.password_hash not in stored


def test_create_user_does_not_commit(app, seeded_roles, make_user):
    admin_data = make_user("ADMINISTRADOR")

    with app.app_context():
        create_user(actor=get_admin(admin_data), **default_data())
        db.session.rollback()

        assert count_users() == 1  # solo el administrador
        assert audit_entries() == []


def test_create_user_rejects_a_duplicate_username_ignoring_case(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")

    with app.app_context():
        admin = get_admin(admin_data)

        with pytest.raises(DuplicateUserError) as error:
            create_user(
                actor=admin,
                **default_data(username=admin.username.upper()),
            )

        assert error.value.field == "username"
        assert count_users() == 1
        assert audit_entries() == []


def test_create_user_rejects_a_duplicate_email_ignoring_case(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")

    with app.app_context():
        admin = get_admin(admin_data)

        with pytest.raises(DuplicateUserError) as error:
            create_user(
                actor=admin,
                **default_data(email=admin.email.upper()),
            )

        assert error.value.field == "email"
        assert count_users() == 1
        assert audit_entries() == []


def test_create_user_rejects_unknown_role(app, seeded_roles, make_user):
    admin_data = make_user("ADMINISTRADOR")

    with app.app_context(), pytest.raises(UnknownRoleError):
        create_user(
            actor=get_admin(admin_data),
            **default_data(role_code="SUPERADMIN"),
        )


def test_create_user_rejects_a_weak_temporary_password(
    app,
    seeded_roles,
    make_user,
):
    admin_data = make_user("ADMINISTRADOR")

    with app.app_context():
        with pytest.raises(PasswordPolicyError):
            create_user(
                actor=get_admin(admin_data),
                **default_data(temporary_password="corta"),
            )

        db.session.rollback()

        assert count_users() == 1
        assert audit_entries() == []


def test_create_user_recovers_from_a_unique_constraint_race(
    app,
    seeded_roles,
    make_user,
    monkeypatch,
):
    """Si dos altas simultáneas pasan la comprobación, gana la restricción."""
    admin_data = make_user("ADMINISTRADOR")

    with app.app_context():
        admin = get_admin(admin_data)
        create_user(actor=admin, **default_data())
        db.session.commit()

        # Simula que la comprobación previa no vio al otro usuario.
        monkeypatch.setattr(service, "_is_in_use", lambda column, value: False)

        with pytest.raises(DuplicateUserError) as error:
            create_user(actor=admin, **default_data())

        assert error.value.field is None

        # La sesión sigue siendo utilizable y no quedó auditoría del intento.
        monkeypatch.undo()
        create_user(
            actor=admin,
            **default_data(
                username="otra.persona",
                email="otra@workdesk.local",
            ),
        )
        db.session.commit()

        assert count_users() == 3
        assert len(audit_entries()) == 2


# --- Listado ----------------------------------------------------------


def test_list_users_orders_by_last_name_then_first_name(
    app,
    seeded_roles,
):
    with app.app_context():
        add_users(3)

        page = list_users()

        assert [user.apellido for user in page.items] == [
            "Apellido00",
            "Apellido01",
            "Apellido02",
        ]
        assert page.total == 3


@pytest.mark.parametrize(
    "query",
    [
        "nombre01",
        "NOMBRE01",
        "apellido01",
        "Nombre01 Apellido01",
        "buscado01",
        "buscado01@workdesk",
    ],
)
def test_list_users_search_matches_every_visible_field(
    app,
    seeded_roles,
    query,
):
    with app.app_context():
        add_users(3, prefix="buscado")

        page = list_users(query_text=query)

        assert [user.username for user in page.items] == ["buscado01"]


def test_list_users_search_treats_wildcards_literally(app, seeded_roles):
    with app.app_context():
        add_users(3)

        assert list_users(query_text="%").total == 0
        assert list_users(query_text="_").total == 0
        assert list_users(query_text="\\").total == 0


def test_list_users_search_text_is_limited_in_length(app, seeded_roles):
    with app.app_context():
        add_users(2)

        assert list_users(query_text="x" * 5000).total == 0


def test_list_users_filters_by_role(app, seeded_roles):
    with app.app_context():
        add_users(2, role_code="SOLICITANTE", prefix="sol")
        add_users(3, role_code="TECNICO", prefix="tec")

        page = list_users(role_code="TECNICO")

        assert page.total == 3
        assert {user.rol.codigo for user in page.items} == {"TECNICO"}


def test_list_users_filters_by_status(app, seeded_roles):
    with app.app_context():
        add_users(2, prefix="act")
        add_users(3, prefix="ina", activo=False)

        assert list_users(status="activo").total == 2
        assert list_users(status="inactivo").total == 3
        assert list_users().total == 5


def test_list_users_combines_search_and_filters(app, seeded_roles):
    with app.app_context():
        add_users(3, role_code="SOLICITANTE", prefix="sol")
        add_users(3, role_code="TECNICO", prefix="tec")

        page = list_users(query_text="02", role_code="TECNICO")

        assert [user.username for user in page.items] == ["tec02"]


def test_list_users_paginates_in_the_database(app, seeded_roles):
    with app.app_context():
        add_users(PAGE_SIZE + 5)

        first = list_users(page=1)
        second = list_users(page=2)
        beyond = list_users(page=99)

        assert len(first.items) == PAGE_SIZE
        assert len(second.items) == 5
        assert first.total == PAGE_SIZE + 5
        assert first.pages == 2
        assert first.has_next is True
        assert second.has_next is False
        assert beyond.items == []


def test_list_users_loads_roles_without_extra_queries(app, seeded_roles):
    with app.app_context():
        add_users(10)

        statements = []

        def count_statement(conn, cursor, statement, *args):
            statements.append(statement)

        event.listen(db.engine, "before_cursor_execute", count_statement)

        try:
            page = list_users()

            # Acceder al rol de cada fila no debe lanzar una consulta por fila.
            names = [user.rol.nombre for user in page.items]
        finally:
            event.remove(db.engine, "before_cursor_execute", count_statement)

        assert len(names) == 10
        # Una consulta para la página y otra para el total.
        assert len(statements) <= 2
