from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db


class ConfigDataType(StrEnum):
    """Cómo se interpreta el texto guardado en `valor` (docs/09, 26.1).

    Hoy solo hay parámetros enteros; el resto del vocabulario existe para que añadir un
    interruptor o un texto no necesite cambiar la restricción de la base de datos.
    """

    TEXTO = "TEXTO"
    ENTERO = "ENTERO"
    BOOLEANO = "BOOLEANO"
    DECIMAL = "DECIMAL"
    JSON = "JSON"


class Configuracion(db.Model):
    """Un parámetro administrable cuyo valor reemplaza al inicial (docs/09, 26.1).

    **Una fila es un valor elegido por el Administrador; sin fila, rige el valor inicial**
    (la variable de entorno o el valor por defecto de `settings.py`). Así la aplicación
    arranca sin cargar nada y «volver al valor inicial» es borrar la fila. No hay campo
    `activo`: la configuración vigente es el valor actual de la clave, y el historial de
    cambios está en la auditoría administrativa.

    Las definiciones (qué claves existen, su rango y su valor por defecto) no están en la
    base de datos sino en `settings.py`: una fila con una clave que el código no conoce se
    ignora, y un valor guardado que ya no es válido se descarta con un aviso en el log.
    """

    __tablename__ = "configuracion"
    __table_args__ = (
        CheckConstraint(
            "tipo_dato IN ('TEXTO', 'ENTERO', 'BOOLEANO', 'DECIMAL', 'JSON')",
            name="ck_configuracion_tipo_dato",
        ),
        CheckConstraint(
            "length(btrim(clave)) > 0",
            name="ck_configuracion_clave_no_vacia",
        ),
        CheckConstraint(
            "length(btrim(valor)) > 0",
            name="ck_configuracion_valor_no_vacio",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )

    # Identificador del parámetro (`sesion.inactividad_minutos`). Único.
    clave: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    # El valor serializado como texto; `tipo_dato` dice cómo leerlo.
    valor: Mapped[str] = mapped_column(Text, nullable=False)

    tipo_dato: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ConfigDataType.ENTERO.value,
    )

    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Agrupación funcional: el primer tramo de la clave (`sesion`, `archivos`...).
    categoria: Mapped[str | None] = mapped_column(String(50), nullable=True)

    fecha_modificacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    usuario_modificacion_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=True,
    )
