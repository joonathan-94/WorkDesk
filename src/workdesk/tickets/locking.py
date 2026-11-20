"""Bloqueo temporal de edición de un ticket (docs/06, RN-115 a RN-117;
docs/09, 28; docs/10, secciones 71 a 74).

Mientras una persona tiene abierta la pantalla de **editar** el ticket o de
**cambiar su prioridad**, el ticket queda reservado para ella: las demás pueden
consultarlo, pero no editarlo, y se les dice quién lo está editando. Es una
mejora de la experiencia; la garantía de integridad sigue siendo la versión del
ticket (`tickets.version`), que se comprueba siempre al guardar, también si
este mecanismo fallara (por ejemplo, por una pestaña que quedó abierta).

Ciclo de vida de un bloqueo:

- **Adquirir:** al abrir la pantalla (y al guardar, si no se tenía). Sirve
  también para **renovar**: quien ya lo tiene vuelve a fijar su expiración.
- **Renovar:** la pantalla lo hace cada pocos segundos mientras está abierta
  (`EDIT_LOCK_HEARTBEAT_SECONDS`, mejora progresiva con JavaScript).
- **Liberar:** al guardar, al cancelar o al salir de la pantalla.
- **Expirar:** si el navegador se cierra o la red cae, el bloqueo deja de estar
  vigente solo, a los `EDIT_LOCK_TTL_SECONDS` sin renovarse (RN-117).

Un bloqueo está **vigente** cuando no se liberó y su expiración es futura. La
base garantiza que no haya dos no liberados del mismo ticket (índice único
parcial); como un índice no puede depender de `now()`, quien adquiere primero
libera de forma lógica el bloqueo expirado que estorba, en la misma transacción
y con la fila del ticket bloqueada (`SELECT ... FOR UPDATE`), así que dos
personas que abren la pantalla a la vez no se pisan.

Solo se bloquea la edición de los datos y de la prioridad. Los demás cambios
(estado, asignación, comentarios...) son acciones puntuales y confían en la
versión del ticket o en ser aditivos.

Nada de aquí hace commit: lo hace quien llama. Las horas las toma de la base de
datos (`clock_timestamp()`), no del reloj del servidor web, para que todos
comparen contra el mismo reloj.
"""

from dataclasses import dataclass
from datetime import timedelta

from flask import current_app
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models import Ticket, TicketEditLock, User
from .service import TicketRuleError
from .versioning import lock_ticket


@dataclass(frozen=True)
class EditLockStatus:
    """Resultado de adquirir (o renovar) el bloqueo: de quién es."""

    lock: TicketEditLock
    # True: el bloqueo es de quien lo pidió. False: lo tiene otra persona.
    mine: bool


def acquire_edit_lock(ticket: Ticket, actor: User) -> EditLockStatus:
    """Adquiere o renueva el bloqueo de edición del ticket para `actor`.

    - Si nadie lo tiene (o el que había expiró), se crea uno nuevo.
    - Si ya es de `actor`, se renueva su expiración (también si ya había
      expirado pero nadie lo había tomado).
    - Si lo tiene otra persona y sigue vigente, no se toca y se devuelve el
      suyo con `mine=False` para informar quién edita.

    Es idempotente, así que renovar y adquirir son la misma operación.
    """
    if not actor.is_active:
        raise TicketRuleError("El usuario no está activo.")

    # Serializa a quienes adquieren a la vez: la segunda espera a la primera y
    # ve su bloqueo.
    lock_ticket(ticket)

    now = _now()
    expires = now + _ttl()
    current = _unreleased(ticket)

    if current is not None:
        if current.usuario_id == actor.id:
            current.fecha_expiracion = expires
            db.session.flush()

            return EditLockStatus(lock=current, mine=True)

        if current.fecha_expiracion > now:
            return EditLockStatus(lock=current, mine=False)

        # Expiró: se libera de forma lógica para que el índice único admita el
        # nuevo.
        current.fecha_liberacion = now
        db.session.flush()

    lock = TicketEditLock(
        ticket_id=ticket.id,
        usuario_id=actor.id,
        fecha_inicio=now,
        fecha_expiracion=expires,
    )

    db.session.add(lock)
    db.session.flush()

    return EditLockStatus(lock=lock, mine=True)


def release_edit_lock(ticket: Ticket, actor: User) -> bool:
    """Libera el bloqueo de `actor` sobre el ticket (al guardar, cancelar o
    salir de la pantalla). Devuelve si había uno suyo que liberar; el de otra
    persona nunca se toca."""
    lock_ticket(ticket)

    current = _unreleased(ticket)

    if current is None or current.usuario_id != actor.id:
        return False

    current.fecha_liberacion = _now()
    db.session.flush()

    return True


def current_edit_lock(ticket: Ticket) -> TicketEditLock | None:
    """El bloqueo vigente del ticket (de quien sea), con la persona cargada, o
    None. No modifica nada: sirve para informar quién está editando."""
    return db.session.scalar(
        db.select(TicketEditLock)
        .where(
            TicketEditLock.ticket_id == ticket.id,
            TicketEditLock.fecha_liberacion.is_(None),
            TicketEditLock.fecha_expiracion > func.clock_timestamp(),
        )
        .options(joinedload(TicketEditLock.usuario))
    )


def _unreleased(ticket: Ticket) -> TicketEditLock | None:
    """El bloqueo no liberado del ticket (vigente o expirado); a lo sumo uno."""
    return db.session.scalar(
        db.select(TicketEditLock)
        .where(
            TicketEditLock.ticket_id == ticket.id,
            TicketEditLock.fecha_liberacion.is_(None),
        )
        .options(joinedload(TicketEditLock.usuario))
    )


def _now():
    return db.session.scalar(db.select(func.clock_timestamp()))


def _ttl() -> timedelta:
    return timedelta(seconds=current_app.config["EDIT_LOCK_TTL_SECONDS"])
