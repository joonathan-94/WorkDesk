"""Secciones del hub de administración (docs/11, UI-014).

Cada tarjeta enlaza con su pantalla cuando existe (`endpoint`). Las
secciones previstas pero todavía no implementadas se muestran como
"Próximamente", sin enlace: así el hub refleja el diseño sin presentar como
disponible algo que no lo está. Al implementar una sección, basta con
indicar su `endpoint`.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class HubCard:
    title: str
    description: str
    icon: str
    endpoint: str | None = None
    # Argumentos de la ruta, como pares (nombre, valor).
    args: tuple[tuple[str, str], ...] = ()

    @property
    def url_args(self) -> dict[str, str]:
        return dict(self.args)


@dataclass(frozen=True)
class HubSection:
    title: str
    cards: tuple[HubCard, ...]


HUB_SECTIONS = (
    HubSection(
        title="Personas y organización",
        cards=(
            HubCard(
                title="Usuarios",
                description="Consulta, crea y administra las cuentas.",
                icon="people",
                endpoint="users.list_users_page",
            ),
            HubCard(
                title="Grupos",
                description="Grupos de atención y sus miembros.",
                icon="diagram-3",
                endpoint="groups.list_groups_page",
            ),
        ),
    ),
    HubSection(
        title="Configuración de tickets",
        cards=(
            HubCard(
                title="Categorías",
                description="Clasificación de las solicitudes.",
                icon="tags",
                endpoint="catalogs.categories_list",
            ),
            HubCard(
                title="Prioridades",
                description="Niveles de prioridad de los tickets.",
                icon="flag",
                endpoint="catalogs.priorities_list",
            ),
            HubCard(
                title="Ubicaciones",
                description="Sedes, oficinas y áreas.",
                icon="geo-alt",
                endpoint="catalogs.locations_list",
            ),
            HubCard(
                title="Motivos de espera",
                description="Motivos opcionales al poner un ticket en espera.",
                icon="hourglass-split",
                endpoint="catalogs.wait_reasons_list",
            ),
            HubCard(
                title="Estados y transiciones",
                description="Nombres y transiciones del flujo.",
                icon="diagram-2",
                endpoint="catalogs.states_page",
            ),
            HubCard(
                title="Comentarios y edición",
                description="Plazo de corrección y bloqueo de edición.",
                icon="chat-square-text",
                endpoint="admin.settings_screen",
                args=(("slug", "colaboracion"),),
            ),
            HubCard(
                title="Posibles duplicados",
                description="Aviso de tickets parecidos al crear uno.",
                icon="files",
                endpoint="admin.settings_screen",
                args=(("slug", "duplicados"),),
            ),
        ),
    ),
    HubSection(
        title="Operación y políticas",
        cards=(
            HubCard(
                title="SLA",
                description="Tiempos objetivo y calendario laboral.",
                icon="clock",
                endpoint="sla.index",
            ),
            HubCard(
                title="Cierre y reapertura",
                description="Plazos de validación y reapertura.",
                icon="arrow-repeat",
                endpoint="admin.settings_screen",
                args=(("slug", "cierre"),),
            ),
            HubCard(
                title="Notificaciones",
                description="Eventos y destinatarios.",
                icon="bell",
                endpoint="admin.notification_settings",
            ),
            HubCard(
                title="Archivos",
                description="Tamaño y tipos permitidos.",
                icon="paperclip",
                endpoint="admin.settings_screen",
                args=(("slug", "archivos"),),
            ),
            HubCard(
                title="Carga y planificador",
                description="Carga alta y tareas automáticas.",
                icon="speedometer2",
                endpoint="admin.settings_screen",
                args=(("slug", "operacion"),),
            ),
            HubCard(
                title="Retención",
                description="Conservación de la información.",
                icon="archive",
            ),
        ),
    ),
    HubSection(
        title="Sistema y seguridad",
        cards=(
            HubCard(
                title="Seguridad y sesión",
                description="Bloqueo de cuentas, contraseñas y sesión.",
                icon="lock",
                endpoint="admin.settings_screen",
                args=(("slug", "seguridad"),),
            ),
            HubCard(
                title="Auditoría",
                description="Registro de acciones administrativas.",
                icon="shield-check",
            ),
            HubCard(
                title="Respaldos",
                description="Copias de seguridad y restauración.",
                icon="hdd",
            ),
            HubCard(
                title="Estado del sistema",
                description="Salud de la aplicación y la base de datos.",
                icon="activity",
            ),
        ),
    ),
)
