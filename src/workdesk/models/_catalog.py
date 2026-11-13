from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, func, true
from sqlalchemy.orm import Mapped, mapped_column


class CatalogAuditMixin:
    """Columnas de vigencia y trazabilidad comunes a los catálogos editables.

    `activo` solo impide elegir el valor en operaciones nuevas: los tickets
    históricos que ya lo referencian no se ven afectados (docs/09, 13.2).
    Los datos cargados por seed no tienen creador (`usuario_creacion_id` NULL).
    """

    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )

    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    usuario_creacion_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=True,
    )

    fecha_modificacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    usuario_modificacion_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=True,
    )
