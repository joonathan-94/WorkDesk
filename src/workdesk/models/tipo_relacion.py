from enum import StrEnum

from sqlalchemy import BigInteger, Boolean, Identity, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from ._catalog import CatalogAuditMixin


class RelationType(StrEnum):
    """Códigos de los tipos de relación entre tickets (docs/09, 19.1).

    - `DUPLICADO` es direccional: va del ticket duplicado al principal.
    - `RELACIONADO` es simétrica: «A está relacionado con B» es lo mismo que
      «B está relacionado con A».
    """

    DUPLICADO = "DUPLICADO"
    RELACIONADO = "RELACIONADO"


class TipoRelacionTicket(CatalogAuditMixin, db.Model):
    """Catálogo de los tipos de relación entre tickets (docs/09, 19.1).

    Hoy lo cargan los datos iniciales (`seed-catalogs`): no tiene pantalla de
    administración porque los dos tipos son estructurales.
    """

    __tablename__ = "tipos_relacion_ticket"

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )

    codigo: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
    )

    nombre: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    descripcion: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # TRUE si la relación no tiene dirección (RELACIONADO).
    es_simetrica: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
