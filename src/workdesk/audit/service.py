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

    # Catálogos de tickets (categorías, prioridades y ubicaciones). El tipo
    # concreto va en `entidad_tipo`: "categoria", "prioridad" o "ubicacion".
    CATALOGO_CREADO = "CATALOGO_CREADO"
    CATALOGO_MODIFICADO = "CATALOGO_MODIFICADO"
    CATALOGO_ACTIVADO = "CATALOGO_ACTIVADO"
    CATALOGO_DESACTIVADO = "CATALOGO_DESACTIVADO"


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
