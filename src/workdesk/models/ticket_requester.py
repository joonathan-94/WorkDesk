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


class TicketRequester(db.Model):
    """Participación de un usuario como solicitante de un ticket.

    Relación N:M temporal (docs/09, 14.1): un ticket puede tener 0..N
    solicitantes. La participación vigente es la que no tiene `fecha_retiro`;
    al retirar a alguien el registro se conserva, nunca se elimina.
    """

    __tablename__ = "tickets_solicitantes"
    __table_args__ = (
        CheckConstraint(
            "fecha_retiro IS NULL OR fecha_retiro >= fecha_asociacion",
            name="ck_tickets_solicitantes_retiro_posterior",
        ),
        # Nadie puede figurar dos veces como solicitante vigente del mismo
        # ticket; sí puede volver a asociarse después de haber sido retirado.
        Index(
            "uq_tickets_solicitantes_vigente",
            "ticket_id",
            "solicitante_id",
            unique=True,
            postgresql_where=text("fecha_retiro IS NULL"),
        ),
        Index("ix_tickets_solicitantes_ticket_id", "ticket_id"),
        Index("ix_tickets_solicitantes_solicitante_id", "solicitante_id"),
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

    solicitante_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )

    fecha_asociacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    asociado_por_usuario_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=True,
    )

    fecha_retiro: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    retirado_por_usuario_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=True,
    )

    ticket = relationship("Ticket", back_populates="solicitantes")
    solicitante = relationship("User", foreign_keys=[solicitante_id])
