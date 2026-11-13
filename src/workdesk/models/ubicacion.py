from sqlalchemy import BigInteger, Identity, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from ._catalog import CatalogAuditMixin


class Ubicacion(CatalogAuditMixin, db.Model):
    """Ubicaciones físicas configurables (docs/09, 11.5).

    `tipo` (sucursal, oficina, edificio, piso, área...) lo controla la
    aplicación, no la base de datos: no hay tabla de tipos en el MVP.
    """

    __tablename__ = "ubicaciones"

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )

    nombre: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    descripcion: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    tipo: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
