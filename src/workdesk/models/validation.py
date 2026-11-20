from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db


class ValidationType(StrEnum):
    """Respuesta de un solicitante frente a una resolución."""

    ACEPTADA = "ACEPTADA"
    RECHAZADA = "RECHAZADA"


class Validation(db.Model):
    """Respuesta de un solicitante a la resolución de un ticket (docs/09, 16.1).

    Cada vez que un ticket entra en `Resuelto` empieza un nuevo ciclo de
    resolución (`ciclo_resolucion`, desde 1). Un mismo solicitante responde
    una sola vez por ciclo; puede volver a responder en ciclos posteriores.
    No existe una tabla de resoluciones: el ciclo se deduce de los eventos
    `TICKET_RESUELTO` del historial.

    La confirmación de cualquier solicitante cierra el ticket completo.
    """

    __tablename__ = "validaciones"
    __table_args__ = (
        CheckConstraint(
            "ciclo_resolucion >= 1",
            name="ck_validaciones_ciclo_gte_1",
        ),
        CheckConstraint(
            "tipo_validacion IN ('ACEPTADA', 'RECHAZADA')",
            name="ck_validaciones_tipo_valido",
        ),
        # Un rechazo siempre explica por qué (docs/09, 16.1).
        CheckConstraint(
            "tipo_validacion <> 'RECHAZADA' "
            "OR (motivo_rechazo IS NOT NULL "
            "AND length(btrim(motivo_rechazo)) > 0)",
            name="ck_validaciones_rechazo_con_motivo",
        ),
        UniqueConstraint(
            "ticket_id",
            "solicitante_id",
            "ciclo_resolucion",
            name="uq_validaciones_ticket_solicitante_ciclo",
        ),
        Index("ix_validaciones_ticket_ciclo", "ticket_id", "ciclo_resolucion"),
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

    ciclo_resolucion: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    tipo_validacion: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    motivo_rechazo: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    comentario_adicional: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    fecha_validacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    ticket = relationship("Ticket")
    solicitante = relationship("User", foreign_keys=[solicitante_id])
