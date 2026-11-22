from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db


class PeriodoSla(db.Model):
    """Un tramo de la vida de un ticket bajo unas condiciones de SLA (docs/09, 20.3).

    Es el **snapshot** de lo que se aplicó al ticket: copia los objetivos de la
    política de su prioridad, así que editar la política después no cambia lo que
    ya se calculó. Cuando cambian las condiciones (la prioridad, el estado del
    ticket) el período vigente se cierra y se abre otro; nunca se sobrescribe uno
    cerrado.

    El cierre de un período **no reinicia el reloj**: `segundos_consumidos` es lo
    que se consumió *dentro de este período* (en tiempo laboral) y el consumo del
    ticket es la suma de todos sus períodos. El vencimiento del período siguiente
    se calcula con lo que quede del objetivo.

    Un período **pausado** (el ticket está en espera y la política pausa) es un
    período abierto sin `fecha_vencimiento_resolucion`: no consume tiempo y no
    vence. No hay una columna de pausa porque ese vacío ya lo dice.

    Se aparta de docs/09 en una columna: `calendario_laboral_id` admite NULL. Es la
    versión del calendario con que se calculó, y NULL significa que se usó el
    calendario por defecto, que mientras el Administrador no guarda ninguno no
    tiene fila (docs/09, 40.8).
    """

    __tablename__ = "tickets_sla_periodos"
    __table_args__ = (
        CheckConstraint(
            "fecha_fin IS NULL OR fecha_fin >= fecha_inicio",
            name="ck_tickets_sla_periodos_fin_desde_inicio",
        ),
        CheckConstraint(
            "segundos_consumidos >= 0",
            name="ck_tickets_sla_periodos_consumo_no_negativo",
        ),
        CheckConstraint(
            "tiempo_objetivo_resolucion_minutos > 0",
            name="ck_tickets_sla_periodos_resolucion_positiva",
        ),
        CheckConstraint(
            "tiempo_objetivo_respuesta_minutos IS NULL "
            "OR tiempo_objetivo_respuesta_minutos > 0",
            name="ck_tickets_sla_periodos_respuesta_positiva",
        ),
        CheckConstraint(
            "umbral_aviso_porcentaje IS NULL "
            "OR (umbral_aviso_porcentaje >= 1 AND umbral_aviso_porcentaje <= 100)",
            name="ck_tickets_sla_periodos_umbral_aviso",
        ),
        # La fecha de aviso solo existe con el reloj en marcha y cae entre el inicio y el
        # vencimiento.
        CheckConstraint(
            "fecha_umbral_aviso IS NULL OR ("
            "fecha_vencimiento_resolucion IS NOT NULL "
            "AND fecha_umbral_aviso >= fecha_inicio "
            "AND fecha_umbral_aviso <= fecha_vencimiento_resolucion)",
            name="ck_tickets_sla_periodos_fecha_umbral_aviso",
        ),
        # Un ticket tiene como máximo un período vigente (sin fecha de fin).
        Index(
            "uq_tickets_sla_periodos_vigente",
            "ticket_id",
            unique=True,
            postgresql_where=text("fecha_fin IS NULL"),
        ),
        # El historial de un ticket, en orden.
        Index("ix_tickets_sla_periodos_ticket_inicio", "ticket_id", "fecha_inicio"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )

    ticket_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tickets.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # La política de la que salen los objetivos. NULL no ocurre hoy, pero el
    # diseño lo prevé para períodos sin política de origen.
    politica_sla_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("politicas_sla.id", ondelete="RESTRICT"),
        nullable=True,
    )

    prioridad_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("prioridades.id", ondelete="RESTRICT"),
        nullable=False,
    )

    calendario_laboral_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("calendarios_laborales.id", ondelete="RESTRICT"),
        nullable=True,
    )

    tiempo_objetivo_respuesta_minutos: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    tiempo_objetivo_resolucion_minutos: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    pausa_en_espera: Mapped[bool] = mapped_column(
        nullable=False,
    )

    fecha_inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # NULL mientras el período está vigente.
    fecha_fin: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Segundos laborales consumidos dentro de este período. Se fija al cerrarlo
    # (0 si estuvo pausado); mientras está vigente se calcula al consultarlo.
    segundos_consumidos: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    fecha_vencimiento_respuesta: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # NULL significa «pausado» (el reloj no corre).
    fecha_vencimiento_resolucion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # El umbral de aviso con que se abrió el período (copia del de la política, como
    # los objetivos) y el momento en que el consumo lo alcanza, calculado en tiempo
    # laboral al abrirlo. Es lo que permite filtrar y ordenar por «próximo a vencer»
    # en la base de datos. NULL sin umbral, o con el período pausado.
    umbral_aviso_porcentaje: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    fecha_umbral_aviso: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Cuándo el planificador avisó de que el consumo alcanzó el umbral y de que el
    # ticket venció (`run-scheduler`). Son la marca de idempotencia: un aviso se
    # envía una sola vez. Un período nuevo con la misma prioridad las hereda (el
    # consumo nunca baja, así que no se vuelve a avisar de lo mismo); un cambio de
    # prioridad abre un SLA distinto y empieza sin ellas.
    fecha_aviso_umbral_enviado: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    fecha_aviso_vencimiento_enviado: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Quién provocó el cambio que abrió este período (el que cambió la prioridad
    # o el estado) y por qué. NULL en el período que abre la creación del ticket.
    usuario_cambio_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=True,
    )

    motivo_cambio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    @property
    def esta_vigente(self) -> bool:
        return self.fecha_fin is None

    @property
    def esta_pausado(self) -> bool:
        """Vigente y sin vencimiento: el reloj no corre."""
        return self.fecha_fin is None and self.fecha_vencimiento_resolucion is None
