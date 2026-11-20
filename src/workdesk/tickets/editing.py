"""Edición de tickets ya creados (docs/06, RN-155).

Dos operaciones, ambas sobre un ticket que no esté cerrado:

- `update_ticket`: título, descripción, categoría y ubicación.
- `change_priority`: la prioridad, con motivo obligatorio.

Ninguna hace commit: el cambio y su evento de historial se confirman o se
revierten juntos, y el commit lo realiza quien llama. Quién puede editar lo
decide la capa de rutas (`can_edit_ticket`, `can_change_priority`).
"""

from ..extensions import db
from ..models import (
    Categoria,
    Prioridad,
    Ticket,
    TicketEvent,
    Ubicacion,
    User,
)
from .service import (
    CLOSED_STATE_CODE,
    MAX_REASON_LENGTH,
    TicketRuleError,
    clean_title_and_description,
    record_ticket_event,
)
from .versioning import TicketClosedError, apply_ticket_changes


def update_ticket(
    ticket: Ticket,
    *,
    actor: User,
    expected_version: int,
    title: str,
    description: str,
    category_id: int,
    location_id: int | None,
) -> bool:
    """Edita título, descripción, categoría y ubicación del ticket.

    `expected_version` es la versión del ticket que tenía quien abrió el
    formulario: si otra persona lo modificó entretanto, se lanza
    `TicketConflictError` en lugar de pisar su cambio (control optimista).

    Solo se aplica y se registra lo que cambió. Devuelve False, sin tocar
    nada, si no hay cambios. La categoría y la ubicación nuevas deben estar
    activas, pero la que el ticket ya tiene puede conservarse aunque se haya
    desactivado.

    Registra `TICKET_MODIFICADO` (título, descripción, ubicación) y
    `CATEGORIA_CAMBIADA`, cada uno con los valores anterior y nuevo.
    """
    _ensure_editable(ticket, actor)

    title, description = clean_title_and_description(title, description)
    category = _get_choice(
        Categoria,
        category_id,
        current_id=ticket.categoria_id,
        label="La categoría",
    )
    location = (
        None
        if location_id is None
        else _get_choice(
            Ubicacion,
            location_id,
            current_id=ticket.ubicacion_id,
            label="La ubicación",
        )
    )

    changes: dict = {}
    old_data: dict = {}
    new_data: dict = {}

    if title != ticket.titulo:
        changes["titulo"] = title
        old_data["titulo"] = ticket.titulo
        new_data["titulo"] = title

    if description != ticket.descripcion:
        changes["descripcion"] = description
        old_data["descripcion"] = ticket.descripcion
        new_data["descripcion"] = description

    new_location_id = None if location is None else location.id

    if new_location_id != ticket.ubicacion_id:
        changes["ubicacion_id"] = new_location_id
        old_data["ubicacion"] = (
            None if ticket.ubicacion is None else ticket.ubicacion.nombre
        )
        new_data["ubicacion"] = None if location is None else location.nombre

    old_category = ticket.categoria
    category_changed = category.id != ticket.categoria_id

    if category_changed:
        changes["categoria_id"] = category.id

    if not changes:
        return False

    apply_ticket_changes(ticket, actor, expected_version, changes)

    if new_data:
        record_ticket_event(
            ticket,
            TicketEvent.TICKET_MODIFICADO,
            actor=actor,
            detail="Datos del ticket modificados.",
            old_value=old_data,
            new_value=new_data,
        )

    if category_changed:
        record_ticket_event(
            ticket,
            TicketEvent.CATEGORIA_CAMBIADA,
            actor=actor,
            detail=(
                f"Categoría cambiada de «{old_category.nombre}» "
                f"a «{category.nombre}»."
            ),
            old_value=_category_snapshot(old_category),
            new_value=_category_snapshot(category),
        )

    return True


def change_priority(
    ticket: Ticket,
    *,
    actor: User,
    expected_version: int,
    priority_id: int,
    reason: str | None,
) -> bool:
    """Cambia la prioridad del ticket (docs/06, RN-22).

    El motivo es obligatorio y se guarda en el historial junto con la
    prioridad anterior y la nueva. Elegir la misma prioridad que ya tiene el
    ticket no genera cambio ni registro: devuelve False. La prioridad nueva
    debe estar activa.

    Registra `PRIORIDAD_CAMBIADA`, con el motivo en `contexto`.
    """
    _ensure_editable(ticket, actor)

    priority = db.session.get(Prioridad, priority_id)

    if priority is None:
        raise TicketRuleError("La prioridad seleccionada no está disponible.")

    if priority.id == ticket.prioridad_id:
        return False

    if not priority.activo:
        raise TicketRuleError("La prioridad seleccionada no está disponible.")

    reason = (reason or "").strip()

    if not reason:
        raise TicketRuleError("Indica el motivo del cambio de prioridad.")

    if len(reason) > MAX_REASON_LENGTH:
        raise TicketRuleError(
            f"El motivo no puede superar los {MAX_REASON_LENGTH} caracteres."
        )

    old_priority = ticket.prioridad

    apply_ticket_changes(ticket, actor, expected_version, {"prioridad_id": priority.id})

    record_ticket_event(
        ticket,
        TicketEvent.PRIORIDAD_CAMBIADA,
        actor=actor,
        detail=(
            f"Prioridad cambiada de «{old_priority.nombre}» "
            f"a «{priority.nombre}»."
        ),
        old_value=_priority_snapshot(old_priority),
        new_value=_priority_snapshot(priority),
        context={"motivo": reason},
    )

    return True


def _ensure_editable(ticket: Ticket, actor: User) -> None:
    if not actor.is_active:
        raise TicketRuleError("El usuario no está activo.")

    if ticket.estado.codigo == CLOSED_STATE_CODE:
        raise TicketClosedError(
            "Un ticket cerrado no se puede editar. Primero debe reabrirse."
        )


def _get_choice(model, record_id: int, *, current_id, label: str):
    """Registro de catálogo elegido para el ticket.

    Debe estar activo, salvo que sea el que el ticket ya tiene: desactivar un
    valor no obliga a cambiar los tickets que lo usan.
    """
    record = db.session.get(model, record_id)

    if record is None or (not record.activo and record.id != current_id):
        raise TicketRuleError(f"{label} seleccionada no está disponible.")

    return record


def _category_snapshot(category: Categoria) -> dict:
    return {"categoria_id": category.id, "nombre": category.nombre}


def _priority_snapshot(priority: Prioridad) -> dict:
    return {
        "prioridad_id": priority.id,
        "codigo": priority.codigo,
        "nombre": priority.nombre,
    }
