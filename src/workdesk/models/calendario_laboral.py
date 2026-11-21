from datetime import date, datetime, time

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    SmallInteger,
    String,
    Time,
    UniqueConstraint,
    func,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db


class CalendarioLaboral(db.Model):
    """Una versión del calendario laboral global (docs/09, 21.2).

    Es la cabecera de la versión: la zona horaria en la que se interpretan las
    horas y, colgando de ella, las franjas de cada día (`HorarioLaboral`) y los
    feriados (`Feriado`).

    **Una versión nunca se modifica.** Guardar un cambio crea una versión nueva y
    deja la anterior como histórica (`activo` falso), de modo que nada de lo que
    ya se calculó con una versión (los períodos de SLA, desde la entrega 4)
    cambia retroactivamente (docs/11, UI-022). Por eso no hay columnas de
    modificación: quién y cuándo la guardó es lo único que hay que recordar.

    Solo una versión está vigente a la vez (índice único parcial). Mientras no
    exista ninguna fila, el sistema usa el calendario por defecto definido en
    código (`worktime.DEMO_CALENDAR`; docs/09, 40.8).
    """

    __tablename__ = "calendarios_laborales"
    __table_args__ = (
        CheckConstraint(
            "version >= 1",
            name="ck_calendarios_laborales_version_positiva",
        ),
        UniqueConstraint(
            "version",
            name="uq_calendarios_laborales_version",
        ),
        # Como máximo una versión vigente.
        Index(
            "uq_calendarios_laborales_vigente",
            "activo",
            unique=True,
            postgresql_where=text("activo"),
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )

    # Correlativa en todo el sistema (hay un único calendario global): 1, 2, 3...
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Nombre de una zona IANA (por ejemplo `America/Santiago`).
    zona_horaria: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

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

    horarios = relationship(
        "HorarioLaboral",
        back_populates="calendario",
        order_by="HorarioLaboral.dia_semana, HorarioLaboral.hora_inicio",
    )
    feriados = relationship(
        "Feriado",
        back_populates="calendario",
        order_by="Feriado.fecha",
    )
    creado_por = relationship("User")


class HorarioLaboral(db.Model):
    """Una franja de trabajo de un día de la semana de una versión (docs/09, 21.3).

    Un día puede tener varias franjas (una pausa de almuerzo son dos) y un día
    sin ninguna no es laboral. `dia_semana` sigue ISO-8601: 1 es lunes y 7,
    domingo (el motor de `worktime.py` usa 0 para el lunes: la conversión se
    hace al cargar el calendario). Las franjas de un mismo día no pueden
    solaparse: lo comprueba el servicio antes de guardar la versión, que se
    escribe de una sola vez y no se modifica después.
    """

    __tablename__ = "horarios_laborales"
    __table_args__ = (
        CheckConstraint(
            "dia_semana BETWEEN 1 AND 7",
            name="ck_horarios_laborales_dia_semana",
        ),
        CheckConstraint(
            "hora_inicio < hora_fin",
            name="ck_horarios_laborales_inicio_antes_de_fin",
        ),
        # También sirve de índice por versión (su primera columna).
        UniqueConstraint(
            "calendario_laboral_id",
            "dia_semana",
            "hora_inicio",
            name="uq_horarios_laborales_franja",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )

    calendario_laboral_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("calendarios_laborales.id", ondelete="RESTRICT"),
        nullable=False,
    )

    dia_semana: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    hora_inicio: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )

    # No se incluye: la franja llega hasta justo antes de esta hora.
    hora_fin: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )

    calendario = relationship("CalendarioLaboral", back_populates="horarios")


class Feriado(db.Model):
    """Un día que no es laborable en una versión del calendario (docs/09, 21.4)."""

    __tablename__ = "feriados"
    __table_args__ = (
        CheckConstraint(
            "btrim(nombre) <> ''",
            name="ck_feriados_nombre_no_vacio",
        ),
        # También sirve de índice por versión (su primera columna).
        UniqueConstraint(
            "calendario_laboral_id",
            "fecha",
            name="uq_feriados_calendario_fecha",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )

    calendario_laboral_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("calendarios_laborales.id", ondelete="RESTRICT"),
        nullable=False,
    )

    fecha: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    nombre: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    calendario = relationship("CalendarioLaboral", back_populates="feriados")
