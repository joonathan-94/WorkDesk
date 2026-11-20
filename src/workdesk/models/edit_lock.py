from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db


class TicketEditLock(db.Model):
    """Bloqueo lógico temporal de la edición de un ticket (docs/09, 28.2).

    Mientras una persona tiene abierta la pantalla de edición, el ticket queda
    reservado para ella: otras personas pueden consultarlo, pero no editarlo
    (docs/06, RN-115). Es una mejora de la experiencia, no la garantía de
    integridad: la segunda barrera, que nunca se omite, es `tickets.version`.

    Un bloqueo está **vigente** cuando `fecha_liberacion IS NULL` y
    `fecha_expiracion` es futura. El índice único solo cubre los bloqueos no
    liberados (un predicado con `now()` no es posible en un índice), así que
    quien adquiere un bloqueo primero libera de forma lógica el expirado que
    estorba, dentro de la misma transacción y con la fila del ticket
    bloqueada (`tickets/locking.py`).
    """

    __tablename__ = "bloqueos_edicion_tickets"
    __table_args__ = (
        CheckConstraint(
            "fecha_expiracion > fecha_inicio",
            name="ck_bloqueos_edicion_expiracion_posterior",
        ),
        CheckConstraint(
            "fecha_liberacion IS NULL OR fecha_liberacion >= fecha_inicio",
            name="ck_bloqueos_edicion_liberacion_posterior",
        ),
        # Nunca dos bloqueos no liberados del mismo ticket.
        Index(
            "uq_bloqueos_edicion_ticket_no_liberado",
            "ticket_id",
            unique=True,
            postgresql_where=text("fecha_liberacion IS NULL"),
        ),
        Index("ix_bloqueos_edicion_usuario_id", "usuario_id"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )

    ticket_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tickets.id", ondelete="RESTRICT"),
        nullable=False,
    )

    usuario_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )

    fecha_inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    fecha_expiracion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Liberación explícita (guardar, cancelar) o normalización de un bloqueo
    # expirado por quien adquiere el siguiente.
    fecha_liberacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ticket = relationship("Ticket")
    usuario = relationship("User")
