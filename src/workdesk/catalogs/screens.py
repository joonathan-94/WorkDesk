"""Descripción de cada pantalla de catálogo.

Las tres comparten las mismas plantillas (listado, formulario y
confirmación). Este módulo guarda lo que cambia entre ellas: textos, rutas,
columnas y la plantilla de sus campos. Es solo presentación; las reglas
están en `catalogs.service`.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogScreen:
    title: str
    description: str
    singular: str
    # Columnas del listado, en orden; cada clave la dibuja la plantilla.
    columns: tuple[str, ...]
    fields_template: str
    list_endpoint: str
    edit_endpoint: str
    deactivate_endpoint: str
    activate_endpoint: str
    created_message: str
    updated_message: str
    deactivated_message: str
    activated_message: str
    duplicate_message: str
    empty_message: str
    # None cuando el catálogo no admite altas desde la interfaz.
    new_label: str | None = None
    new_endpoint: str | None = None


CATEGORIES = CatalogScreen(
    title="Categorías",
    description="Clasificación de las solicitudes.",
    singular="categoría",
    columns=("nombre", "descripcion", "orden", "estado"),
    fields_template="catalogs/_fields_category.html",
    list_endpoint="catalogs.categories_list",
    new_endpoint="catalogs.category_new",
    new_label="Nueva categoría",
    edit_endpoint="catalogs.category_edit",
    deactivate_endpoint="catalogs.category_deactivate",
    activate_endpoint="catalogs.category_activate",
    created_message="La categoría «{name}» fue creada.",
    updated_message="La categoría «{name}» se actualizó.",
    deactivated_message=(
        "La categoría «{name}» fue desactivada. Ya no se puede elegir en "
        "tickets nuevos."
    ),
    activated_message="La categoría «{name}» fue reactivada.",
    duplicate_message="Ya existe una categoría con ese nombre.",
    empty_message="No hay categorías con esos criterios.",
)

PRIORITIES = CatalogScreen(
    title="Prioridades",
    description="Niveles de prioridad de los tickets.",
    singular="prioridad",
    columns=("nombre", "nivel", "color", "descripcion", "estado"),
    fields_template="catalogs/_fields_priority.html",
    list_endpoint="catalogs.priorities_list",
    edit_endpoint="catalogs.priority_edit",
    deactivate_endpoint="catalogs.priority_deactivate",
    activate_endpoint="catalogs.priority_activate",
    created_message="La prioridad «{name}» fue creada.",
    updated_message="La prioridad «{name}» se actualizó.",
    deactivated_message=(
        "La prioridad «{name}» fue desactivada. Ya no se puede elegir en "
        "tickets nuevos."
    ),
    activated_message="La prioridad «{name}» fue reactivada.",
    duplicate_message="Ya existe una prioridad con ese nombre.",
    empty_message="No hay prioridades con esos criterios.",
)

LOCATIONS = CatalogScreen(
    title="Ubicaciones",
    description="Sedes, oficinas y áreas disponibles en los tickets.",
    singular="ubicación",
    columns=("nombre", "tipo", "descripcion", "estado"),
    fields_template="catalogs/_fields_location.html",
    list_endpoint="catalogs.locations_list",
    new_endpoint="catalogs.location_new",
    new_label="Nueva ubicación",
    edit_endpoint="catalogs.location_edit",
    deactivate_endpoint="catalogs.location_deactivate",
    activate_endpoint="catalogs.location_activate",
    created_message="La ubicación «{name}» fue creada.",
    updated_message="La ubicación «{name}» se actualizó.",
    deactivated_message=(
        "La ubicación «{name}» fue desactivada. Ya no se puede elegir en "
        "tickets nuevos."
    ),
    activated_message="La ubicación «{name}» fue reactivada.",
    duplicate_message="Ya existe una ubicación con ese nombre.",
    empty_message="No hay ubicaciones con esos criterios.",
)
