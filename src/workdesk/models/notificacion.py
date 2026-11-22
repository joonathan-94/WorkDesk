from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    String,
    Text,
    event,
    false,
    func,
    inspect,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db


class NotificationEvent(StrEnum):
    """Los eventos que pueden generar una notificación interna (docs/06, RN-94).

    Es un vocabulario controlado que vive en la aplicación (como `TicketEvent`):
    la base de datos no lo restringe, así que añadir un evento no necesita una
    migración, pero sí decidir su nombre y su icono (un test lo exige).
    """

    TICKET_CREADO = "TICKET_CREADO"
    TICKET_ASIGNADO = "TICKET_ASIGNADO"
    TICKET_REASIGNADO = "TICKET_REASIGNADO"
    ESTADO_CAMBIADO = "ESTADO_CAMBIADO"
    COMENTARIO_PUBLICO = "COMENTARIO_PUBLICO"
    NOTA_INTERNA = "NOTA_INTERNA"
    TICKET_EN_ESPERA = "TICKET_EN_ESPERA"
    TICKET_RESUELTO = "TICKET_RESUELTO"
    VALIDACION_PENDIENTE = "VALIDACION_PENDIENTE"
    TICKET_CERRADO = "TICKET_CERRADO"
    TICKET_REABIERTO = "TICKET_REABIERTO"
    SLA_PROXIMO_A_VENCER = "SLA_PROXIMO_A_VENCER"
    SLA_VENCIDO = "SLA_VENCIDO"
    SLA_PRIORIDAD_BAJADA = "SLA_PRIORIDAD_BAJADA"


NOTIFICATION_EVENT_LABELS = {
    NotificationEvent.TICKET_CREADO: "Ticket creado",
    NotificationEvent.TICKET_ASIGNADO: "Ticket asignado",
    NotificationEvent.TICKET_REASIGNADO: "Ticket reasignado",
    NotificationEvent.ESTADO_CAMBIADO: "Cambio de estado",
    NotificationEvent.COMENTARIO_PUBLICO: "Comentario nuevo",
    NotificationEvent.NOTA_INTERNA: "Nota interna",
    NotificationEvent.TICKET_EN_ESPERA: "Ticket en espera",
    NotificationEvent.TICKET_RESUELTO: "Ticket resuelto",
    NotificationEvent.VALIDACION_PENDIENTE: "Solución pendiente de validar",
    NotificationEvent.TICKET_CERRADO: "Ticket cerrado",
    NotificationEvent.TICKET_REABIERTO: "Ticket reabierto",
    NotificationEvent.SLA_PROXIMO_A_VENCER: "SLA próximo a vencer",
    NotificationEvent.SLA_VENCIDO: "SLA vencido",
    NotificationEvent.SLA_PRIORIDAD_BAJADA: "Prioridad bajada con el SLA en riesgo",
}

# Icono de Bootstrap Icons de cada evento (docs/11, sección 12).
NOTIFICATION_EVENT_ICONS = {
    NotificationEvent.TICKET_CREADO: "plus-circle",
    NotificationEvent.TICKET_ASIGNADO: "person-check",
    NotificationEvent.TICKET_REASIGNADO: "arrow-left-right",
    NotificationEvent.ESTADO_CAMBIADO: "arrow-repeat",
    NotificationEvent.COMENTARIO_PUBLICO: "chat-left-text",
    NotificationEvent.NOTA_INTERNA: "journal-text",
    NotificationEvent.TICKET_EN_ESPERA: "pause-circle",
    NotificationEvent.TICKET_RESUELTO: "check-circle",
    NotificationEvent.VALIDACION_PENDIENTE: "patch-question",
    NotificationEvent.TICKET_CERRADO: "lock",
    NotificationEvent.TICKET_REABIERTO: "arrow-counterclockwise",
    NotificationEvent.SLA_PROXIMO_A_VENCER: "hourglass-split",
    NotificationEvent.SLA_VENCIDO: "exclamation-triangle",
    NotificationEvent.SLA_PRIORIDAD_BAJADA: "arrow-down-circle",
}


class NotificationContentImmutableError(Exception):
    """Se intentó reescribir el contenido de una notificación."""


# Lo único que cambia en una notificación es su estado de lectura.
_CONTENT_COLUMNS = (
    "usuario_id",
    "ticket_id",
    "tipo_evento",
    "titulo",
    "mensaje",
    "fecha_creacion",
)


class Notificacion(db.Model):
    """Aviso interno para un usuario (docs/09, 22.1).

    El contenido original **no se reescribe**: solo evoluciona su condición de
    lectura (`leida` y `fecha_lectura`, que van siempre juntas). Leerla no la
    elimina. Es siempre interna: WorkDesk no envía correo ni mensajes externos.
    """

    __tablename__ = "notificaciones"
    __table_args__ = (
        # `leida` y `fecha_lectura` van siempre juntas (docs/09, 34.9).
        CheckConstraint(
            "(leida AND fecha_lectura IS NOT NULL) "
            "OR (NOT leida AND fecha_lectura IS NULL)",
            name="ck_notificaciones_lectura_coherente",
        ),
        # El mensaje tiene al menos un carácter que no es un espacio, un salto de
        # línea ni un tabulador (`btrim` solo recorta espacios).
        CheckConstraint(
            r"mensaje ~ '\S'",
            name="ck_notificaciones_mensaje_no_vacio",
        ),
        # El contador de no leídas y el listado de cada usuario.
        Index(
            "ix_notificaciones_usuario_leida_fecha",
            "usuario_id",
            "leida",
            "fecha_creacion",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )

    usuario_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Opcional: una notificación puede ser un aviso general.
    ticket_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("tickets.id", ondelete="RESTRICT"),
        nullable=True,
    )

    tipo_evento: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    titulo: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    mensaje: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    leida: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )

    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # La primera lectura: no cambia aunque se vuelva a marcar.
    fecha_lectura: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ticket = relationship("Ticket")

    @property
    def etiqueta(self) -> str:
        """El nombre del evento, o el código si el vocabulario cambió."""
        try:
            return NOTIFICATION_EVENT_LABELS[NotificationEvent(self.tipo_evento)]
        except (KeyError, ValueError):
            return self.tipo_evento

    @property
    def icono(self) -> str:
        try:
            return NOTIFICATION_EVENT_ICONS[NotificationEvent(self.tipo_evento)]
        except (KeyError, ValueError):
            return "bell"


@event.listens_for(Notificacion, "before_update")
def _reject_content_changes(mapper, connection, target):
    state = inspect(target)

    for column in _CONTENT_COLUMNS:
        if state.attrs[column].history.has_changes():
            raise NotificationContentImmutableError(
                "El contenido de una notificación no puede modificarse."
            )
