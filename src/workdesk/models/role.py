from sqlalchemy import BigInteger, Identity, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db


class Role(db.Model):
    __tablename__ = "roles"

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