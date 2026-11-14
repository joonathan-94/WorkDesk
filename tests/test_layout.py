import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import pytest
from flask import url_for
from flask_login import AnonymousUserMixin

from src.workdesk.admin.hub import HUB_SECTIONS
from src.workdesk.navigation import (
    ACCOUNT_NAVIGATION,
    MAIN_NAVIGATION,
    build_links,
    user_initials,
)

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "src" / "workdesk"
TEMPLATES_DIR = PACKAGE_DIR / "templates"
STATIC_DIR = PACKAGE_DIR / "static"
VENDOR_DIR = STATIC_DIR / "vendor"

VENDOR_FILES = (
    "bootstrap/css/bootstrap.min.css",
    "bootstrap/js/bootstrap.bundle.min.js",
    "bootstrap/LICENSE",
    "bootstrap-icons/font/bootstrap-icons.min.css",
    "bootstrap-icons/font/fonts/bootstrap-icons.woff2",
    "bootstrap-icons/font/fonts/bootstrap-icons.woff",
    "bootstrap-icons/LICENSE",
)


@dataclass
class StubRole:
    codigo: str


@dataclass
class StubUser:
    rol: StubRole
    nombre: str = "Tony"
    apellido: str = "Soprano"
    username: str = "tony.soprano"
    is_authenticated: bool = True
    is_active: bool = True


def stub(role_code: str, **kwargs) -> StubUser:
    return StubUser(rol=StubRole(role_code), **kwargs)


def labels(user, items=MAIN_NAVIGATION, endpoint=None):
    return [link.label for link in build_links(user, items, endpoint)]


def login(client, user_data):
    return client.post(
        "/login",
        data={
            "username": user_data["username"],
            "password": user_data["password"],
        },
    )


def page(client, make_user, role_code, path="/dashboard"):
    login(client, make_user(role_code))

    return client.get(path).get_data(as_text=True)


# --- Navegación por rol (lógica) -------------------------------------


@pytest.mark.parametrize(
    "role_code",
    ["SOLICITANTE", "TECNICO", "SUPERVISOR"],
)
def test_non_admin_roles_see_the_dashboard_and_create_ticket(role_code):
    # Todos los roles pueden crear tickets; Administración es solo del
    # Administrador.
    assert labels(stub(role_code)) == ["Dashboard", "Crear ticket"]


def test_administrator_sees_the_administration_hub():
    assert labels(stub("ADMINISTRADOR")) == [
        "Dashboard",
        "Crear ticket",
        "Administración",
    ]


@pytest.mark.parametrize(
    "role_code",
    ["SOLICITANTE", "TECNICO", "SUPERVISOR", "ADMINISTRADOR"],
)
def test_every_role_sees_its_account_link(role_code):
    assert labels(stub(role_code), ACCOUNT_NAVIGATION) == ["Mi cuenta"]


def test_inactive_users_see_no_navigation():
    inactive = stub("ADMINISTRADOR", is_active=False)

    assert labels(inactive) == []
    assert labels(inactive, ACCOUNT_NAVIGATION) == []


def test_anonymous_users_see_no_navigation():
    anonymous = AnonymousUserMixin()

    assert labels(anonymous) == []
    assert labels(anonymous, ACCOUNT_NAVIGATION) == []


@pytest.mark.parametrize(
    ("endpoint", "expected_active"),
    [
        ("main.dashboard", ["Dashboard"]),
        ("admin.index", ["Administración"]),
        ("users.list_users_page", ["Administración"]),
        ("users.detail", ["Administración"]),
        ("catalogs.categories_list", ["Administración"]),
        ("catalogs.priority_edit", ["Administración"]),
        ("catalogs.location_new", ["Administración"]),
        ("tickets.new_ticket", ["Crear ticket"]),
        # El detalle de un ticket no pertenece a "Crear ticket".
        ("tickets.detail", []),
        ("account.change_password", []),
        (None, []),
    ],
)
def test_the_active_option_follows_the_current_endpoint(
    endpoint,
    expected_active,
):
    links = build_links(stub("ADMINISTRADOR"), MAIN_NAVIGATION, endpoint)

    assert [link.label for link in links if link.active] == expected_active


