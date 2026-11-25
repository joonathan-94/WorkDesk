"""Parámetros administrables: dónde se lee su valor vigente y cómo se cambia (docs/09, 26.1).

El valor vigente de cada parámetro de `settings.py` es, por orden:

1. el que el Administrador guardó en la tabla `configuracion`, si lo hay;
2. el valor inicial: la variable de entorno o, si no está definida, el valor por defecto
   (`app.config`, que se llena al iniciar la aplicación).

**Lectura.** Todo el código lee con `value_of(settings.X)` y nunca con
`current_app.config[...]` (un test lo vigila). La primera lectura de una petición trae toda la
tabla en **una consulta** (son unas pocas filas) y la guarda en `g`; las demás lecturas de la
misma petición no cuestan nada. No hay caché entre peticiones, a propósito: el planificador
(`run-scheduler`) es otro proceso y una caché dentro del servidor web no vería un cambio del
Administrador, ni al revés. Los procesos que viven más que una petición (el planificador)
llaman a `forget_cached_settings()` al empezar cada pasada.

**Escritura.** `save_setting` y `reset_setting` no hacen commit (se confirman con la
operación que los llama), exigen ser Administrador, validan con las mismas reglas que
`validate_settings` (también las que relacionan dos parámetros) y auditan el cambio.
Se serializan con un bloqueo de PostgreSQL: dos Administradores que cambian a la vez el
latido y la duración del bloqueo de edición podrían, cada uno por su lado, dejar una
combinación inválida que ninguna de las dos validaciones vería.
"""

import json
import logging

from flask import current_app, g
from sqlalchemy import func, select

from .audit import AuditAction, record_admin_event
from .extensions import db
from .models import ConfigDataType, Configuracion
from .settings import ALL_SETTINGS, BoolSetting, Setting, settings_problems

logger = logging.getLogger(__name__)

MAX_REASON_LENGTH = 500

# Identificador del bloqueo consultivo de PostgreSQL que serializa los cambios. Un número
# cualquiera pero fijo: solo importa que ningún otro código use el mismo.
_CHANGE_LOCK_ID = 20260701

_CACHE_ATTRIBUTE = "_workdesk_stored_settings"


class SettingRuleError(ValueError):
    """El cambio de configuración no es válido; el mensaje se muestra tal cual."""


class SettingConflictError(SettingRuleError):
    """Otra persona cambió estos valores mientras la pantalla estaba abierta."""

    def __init__(self) -> None:
        super().__init__(
            "Otra persona cambió esta configuración mientras la editabas. Revisa los "
            "valores actuales y vuelve a guardar."
        )


def forget_cached_settings() -> None:
    """Descarta lo leído en esta petición, para que la próxima lectura vaya a la base."""
    g.pop(_CACHE_ATTRIBUTE, None)


def _stored_values() -> dict[str, str]:
    cached = g.get(_CACHE_ATTRIBUTE)

    if cached is None:
        rows = db.session.execute(select(Configuracion.clave, Configuracion.valor))
        cached = {key: value for key, value in rows}
        setattr(g, _CACHE_ATTRIBUTE, cached)

    return cached


def _parse(setting: Setting, raw: str):
    """El valor guardado ya convertido y válido, o `None` (con un aviso) si no lo es.

    Un valor corrupto (alguien tocó la tabla a mano, o una versión futura cambió el rango)
    no debe tumbar cada pantalla: se ignora y rige el valor inicial.
    """
    if isinstance(setting, BoolSetting):
        value = {"true": True, "false": False}.get(raw)
        problem = "no es true ni false" if value is None else None
    else:
        try:
            value = int(raw)
        except ValueError:
            value = None

        problem = "no es un entero" if value is None else setting.problem(value)

    if problem:
        logger.warning(
            "El valor guardado de «%s» no es válido (%s); se usa el inicial.",
            setting.table_key,
            problem,
        )
        return None

    return value


