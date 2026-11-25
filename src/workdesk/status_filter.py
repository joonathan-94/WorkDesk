"""El filtro «Activos / Inactivos» de los listados de administración (usuarios,
catálogos y grupos): los valores que viajan en la URL."""

STATUS_ACTIVE = "activo"
STATUS_INACTIVE = "inactivo"
VALID_STATUSES = frozenset({STATUS_ACTIVE, STATUS_INACTIVE})
