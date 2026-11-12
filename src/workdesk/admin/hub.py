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
            ),
            HubCard(
                title="Prioridades",
                description="Niveles de prioridad y su orden.",
                icon="flag",
            ),
            HubCard(
                title="Ubicaciones",
                description="Sedes, oficinas y áreas.",
                icon="geo-alt",
            ),
            HubCard(
                title="Estados y transiciones",
                description="Nombres y transiciones del flujo.",
                icon="diagram-2",
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
            ),
            HubCard(
                title="Cierre y reapertura",
                description="Plazos de validación y reapertura.",
                icon="arrow-repeat",
            ),
            HubCard(
                title="Notificaciones",
                description="Eventos y destinatarios.",
                icon="bell",
            ),
            HubCard(
                title="Archivos",
                description="Tamaño y tipos permitidos.",
                icon="paperclip",
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
