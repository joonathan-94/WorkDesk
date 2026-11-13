from sqlalchemy import BigInteger, Identity, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from ._catalog import CatalogAuditMixin

# Código de la categoría de respaldo: todo ticket debe tener una categoría
# válida, y esta se usa cuando la clasificación inicial no se conoce.
FALLBACK_CATEGORY_CODE = "SIN_CLASIFICAR"


class Categoria(CatalogAuditMixin, db.Model):
    """Clasificación temática de los tickets (docs/09, 11.1)."""

    __tablename__ = "categorias"
    __table_args__ = (
        # Nombre único sin distinguir mayúsculas, para evitar duplicados
        # indistinguibles como "Redes" y "redes".
        Index(
            "uq_categorias_nombre_lower",
            text("lower(nombre)"),
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )

    codigo: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        unique=True,
    )

    nombre: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    descripcion: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    orden: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
