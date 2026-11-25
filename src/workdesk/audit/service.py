from enum import StrEnum

from flask import has_request_context, request

from ..extensions import db
from ..models import User
from ..models.admin_audit_log import ActorType, AdminAuditLog, AuditResult

MAX_IP_LENGTH = 45
MAX_USER_AGENT_LENGTH = 255

# Fragmentos que delatan datos sensibles en el nombre de una clave.
SENSITIVE_KEY_FRAGMENTS = (
    "password",
    "contrasena",
    "contraseña",
    "hash",
    "secret",
    "csrf",
    "cookie",
    "token",
)

# Es un contador de versión, no un secreto: sí puede auditarse.
ALLOWED_SENSITIVE_KEYS = frozenset({"token_version"})


class AuditAction(StrEnum):
    """Vocabulario controlado de acciones administrativas auditables."""

    USUARIO_CREADO = "USUARIO_CREADO"
    USUARIO_MODIFICADO = "USUARIO_MODIFICADO"
    USUARIO_ACTIVADO = "USUARIO_ACTIVADO"
    USUARIO_DESACTIVADO = "USUARIO_DESACTIVADO"
    CAMBIO_ROL = "CAMBIO_ROL"
    PASSWORD_RESTABLECIDA = "PASSWORD_RESTABLECIDA"
    PASSWORD_CAMBIADA = "PASSWORD_CAMBIADA"

    # Catálogos de tickets (categorías, prioridades, ubicaciones y motivos de
    # espera). El tipo concreto va en `entidad_tipo`: "categoria", "prioridad",
    # "ubicacion" o "motivo_espera".
    CATALOGO_CREADO = "CATALOGO_CREADO"
    CATALOGO_MODIFICADO = "CATALOGO_MODIFICADO"
    CATALOGO_ACTIVADO = "CATALOGO_ACTIVADO"
    CATALOGO_DESACTIVADO = "CATALOGO_DESACTIVADO"

    # Grupos de atención y sus miembros y supervisores (`entidad_tipo` es
    # "grupo"; `entidad_id`, el grupo).
    GRUPO_CREADO = "GRUPO_CREADO"
    GRUPO_MODIFICADO = "GRUPO_MODIFICADO"
    GRUPO_ACTIVADO = "GRUPO_ACTIVADO"
    GRUPO_DESACTIVADO = "GRUPO_DESACTIVADO"
    GRUPO_MIEMBRO_AGREGADO = "GRUPO_MIEMBRO_AGREGADO"
    GRUPO_MIEMBRO_RETIRADO = "GRUPO_MIEMBRO_RETIRADO"
    GRUPO_SUPERVISOR_DESIGNADO = "GRUPO_SUPERVISOR_DESIGNADO"
    GRUPO_SUPERVISOR_RETIRADO = "GRUPO_SUPERVISOR_RETIRADO"

    # Estados y transiciones del flujo de tickets. Los estados no se crean ni se
    # eliminan (`entidad_tipo` "estado"; `entidad_id`, el estado) y las
    # transiciones solo se habilitan o deshabilitan (`entidad_tipo` "transicion").
    ESTADO_MODIFICADO = "ESTADO_MODIFICADO"
    TRANSICION_ACTIVADA = "TRANSICION_ACTIVADA"
    TRANSICION_DESACTIVADA = "TRANSICION_DESACTIVADA"

    # Calendario laboral: cada guardado crea una versión nueva (`entidad_tipo`
    # es "calendario_laboral"; `entidad_id`, la versión creada).
    CALENDARIO_LABORAL_GUARDADO = "CALENDARIO_LABORAL_GUARDADO"

    # Políticas de SLA por prioridad (`entidad_tipo` es "politica_sla";
    # `entidad_id`, la política). Se crean al definir los objetivos de una
    # prioridad y después solo se editan, se desactivan y se reactivan.
    POLITICA_SLA_CREADA = "POLITICA_SLA_CREADA"
    POLITICA_SLA_MODIFICADA = "POLITICA_SLA_MODIFICADA"
    POLITICA_SLA_ACTIVADA = "POLITICA_SLA_ACTIVADA"
    POLITICA_SLA_DESACTIVADA = "POLITICA_SLA_DESACTIVADA"

    # Parámetros administrables (`entidad_tipo` es "configuracion"; `entidad_id`, la fila
    # de la tabla; `detalle`, la clave del parámetro). Un cambio guarda un valor propio y
    # restablecer lo borra para que vuelva a regir el valor inicial.
    CONFIGURACION_MODIFICADA = "CONFIGURACION_MODIFICADA"
    CONFIGURACION_RESTABLECIDA = "CONFIGURACION_RESTABLECIDA"

    # Reasignación masiva de los tickets de un técnico a otros (`entidad_tipo` es
    # "tecnico"; `entidad_id`, el técnico de origen). Una sola entrada por operación,
    # con los tickets movidos y omitidos; el rastro de cada ticket va en su historial.
    REASIGNACION_MASIVA = "REASIGNACION_MASIVA"


def record_admin_event(
    action: AuditAction,
    *,
    actor: User | None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    detail: str | None = None,
    old_value: dict | None = None,
    new_value: dict | None = None,
    reason: str | None = None,
    result: AuditResult = AuditResult.EXITOSO,
) -> AdminAuditLog:
    """Añade un evento de auditoría a la sesión actual.

    No hace commit: el evento forma parte de la misma transacción que la
    operación auditada, de modo que ambos se confirman o se revierten
    juntos. Quien llama es responsable del commit.

    `actor=None` identifica una acción del sistema.
    """
    action = AuditAction(action)
    result = AuditResult(result)

    if entity_id is not None and entity_type is None:
        raise ValueError("entity_id requiere entity_type.")

    _ensure_no_sensitive_data(old_value)
    _ensure_no_sensitive_data(new_value)

    entry = AdminAuditLog(
        actor_usuario_id=None if actor is None else actor.id,
        actor_tipo=(
            ActorType.SISTEMA if actor is None else ActorType.USUARIO
        ).value,
        accion=action.value,
        entidad_tipo=entity_type,
        entidad_id=entity_id,
        detalle=detail,
        valor_anterior=old_value,
        valor_nuevo=new_value,
        ip_origen=_request_ip(),
        user_agent=_request_user_agent(),
        resultado=result.value,
        motivo=reason,
    )

    db.session.add(entry)
    db.session.flush()

    return entry


def _ensure_no_sensitive_data(value) -> None:
    """Rechaza cualquier clave que pueda contener contraseñas o secretos."""
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).lower()

            if normalized not in ALLOWED_SENSITIVE_KEYS and any(
                fragment in normalized
                for fragment in SENSITIVE_KEY_FRAGMENTS
            ):
                raise ValueError(
                    f"La clave '{key}' no puede registrarse en la "
                    "auditoría: podría contener datos sensibles."
                )

            _ensure_no_sensitive_data(nested)

    elif isinstance(value, (list, tuple)):
        for item in value:
            _ensure_no_sensitive_data(item)


def _request_ip() -> str | None:
    if not has_request_context() or not request.remote_addr:
        return None

    return request.remote_addr[:MAX_IP_LENGTH]


def _request_user_agent() -> str | None:
    if not has_request_context():
        return None

    user_agent = request.user_agent.string

    if not user_agent:
        return None

    return user_agent[:MAX_USER_AGENT_LENGTH]
