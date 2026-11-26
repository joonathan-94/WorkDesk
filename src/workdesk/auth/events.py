"""Registrar los eventos de autenticación y aplicar el límite de intentos por equipo.

Nada de aquí hace commit: el evento se confirma junto con lo que lo provoca (el contador de
fallos, el bloqueo, el cierre de la sesión), así que nunca queda uno sin el otro.

**El límite por equipo (IP).** El bloqueo por cuenta (RNF-015) no frena a quien prueba
pocas contraseñas en muchas cuentas: cuatro intentos en cada una de cien cuentas no
bloquean ninguna. Por eso, si desde una misma IP ya hubo `LOGIN_MAX_FAILED_PER_IP` intentos
fallidos dentro del tiempo de bloqueo, en cualquier cuenta, los siguientes se rechazan sin
mirar la cuenta ni la contraseña. Los intentos simultáneos desde una IP se cuentan de uno en
uno (un bloqueo consultivo por IP), como los de una cuenta.
"""

from sqlalchemy import func, select

from .. import settings
from ..audit.service import request_ip, request_user_agent
from ..configuration import value_of
from ..extensions import db
from ..models import User
from ..models.admin_audit_log import AuditResult
from ..models.auth_event import (
    FAILED_EVENTS,
    MAX_IDENTIFIER_LENGTH,
    AuthEvent,
    AuthEventType,
    AuthFailure,
)
from ..users.rules import normalize_username, username_problem

# Prefijo de la clave del bloqueo consultivo por IP: separa este uso de los demás.
_IP_LOCK_PREFIX = "workdesk:login-ip:"

RECENT_ACCESS_LIMIT = 10


def record_auth_event(
    event_type: AuthEventType,
    *,
    user: User | None = None,
    attempted: str | None = None,
    failure: AuthFailure | None = None,
) -> AuthEvent:
    """Añade un evento a la sesión (sin commit).

    `attempted` es lo que se escribió como usuario: solo se guarda si no corresponde a
    ninguna cuenta y tiene forma de username (podría ser una contraseña escrita en el
    campo equivocado). Un rechazo debe decir por qué (`failure`) y un éxito, no.
    """
    event_type = AuthEventType(event_type)
    failed = event_type in FAILED_EVENTS

    if failed != (failure is not None):
        raise ValueError("Un evento fallido lleva su causa y uno correcto, no.")

    entry = AuthEvent(
        usuario_id=None if user is None else user.id,
        identificador_intentado=_safe_identifier(attempted) if user is None else None,
        tipo_evento=event_type.value,
        resultado=(AuditResult.FALLIDO if failed else AuditResult.EXITOSO).value,
        ip_origen=request_ip(),
        user_agent=request_user_agent(),
        detalle=None if failure is None else AuthFailure(failure).value,
    )
    db.session.add(entry)

    return entry


def _safe_identifier(attempted: str | None) -> str | None:
    if not attempted:
        return None

    identifier = normalize_username(attempted)

    if username_problem(identifier) is not None:
        return None

    return identifier[:MAX_IDENTIFIER_LENGTH]


def ip_is_throttled() -> bool:
    """Si la IP de la petición ya agotó sus intentos fallidos recientes.

    Toma un bloqueo consultivo de la IP hasta el fin de la transacción, para que dos
    intentos simultáneos no lean a la vez el mismo recuento. Sin IP o con el límite en 0,
    nunca limita.
    """
    limit = value_of(settings.LOGIN_MAX_FAILED_PER_IP)
    ip = request_ip()

    if limit == 0 or ip is None:
        return False

    db.session.execute(select(func.pg_advisory_xact_lock(func.hashtext(_IP_LOCK_PREFIX + ip))))

    window = func.make_interval(0, 0, 0, 0, 0, value_of(settings.LOGIN_LOCK_MINUTES))
    recent_failures = db.session.scalar(
        select(func.count(AuthEvent.id)).where(
            AuthEvent.ip_origen == ip,
            AuthEvent.tipo_evento == AuthEventType.LOGIN_FALLIDO.value,
            AuthEvent.fecha_hora >= func.now() - window,
        )
    )

    return recent_failures >= limit


def recent_access(user: User, limit: int = RECENT_ACCESS_LIMIT) -> list[AuthEvent]:
    """Los últimos eventos de acceso de una cuenta, del más reciente al más antiguo
    (para que la persona vea en «Mi cuenta» si alguien intentó entrar)."""
    return list(
        db.session.scalars(
            select(AuthEvent)
            .where(AuthEvent.usuario_id == user.id)
            .order_by(AuthEvent.fecha_hora.desc(), AuthEvent.id.desc())
            .limit(limit)
        )
    )
