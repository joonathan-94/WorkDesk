"""La base de conocimiento: artículos y su vínculo con tickets (docs/09, sección 23)."""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    false,
    func,
    true,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from ..search import indexed_text_sql

MAX_ARTICLE_TITLE_LENGTH = 200
MAX_ARTICLE_CONTENT_LENGTH = 20_000


class ArticleVisibility(StrEnum):
    """Quién puede leer un artículo publicado (docs/09, 23.1).

    `PUBLICO` no significa abierto a Internet: es visible para cualquier persona con sesión,
    también los Solicitantes. `PRIVADO` es solo para el personal.
    """

    PUBLICO = "PUBLICO"
    PRIVADO = "PRIVADO"


class ArticleLinkType(StrEnum):
    """Por qué un ticket está vinculado a un artículo (docs/09, 23.2)."""

    REFERENCIA = "REFERENCIA"
    ORIGEN_RESOLUCION = "ORIGEN_RESOLUCION"


# El índice de búsqueda: el título pesa más que el contenido. Lo calcula PostgreSQL (columna
# generada), así que nunca queda desactualizado respecto del texto.
_SEARCH_EXPRESSION = (
    f"{indexed_text_sql('titulo', 'A')} || {indexed_text_sql('contenido', 'B')}"
)


class Article(db.Model):
    """Un artículo de conocimiento.

    `publicado` y `visibilidad` son independientes: hay borradores públicos y artículos
    publicados privados. Desactivar no borra: el artículo deja de verse pero conserva su
    historial y sus vínculos. `version` detecta que otra persona lo editó mientras tanto.

    Respecto de docs/09 se añaden `categoria_id` (se reutiliza el catálogo de categorías de
    los tickets), `destacado` (los artículos destacados de UI-009), `version` y la columna de
    búsqueda `vector_busqueda`.
    """

    __tablename__ = "articulos_conocimiento"
    __table_args__ = (
        CheckConstraint(
            "visibilidad IN ('PUBLICO', 'PRIVADO')",
            name="ck_articulos_conocimiento_visibilidad",
        ),
        CheckConstraint(
            "titulo ~ '\\S'",
            name="ck_articulos_conocimiento_titulo_no_vacio",
        ),
        CheckConstraint(
            "contenido ~ '\\S'",
            name="ck_articulos_conocimiento_contenido_no_vacio",
        ),
        # Publicado y su fecha van siempre juntos.
        CheckConstraint(
            "publicado = (fecha_publicacion IS NOT NULL)",
            name="ck_articulos_conocimiento_publicacion_coherente",
        ),
        # Solo se destaca lo que se puede leer.
        CheckConstraint(
            "NOT destacado OR (publicado AND activo)",
            name="ck_articulos_conocimiento_destacado_publicado",
        ),
        CheckConstraint(
            "(activo AND fecha_desactivacion IS NULL AND usuario_desactivacion_id IS NULL) "
            "OR (NOT activo AND fecha_desactivacion IS NOT NULL)",
            name="ck_articulos_conocimiento_desactivacion_coherente",
        ),
        CheckConstraint("version >= 1", name="ck_articulos_conocimiento_version_positiva"),
        Index(
            "ix_articulos_conocimiento_busqueda",
            "vector_busqueda",
            postgresql_using="gin",
        ),
        Index("ix_articulos_conocimiento_categoria", "categoria_id"),
        Index("ix_articulos_conocimiento_publicacion", "fecha_publicacion", "id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)

    titulo: Mapped[str] = mapped_column(String(MAX_ARTICLE_TITLE_LENGTH), nullable=False)
    contenido: Mapped[str] = mapped_column(Text, nullable=False)

    categoria_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("categorias.id", ondelete="RESTRICT"),
        nullable=False,
    )

    visibilidad: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default=ArticleVisibility.PRIVADO.value,
    )

    publicado: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    fecha_publicacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    destacado: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )

    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    autor_usuario_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_modificacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    usuario_modificacion_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True
    )
    fecha_desactivacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    usuario_desactivacion_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True
    )

    # Solo para buscar: la calcula la base de datos y no se carga al leer un artículo.
    vector_busqueda: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(_SEARCH_EXPRESSION, persisted=True),
        deferred=True,
    )

    categoria = relationship("Categoria")
    autor = relationship("User", foreign_keys=[autor_usuario_id])

    @property
    def es_privado(self) -> bool:
        return self.visibilidad == ArticleVisibility.PRIVADO.value


class TicketArticle(db.Model):
    """Un ticket vinculado a un artículo (docs/09, 23.2). Un mismo par, una sola vez."""

    __tablename__ = "tickets_articulos_conocimiento"
    __table_args__ = (
        CheckConstraint(
            "tipo_vinculacion IN ('REFERENCIA', 'ORIGEN_RESOLUCION')",
            name="ck_tickets_articulos_tipo",
        ),
        UniqueConstraint("ticket_id", "articulo_id", name="uq_tickets_articulos_par"),
        Index("ix_tickets_articulos_articulo", "articulo_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tickets.id", ondelete="RESTRICT"), nullable=False
    )
    articulo_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("articulos_conocimiento.id", ondelete="RESTRICT"),
        nullable=False,
    )
    tipo_vinculacion: Mapped[str] = mapped_column(String(20), nullable=False)
    usuario_creacion_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
    )
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    articulo = relationship("Article")
    ticket = relationship("Ticket")
