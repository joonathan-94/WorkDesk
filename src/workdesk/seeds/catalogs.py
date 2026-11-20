"""Datos iniciales de los catálogos de tickets (docs/09, sección 40).

Es idempotente, igual que `seed_roles`: cada registro se identifica por su
`codigo` y, si ya existe, no se toca. Así volver a ejecutarlo nunca pisa lo
que un Administrador haya renombrado o desactivado.

Las ubicaciones no se cargan aquí: no hay ninguna obligatoria para operar y
dependen de cada organización (los datos de ejemplo no van aquí: ver
`seed-demo` y `seed-demo-tickets`).
"""

from ..extensions import db
from ..models import (
    Categoria,
    Estado,
    MotivoCierre,
    MotivoEspera,
    Prioridad,
    StateAction,
    TipoRelacionTicket,
    TransicionEstado,
)
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

# Motivos opcionales de espera (docs/08, 6.4). "Otro motivo" es la alternativa
# genérica (RF-044): permite escribir un texto y va siempre al final.
INITIAL_WAIT_REASONS = (
    {
        "codigo": "INFORMACION_PENDIENTE",
        "nombre": "Información pendiente",
        "descripcion": "Se espera un dato o una respuesta del solicitante.",
        "orden": 1,
    },
    {
        "codigo": "ESPERA_TERCERO",
        "nombre": "Espera de un tercero",
        "descripcion": "Depende de un proveedor u otra área.",
        "orden": 2,
    },
    {
        "codigo": "APROBACION_PENDIENTE",
        "nombre": "Aprobación pendiente",
        "descripcion": "Falta una autorización para continuar.",
        "orden": 3,
    },
    {
        "codigo": "RECURSO_PENDIENTE",
        "nombre": "Recurso pendiente",
        "descripcion": "Falta un equipo, repuesto o licencia.",
        "orden": 4,
    },
    {
        "codigo": "OTRO",
        "nombre": "Otro motivo",
        "descripcion": "Otra causa de espera, que se describe con un texto.",
        "orden": 5,
        "permite_texto_otro": True,
    },
)

# Tipos de relación entre tickets (docs/09, 19.1). `DUPLICADO` va del ticket
# duplicado al principal; `RELACIONADO` no tiene dirección.
INITIAL_RELATION_TYPES = (
    {
        "codigo": "DUPLICADO",
        "nombre": "Duplicado",
        "descripcion": "El ticket repite otro ya registrado (el principal).",
        "es_simetrica": False,
    },
    {
        "codigo": "RELACIONADO",
        "nombre": "Relacionado",
        "descripcion": "Los tickets tratan temas conectados.",
        "es_simetrica": True,
    },
)

# Transiciones estructuralmente válidas del flujo (docs/08, sección 34; docs/09,
# 12.2): (origen, destino, acción, descripción). Quién ejecuta cada acción lo
# decide el código de autorización, no esta tabla.
#
# `DESASIGNACION` (quitar al último técnico de un ticket `Asignado` lo deja en
# `Nuevo`) no figura en docs/08: se añade porque `Asignado` significa tener
# responsables. `AUTO_CIERRE` se carga ya, pero nada la usa hasta el cierre
# automático (v0.5.0).
S = StateAction
INITIAL_TRANSITIONS = (
    ("NUEVO", "ASIGNADO", S.ASIGNAR, "Se asigna un técnico."),
    ("NUEVO", "EN_PROGRESO", S.INICIAR, "Se inicia el trabajo."),
    ("NUEVO", "RESUELTO", S.RESOLVER, "Se resuelve sin pasos previos."),
    ("NUEVO", "CERRADO", S.CIERRE_DIRECTO, "Cierre directo."),
    ("ASIGNADO", "NUEVO", S.DESASIGNACION, "Se quita al último técnico."),
    ("ASIGNADO", "EN_PROGRESO", S.INICIAR, "Se inicia el trabajo."),
    ("ASIGNADO", "RESUELTO", S.RESOLVER, "Se resuelve."),
    ("ASIGNADO", "CERRADO", S.CIERRE_DIRECTO, "Cierre directo."),
    ("EN_PROGRESO", "EN_ESPERA", S.PONER_EN_ESPERA, "Depende de un tercero."),
    ("EN_PROGRESO", "RESUELTO", S.RESOLVER, "Se resuelve."),
    ("EN_PROGRESO", "CERRADO", S.CIERRE_DIRECTO, "Cierre directo."),
    ("EN_ESPERA", "EN_PROGRESO", S.REACTIVAR, "Se retoma el trabajo."),
    ("EN_ESPERA", "RESUELTO", S.RESOLVER, "Se resuelve desde la espera."),
    ("EN_ESPERA", "CERRADO", S.CIERRE_DIRECTO, "Cierre directo."),
    ("RESUELTO", "CERRADO", S.CONFIRMAR, "El solicitante confirma."),
    ("RESUELTO", "CERRADO", S.AUTO_CIERRE, "Cierre automático del sistema."),
    ("RESUELTO", "CERRADO", S.CIERRE_EXCEPCIONAL, "Cierre excepcional."),
    ("RESUELTO", "EN_PROGRESO", S.RECHAZAR, "El solicitante rechaza."),
    ("RESUELTO", "EN_PROGRESO", S.REABRIR, "Reapertura desde Resuelto."),
    ("CERRADO", "EN_PROGRESO", S.REABRIR, "Reapertura desde Cerrado."),
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


def _seed_transitions() -> int:
    """Inserta las transiciones que faltan; devuelve cuántas creó.

    Cada una se identifica por (origen, destino, acción). Si ya existe no se
    toca, así que no se pisa una transición que el Administrador haya
    deshabilitado.
    """
    # Los estados se acaban de añadir a la sesión: hay que volcarlos para
    # poder consultar sus ids.
    db.session.flush()

    state_ids = {
        code: state_id
        for code, state_id in db.session.execute(
            db.select(Estado.codigo, Estado.id)
        )
    }
    existing = set(
        db.session.execute(
            db.select(
                TransicionEstado.estado_origen_id,
                TransicionEstado.estado_destino_id,
                TransicionEstado.accion,
            )
        ).all()
    )
    created = 0

    for origin, destination, action, description in INITIAL_TRANSITIONS:
        key = (state_ids[origin], state_ids[destination], action.value)

        if key in existing:
            continue

        db.session.add(
            TransicionEstado(
                estado_origen_id=key[0],
                estado_destino_id=key[1],
                accion=key[2],
                descripcion=description,
            )
        )
        created += 1

    return created


def seed_catalogs() -> dict[str, int]:
    """Carga estados, sus transiciones, prioridades, categoría de respaldo,
    motivos de cierre, motivos de espera y tipos de relación entre tickets.

    Devuelve cuántos registros creó de cada catálogo. Confirma una sola vez
    al final: o se cargan todos o ninguno.
    """
    created = {
        "estados": _seed_by_code(Estado, INITIAL_STATES),
        "transiciones": _seed_transitions(),
        "prioridades": _seed_by_code(Prioridad, INITIAL_PRIORITIES),
        "categorias": _seed_by_code(Categoria, INITIAL_CATEGORIES),
        "motivos_cierre": _seed_by_code(MotivoCierre, INITIAL_CLOSE_REASONS),
        "motivos_espera": _seed_by_code(MotivoEspera, INITIAL_WAIT_REASONS),
        "tipos_relacion": _seed_by_code(TipoRelacionTicket, INITIAL_RELATION_TYPES),
    }

    db.session.commit()

    return created
