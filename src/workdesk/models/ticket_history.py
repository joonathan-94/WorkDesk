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

    El vocabulario vive solo en la aplicación (`record_ticket_event` rechaza
    cualquier evento que no esté aquí), igual que `AuditAction` en la
    auditoría administrativa: la base de datos no lo restringe, así que añadir
    un evento no requiere una migración. Contiene los eventos que existen hoy;
    v0.4.0 añade los de estado, asignación, comentarios, resolución y cierre
    (docs/09, 24.1).
    """

    TICKET_CREADO = "TICKET_CREADO"
    TICKET_MODIFICADO = "TICKET_MODIFICADO"
    CATEGORIA_CAMBIADA = "CATEGORIA_CAMBIADA"
    PRIORIDAD_CAMBIADA = "PRIORIDAD_CAMBIADA"
    ESTADO_CAMBIADO = "ESTADO_CAMBIADO"
    TECNICO_ASIGNADO = "TECNICO_ASIGNADO"
    TECNICO_DESASIGNADO = "TECNICO_DESASIGNADO"
    GRUPO_CAMBIADO = "GRUPO_CAMBIADO"
    TICKET_ESCALADO = "TICKET_ESCALADO"
    SOLICITANTE_AGREGADO = "SOLICITANTE_AGREGADO"
    SOLICITANTE_RETIRADO = "SOLICITANTE_RETIRADO"


class HistoryVisibility(StrEnum):
    """Quién puede ver un evento del historial (docs/13, sección 9).

    - `PUBLICO`: lo ven todas las personas con acceso al ticket, incluido el
      Solicitante.
    - `INTERNO`: solo el personal (Técnico, Supervisor y Administrador). Una
      nota interna y todo lo que la rodea nunca llega al Solicitante.
    """

    PUBLICO = "PUBLICO"
    INTERNO = "INTERNO"


# Visibilidad con la que se registra cada evento si quien lo registra no
# indica otra. Cada evento del vocabulario debe aparecer aquí: así, al añadir
# uno nuevo hay que decidir explícitamente quién puede verlo (un test lo
# comprueba).
DEFAULT_EVENT_VISIBILITY = {
    TicketEvent.TICKET_CREADO: HistoryVisibility.PUBLICO,
    TicketEvent.TICKET_MODIFICADO: HistoryVisibility.PUBLICO,
    TicketEvent.CATEGORIA_CAMBIADA: HistoryVisibility.PUBLICO,
    TicketEvent.PRIORIDAD_CAMBIADA: HistoryVisibility.PUBLICO,
    # El cambio de estado lo ve el Solicitante; el motivo de espera y su
    # texto, no (se muestran solo al personal, como el motivo de prioridad).
    TicketEvent.ESTADO_CAMBIADO: HistoryVisibility.PUBLICO,
    # Quién atiende el ticket es público ("Atendido por", docs/11, UI-005).
    # El grupo y el escalamiento son internos: el Solicitante no conoce la
    # estructura de grupos (docs/11, UI-005).
    TicketEvent.TECNICO_ASIGNADO: HistoryVisibility.PUBLICO,
    TicketEvent.TECNICO_DESASIGNADO: HistoryVisibility.PUBLICO,
    TicketEvent.GRUPO_CAMBIADO: HistoryVisibility.INTERNO,
    TicketEvent.TICKET_ESCALADO: HistoryVisibility.INTERNO,
    # El Solicitante no ve a las demás personas que figuran en el ticket
    # (docs/06, RN-153; docs/11, UI-005): quién se agrega o se retira como
    # solicitante es solo del personal.
    TicketEvent.SOLICITANTE_AGREGADO: HistoryVisibility.INTERNO,
    TicketEvent.SOLICITANTE_RETIRADO: HistoryVisibility.INTERNO,
}


TICKET_EVENT_LABELS = {
    TicketEvent.TICKET_CREADO: "Ticket creado",
    TicketEvent.TICKET_MODIFICADO: "Ticket modificado",
    TicketEvent.CATEGORIA_CAMBIADA: "Categoría cambiada",
    TicketEvent.PRIORIDAD_CAMBIADA: "Prioridad cambiada",
    TicketEvent.ESTADO_CAMBIADO: "Estado cambiado",
    TicketEvent.TECNICO_ASIGNADO: "Técnico asignado",
    TicketEvent.TECNICO_DESASIGNADO: "Técnico desasignado",
    TicketEvent.GRUPO_CAMBIADO: "Grupo cambiado",
    TicketEvent.TICKET_ESCALADO: "Ticket escalado",
    TicketEvent.SOLICITANTE_AGREGADO: "Solicitante agregado",
    TicketEvent.SOLICITANTE_RETIRADO: "Solicitante retirado",
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
            f"visibilidad IN ({_sql_list(HistoryVisibility)})",
            name="ck_historial_ticket_visibilidad",
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

    # Código de `TicketEvent`. Sin CHECK en la base de datos: lo valida el
    # servicio que registra el evento.
    tipo_evento: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # Quién puede ver el evento. Lo filtra la consulta (nunca la plantilla):
    # ver `visible_history_condition` en `tickets/service.py`.
    visibilidad: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default=HistoryVisibility.PUBLICO.value,
        server_default=HistoryVisibility.PUBLICO.value,
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

    # Motivo del catálogo cuando el evento es la entrada a `En espera`
    # (docs/09, 12.3). Un motivo desactivado después sigue referenciado.
    motivo_espera_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("motivos_espera.id", ondelete="RESTRICT"),
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

    # Solo cuando el evento es la entrada a `En espera` con un motivo.
    motivo_espera = relationship("MotivoEspera")

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
