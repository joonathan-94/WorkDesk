from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Identity,
    Index,
    Integer,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from ._catalog import CatalogAuditMixin


class PoliticaSla(CatalogAuditMixin, db.Model):
    """Objetivos de SLA de una prioridad (docs/09, 20.2).

    Es la **configuración vigente**: el Administrador la edita en el sitio y lo
    que ya se calculó no cambia, porque cada ticket guarda su propia copia de los
    objetivos en el período de SLA que abre (docs/09, 20.1 y 20.3: desde la
    entrega 4). Por eso editar una política no necesita versiones.

    El MVP tiene **una política por prioridad**: el servicio nunca crea una
    segunda fila para la misma prioridad (activa o no) y el índice único parcial
    impide dos activas. Desactivarla significa que esa prioridad no tiene SLA; se
    puede reactivar con los objetivos que tenía.

    Los tiempos son **minutos laborales**: se miden con el calendario vigente
    (`worktime.py`), no con el reloj de pared.

    Se omiten dos columnas de docs/09, 20.2:

    - `calendario_laboral_id`: el calendario es global y versionado (docs/09,
      21), así que una política que apuntara a una versión se quedaría con la
      antigua en cuanto se guardara otra. Cada período de SLA guarda la versión
      con la que se calculó.
    - `nombre`: hay una política por prioridad y su nombre sería el de la
      prioridad; copiarlo daría dos fuentes de verdad al renombrarla.
    """

    __tablename__ = "politicas_sla"
    __table_args__ = (
        CheckConstraint(
            "tiempo_objetivo_resolucion_minutos > 0",
            name="ck_politicas_sla_resolucion_positiva",
        ),
        CheckConstraint(
            "tiempo_objetivo_respuesta_minutos IS NULL "
            "OR tiempo_objetivo_respuesta_minutos > 0",
            name="ck_politicas_sla_respuesta_positiva",
        ),
        # La primera respuesta no puede tardar más que la resolución completa.
        CheckConstraint(
            "tiempo_objetivo_respuesta_minutos IS NULL "
            "OR tiempo_objetivo_respuesta_minutos "
            "<= tiempo_objetivo_resolucion_minutos",
            name="ck_politicas_sla_respuesta_dentro_de_resolucion",
        ),
        CheckConstraint(
            "umbral_aviso_consumo_porcentaje IS NULL "
            "OR umbral_aviso_consumo_porcentaje BETWEEN 1 AND 100",
            name="ck_politicas_sla_umbral_rango",
        ),
        # Como máximo una política activa por prioridad.
        Index(
            "uq_politicas_sla_prioridad_vigente",
            "prioridad_id",
            unique=True,
            postgresql_where=text("activo"),
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )

    prioridad_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("prioridades.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Opcional: sin valor, la política no tiene objetivo de primera respuesta.
    tiempo_objetivo_respuesta_minutos: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    tiempo_objetivo_resolucion_minutos: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Si el reloj se detiene mientras el ticket está en espera.
    pausa_en_espera: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )

    # Porcentaje del tiempo objetivo consumido a partir del cual el ticket pasa a
    # «próximo a vencer». Sin valor, no hay aviso previo al vencimiento.
    umbral_aviso_consumo_porcentaje: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    prioridad = relationship("Prioridad")
