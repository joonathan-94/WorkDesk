"""Reglas de la administración de catálogos de tickets.

Cubre categorías, prioridades y ubicaciones (docs/06, RN-152). Las tres
comparten las operaciones de crear, editar, desactivar y reactivar; lo que
cambia de uno a otro son sus campos y algunas protecciones.

Ninguna función hace commit: el cambio y su evento de auditoría se
confirman o se revierten juntos, y el commit lo realiza quien llama.
"""

from sqlalchemy.exc import IntegrityError

from ..audit import AuditAction, record_admin_event
from ..extensions import db
from ..models import Categoria, Prioridad, Ubicacion, User
from ..models.categoria import FALLBACK_CATEGORY_CODE
from ..models.ubicacion import LocationType

STATUS_ACTIVE = "activo"
STATUS_INACTIVE = "inactivo"
VALID_STATUSES = frozenset({STATUS_ACTIVE, STATUS_INACTIVE})

# Valor de `entidad_tipo` en la auditoría para cada catálogo.
ENTITY_TYPES = {
    Categoria: "categoria",
    Prioridad: "prioridad",
    Ubicacion: "ubicacion",
}

_DUPLICATE_MESSAGE = "Ya existe un registro con ese nombre."


class CatalogRuleError(ValueError):
    """Una regla de los catálogos impide la operación.

    El mensaje está pensado para mostrarse al usuario.
    """


class DuplicateNameError(CatalogRuleError):
    """Ya existe otro registro del mismo catálogo con ese nombre."""


class ProtectedItemError(CatalogRuleError):
    """El registro es imprescindible y no puede desactivarse."""


class LastActivePriorityError(CatalogRuleError):
    """Desactivar la prioridad dejaría al sistema sin ninguna activa."""


class ActivationConflictError(CatalogRuleError):
    """Reactivar el registro choca con otro que ya está activo."""


class NothingToChangeError(CatalogRuleError):
    """La operación no cambiaría nada."""


# --- Consultas --------------------------------------------------------


def list_categories(status: str = "") -> list[Categoria]:
    """Categorías por orden manual (las sin orden al final) y nombre."""
    return _list(
        Categoria,
        status,
        Categoria.orden.asc().nulls_last(),
        db.func.lower(Categoria.nombre),
    )


def list_priorities(status: str = "") -> list[Prioridad]:
    """Prioridades de menor a mayor nivel."""
    return _list(Prioridad, status, Prioridad.nivel)


def list_locations(status: str = "") -> list[Ubicacion]:
    return _list(Ubicacion, status, db.func.lower(Ubicacion.nombre))


def get_item(model, item_id: int):
    return db.session.get(model, item_id)


# --- Alta y edición ---------------------------------------------------


def create_category(
    *,
    actor: User,
    nombre: str,
    descripcion: str | None = None,
    orden: int | None = None,
) -> Categoria:
    """Crea una categoría activa. No lleva código: ese valor es solo de las
    categorías del seed. Lanza `DuplicateNameError` si el nombre ya existe.
    """
    return _create_item(
        Categoria,
        actor,
        {
            "nombre": _clean_name(nombre),
            "descripcion": _blank_to_none(descripcion),
            "orden": orden,
        },
    )


def update_category(
    category: Categoria,
    *,
    actor: User,
    nombre: str,
    descripcion: str | None,
    orden: int | None,
) -> bool:
    """Edita la categoría. Devuelve False, sin auditar, si nada cambió."""
    return _update_item(
        category,
        actor,
        {
            "nombre": _clean_name(nombre),
            "descripcion": _blank_to_none(descripcion),
            "orden": orden,
        },
    )


def update_priority(
    priority: Prioridad,
    *,
    actor: User,
    nombre: str,
    descripcion: str | None,
) -> bool:
    """Edita nombre y descripción de la prioridad.

    No se crean prioridades nuevas y su nivel y color son fijos: son
    exactamente cuatro y su semántica visual la define el Design System
    (docs/11, UI-019).
    """
    return _update_item(
        priority,
        actor,
        {
            "nombre": _clean_name(nombre),
            "descripcion": _blank_to_none(descripcion),
        },
    )


def create_location(
    *,
    actor: User,
    nombre: str,
    descripcion: str | None = None,
    tipo: str | None = None,
) -> Ubicacion:
    """Crea una ubicación activa. El tipo es opcional pero, si se indica,
    debe ser uno de `LocationType`.
    """
    return _create_item(
        Ubicacion,
        actor,
        {
            "nombre": _clean_name(nombre),
            "descripcion": _blank_to_none(descripcion),
            "tipo": _normalize_location_type(tipo),
        },
    )


def update_location(
    location: Ubicacion,
    *,
    actor: User,
    nombre: str,
    descripcion: str | None,
    tipo: str | None,
) -> bool:
    return _update_item(
        location,
        actor,
        {
            "nombre": _clean_name(nombre),
            "descripcion": _blank_to_none(descripcion),
            "tipo": _normalize_location_type(tipo),
        },
    )


# --- Activación y desactivación ---------------------------------------


def deactivation_blocker(item, *, lock: bool = False) -> str | None:
    """Devuelve por qué el registro no puede desactivarse, o None si puede.

    - La categoría de respaldo (`SIN_CLASIFICAR`) nunca se desactiva: todo
      ticket necesita una categoría válida (docs/06, RN-16).
    - Siempre debe quedar al menos una prioridad activa: sin ninguna no se
      podrían crear tickets.

    Con `lock=True` se bloquean las prioridades activas (`FOR UPDATE`): si
    dos Administradores desactivan a la vez las dos últimas, el segundo
    espera, vuelve a contar y ve el resultado ya confirmado del primero.
    """
    if isinstance(item, Categoria) and item.codigo == FALLBACK_CATEGORY_CODE:
        return (
            "Esta es la categoría de respaldo para tickets sin clasificar: "
            "no se puede desactivar."
        )

    if isinstance(item, Prioridad) and item.activo:
        statement = db.select(Prioridad.id).where(Prioridad.activo.is_(True))

        if lock:
            statement = statement.with_for_update()

        active_ids = db.session.scalars(statement).all()

        if not any(priority_id != item.id for priority_id in active_ids):
            return "Debe quedar al menos una prioridad activa."

    return None


