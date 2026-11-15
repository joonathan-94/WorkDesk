from sqlalchemy import (
    BigInteger,
    Boolean,
    Identity,
    Index,
    Integer,
    String,
    Text,
    false,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from ._catalog import CatalogAuditMixin


class MotivoEspera(CatalogAuditMixin, db.Model):
    """Motivo opcional con el que un ticket pasa a `En espera` (docs/09, 12.3).

    Es un catálogo configurable: entrar a `En espera` no exige motivo, y
    cuando se usa uno queda en el historial del evento. No hay una columna
    `motivo_espera_id` en `tickets`, porque un ticket puede atravesar varias
    esperas: el motivo vigente se obtiene del último evento de entrada a
    `En espera`.
    """

    __tablename__ = "motivos_espera"
    __table_args__ = (
        # Nombre único sin distinguir mayúsculas, como el resto de catálogos.
        Index(
            "uq_motivos_espera_nombre_lower",
            text("lower(nombre)"),
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )

    # Solo los motivos cargados por seed tienen código; los creados desde la
    # interfaz no, igual que las categorías.
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

    # Si es True, al elegir este motivo se puede añadir un texto libre (la
    # opción genérica "Otro motivo").
    permite_texto_otro: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )

    # No figura en docs/09 12.3, pero hace falta para que la opción genérica
    # vaya siempre al final del desplegable (docs/09 12.4 lo define para los
    # motivos de cierre).
    orden: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
