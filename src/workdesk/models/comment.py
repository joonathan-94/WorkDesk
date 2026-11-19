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
    false,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db

# Límite de caracteres de un comentario o nota (docs/09, 17.1). Lo comprueba el
# servicio y el formulario; la base de datos guarda TEXT.
MAX_COMMENT_LENGTH = 5000


class CommentType(StrEnum):
    """Tipo de un comentario. Se define al crearlo y no cambia nunca.

    - `PUBLICO`: lo ven el personal y los Solicitantes con acceso al ticket.
    - `INTERNO` (nota interna): solo lo ve el personal. Cambiar el tipo de un
      comentario ya publicado alteraría retroactivamente quién lo ve, por eso
      una edición nunca lo modifica.
    """

    PUBLICO = "PUBLICO"
    INTERNO = "INTERNO"


def _sql_list(codes: type[StrEnum]) -> str:
    return ", ".join(f"'{code.value}'" for code in codes)


class Comment(db.Model):
    """Comentario público o nota interna de un ticket (docs/09, 17.1).

    Una única tabla representa ambos tipos. La eliminación es lógica: el
    comentario se conserva (con quién y cuándo lo eliminó) y deja de mostrarse.
    El contenido anterior de una edición o eliminación se guarda en el
    historial del ticket, no en una tabla de versiones.
    """

    __tablename__ = "comentarios"
    __table_args__ = (
        CheckConstraint(
            f"tipo IN ({_sql_list(CommentType)})",
            name="ck_comentarios_tipo",
        ),
        CheckConstraint(
            "length(btrim(contenido)) > 0",
            name="ck_comentarios_contenido_no_vacio",
        ),
        # Activo: sin datos de eliminación. Eliminado: con fecha.
        CheckConstraint(
            "(activo AND fecha_eliminacion IS NULL "
            "AND usuario_eliminacion_id IS NULL) "
            "OR (NOT activo AND fecha_eliminacion IS NOT NULL)",
            name="ck_comentarios_eliminacion_coherente",
        ),
        CheckConstraint(
            "NOT editado OR fecha_modificacion IS NOT NULL",
            name="ck_comentarios_edicion_coherente",
        ),
        Index(
            "ix_comentarios_ticket_fecha",
            "ticket_id",
            "fecha_creacion",
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

    autor_usuario_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Código de `CommentType`.
    tipo: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    contenido: Mapped[str] = mapped_column(
        Text,
        nullable=False,
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

    # Quién editó por última vez (puede no ser el autor).
    usuario_modificacion_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=True,
    )

    editado: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
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

    ticket = relationship("Ticket")
    autor = relationship("User", foreign_keys=[autor_usuario_id])

    @property
    def es_nota_interna(self) -> bool:
        return self.tipo == CommentType.INTERNO.value
