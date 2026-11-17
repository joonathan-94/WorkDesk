from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db


class TicketTechnician(db.Model):
    """Asignación de un técnico a un ticket (docs/09, 15.1).

    Relación N:M temporal: un ticket tiene 0..N técnicos a la vez y un técnico
    0..N tickets. La asignación vigente es la que no tiene `fecha_desasignacion`;
    al quitar a alguien el registro se conserva. La asignación es organizativa:
    no es requisito para que un técnico actúe sobre el ticket (RF-011).
    """

    __tablename__ = "tickets_tecnicos"
    __table_args__ = (
        CheckConstraint(
            "fecha_desasignacion IS NULL OR fecha_desasignacion >= fecha_asignacion",
            name="ck_tickets_tecnicos_desasignacion_posterior",
        ),
        # Un técnico no figura dos veces como asignado vigente del mismo
        # ticket (es también el respaldo cuando dos personas se asignan a la
        # vez); puede volver a asignarse después de haber sido quitado.
        Index(
            "uq_tickets_tecnicos_vigente",
            "ticket_id",
            "tecnico_id",
            unique=True,
            postgresql_where=text("fecha_desasignacion IS NULL"),
        ),
        Index(
            "ix_tickets_tecnicos_ticket_desasignacion",
            "ticket_id",
            "fecha_desasignacion",
        ),
        Index(
            "ix_tickets_tecnicos_tecnico_desasignacion",
            "tecnico_id",
            "fecha_desasignacion",
        ),
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

    tecnico_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )

    fecha_asignacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    asignado_por_usuario_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=True,
    )

    fecha_desasignacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    desasignado_por_usuario_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=True,
    )

    motivo_desasignacion: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    ticket = relationship("Ticket", back_populates="tecnicos")
    tecnico = relationship("User", foreign_keys=[tecnico_id])
