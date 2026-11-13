from sqlalchemy import BigInteger, Identity, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db


class Estado(db.Model):
    """Estados estructurales del ticket (docs/09, 12.1).

    Son exactamente seis y su `codigo` es inmutable. Solo los atributos
    visibles (`nombre_visible`, `descripcion`, `color`) son configurables, por
    eso no lleva las columnas de vigencia de los demás catálogos.
    """

    __tablename__ = "estados"

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

    nombre_visible: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    descripcion: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    color: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    orden: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
