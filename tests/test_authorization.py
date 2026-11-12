import pytest
from flask_login import AnonymousUserMixin

from src.workdesk.extensions import db
from src.workdesk.models import User
from src.workdesk.security import (
    RoleCode,
    can_manage_users,
    can_view_audit,
    has_any_role,
)

NON_ADMIN_ROLES = ("SOLICITANTE", "TECNICO", "SUPERVISOR")


def login(client, user_data):
    return client.post(
        "/login",
        data={
            "username": user_data["username"],
            "password": user_data["password"],
        },
    )


def test_admin_area_redirects_anonymous_user_to_login(client):
    response = client.get("/admin")

    assert response.status_code == 302
    assert "/login" in response.location


@pytest.mark.parametrize("role_code", NON_ADMIN_ROLES)
def test_admin_area_is_forbidden_for_non_admin_roles(
    client,
    make_user,
    role_code,
):
    user_data = make_user(role_code)
    login(client, user_data)

    response = client.get("/admin")

    assert response.status_code == 403
    assert "Acceso denegado" in response.get_data(as_text=True)


def test_admin_area_is_available_to_administrator(client, make_user):
    user_data = make_user("ADMINISTRADOR")
    login(client, user_data)

    response = client.get("/admin")

    assert response.status_code == 200
    assert "Administración" in response.get_data(as_text=True)


def test_deactivated_administrator_loses_admin_access(
    client,
    app,
    make_user,
):
    user_data = make_user("ADMINISTRADOR")
    login(client, user_data)

    with app.app_context():
        user = db.session.get(User, user_data["id"])
        user.activo = False
        db.session.commit()

    response = client.get("/admin")

    assert response.status_code == 302
    assert "/login" in response.location


@pytest.mark.parametrize(
    ("role_code", "expected"),
    (
        ("SOLICITANTE", False),
        ("TECNICO", False),
        ("SUPERVISOR", False),
        ("ADMINISTRADOR", True),
    ),
)
def test_user_and_audit_policies_follow_permission_matrix(
    app,
    make_user,
    role_code,
    expected,
):
    user_data = make_user(role_code)

    with app.app_context():
        user = db.session.get(User, user_data["id"])

        assert can_manage_users(user) is expected
        assert can_view_audit(user) is expected


def test_has_any_role_accepts_any_of_the_given_roles(app, make_user):
    user_data = make_user("SUPERVISOR")

    with app.app_context():
        user = db.session.get(User, user_data["id"])

        assert has_any_role(user, RoleCode.TECNICO, RoleCode.SUPERVISOR)
        assert not has_any_role(user, RoleCode.ADMINISTRADOR)


def test_policies_deny_anonymous_user():
    anonymous = AnonymousUserMixin()

    assert not can_manage_users(anonymous)
    assert not can_view_audit(anonymous)
    assert not has_any_role(anonymous, RoleCode.ADMINISTRADOR)