def test_account_option_is_active_in_the_account_pages():
    links = build_links(
        stub("TECNICO"),
        ACCOUNT_NAVIGATION,
        "account.change_password",
    )

    assert [link.active for link in links] == [True]


def test_every_navigation_endpoint_exists(app):
    with app.test_request_context():
        for item in MAIN_NAVIGATION + ACCOUNT_NAVIGATION:
            assert url_for(item.endpoint)


# --- Iniciales del avatar --------------------------------------------


@pytest.mark.parametrize(
    ("nombre", "apellido", "expected"),
    [
        ("Tony", "Soprano", "TS"),
        ("walter", "white", "WW"),
        ("  Jesse ", " Pinkman ", "JP"),
        ("Saul", "", "S"),
        ("", "Goodman", "G"),
    ],
)
def test_initials_use_the_first_letter_of_name_and_surname(
    nombre,
    apellido,
    expected,
):
    user = stub("TECNICO", nombre=nombre, apellido=apellido)

    assert user_initials(user) == expected


def test_initials_fall_back_to_the_username():
    user = stub("TECNICO", nombre="", apellido="", username="mike.e")

    assert user_initials(user) == "M"


# --- Layout renderizado ----------------------------------------------


def test_sidebar_is_filtered_by_role_in_the_rendered_page(
    client,
    app,
    seeded_roles,
    make_user,
):
    technician = page(client, make_user, "TECNICO")
    admin = page(app.test_client(), make_user, "ADMINISTRADOR")

    assert "Dashboard" in technician
    assert "Mi cuenta" in technician
    assert 'href="/admin"' not in technician
    assert 'href="/admin"' in admin


def test_the_current_section_is_marked_as_active(
    client,
    seeded_roles,
    make_user,
):
    login(client, make_user("ADMINISTRADOR"))

    dashboard = client.get("/dashboard").get_data(as_text=True)
    admin = client.get("/admin").get_data(as_text=True)
    users = client.get("/users").get_data(as_text=True)

    active_dashboard = re.search(
        r'class="sidebar-link is-active"\s+href="([^"]+)"',
        dashboard,
    )
    active_admin = re.search(
        r'class="sidebar-link is-active"\s+href="([^"]+)"',
        admin,
    )
    active_users = re.search(
        r'class="sidebar-link is-active"\s+href="([^"]+)"',
        users,
    )

    assert active_dashboard.group(1) == "/dashboard"
    assert active_admin.group(1) == "/admin"
    assert active_users.group(1) == "/admin"
    assert 'aria-current="page"' in dashboard


def test_topbar_shows_the_avatar_name_and_role(
    client,
    seeded_roles,
    make_user,
):
    content = page(client, make_user, "ADMINISTRADOR")
    visible = " ".join(content.split())

    assert re.search(r'class="user-avatar"[^>]*>\s*AP\s*<', content)
    assert "Administrador Pruebas" in visible
    assert 'action="/logout"' in content
    assert "Cerrar sesión" in content


def test_layout_offers_a_skip_link_and_a_mobile_menu(
    client,
    seeded_roles,
    make_user,
):
    content = page(client, make_user, "TECNICO")

    assert 'href="#main-content"' in content
    assert 'id="main-content"' in content
    assert 'data-bs-target="#app-sidebar"' in content


def test_layout_loads_bootstrap_and_the_theme_from_the_local_server(
    client,
    seeded_roles,
    make_user,
):
    content = page(client, make_user, "TECNICO")

    for asset in (
        "/static/vendor/bootstrap/css/bootstrap.min.css",
        "/static/vendor/bootstrap/js/bootstrap.bundle.min.js",
        "/static/vendor/bootstrap-icons/font/bootstrap-icons.min.css",
        "/static/css/theme.css",
        "/static/css/layout.css",
    ):
        assert asset in content


