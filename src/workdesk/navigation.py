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

from .notifications.service import count_unread
from .security import STAFF_ROLES, RoleCode, current_actor, has_any_role


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
# docs/11 (carga de trabajo, reportes, base de conocimiento...) se añadirán con
# su módulo.
# Pantallas que cuentan como parte de "Tickets" / "Mis tickets": el listado,
# el detalle y las acciones sobre un ticket. "Crear ticket" tiene su propia
# opción y no está aquí.
TICKET_SCREENS = (
    "tickets.list_tickets_page",
    "tickets.detail",
    "tickets.edit_ticket",
    "tickets.change_ticket_priority",
    "tickets.change_ticket_state",
    "tickets.assignment_page",
    "tickets.escalate",
    "tickets.requesters_page",
    "tickets.remove_ticket_requester",
    "tickets.relations_page",
    "tickets.remove_ticket_relation",
    "tickets.mark_ticket_duplicate",
    "tickets.edit_ticket_comment",
    "tickets.delete_ticket_comment",
    "tickets.delete_ticket_attachment",
)

MAIN_NAVIGATION = (
    NavItem(
        label="Dashboard",
        endpoint="main.dashboard",
        icon="speedometer2",
        active_prefixes=("main.",),
    ),
    # El personal ve todos los tickets ("Tickets"); el Solicitante, solo los
    # suyos ("Mis tickets"). Ambas llevan al mismo listado, que filtra por rol
    # en la consulta. El detalle de un ticket cuenta como parte de esta opción.
    NavItem(
        label="Tickets",
        endpoint="tickets.list_tickets_page",
        icon="card-list",
        roles=STAFF_ROLES,
        active_prefixes=TICKET_SCREENS,
    ),
    NavItem(
        label="Mis tickets",
        endpoint="tickets.list_tickets_page",
        icon="card-list",
        roles=(RoleCode.SOLICITANTE,),
        active_prefixes=TICKET_SCREENS,
    ),
    # Solo se marca activa en el formulario de creación.
    NavItem(
        label="Crear ticket",
        endpoint="tickets.new_ticket",
        icon="plus-circle",
        active_prefixes=("tickets.new_ticket",),
    ),
    # La carga de trabajo del equipo: solo el personal (la ruta lo vuelve a comprobar).
    NavItem(
        label="Carga de trabajo",
        endpoint="workload.workload_page",
        icon="people",
        roles=STAFF_ROLES,
        active_prefixes=("workload.",),
    ),
    # Los avisos del propio usuario: los ven los cuatro roles (docs/11, 5.x).
    NavItem(
        label="Notificaciones",
        endpoint="notifications.list_notifications_page",
        icon="bell",
        active_prefixes=("notifications.",),
    ),
    # El Supervisor gestiona los técnicos de sus grupos. El Administrador llega
    # a los grupos desde Administración.
    NavItem(
        label="Grupos",
        endpoint="groups.list_groups_page",
        icon="diagram-3",
        roles=(RoleCode.SUPERVISOR,),
        active_prefixes=("groups.",),
    ),
    NavItem(
        label="Administración",
        endpoint="admin.index",
        icon="gear",
        roles=(RoleCode.ADMINISTRADOR,),
        active_prefixes=("admin.", "users.", "catalogs.", "groups.", "sla."),
    ),
)

# Grupo inferior, separado del principal.
ACCOUNT_NAVIGATION = (
    NavItem(
        label="Mi cuenta",
        endpoint="account.index",
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
        # El contador de la campana: se vuelve a calcular en cada página.
        "unread_notifications": count_unread(current_actor()),
    }


def _is_visible(user, item: NavItem) -> bool:
    if item.roles is None:
        return bool(user.is_authenticated and user.is_active)

    return has_any_role(user, *item.roles)
