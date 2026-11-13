from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Identity,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from ._catalog import CatalogAuditMixin


class Prioridad(CatalogAuditMixin, db.Model):
    """Niveles de prioridad (docs/09, 11.2). La prioridad es siempre manual."""

    __tablename__ = "prioridades"
    __table_args__ = (
        CheckConstraint(
            "nivel > 0",
            name="ck_prioridades_nivel_gt_0",
        ),
        # Dos prioridades activas no pueden compartir nivel; una desactivada
        # sí, para poder reutilizar el nivel sin perder el histórico.
        Index(
            "uq_prioridades_nivel_activo",
            "nivel",
            unique=True,
            postgresql_where=text("activo"),
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

    # Valor ordinal para ordenar y comparar; no impone una cola rígida.
    nivel: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    color: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
