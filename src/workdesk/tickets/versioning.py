"""Control de versión de los tickets (docs/10, secciones 75 y 76).

Cada ticket lleva una versión que sube con cada cambio de su estructura
(edición, prioridad, estado...). Quien guarda debe hacerlo sobre la versión
que leyó: si otra persona lo modificó entretanto, el guardado se rechaza en
lugar de pisar su cambio en silencio.

Lo comparten la edición de datos (`tickets/editing.py`) y los cambios de
estado (`tickets/lifecycle.py`). Nada de aquí hace commit.
"""

from sqlalchemy import func, update

from ..extensions import db
from ..models import Ticket, User
from .service import TicketRuleError


class TicketClosedError(TicketRuleError):
    """Un ticket cerrado no se modifica: primero debe reabrirse."""


class TicketConflictError(TicketRuleError):
    """Otra persona modificó el ticket mientras se editaba."""


def apply_ticket_changes(
    ticket: Ticket,
    actor: User,
    expected_version: int,
    changes: dict,
) -> None:
    """Aplica `changes` solo si la versión del ticket sigue siendo la esperada.

    Es un `UPDATE ... WHERE version = :esperada`: si otra transacción lo
    modificó antes, no coincide ninguna fila y se informa el conflicto. Si
    dos guardados llegan a la vez, el segundo espera al primero y, al volver
    a evaluar la condición, ya no encuentra la versión que esperaba.

    Sube la versión en uno y registra quién y cuándo modificó el ticket.
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
            usuario_modificacion_id=actor.id,
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
