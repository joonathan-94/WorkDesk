from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    String,
    Text,
    event,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from .admin_audit_log import ActorType


class TicketEvent(StrEnum):
    """Vocabulario controlado de eventos del historial de un ticket.

    Contiene solo los eventos que existen hoy; v0.4.0 añadirá los de estado,
    asignación, comentarios, resolución y cierre (docs/09, 24.1).
    """

    TICKET_CREADO = "TICKET_CREADO"
    TICKET_MODIFICADO = "TICKET_MODIFICADO"
    CATEGORIA_CAMBIADA = "CATEGORIA_CAMBIADA"
    PRIORIDAD_CAMBIADA = "PRIORIDAD_CAMBIADA"


TICKET_EVENT_LABELS = {
    TicketEvent.TICKET_CREADO: "Ticket creado",
    TicketEvent.TICKET_MODIFICADO: "Ticket modificado",
    TicketEvent.CATEGORIA_CAMBIADA: "Categoría cambiada",
    TicketEvent.PRIORIDAD_CAMBIADA: "Prioridad cambiada",
}


class TicketHistoryImmutableError(Exception):
    """Se intentó modificar o eliminar un evento del historial."""


def _sql_list(codes: type[StrEnum]) -> str:
    return ", ".join(f"'{code.value}'" for code in codes)


class TicketHistory(db.Model):
    """Historial operativo de un ticket, append-only (docs/09, 24.1).

    Es la fuente cronológica para reconstruir la vida del ticket. Una
    corrección se registra como un evento nuevo, nunca editando el original.
    """

    __tablename__ = "historial_ticket"
    __table_args__ = (
        CheckConstraint(
            f"actor_tipo IN ({_sql_list(ActorType)})",
            name="ck_historial_ticket_actor_tipo",
        ),
        CheckConstraint(
            "(actor_tipo = 'SISTEMA' AND actor_usuario_id IS NULL) "
            "OR (actor_tipo = 'USUARIO' AND actor_usuario_id IS NOT NULL)",
            name="ck_historial_ticket_actor_coherente",
        ),
        CheckConstraint(
            f"tipo_evento IN ({_sql_list(TicketEvent)})",
            name="ck_historial_ticket_tipo_evento",
        ),
        Index(
            "ix_historial_ticket_ticket_fecha",
            "ticket_id",
            "fecha_hora",
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

    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # NULL para eventos del sistema; no existe un usuario ficticio "Sistema".
    actor_usuario_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=True,
    )

    actor_tipo: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    tipo_evento: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    estado_anterior_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("estados.id", ondelete="RESTRICT"),
        nullable=True,
    )

    estado_nuevo_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("estados.id", ondelete="RESTRICT"),
        nullable=True,
    )

    detalle: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    valor_anterior: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    valor_nuevo: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Datos variables del evento, por ejemplo el motivo de un cambio.
    contexto: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # None cuando el evento lo generó el sistema.
    actor = relationship("User", foreign_keys=[actor_usuario_id])

    @property
    def evento_nombre(self) -> str:
        """Nombre visible del evento; devuelve el código si es desconocido."""
        try:
            return TICKET_EVENT_LABELS[TicketEvent(self.tipo_evento)]
        except ValueError:
            return self.tipo_evento


@event.listens_for(TicketHistory, "before_update")
@event.listens_for(TicketHistory, "before_delete")
def _reject_history_changes(mapper, connection, target):
    raise TicketHistoryImmutableError(
        "Los eventos del historial no pueden modificarse ni eliminarse."
    )