def deactivate_item(item, *, actor: User, reason: str | None = None) -> None:
    """Desactiva el registro: deja de poder elegirse en tickets nuevos.

    Los tickets que ya lo usan no se tocan. Audita `CATALOGO_DESACTIVADO`.
    """
    if not item.activo:
        raise NothingToChangeError("Este elemento ya está desactivado.")

    blocker = deactivation_blocker(item, lock=True)

    if blocker is not None:
        if isinstance(item, Prioridad):
            raise LastActivePriorityError(blocker)

        raise ProtectedItemError(blocker)

    item.activo = False
    item.mark_modified(actor)

    record_admin_event(
        AuditAction.CATALOGO_DESACTIVADO,
        actor=actor,
        entity_type=ENTITY_TYPES[type(item)],
        entity_id=item.id,
        detail=item.nombre,
        old_value={"activo": True},
        new_value={"activo": False},
        reason=_blank_to_none(reason),
    )


def activate_item(item, *, actor: User, reason: str | None = None) -> None:
    """Reactiva el registro. Audita `CATALOGO_ACTIVADO`.

    Una prioridad solo puede reactivarse si ninguna otra prioridad activa
    tiene su mismo nivel (lo garantiza un índice único parcial).
    """
    if item.activo:
        raise NothingToChangeError("Este elemento ya está activo.")

    try:
        with db.session.begin_nested():
            item.activo = True
            item.mark_modified(actor)
            db.session.flush()
    except IntegrityError as error:
        raise ActivationConflictError(
            "No se puede reactivar: ya hay otra prioridad activa con el "
            "mismo nivel."
        ) from error

    record_admin_event(
        AuditAction.CATALOGO_ACTIVADO,
        actor=actor,
        entity_type=ENTITY_TYPES[type(item)],
        entity_id=item.id,
        detail=item.nombre,
        old_value={"activo": False},
        new_value={"activo": True},
        reason=_blank_to_none(reason),
    )


# --- Piezas comunes ---------------------------------------------------


def _create_item(model, actor: User, values: dict):
    _ensure_name_available(model, values["nombre"])

    item = model(**values, usuario_creacion_id=actor.id)

    # Dos altas simultáneas pueden pasar la comprobación anterior y chocar
    # en el índice único del nombre. El savepoint deshace solo este intento
    # y deja intacta el resto de la transacción.
    try:
        with db.session.begin_nested():
            db.session.add(item)
            db.session.flush()
    except IntegrityError as error:
        raise DuplicateNameError(_DUPLICATE_MESSAGE) from error

    record_admin_event(
        AuditAction.CATALOGO_CREADO,
        actor=actor,
        entity_type=ENTITY_TYPES[model],
        entity_id=item.id,
        detail=item.nombre,
        new_value={**values, "activo": True},
    )

    return item


def _update_item(item, actor: User, new_values: dict) -> bool:
    """Aplica solo los campos que cambiaron y audita los valores anterior y
    nuevo de esos campos. Devuelve False si no cambió nada.
    """
    changed = {
        field: value
        for field, value in new_values.items()
        if getattr(item, field) != value
    }

    if not changed:
        return False

    if "nombre" in changed:
        _ensure_name_available(
            type(item),
            changed["nombre"],
            exclude_id=item.id,
        )

    old_values = {field: getattr(item, field) for field in changed}

    try:
        with db.session.begin_nested():
            for field, value in changed.items():
                setattr(item, field, value)

            item.mark_modified(actor)
            db.session.flush()
    except IntegrityError as error:
        raise DuplicateNameError(_DUPLICATE_MESSAGE) from error

    record_admin_event(
        AuditAction.CATALOGO_MODIFICADO,
        actor=actor,
        entity_type=ENTITY_TYPES[type(item)],
        entity_id=item.id,
        detail=item.nombre,
        old_value=old_values,
        new_value=changed,
    )

    return True


def _clean_name(nombre: str) -> str:
    nombre = nombre.strip()

    if not nombre:
        raise CatalogRuleError("El nombre es obligatorio.")

    return nombre


def _ensure_name_available(model, nombre: str, *, exclude_id=None) -> None:
    # `lower` se aplica en la base de datos a ambos lados, igual que en el
    # índice único, para que las dos comprobaciones coincidan siempre.
    statement = db.select(model.id).where(
        db.func.lower(model.nombre) == db.func.lower(nombre)
    )

    if exclude_id is not None:
        statement = statement.where(model.id != exclude_id)

    if db.session.scalar(statement.limit(1)) is not None:
        raise DuplicateNameError(_DUPLICATE_MESSAGE)


def _normalize_location_type(tipo: str | None) -> str | None:
    tipo = _blank_to_none(tipo)

    if tipo is not None and tipo not in {t.value for t in LocationType}:
        raise CatalogRuleError("Selecciona un tipo de ubicación válido.")

    return tipo


def _list(model, status: str, *order_by) -> list:
    statement = db.select(model).order_by(*order_by)

    if status == STATUS_ACTIVE:
        statement = statement.where(model.activo.is_(True))
    elif status == STATUS_INACTIVE:
        statement = statement.where(model.activo.is_(False))

    return list(db.session.scalars(statement))


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None

    value = value.strip()

    return value or None
