from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from ._catalog import CatalogAuditMixin


class Grupo(CatalogAuditMixin, db.Model):
    """Grupo o cola de atención (docs/09, 10.1).

    Es opcional y solo organiza: un ticket puede crearse sin grupo y la
    pertenencia de un técnico no limita su acceso a los tickets. Los grupos
    no se eliminan, solo se desactivan (RF-117). Comparte con los catálogos
    las columnas de vigencia y trazabilidad (`CatalogAuditMixin`).
    """

    __tablename__ = "grupos"
    __table_args__ = (
        # Nombre único sin distinguir mayúsculas, como el resto de catálogos.
        Index(
            "uq_grupos_nombre_lower",
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

    fecha_desactivacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    usuario_desactivacion_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=True,
    )

    membresias = relationship(
        "UsuarioGrupo",
        back_populates="grupo",
        order_by="UsuarioGrupo.id",
    )
    designaciones = relationship(
        "GrupoSupervisor",
        back_populates="grupo",
        order_by="GrupoSupervisor.id",
    )

    @property
    def miembros_vigentes(self) -> list["UsuarioGrupo"]:
        """Membresías actuales (las que no tienen `fecha_fin`)."""
        return [m for m in self.membresias if m.fecha_fin is None]

    @property
    def supervisores_vigentes(self) -> list["GrupoSupervisor"]:
        """Supervisores responsables actuales."""
        return [d for d in self.designaciones if d.fecha_fin is None]

    def deactivate(self, actor) -> None:
        self.activo = False
        self.fecha_desactivacion = datetime.now(UTC)
        self.usuario_desactivacion_id = actor.id
        self.mark_modified(actor)

    def reactivate(self, actor) -> None:
        self.activo = True
        self.fecha_desactivacion = None
        self.usuario_desactivacion_id = None
        self.mark_modified(actor)


class UsuarioGrupo(db.Model):
    """Pertenencia temporal de un técnico a un grupo (docs/09, 10.2).

    Relación N:M con vigencia: la membresía actual es la que no tiene
    `fecha_fin`. Al retirar a alguien el registro se conserva.
    """

    __tablename__ = "usuarios_grupos"
    __table_args__ = (
        CheckConstraint(
            "fecha_fin IS NULL OR fecha_fin >= fecha_inicio",
            name="ck_usuarios_grupos_fin_posterior",
        ),
        # Nadie figura dos veces como miembro vigente del mismo grupo; sí
        # puede volver a entrar después de haber sido retirado.
        Index(
            "uq_usuarios_grupos_vigente",
            "usuario_id",
            "grupo_id",
            unique=True,
            postgresql_where=text("fecha_fin IS NULL"),
        ),
        Index("ix_usuarios_grupos_grupo_id", "grupo_id"),
        Index("ix_usuarios_grupos_usuario_id", "usuario_id"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )

    usuario_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )

    grupo_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("grupos.id", ondelete="RESTRICT"),
        nullable=False,
    )

    fecha_inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # NULL indica pertenencia vigente.
    fecha_fin: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # NULL cuando lo hizo el sistema.
    asignado_por_usuario_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=True,
    )

    retirado_por_usuario_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=True,
    )

    motivo_retiro: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    grupo = relationship("Grupo", back_populates="membresias")
    usuario = relationship("User", foreign_keys=[usuario_id])


class GrupoSupervisor(db.Model):
    """Supervisor responsable de un grupo (docs/09, 10.3).

    Un grupo puede tener varios supervisores responsables y un Supervisor
    serlo de varios grupos. Mismo patrón de vigencia que `UsuarioGrupo`.
    Solo el Administrador crea o cierra designaciones.
    """

    __tablename__ = "grupos_supervisores"
    __table_args__ = (
        CheckConstraint(
            "fecha_fin IS NULL OR fecha_fin >= fecha_inicio",
            name="ck_grupos_supervisores_fin_posterior",
        ),
        Index(
            "uq_grupos_supervisores_vigente",
            "grupo_id",
            "supervisor_id",
            unique=True,
            postgresql_where=text("fecha_fin IS NULL"),
        ),
        Index("ix_grupos_supervisores_grupo_id", "grupo_id"),
        Index("ix_grupos_supervisores_supervisor_id", "supervisor_id"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )

    grupo_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("grupos.id", ondelete="RESTRICT"),
        nullable=False,
    )

    supervisor_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )

    fecha_inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    fecha_fin: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    asignado_por_usuario_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=True,
    )

    retirado_por_usuario_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=True,
    )

    motivo_retiro: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    grupo = relationship("Grupo", back_populates="designaciones")
    supervisor = relationship("User", foreign_keys=[supervisor_id])