def _serialize(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"

    return str(value)


def initial_value(setting: Setting):
    """El valor que rige cuando el Administrador no eligió uno propio."""
    return current_app.config[setting.key]


def value_of(setting: Setting):
    """El valor vigente de `setting` (un entero o un booleano según su tipo; ver el módulo)."""
    raw = _stored_values().get(setting.table_key)

    if raw is not None and (value := _parse(setting, raw)) is not None:
        return value

    return initial_value(setting)


def effective_values() -> dict:
    """Todos los valores vigentes, por nombre de variable de entorno."""
    return {setting.key: value_of(setting) for setting in ALL_SETTINGS}


def has_own_value(setting: Setting) -> bool:
    """Si el Administrador eligió un valor propio (y no rige el inicial)."""
    return setting.table_key in _stored_values()


def stored_text(table_key: str) -> str | None:
    """El texto guardado para una clave, o `None` si no hay fila."""
    return _stored_values().get(table_key)


def document_token(table_key: str) -> str:
    """Como `state_token`, para una clave que guarda un documento (no un parámetro)."""
    return f"{table_key}={_stored_values().get(table_key, '-')}"


def state_token(group) -> str:
    """Una huella de lo guardado para los parámetros de `group`.

    Una pantalla la envía al guardar: si ya no coincide, otra persona cambió alguno
    mientras se editaba y no se guarda nada.
    """
    stored = _stored_values()

    return ";".join(
        f"{setting.table_key}={stored.get(setting.table_key, '-')}" for setting in group
    )


# --- Cambios ------------------------------------------------------------------------------


def _clean_reason(reason: str | None) -> str | None:
    reason = (reason or "").strip()

    if len(reason) > MAX_REASON_LENGTH:
        raise SettingRuleError(f"El motivo no puede superar los {MAX_REASON_LENGTH} caracteres.")

    return reason or None


def _begin_change(actor) -> None:
    """Comprueba el permiso y toma el bloqueo que serializa los cambios."""
    # Importado aquí y no arriba: `security.authorization` lee la configuración y este
    # módulo importaría de vuelta al cargarse.
    from .security import can_manage_settings

    if not can_manage_settings(actor):
        raise PermissionError("Solo un Administrador puede cambiar la configuración.")

    # Se libera solo al terminar la transacción. Se descarta lo leído antes: otro
    # Administrador pudo confirmar un cambio mientras esperábamos el bloqueo.
    db.session.execute(select(func.pg_advisory_xact_lock(_CHANGE_LOCK_ID)))
    forget_cached_settings()


def _check_valid(changes: dict) -> None:
    candidate = effective_values()
    candidate.update({setting.key: value for setting, value in changes.items()})

    if problems := settings_problems(candidate):
        raise SettingRuleError(" ".join(problems))


def _row_of(setting: Setting) -> Configuracion | None:
    return db.session.scalar(
        select(Configuracion).where(Configuracion.clave == setting.table_key)
    )


def _write(setting: Setting, value, previous, *, actor, reason) -> None:
    row = _row_of(setting)
    kind = ConfigDataType.BOOLEANO if isinstance(setting, BoolSetting) else ConfigDataType.ENTERO

    if row is None:
        row = Configuracion(
            clave=setting.table_key,
            valor=_serialize(value),
            tipo_dato=kind.value,
            categoria=setting.table_key.partition(".")[0],
            usuario_modificacion_id=actor.id,
        )
        db.session.add(row)
    else:
        row.valor = _serialize(value)
        row.tipo_dato = kind.value
        row.fecha_modificacion = func.now()
        row.usuario_modificacion_id = actor.id

    db.session.flush()

    record_admin_event(
        AuditAction.CONFIGURACION_MODIFICADA,
        actor=actor,
        entity_type="configuracion",
        entity_id=row.id,
        detail=setting.table_key,
        old_value={"valor": previous},
        new_value={"valor": value},
        reason=reason,
    )


def save_settings(
    changes: dict,
    *,
    actor,
    reason: str | None = None,
    base_token: str | None = None,
    group=(),
) -> list:
    """Guarda varios valores propios a la vez y devuelve los parámetros que cambiaron.

    Se validan **juntos**, así que dos parámetros relacionados (la duración y el latido del
    bloqueo) pueden cambiarse a la vez en cualquier combinación válida. Los que ya tenían ese
    valor no se escriben ni se auditan. Con `base_token` (ver `state_token`, calculada sobre
    `group`) se rechaza con `SettingConflictError` si alguno de esos parámetros cambió desde
    entonces.

    Lanza `PermissionError` si `actor` no es Administrador y `SettingRuleError` si algo no es
    válido. No hace commit.
    """
    reason = _clean_reason(reason)
    _begin_change(actor)

    if base_token is not None and base_token != state_token(group):
        raise SettingConflictError()

    _check_valid(changes)

    previous = {setting: value_of(setting) for setting in changes}
    pending = {
        setting: value for setting, value in changes.items() if value != previous[setting]
    }

    for setting, value in pending.items():
        _write(setting, value, previous[setting], actor=actor, reason=reason)

    forget_cached_settings()

    return list(pending)


def save_setting(setting: Setting, value, *, actor, reason: str | None = None) -> bool:
    """Como `save_settings` para un solo parámetro. `False` si ya era el vigente."""
    return bool(save_settings({setting: value}, actor=actor, reason=reason))


def reset_setting(setting: Setting, *, actor, reason: str | None = None) -> bool:
    """Borra el valor propio de `setting` para que vuelva a regir el inicial.

    Devuelve `False` si no tenía valor propio. Lanza lo mismo que `save_settings`; volver al
    inicial también se valida, porque puede dejar dos parámetros incompatibles entre sí.
    """
    reason = _clean_reason(reason)
    _begin_change(actor)

    row = _row_of(setting)

    if row is None:
        return False

    initial = initial_value(setting)
    _check_valid({setting: initial})

    previous = value_of(setting)
    row_id = row.id

    db.session.delete(row)
    db.session.flush()

    record_admin_event(
        AuditAction.CONFIGURACION_RESTABLECIDA,
        actor=actor,
        entity_type="configuracion",
        entity_id=row_id,
        detail=setting.table_key,
        old_value={"valor": previous},
        new_value={"valor": initial},
        reason=reason,
    )
    forget_cached_settings()

    return True


def save_document(
    table_key: str,
    value,
    *,
    initial,
    current,
    actor,
    reason: str | None = None,
    base_token: str | None = None,
) -> bool:
    """Guarda como JSON un documento que no es un parámetro de `settings.py`.

    `current` devuelve el valor vigente ya interpretado (se llama con el bloqueo tomado) e
    `initial` es el que rige sin fila: guardar el inicial borra la fila. Mismas garantías que
    `save_settings`: solo el Administrador, serializado, con auditoría, detección de
    conflictos (`base_token`, ver `document_token`) y sin escribir si nada cambió. No hace
    commit.
    """
    reason = _clean_reason(reason)
    _begin_change(actor)

    if base_token is not None and base_token != document_token(table_key):
        raise SettingConflictError()

    previous = current()

    if value == previous:
        return False

    row = db.session.scalar(select(Configuracion).where(Configuracion.clave == table_key))
    action = AuditAction.CONFIGURACION_MODIFICADA

    if value == initial and row is not None:
        row_id = row.id
        db.session.delete(row)
        db.session.flush()
        action = AuditAction.CONFIGURACION_RESTABLECIDA
    else:
        if row is None:
            row = Configuracion(
                clave=table_key,
                tipo_dato=ConfigDataType.JSON.value,
                categoria=table_key.partition(".")[0],
            )
            db.session.add(row)

        row.valor = json.dumps(value, ensure_ascii=False)
        row.fecha_modificacion = func.now()
        row.usuario_modificacion_id = actor.id
        db.session.flush()
        row_id = row.id

    record_admin_event(
        action,
        actor=actor,
        entity_type="configuracion",
        entity_id=row_id,
        detail=table_key,
        old_value={"valor": previous},
        new_value={"valor": value},
        reason=reason,
    )
    forget_cached_settings()

    return True

