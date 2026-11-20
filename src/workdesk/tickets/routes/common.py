"""Piezas que comparten las rutas de tickets.

Lo más importante es `visible_ticket_or_404`: todas las rutas de un ticket
empiezan por ahí, así que un ticket que el usuario no puede ver responde 404
igual que uno inexistente (los números son correlativos y, con un 403,
cualquiera podría descubrir cuáles existen). La red de seguridad
`tests/test_route_authorization.py` lo comprueba sobre todas las rutas.
"""

from flask import abort, flash, redirect, url_for
from flask_login import current_user

from ...extensions import db
from ...security import can_assign_self, can_view_ticket
from ..service import CLOSED_STATE_CODE, TicketRuleError, get_ticket_by_public_id
from ..versioning import TicketClosedError, TicketConflictError


def visible_ticket_or_404(public_id: str):
    """Ticket que el usuario puede ver; 404 en cualquier otro caso.

    Un identificador que no sea un número no puede existir. Un ticket ajeno
    responde igual que uno inexistente (404): los números son correlativos y,
    con un 403, cualquiera podría descubrir cuáles existen.
    """
    if not (public_id.isascii() and public_id.isdecimal()):
        abort(404)

    ticket = get_ticket_by_public_id(public_id)

    if ticket is None or not can_view_ticket(current_user, ticket):
        abort(404)

    return ticket


def ticket_is_closed(ticket) -> bool:
    return ticket.estado.codigo == CLOSED_STATE_CODE


# Aviso de las operaciones que cuelgan del ticket (asignación, escalamiento,
# solicitantes...) cuando el ticket ya está cerrado.
CLOSED_MODIFY_MESSAGE = (
    "Un ticket cerrado no se puede modificar. Primero debe reabrirse."
)


def closed_redirect(
    ticket,
    message="Un ticket cerrado no se puede editar. Primero debe reabrirse.",
):
    flash(message, "error")

    return redirect(url_for("tickets.detail", public_id=ticket.public_id))


def choices_with_current(items, current) -> list:
    """Elementos de catálogo activos, más el que el ticket ya tiene.

    Si el valor actual se desactivó después de crear el ticket, sigue
    pudiendo conservarse (aunque no pueda elegirse en otros tickets).
    """
    items = list(items)

    if current is not None and all(item.id != current.id for item in items):
        items.append(current)

    return items


def catalog_label(item) -> str:
    """Nombre de un elemento de catálogo, marcando los desactivados."""
    name = item.nombre if hasattr(item, "nombre") else item.nombre_visible

    return name if item.activo else f"{name} (inactiva)"


def run_ticket_operation(ticket, operation, success_message, *, back, quiet=False):
    """Ejecuta una operación que cuelga del ticket (asignación, solicitantes),
    confirma y vuelve a `back`.

    Un ticket cerrado, un conflicto de versión o una regla incumplida se
    muestran como aviso sin guardar nada.
    """
    public_id = ticket.public_id

    try:
        operation()
        db.session.commit()
    except TicketClosedError as error:
        db.session.rollback()
        flash(str(error), "error")

        return redirect(url_for("tickets.detail", public_id=public_id))
    except (TicketConflictError, TicketRuleError) as error:
        db.session.rollback()
        flash(str(error), "error")
    else:
        if not quiet:
            flash(success_message, "success")

    return redirect(url_for(back, public_id=public_id))


def my_assignment(ticket):
    """La asignación vigente del usuario actual en el ticket, si es técnico y
    está asignado."""
    if not can_assign_self(current_user):
        return None

    return next(
        (a for a in ticket.tecnicos_vigentes if a.tecnico_id == current_user.id),
        None,
    )


def requester_choices(users) -> list[tuple[int, str]]:
    """Opciones para elegir solicitantes. Incluyen el usuario para distinguir
    a personas con el mismo nombre."""
    return [
        (user.id, f"{user.apellido}, {user.nombre} ({user.username})")
        for user in users
    ]
