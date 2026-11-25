from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    String,
    Text,
    UniqueConstraint,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from ._modification import ModificationMixin


class StateAction(StrEnum):
    """Acciones que provocan una transición de estado (docs/09, 12.2).

    El código de la acción es el mecanismo funcional: un mismo par origen y
    destino puede existir con acciones distintas (por ejemplo, `CONFIRMAR`,
    `AUTO_CIERRE` y `CIERRE_EXCEPCIONAL` llevan de `RESUELTO` a `CERRADO`).

    Como el vocabulario de eventos del historial, vive solo en la aplicación:
    la base de datos no lo restringe. Quién puede ejecutar cada acción no se
    guarda en la tabla (docs/09: "no almacena permisos arbitrarios"): lo
    decide el código de autorización.
    """

    ASIGNAR = "ASIGNAR"
    DESASIGNACION = "DESASIGNACION"
    INICIAR = "INICIAR"
    PONER_EN_ESPERA = "PONER_EN_ESPERA"
    REACTIVAR = "REACTIVAR"
    RESOLVER = "RESOLVER"
    CIERRE_DIRECTO = "CIERRE_DIRECTO"
    CONFIRMAR = "CONFIRMAR"
    RECHAZAR = "RECHAZAR"
    AUTO_CIERRE = "AUTO_CIERRE"
    CIERRE_EXCEPCIONAL = "CIERRE_EXCEPCIONAL"
    REABRIR = "REABRIR"


# Nombre de cada acción para las pantallas de administración. Es neutro (el
# de la acción, no el del botón que ve quien la ejecuta: «Confirmar la
# solución», no «Sí, está resuelto») y, como el resto del vocabulario, vive
# solo en la aplicación.
STATE_ACTION_LABELS = {
    StateAction.ASIGNAR: "Asignar técnico",
    StateAction.DESASIGNACION: "Quitar al último técnico",
    StateAction.INICIAR: "Iniciar trabajo",
    StateAction.PONER_EN_ESPERA: "Poner en espera",
    StateAction.REACTIVAR: "Reactivar",
    StateAction.RESOLVER: "Resolver",
    StateAction.CIERRE_DIRECTO: "Cierre directo",
    StateAction.CONFIRMAR: "Confirmar la solución",
    StateAction.RECHAZAR: "Rechazar la solución",
    StateAction.AUTO_CIERRE: "Cierre automático",
    StateAction.CIERRE_EXCEPCIONAL: "Cierre excepcional",
    StateAction.REABRIR: "Reabrir",
}


class TransicionEstado(ModificationMixin, db.Model):
    """Transición habilitada entre dos de los seis estados (docs/09, 12.2).

    El conjunto de filas es el de transiciones estructuralmente válidas del
    flujo (docs/08, sección 34). `activa` permite al Administrador
    deshabilitar una, siempre dentro de ese conjunto: no se crean
    transiciones nuevas ni se rompe el ciclo de vida.
    """

    __tablename__ = "transiciones_estados"
    __table_args__ = (
        UniqueConstraint(
            "estado_origen_id",
            "estado_destino_id",
            "accion",
            name="uq_transiciones_estados_origen_destino_accion",
        ),
        CheckConstraint(
            "estado_origen_id <> estado_destino_id",
            name="ck_transiciones_estados_origen_distinto_destino",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )

    estado_origen_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("estados.id", ondelete="RESTRICT"),
        nullable=False,
    )

    estado_destino_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("estados.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Código de `StateAction`.
    accion: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    activa: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )

    descripcion: Mapped[str | None] = mapped_column(
        Text,
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

    estado_origen = relationship("Estado", foreign_keys=[estado_origen_id])
    estado_destino = relationship("Estado", foreign_keys=[estado_destino_id])
    modificada_por = relationship("User", foreign_keys=[usuario_modificacion_id])

    @property
    def accion_nombre(self) -> str:
        """Nombre visible de la acción; devuelve el código si es desconocido."""
        try:
            return STATE_ACTION_LABELS[StateAction(self.accion)]
        except ValueError:
            return self.accion
