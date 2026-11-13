"""Datos iniciales de los catálogos de tickets (docs/09, sección 40).

Es idempotente, igual que `seed_roles`: cada registro se identifica por su
`codigo` y, si ya existe, no se toca. Así volver a ejecutarlo nunca pisa lo
que un Administrador haya renombrado o desactivado.

Las ubicaciones no se cargan aquí: no hay ninguna obligatoria para operar y
dependen de cada organización (los datos de ejemplo irán en `seed-demo`).
"""

from ..extensions import db
from ..models import Categoria, Estado, MotivoCierre, Prioridad
from ..models.categoria import FALLBACK_CATEGORY_CODE

# Estructurales protegidos. Colores según docs/11, sección 7.
INITIAL_STATES = (
    {
        "codigo": "NUEVO",
        "nombre_visible": "Nuevo",
        "descripcion": "Ticket registrado, pendiente de atención.",
        "color": "#64748B",
        "orden": 1,
    },
    {
        "codigo": "ASIGNADO",
        "nombre_visible": "Asignado",
        "descripcion": "Ticket con técnico asignado, sin iniciar el trabajo.",
        "color": "#7C3AED",
        "orden": 2,
    },
    {
        "codigo": "EN_PROGRESO",
        "nombre_visible": "En progreso",
        "descripcion": "Ticket en atención.",
        "color": "#1D4ED8",
        "orden": 3,
    },
    {
        "codigo": "EN_ESPERA",
        "nombre_visible": "En espera",
        "descripcion": "Atención detenida a la espera de un tercero o dato.",
        "color": "#F59E0B",
        "orden": 4,
    },
    {
        "codigo": "RESUELTO",
        "nombre_visible": "Resuelto",
        "descripcion": "Solución aplicada, pendiente de validación.",
        "color": "#16A34A",
        "orden": 5,
    },
    {
        "codigo": "CERRADO",
        "nombre_visible": "Cerrado",
        "descripcion": "Ticket finalizado.",
        "color": "#94A3B8",
        "orden": 6,
    },
)

INITIAL_PRIORITIES = (
    {
        "codigo": "BAJA",
        "nombre": "Baja",
        "descripcion": "Sin urgencia ni impacto relevante.",
        "nivel": 1,
        "color": "#94A3B8",
    },
    {
        "codigo": "MEDIA",
        "nombre": "Media",
        "descripcion": "Prioridad habitual.",
        "nivel": 2,
        "color": "#1D4ED8",
    },
    {
        "codigo": "ALTA",
        "nombre": "Alta",
        "descripcion": "Afecta el trabajo y debe atenderse pronto.",
        "nivel": 3,
        "color": "#EA580C",
    },
    {
        "codigo": "CRITICA",
        "nombre": "Crítica",
        "descripcion": "Impide operar o afecta a muchas personas.",
        "nivel": 4,
        "color": "#EF4444",
    },
)

INITIAL_CATEGORIES = (
    {
        "codigo": FALLBACK_CATEGORY_CODE,
        "nombre": "Sin clasificar",
        "descripcion": "Clasificación pendiente o desconocida.",
        "orden": 0,
    },
)

INITIAL_CLOSE_REASONS = (
    {
        "codigo": "RESOLUCION_VALIDADA",
        "nombre": "Resolución validada",
        "descripcion": "El solicitante confirmó la solución.",
        "orden": 1,
    },
    {
        "codigo": "CIERRE_DIRECTO",
        "nombre": "Cierre directo",
        "descripcion": "Cerrado sin pasar por la validación del solicitante.",
        "orden": 2,
    },
    {
        "codigo": "INACTIVIDAD",
        "nombre": "Inactividad",
        "descripcion": "Cierre automático por falta de respuesta.",
        "orden": 3,
    },
    {
        "codigo": "DUPLICADO",
        "nombre": "Duplicado",
        "descripcion": "El ticket repite otro ya registrado.",
        "orden": 4,
    },
    {
        "codigo": "CANCELACION",
        "nombre": "Cancelación",
        "descripcion": "La solicitud ya no es necesaria.",
        "orden": 5,
    },
    {
        "codigo": "CIERRE_EXCEPCIONAL",
        "nombre": "Cierre excepcional",
        "descripcion": "Cierre autorizado fuera del flujo normal.",
        "orden": 6,
    },
)


def _seed_by_code(model, rows) -> int:
    """Inserta los registros cuyo `codigo` no existe; devuelve cuántos creó."""
    created = 0

    for row in rows:
        existing = db.session.scalar(
            db.select(model).where(model.codigo == row["codigo"])
        )

        if existing is not None:
            continue

        db.session.add(model(**row))
        created += 1

    return created


def seed_catalogs() -> dict[str, int]:
    """Carga estados, prioridades, categoría de respaldo y motivos de cierre.

    Devuelve cuántos registros creó de cada catálogo. Confirma una sola vez
    al final: o se cargan todos o ninguno.
    """
    created = {
        "estados": _seed_by_code(Estado, INITIAL_STATES),
        "prioridades": _seed_by_code(Prioridad, INITIAL_PRIORITIES),
        "categorias": _seed_by_code(Categoria, INITIAL_CATEGORIES),
        "motivos_cierre": _seed_by_code(MotivoCierre, INITIAL_CLOSE_REASONS),
    }

    db.session.commit()

    return created