@pytest.mark.parametrize(
    ("category", "bootstrap_level"),
    [("success", "alert-success"), ("error", "alert-danger")],
)
def test_flash_categories_map_to_bootstrap_alerts(
    client,
    seeded_roles,
    make_user,
    category,
    bootstrap_level,
):
    admin = make_user("ADMINISTRADOR")
    login(client, admin)

    with client.session_transaction() as client_session:
        client_session["_flashes"] = [(category, "Mensaje de prueba")]

    content = client.get("/dashboard").get_data(as_text=True)

    assert bootstrap_level in content
    assert "Mensaje de prueba" in content


# --- Hub de administración -------------------------------------------


def test_hub_shows_every_documented_section(
    client,
    seeded_roles,
    make_user,
):
    content = page(client, make_user, "ADMINISTRADOR", "/admin")

    for section in HUB_SECTIONS:
        assert section.title in content

        for card in section.cards:
            assert card.title in content


def test_hub_links_only_the_implemented_sections(
    client,
    seeded_roles,
    make_user,
):
    content = page(client, make_user, "ADMINISTRADOR", "/admin")

    implemented = [
        card
        for section in HUB_SECTIONS
        for card in section.cards
        if card.endpoint
    ]
    planned = [
        card
        for section in HUB_SECTIONS
        for card in section.cards
        if not card.endpoint
    ]

    assert [card.title for card in implemented] == [
        "Usuarios",
        "Categorías",
        "Prioridades",
        "Ubicaciones",
    ]
    assert 'href="/users"' in content
    assert 'href="/admin/categories"' in content
    assert 'href="/admin/priorities"' in content
    assert 'href="/admin/locations"' in content
    assert content.count("Próximamente") == len(planned)


def test_hub_endpoints_exist(app):
    with app.test_request_context():
        for section in HUB_SECTIONS:
            for card in section.cards:
                if card.endpoint:
                    assert url_for(card.endpoint)


# --- Activos locales (sin CDN) ---------------------------------------


@pytest.mark.parametrize("relative_path", VENDOR_FILES)
def test_vendor_assets_are_served_locally(client, relative_path):
    response = client.get(f"/static/vendor/{relative_path}")

    assert response.status_code == 200
    assert len(response.data) > 500


def test_vendor_checksums_match_the_documented_ones():
    readme = (VENDOR_DIR / "README.md").read_text(encoding="utf-8")
    documented = {
        path: checksum
        for checksum, path in re.findall(
            r"^([0-9a-f]{64})\s+(\S+)$",
            readme,
            flags=re.MULTILINE,
        )
    }

    assert set(documented) == set(VENDOR_FILES)

    for relative_path, checksum in documented.items():
        actual = hashlib.sha256(
            (VENDOR_DIR / relative_path).read_bytes()
        ).hexdigest()

        assert actual == checksum, relative_path


def test_templates_do_not_load_external_resources():
    external = re.compile(r"""(?:src|href)\s*=\s*["']\s*(?:https?:)?//""")

    for template in TEMPLATES_DIR.rglob("*.html"):
        text = template.read_text(encoding="utf-8")

        assert not external.search(text), template.name


def test_own_stylesheets_do_not_import_external_resources():
    for stylesheet in (STATIC_DIR / "css").glob("*.css"):
        text = stylesheet.read_text(encoding="utf-8")

        assert "http://" not in text, stylesheet.name
        assert "https://" not in text, stylesheet.name


# --- Pantallas de acceso (no usan Bootstrap) -------------------------


def test_login_page_keeps_its_own_styles_without_bootstrap(client):
    content = client.get("/login").get_data(as_text=True)

    assert "css/app.css" in content
    assert "css/auth.css" in content
    assert "bootstrap" not in content


def test_auth_stylesheet_defines_the_form_controls_of_the_access_pages():
    text = (STATIC_DIR / "css" / "auth.css").read_text(encoding="utf-8")

    for selector in (".form-control {", ".password-toggle {", ".form-error {"):
        assert selector in text
