"""Los eventos de autenticación (docs/09, sección 9.3; RNF-015 y RNF-022).

Un registro de **solo añadir** de cada intento de entrar y de cada salida: quién (o qué
nombre se escribió), cuándo, desde dónde, con qué resultado y, si falló, por qué. Está
separado de la auditoría administrativa a propósito: allí van las decisiones de quien
administra; aquí, el tráfico de accesos, que es mucho más numeroso y tiene su propia
retención.

**Nunca guarda contraseñas ni tokens.** El nombre escrito solo se guarda cuando el evento
no está ligado a una cuenta (no existe, o el intento se rechazó por el límite del equipo
antes de mirarla) y además tiene forma de username: alguien pudo escribir su contraseña en
ese campo por error, y una contraseña no debe quedar en un registro.
"""

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
    event,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from .admin_audit_log import AuditResult


class AuthEventType(StrEnum):
    LOGIN_EXITOSO = "LOGIN_EXITOSO"
    LOGIN_FALLIDO = "LOGIN_FALLIDO"
    # La cuenta alcanzó el límite de intentos fallidos y quedó bloqueada un tiempo.
    BLOQUEO_TEMPORAL = "BLOQUEO_TEMPORAL"
    CIERRE_SESION = "CIERRE_SESION"
    SESION_EXPIRADA = "SESION_EXPIRADA"
    # La contraseña actual no coincidió al cambiarla desde «Mi cuenta» (cuenta para el
    # mismo bloqueo que el login).
    VERIFICACION_FALLIDA = "VERIFICACION_FALLIDA"


# Los que son un intento rechazado: su `resultado` es FALLIDO.
FAILED_EVENTS = frozenset({AuthEventType.LOGIN_FALLIDO, AuthEventType.VERIFICACION_FALLIDA})


class AuthFailure(StrEnum):
    """Por qué se rechazó un intento. Es un dato interno: la persona siempre lee el mismo
    mensaje (salvo el límite por equipo, que no delata ninguna cuenta)."""

    USUARIO_DESCONOCIDO = "USUARIO_DESCONOCIDO"
    USUARIO_INACTIVO = "USUARIO_INACTIVO"
    CUENTA_BLOQUEADA = "CUENTA_BLOQUEADA"
    CONTRASENA_INCORRECTA = "CONTRASENA_INCORRECTA"
    DEMASIADOS_INTENTOS_IP = "DEMASIADOS_INTENTOS_IP"


AUTH_EVENT_LABELS: dict[AuthEventType, str] = {
    AuthEventType.LOGIN_EXITOSO: "Inicio de sesión",
    AuthEventType.LOGIN_FALLIDO: "Intento de inicio de sesión fallido",
    AuthEventType.BLOQUEO_TEMPORAL: "Cuenta bloqueada temporalmente",
    AuthEventType.CIERRE_SESION: "Cierre de sesión",
    AuthEventType.SESION_EXPIRADA: "Sesión expirada",
    AuthEventType.VERIFICACION_FALLIDA: "Contraseña actual incorrecta al cambiarla",
}

AUTH_FAILURE_LABELS: dict[AuthFailure, str] = {
    AuthFailure.USUARIO_DESCONOCIDO: "El usuario no existe",
    AuthFailure.USUARIO_INACTIVO: "La cuenta está desactivada",
    AuthFailure.CUENTA_BLOQUEADA: "La cuenta estaba bloqueada",
    AuthFailure.CONTRASENA_INCORRECTA: "Contraseña incorrecta",
    AuthFailure.DEMASIADOS_INTENTOS_IP: "Demasiados intentos fallidos desde ese equipo",
}

MAX_IDENTIFIER_LENGTH = 50
MAX_IP_LENGTH = 45
MAX_USER_AGENT_LENGTH = 255


class AuthEventImmutableError(Exception):
    """Se intentó modificar o eliminar un evento de autenticación."""


def _sql_list(codes) -> str:
    return ", ".join(f"'{code.value}'" for code in codes)


class AuthEvent(db.Model):
    __tablename__ = "eventos_autenticacion"
    __table_args__ = (
        CheckConstraint(
            f"resultado IN ({_sql_list(AuditResult)})",
            name="ck_eventos_autenticacion_resultado",
        ),
        # Un inicio de sesión correcto siempre es de una cuenta concreta.
        CheckConstraint(
            "tipo_evento <> 'LOGIN_EXITOSO' OR usuario_id IS NOT NULL",
            name="ck_eventos_autenticacion_exito_con_usuario",
        ),
        # Un rechazo dice por qué; un evento correcto, no.
        CheckConstraint(
            "(resultado = 'FALLIDO') = (detalle IS NOT NULL)",
            name="ck_eventos_autenticacion_detalle_si_falla",
        ),
        Index("ix_eventos_autenticacion_fecha_hora", "fecha_hora", "id"),
        Index("ix_eventos_autenticacion_usuario_fecha", "usuario_id", "fecha_hora"),
        # Para contar los fallos recientes desde un equipo (el límite por IP).
        Index("ix_eventos_autenticacion_ip_fecha", "ip_origen", "fecha_hora"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)

    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # NULL cuando lo escrito no corresponde a ninguna cuenta.
    usuario_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=True,
    )

    identificador_intentado: Mapped[str | None] = mapped_column(
        String(MAX_IDENTIFIER_LENGTH), nullable=True
    )

    # Código controlado por la aplicación (`AuthEventType`).
    tipo_evento: Mapped[str] = mapped_column(String(30), nullable=False)

    resultado: Mapped[str] = mapped_column(String(20), nullable=False)

    ip_origen: Mapped[str | None] = mapped_column(String(MAX_IP_LENGTH), nullable=True)

    user_agent: Mapped[str | None] = mapped_column(String(MAX_USER_AGENT_LENGTH), nullable=True)

    # Causa de un rechazo (`AuthFailure`); vacío si el evento fue correcto.
    detalle: Mapped[str | None] = mapped_column(String(30), nullable=True)

    @property
    def etiqueta(self) -> str:
        try:
            return AUTH_EVENT_LABELS[AuthEventType(self.tipo_evento)]
        except ValueError:
            return self.tipo_evento

    @property
    def causa(self) -> str | None:
        if self.detalle is None:
            return None

        try:
            return AUTH_FAILURE_LABELS[AuthFailure(self.detalle)]
        except ValueError:
            return self.detalle

    @property
    def fallido(self) -> bool:
        return self.resultado == AuditResult.FALLIDO


@event.listens_for(AuthEvent, "before_update")
@event.listens_for(AuthEvent, "before_delete")
def _reject_auth_event_changes(mapper, connection, target):
    # Como la auditoría y el historial: un registro de lo que pasó no se reescribe.
    raise AuthEventImmutableError(
        "Los eventos de autenticación no pueden modificarse ni eliminarse."
    )
