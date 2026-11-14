from enum import StrEnum

from sqlalchemy import BigInteger, Identity, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from ._catalog import CatalogAuditMixin


class LocationType(StrEnum):
    """Tipos de ubicación que acepta la aplicación (docs/06, RN-15).

    La lista vive en la aplicación, no en la base de datos: así se evitan
    variantes duplicadas ("Oficina", "oficina", "Ofic.") sin crear una tabla
    de tipos en el MVP (docs/09, 11.5).
    """

    SUCURSAL = "SUCURSAL"
    OFICINA = "OFICINA"
    EDIFICIO = "EDIFICIO"
    PISO = "PISO"
    AREA = "AREA"
    INSTALACION = "INSTALACION"
    OTRA = "OTRA"


LOCATION_TYPE_LABELS = {
    LocationType.SUCURSAL: "Sucursal",
    LocationType.OFICINA: "Oficina",
    LocationType.EDIFICIO: "Edificio",
    LocationType.PISO: "Piso",
    LocationType.AREA: "Área",
    LocationType.INSTALACION: "Instalación",
    LocationType.OTRA: "Otra",
}


class Ubicacion(CatalogAuditMixin, db.Model):
    """Ubicaciones físicas configurables (docs/09, 11.5)."""

    __tablename__ = "ubicaciones"
    __table_args__ = (
        # Nombre único sin distinguir mayúsculas: dos ubicaciones idénticas
        # serían indistinguibles en un desplegable.
        Index(
            "uq_ubicaciones_nombre_lower",
            text("lower(nombre)"),
            unique=True,
        ),
    )

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

    # Código de LocationType, o NULL si no se especificó.
    tipo: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    @property
    def tipo_nombre(self) -> str | None:
        """Nombre visible del tipo; devuelve el valor tal cual si es desconocido."""
        if self.tipo is None:
            return None

        try:
            return LOCATION_TYPE_LABELS[LocationType(self.tipo)]
        except ValueError:
            return self.tipo
