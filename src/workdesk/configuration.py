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

import logging

from flask import current_app, g
from sqlalchemy import func, select

from .audit import AuditAction, record_admin_event
from .extensions import db
from .models import ConfigDataType, Configuracion
from .settings import INT_SETTINGS, IntSetting, settings_problems

logger = logging.getLogger(__name__)

MAX_REASON_LENGTH = 500

# Identificador del bloqueo consultivo de PostgreSQL que serializa los cambios. Un número
# cualquiera pero fijo: solo importa que ningún otro código use el mismo.
_CHANGE_LOCK_ID = 20260701

_CACHE_ATTRIBUTE = "_workdesk_stored_settings"


class SettingRuleError(ValueError):
    """El cambio de configuración no es válido; el mensaje se muestra tal cual."""


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


def _parse(setting: IntSetting, raw: str) -> int | None:
    """El valor guardado como entero válido, o `None` (con un aviso) si no lo es.

    Un valor corrupto (alguien tocó la tabla a mano, o una versión futura cambió el rango)
    no debe tumbar cada pantalla: se ignora y rige el valor inicial.
    """
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


def initial_value(setting: IntSetting) -> int:
    """El valor que rige cuando el Administrador no eligió uno propio."""
    return current_app.config[setting.key]


def value_of(setting: IntSetting) -> int:
    """El valor vigente de `setting` (ver el módulo)."""
    raw = _stored_values().get(setting.table_key)

    if raw is not None and (value := _parse(setting, raw)) is not None:
        return value

    return initial_value(setting)


def effective_values() -> dict[str, int]:
    """Todos los valores vigentes, por nombre de variable de entorno."""
    return {setting.key: value_of(setting) for setting in INT_SETTINGS}


def has_own_value(setting: IntSetting) -> bool:
    """Si el Administrador eligió un valor propio (y no rige el inicial)."""
    return setting.table_key in _stored_values()


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


def _check_valid(setting: IntSetting, new_value: object) -> None:
    candidate = {**effective_values(), setting.key: new_value}

    if problems := settings_problems(candidate):
        raise SettingRuleError(" ".join(problems))


def save_setting(
    setting: IntSetting,
    value: int,
    *,
    actor,
    reason: str | None = None,
) -> bool:
    """Guarda un valor propio para `setting`. Devuelve `False` si ya era el vigente.

    Lanza `PermissionError` si `actor` no es Administrador y `SettingRuleError` si el valor
    no es válido (solo o junto a los demás parámetros). No hace commit.
    """
    reason = _clean_reason(reason)
    _begin_change(actor)
    _check_valid(setting, value)

    current = value_of(setting)

    if value == current:
        return False

    row = db.session.scalar(select(Configuracion).where(Configuracion.clave == setting.table_key))

    if row is None:
        row = Configuracion(
            clave=setting.table_key,
            valor=str(value),
            tipo_dato=ConfigDataType.ENTERO.value,
            categoria=setting.table_key.partition(".")[0],
            usuario_modificacion_id=actor.id,
        )
        db.session.add(row)
    else:
        row.valor = str(value)
        row.fecha_modificacion = func.now()
        row.usuario_modificacion_id = actor.id

    db.session.flush()

    record_admin_event(
        AuditAction.CONFIGURACION_MODIFICADA,
        actor=actor,
        entity_type="configuracion",
        entity_id=row.id,
        detail=setting.table_key,
        old_value={"valor": current},
        new_value={"valor": value},
        reason=reason,
    )
    forget_cached_settings()

    return True


def reset_setting(setting: IntSetting, *, actor, reason: str | None = None) -> bool:
    """Borra el valor propio de `setting` para que vuelva a regir el inicial.

    Devuelve `False` si no tenía valor propio. Lanza lo mismo que `save_setting`; volver al
    inicial también se valida, porque puede dejar dos parámetros incompatibles entre sí.
    """
    reason = _clean_reason(reason)
    _begin_change(actor)

    row = db.session.scalar(select(Configuracion).where(Configuracion.clave == setting.table_key))

    if row is None:
        return False

    initial = initial_value(setting)
    _check_valid(setting, initial)

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

