from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Text,
    func,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db


class TicketRelation(db.Model):
    """Relación entre dos tickets (docs/09, 19.2).

    - `DUPLICADO`: `ticket_origen_id` es el ticket **duplicado** y
      `ticket_destino_id` el **principal**.
    - `RELACIONADO` (simétrica): el par se guarda normalizado, con el id menor
      en `ticket_origen_id`, para que A-B y B-A sean la misma relación.

    La eliminación es lógica: una relación desactivada se conserva como
    historial y, si vuelve a establecerse, se crea una nueva.
    """

    __tablename__ = "tickets_relaciones"
    __table_args__ = (
        CheckConstraint(
            "ticket_origen_id <> ticket_destino_id",
            name="ck_tickets_relaciones_distintos",
        ),
        CheckConstraint(
            "(activo AND fecha_desactivacion IS NULL "
            "AND usuario_desactivacion_id IS NULL) "
            "OR (NOT activo AND fecha_desactivacion IS NOT NULL)",
            name="ck_tickets_relaciones_desactivacion_coherente",
        ),
        # Una misma relación vigente no se repite, ni invertida: el par se
        # compara sin importar el orden (menor, mayor).
        Index(
            "uq_tickets_relaciones_par_vigente",
            text("least(ticket_origen_id, ticket_destino_id)"),
            text("greatest(ticket_origen_id, ticket_destino_id)"),
            "tipo_relacion_id",
            unique=True,
            postgresql_where=text("activo"),
        ),
        Index("ix_tickets_relaciones_origen", "ticket_origen_id"),
        Index("ix_tickets_relaciones_destino", "ticket_destino_id"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )

    ticket_origen_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tickets.id", ondelete="RESTRICT"),
        nullable=False,
    )

    ticket_destino_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tickets.id", ondelete="RESTRICT"),
        nullable=False,
    )

    tipo_relacion_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tipos_relacion_ticket.id", ondelete="RESTRICT"),
        nullable=False,
    )

    comentario: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    usuario_creacion_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )

    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )

    fecha_desactivacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    usuario_desactivacion_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=True,
    )

    origen = relationship("Ticket", foreign_keys=[ticket_origen_id])
    destino = relationship("Ticket", foreign_keys=[ticket_destino_id])
    tipo = relationship("TipoRelacionTicket")
    creada_por = relationship("User", foreign_keys=[usuario_creacion_id])
