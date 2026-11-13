from sqlalchemy import BigInteger, Identity, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from ._catalog import CatalogAuditMixin


class MotivoCierre(CatalogAuditMixin, db.Model):
    """Clasificación del cierre de un ticket (docs/09, 12.4).

    La cancelación y la duplicidad no son estados: se representan como un
    cierre con el motivo `CANCELACION` o `DUPLICADO` (docs/09, sección 38).
    """

    __tablename__ = "motivos_cierre"

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )

    codigo: Mapped[str] = mapped_column(
        String,
        nullable=False,
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
