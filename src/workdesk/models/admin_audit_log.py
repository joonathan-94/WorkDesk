from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    String,
    Text,
    event,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db


class ActorType(StrEnum):
    USUARIO = "USUARIO"
    SISTEMA = "SISTEMA"


class AuditResult(StrEnum):
    EXITOSO = "EXITOSO"
    FALLIDO = "FALLIDO"


class AuditLogImmutableError(Exception):
    """Se intentó modificar o eliminar un registro de auditoría."""


def _sql_list(codes: type[StrEnum]) -> str:
    return ", ".join(f"'{code.value}'" for code in codes)


class AdminAuditLog(db.Model):
    """Registro append-only de acciones administrativas y de seguridad.

    Los eventos puramente de autenticación quedan fuera de esta tabla
    (`eventos_autenticacion`). Ver docs/09_modelo_de_datos.md, sección 25.1.
    """

    __tablename__ = "auditoria_administrativa"
    __table_args__ = (
        CheckConstraint(
            f"actor_tipo IN ({_sql_list(ActorType)})",
            name="ck_auditoria_administrativa_actor_tipo",
        ),
        CheckConstraint(
            "(actor_tipo = 'SISTEMA' AND actor_usuario_id IS NULL) "
            "OR (actor_tipo = 'USUARIO' AND actor_usuario_id IS NOT NULL)",
            name="ck_auditoria_administrativa_actor_coherente",
        ),
        CheckConstraint(
            f"resultado IS NULL OR resultado IN ({_sql_list(AuditResult)})",
            name="ck_auditoria_administrativa_resultado",
        ),
        CheckConstraint(
            "entidad_id IS NULL OR entidad_tipo IS NOT NULL",
            name="ck_auditoria_administrativa_entidad_coherente",
        ),
        Index(
            "ix_auditoria_administrativa_fecha_hora",
            "fecha_hora",
        ),
        Index(
            "ix_auditoria_administrativa_actor_fecha",
            "actor_usuario_id",
            "fecha_hora",
        ),
        Index(
            "ix_auditoria_administrativa_entidad",
            "entidad_tipo",
            "entidad_id",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )

    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # NULL cuando la acción la ejecuta el sistema.
    actor_usuario_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=True,
    )

    actor_tipo: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # Código controlado por la aplicación (ver AuditAction).
    accion: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # Referencia lógica al objeto afectado. No es una FK porque puede
    # apuntar a tablas distintas.
    entidad_tipo: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    entidad_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    detalle: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    valor_anterior: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    valor_nuevo: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # 45 caracteres cubren la representación textual máxima de IPv6.
    ip_origen: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    resultado: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    motivo: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )


@event.listens_for(AdminAuditLog, "before_update")
@event.listens_for(AdminAuditLog, "before_delete")
def _reject_audit_log_changes(mapper, connection, target):
    # La auditoría es append-only: una corrección se registra como un
    # nuevo evento, nunca editando o borrando el original.
    raise AuditLogImmutableError(
        "Los registros de auditoría no pueden modificarse ni eliminarse."
    )
