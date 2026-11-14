from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Sequence,
    String,
    Text,
    false,
    func,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db

# Secuencia de PostgreSQL que genera el identificador público. Es segura ante
# concurrencia: dos tickets creados a la vez nunca reciben el mismo número.
# El valor se guarda como texto (docs/09, 5.3) para poder cambiar de formato
# en el futuro sin tocar la clave primaria.
PUBLIC_ID_SEQUENCE = Sequence("tickets_public_id_seq", metadata=db.metadata)

MAX_TITLE_LENGTH = 200


class Ticket(db.Model):
    """Entidad central del dominio (docs/09, sección 13).

    Todavía no incluye grupo, impacto ni urgencia: sus catálogos llegan en
    fases posteriores. Los solicitantes y los técnicos no son columnas de
    esta tabla sino asociaciones temporales (`tickets_solicitantes`).
    """

    __tablename__ = "tickets"
    __table_args__ = (
        CheckConstraint(
            "version >= 1",
            name="ck_tickets_version_gte_1",
        ),
        # Los dos datos del cierre van siempre juntos. Que un ticket en
        # estado CERRADO los tenga lo garantiza el servicio de cierre: la
        # base no puede comprobarlo porque depende del código del estado.
        CheckConstraint(
            "(fecha_cierre IS NULL) = (motivo_cierre_id IS NULL)",
            name="ck_tickets_cierre_coherente",
        ),
        CheckConstraint(
            "NOT cerrado_automaticamente "
            "OR cerrado_por_usuario_id IS NULL",
            name="ck_tickets_cierre_automatico_sin_usuario",
        ),
        Index("ix_tickets_estado_id", "estado_id"),
        Index("ix_tickets_prioridad_id", "prioridad_id"),
        Index("ix_tickets_categoria_id", "categoria_id"),
        Index("ix_tickets_ubicacion_id", "ubicacion_id"),
        Index("ix_tickets_fecha_creacion", "fecha_creacion"),
        Index("ix_tickets_fecha_cierre", "fecha_cierre"),
        Index("ix_tickets_creado_por_usuario_id", "creado_por_usuario_id"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )

    public_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        unique=True,
        server_default=text("nextval('tickets_public_id_seq')::text"),
    )

    titulo: Mapped[str] = mapped_column(
        String(MAX_TITLE_LENGTH),
        nullable=False,
    )

    descripcion: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Creador original: no cambia aunque cambien los solicitantes.
    creado_por_usuario_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )

    categoria_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("categorias.id", ondelete="RESTRICT"),
        nullable=False,
    )

    prioridad_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("prioridades.id", ondelete="RESTRICT"),
        nullable=False,
    )

    estado_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("estados.id", ondelete="RESTRICT"),
        nullable=False,
    )

    ubicacion_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("ubicaciones.id", ondelete="RESTRICT"),
        nullable=True,
    )

    resolucion: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    fecha_modificacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    usuario_modificacion_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=True,
    )

    fecha_resolucion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    fecha_cierre: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # NULL si el cierre fue automático.
    cerrado_por_usuario_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=True,
    )

    motivo_cierre_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("motivos_cierre.id", ondelete="RESTRICT"),
        nullable=True,
    )

    cerrado_automaticamente: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )

    # Control optimista de concurrencia: sube con cada actualización
    # relevante para detectar ediciones simultáneas.
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    # Desactivación lógica excepcional; no equivale a un ticket cerrado.
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

    creado_por = relationship("User", foreign_keys=[creado_por_usuario_id])
    categoria = relationship("Categoria")
    prioridad = relationship("Prioridad")
    estado = relationship("Estado")
    ubicacion = relationship("Ubicacion")
    solicitantes = relationship(
        "TicketRequester",
        back_populates="ticket",
        order_by="TicketRequester.id",
    )
