"""Control de versión de los tickets (docs/10, secciones 75 y 76).

Cada ticket lleva una versión que sube con cada cambio de su estructura
(edición, prioridad, estado...). Quien guarda debe hacerlo sobre la versión
que leyó: si otra persona lo modificó entretanto, el guardado se rechaza en
lugar de pisar su cambio en silencio.

Lo comparten la edición de datos (`tickets/editing.py`), los cambios de
estado (`tickets/lifecycle.py`), la asignación (`tickets/assignment.py`) y los
solicitantes (`tickets/requesters.py`). Nada de aquí hace commit.
"""

from collections.abc import Sequence

from sqlalchemy import func, update

from ..extensions import db
from ..models import Estado, Ticket, User
from .service import CLOSED_STATE_CODE, TicketRuleError


class TicketClosedError(TicketRuleError):
    """Un ticket cerrado no se modifica: primero debe reabrirse."""


class TicketConflictError(TicketRuleError):
    """Otra persona modificó el ticket mientras se editaba."""


def apply_ticket_changes(
    ticket: Ticket,
    actor: User | None,
    expected_version: int,
    changes: dict,
) -> None:
    """Aplica `changes` solo si la versión del ticket sigue siendo la esperada.

    Es un `UPDATE ... WHERE version = :esperada`: si otra transacción lo
    modificó antes, no coincide ninguna fila y se informa el conflicto. Si
    dos guardados llegan a la vez, el segundo espera al primero y, al volver
    a evaluar la condición, ya no encuentra la versión que esperaba.

    Sube la versión en uno y registra quién y cuándo modificó el ticket (`actor` es
    None cuando lo hace el sistema, por ejemplo el cierre automático).
    """
    result = db.session.execute(
        update(Ticket)
        .where(
            Ticket.id == ticket.id,
            Ticket.version == expected_version,
        )
        .values(
            **changes,
            version=Ticket.version + 1,
            fecha_modificacion=func.now(),
            usuario_modificacion_id=None if actor is None else actor.id,
        )
        .execution_options(synchronize_session=False)
    )

    if result.rowcount != 1:
        raise TicketConflictError(
            "Otra persona modificó este ticket mientras lo editabas. "
            "Revisa los datos actuales e inténtalo de nuevo."
        )

    # El objeto en memoria debe reflejar lo que acaba de guardarse.
    db.session.refresh(ticket)


def lock_ticket(ticket: Ticket) -> None:
    """Bloquea la fila del ticket (`SELECT ... FOR UPDATE`) y la vuelve a leer.

    Las operaciones que validan contra el estado real del ticket (cambios de
    estado, asignaciones...) la llaman antes de decidir: si dos personas
    actúan a la vez, la segunda espera a que la primera confirme y ve su
    resultado. El bloqueo dura hasta el final de la transacción.
    """
    db.session.execute(
        db.select(Ticket.id).where(Ticket.id == ticket.id).with_for_update()
    )
    db.session.refresh(ticket)


def begin_ticket_operation(
    ticket: Ticket,
    actor: User,
    *,
    expire: Sequence[str] = (),
) -> None:
    """Prepara una operación que modifica el ticket o lo que cuelga de él.

    Comprueba que el actor esté activo, bloquea la fila del ticket
    (`lock_ticket`) y rechaza un ticket cerrado con `TicketClosedError`
    (antes debe reabrirse). Después descarta de la sesión las relaciones
    indicadas en `expire` (técnicos, solicitantes...): pudieron cambiar
    mientras esta operación esperaba el bloqueo y hay que volver a leerlas.

    Es el principio común de las operaciones que validan contra el estado
    real del ticket (asignación, solicitantes...).
    """
    if not actor.is_active:
        raise TicketRuleError("El usuario no está activo.")

    lock_ticket(ticket)

    state = db.session.get(Estado, ticket.estado_id)

    if state.codigo == CLOSED_STATE_CODE:
        raise TicketClosedError(
            "Un ticket cerrado no se puede modificar. Primero debe reabrirse."
        )

    if expire:
        db.session.expire(ticket, list(expire))
