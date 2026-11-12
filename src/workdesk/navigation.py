"""Navegación principal de la aplicación (sidebar y menú de usuario).

La definición vive aquí, en backend, y se filtra por rol antes de llegar a
la plantilla: las opciones no autorizadas ni siquiera se envían al
navegador (docs/11, sección 5.5). Esto es solo presentación: cada ruta
protegida sigue comprobando la autorización por su cuenta.

Para añadir una opción cuando exista su pantalla, basta con añadir un
`NavItem` a `MAIN_NAVIGATION` indicando los roles que la ven.
"""

from dataclasses import dataclass

from flask import request
from flask_login import current_user

from .security import RoleCode, has_any_role


@dataclass(frozen=True)
class NavItem:
    """Opción de navegación.

    `roles` es la lista de roles que la ven; None significa cualquier
    usuario autenticado. `active_prefixes` son los prefijos de endpoint
    (por ejemplo "users.") en los que la opción se marca como activa.
    """

    label: str
    endpoint: str
    icon: str
    roles: tuple[RoleCode, ...] | None = None
    active_prefixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class NavLink:
    """Opción ya filtrada para el usuario actual, lista para dibujarse."""

    label: str
    endpoint: str
    icon: str
    active: bool


# Solo las pantallas que existen hoy. El resto de opciones previstas en
# docs/11 (tickets, carga de trabajo, reportes...) se añadirán con su módulo.
MAIN_NAVIGATION = (
    NavItem(
        label="Dashboard",
        endpoint="main.dashboard",
        icon="speedometer2",
        active_prefixes=("main.",),
    ),
    NavItem(
        label="Administración",
        endpoint="admin.index",
        icon="gear",
        roles=(RoleCode.ADMINISTRADOR,),
        active_prefixes=("admin.", "users."),
    ),
)

# Grupo inferior, separado del principal.
ACCOUNT_NAVIGATION = (
    NavItem(
        label="Mi cuenta",
        endpoint="account.change_password",
        icon="person",
        active_prefixes=("account.",),
    ),
)


def build_links(user, items: tuple[NavItem, ...], current_endpoint: str | None):
    """Devuelve las opciones que `user` puede ver, marcando la activa."""
    links = []

    for item in items:
        if not _is_visible(user, item):
            continue

        active = bool(current_endpoint) and current_endpoint.startswith(
            item.active_prefixes
        )

        links.append(
            NavLink(
                label=item.label,
                endpoint=item.endpoint,
                icon=item.icon,
                active=active,
            )
        )

    return links


def user_initials(user) -> str:
    """Iniciales para el avatar: primera letra del nombre y del apellido."""
    letters = [
        part.strip()[0]
        for part in (user.nombre, user.apellido)
        if part and part.strip()
    ]

    if not letters:
        letters = [user.username[0]]

    return "".join(letters[:2]).upper()


def layout_context() -> dict:
    """Variables que el layout necesita en cada página autenticada."""
    if not current_user.is_authenticated:
        return {}

    endpoint = request.endpoint

    return {
        "main_navigation": build_links(
            current_user,
            MAIN_NAVIGATION,
            endpoint,
        ),
        "account_navigation": build_links(
            current_user,
            ACCOUNT_NAVIGATION,
            endpoint,
        ),
        "user_initials": user_initials(current_user),
    }


def _is_visible(user, item: NavItem) -> bool:
    if item.roles is None:
        return bool(user.is_authenticated and user.is_active)

    return has_any_role(user, *item.roles)
