from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    String,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db


class Attachment(db.Model):
    """Metadatos de un archivo adjunto a un ticket (docs/09, 18.1).

    El binario no vive en la base de datos: está en el almacenamiento local
    (`instance/uploads`, fuera de `static/`) con un nombre interno
    impredecible. Aquí solo se guardan los metadatos. La eliminación es lógica:
    el registro y el archivo se conservan, pero deja de mostrarse y de poder
    descargarse. Pasado un plazo, la retención puede borrar el archivo físico
    (`fecha_purga_archivo`); el registro se conserva siempre.

    `comentario_id` es opcional: un adjunto subido junto a un comentario o a
    una nota interna hereda su visibilidad (el Solicitante no ve los adjuntos
    de una nota interna). Sin comentario, el adjunto es del ticket y lo ve
    quien ve el ticket.
    """

    __tablename__ = "archivos"
    __table_args__ = (
        CheckConstraint(
            "tamano_bytes >= 0",
            name="ck_archivos_tamano_no_negativo",
        ),
        CheckConstraint(
            "(activo AND fecha_eliminacion IS NULL "
            "AND usuario_eliminacion_id IS NULL) "
            "OR (NOT activo AND fecha_eliminacion IS NOT NULL)",
            name="ck_archivos_eliminacion_coherente",
        ),
        # La retención borra el archivo físico de un adjunto ya eliminado y lo anota aquí: solo
        # un adjunto eliminado puede tenerla, y nunca antes de su eliminación.
        CheckConstraint(
            "fecha_purga_archivo IS NULL "
            "OR (NOT activo AND fecha_purga_archivo >= fecha_eliminacion)",
            name="ck_archivos_purga_coherente",
        ),
        Index("ix_archivos_ticket_fecha", "ticket_id", "fecha_subida"),
        Index("ix_archivos_comentario_id", "comentario_id"),
        Index("uq_archivos_nombre_interno", "nombre_interno", unique=True),
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

    comentario_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("comentarios.id", ondelete="RESTRICT"),
        nullable=True,
    )

    # Nombre que entregó el usuario, ya depurado. Solo es metadato y nombre
    # sugerido al descargar; nunca se usa como ruta.
    nombre_original: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Nombre físico generado por el sistema (UUID en hexadecimal).
    nombre_interno: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    # Ruta relativa a la raíz de uploads, controlada por WorkDesk.
    ruta_archivo: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Tipo MIME deducido de la extensión validada, no el que declara el cliente.
    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    tamano_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    # SHA-256 en hexadecimal minúscula.
    hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    usuario_subida_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )

    fecha_subida: Mapped[datetime] = mapped_column(
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

    fecha_eliminacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    usuario_eliminacion_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=True,
    )

    # Cuándo la retención borró el archivo físico (RF-111). La fila se conserva: el historial
    # del ticket la sigue nombrando (RN-110).
    fecha_purga_archivo: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ticket = relationship("Ticket")
    comentario = relationship("Comment")
    subido_por = relationship("User", foreign_keys=[usuario_subida_id])
