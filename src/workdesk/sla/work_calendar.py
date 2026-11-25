"""Calendario laboral administrable (docs/09, 21 y 40.8; docs/11, UI-022).

El calendario laboral dice qué días y a qué horas corre el reloj del SLA. Es
global y está **versionado**, y estas son las reglas que lo gobiernan:

- **Siempre hay un calendario.** Mientras el Administrador no haya guardado
  ninguno, el sistema usa el predeterminado definido en código (`DEMO_CALENDAR`,
  en la zona de `APP_TIMEZONE`). El primer guardado crea la versión 1 y desde
  entonces todo el sistema usa lo guardado. `resolve_work_calendar` es la única
  función que decide cuál es el vigente, así que el SLA, los datos de
  demostración y las pantallas leen siempre de la misma fuente.
- **Guardar nunca modifica una versión:** crea la siguiente y deja la anterior
  como histórica. Así lo que ya se calculó con una versión no cambia
  retroactivamente (el SLA guardará la versión que usó en cada período).
- **Quien guarda dice con qué versión abrió la pantalla** (`base_version`, 0 si
  no había ninguna). Si mientras tanto otra persona guardó, no se guarda nada y
  se avisa, igual que con la versión de un ticket: pisar un cambio que no se vio
  no es una opción. Dos guardados simultáneos se resuelven con la fila vigente
  bloqueada y, cuando todavía no hay ninguna, con los índices únicos.
- **Guardar sin cambios no crea una versión.**

Ninguna función hace commit: la versión nueva y su evento de auditoría se
confirman o se revierten juntos, y el commit lo realiza quien llama.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from functools import cache
from zoneinfo import ZoneInfo, available_timezones

from flask import current_app
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload

from ..audit import AuditAction, record_admin_event
from ..cleaning import blank_to_none, clean_optional_reason
from ..extensions import db
from ..formatting import app_zone
from ..models import CalendarioLaboral, Feriado, HorarioLaboral, User
from ..worktime import (
    DEMO_CALENDAR,
    WEEKDAY_NAMES,
    BusinessClock,
    Franja,
    parse_time,
    schedule_problems,
)

MAX_HOLIDAY_NAME_LENGTH = 100

CONFLICT_MESSAGE = (
    "Otra persona guardó el calendario mientras lo editabas. Revisa los valores "
    "vigentes y vuelve a intentarlo."
)
NOTHING_TO_SAVE_MESSAGE = "No hay cambios que guardar."


class CalendarRuleError(ValueError):
    """Una regla impide guardar el calendario. El mensaje se muestra a quien lo edita."""


class CalendarConflictError(CalendarRuleError):
    """Otra persona guardó una versión mientras esta pantalla estaba abierta."""


class NothingToChangeError(CalendarRuleError):
    """Lo que se quiere guardar es idéntico al calendario vigente."""


@dataclass(frozen=True)
class Holiday:
    """Un feriado: la fecha y cómo se llama."""

    fecha: date
    nombre: str


@dataclass(frozen=True)
class ScheduleLine:
    """Una línea del resumen del horario: «Lunes a viernes» y «09:00–18:00»."""

    days: str
    hours: str


@dataclass(frozen=True)
class ResolvedCalendar:
    """El calendario vigente, listo para usar.

    `clock` es el reloj que mide y avanza en tiempo laboral. `record` es la
    versión guardada de la que sale, o `None` si todavía no se guardó ninguna y
    se usa el calendario por defecto.
    """

    clock: BusinessClock
    zone_name: str
    record: CalendarioLaboral | None

    @property
    def is_default(self) -> bool:
        return self.record is None

    @property
    def version(self) -> int:
        """La versión vigente; 0 si no hay ninguna guardada."""
        return 0 if self.record is None else self.record.version


@dataclass(frozen=True)
class CalendarView:
    """Lo que las pantallas muestran de un calendario, guardado o por defecto."""

    version: int
    zone_name: str
    franjas: tuple[Franja, ...]
    holidays: tuple[Holiday, ...]
    saved_by: User | None
    saved_at: datetime | None

    @property
    def is_default(self) -> bool:
        return self.version == 0

    @property
    def schedule(self) -> list[ScheduleLine]:
        return describe_schedule(self.franjas)

    @property
    def summary(self) -> str:
        return summarize(self.schedule)


@dataclass(frozen=True)
class CalendarVersion:
    """Una fila del historial de versiones."""

    record: CalendarioLaboral
    summary: str
    holiday_count: int


# --- Consultas --------------------------------------------------------------


@cache
def available_zone_names() -> frozenset[str]:
    """Los nombres de zona horaria válidos (se calculan una vez: recorrer la base
    de zonas no es barato)."""
    return frozenset(available_timezones())


def get_active_calendar() -> CalendarioLaboral | None:
    """La versión vigente con sus franjas y feriados, o `None` si nunca se guardó."""
    return db.session.scalar(
        db.select(CalendarioLaboral)
        .where(CalendarioLaboral.activo.is_(True))
        .options(
            selectinload(CalendarioLaboral.horarios),
            selectinload(CalendarioLaboral.feriados),
            joinedload(CalendarioLaboral.creado_por),
        )
    )


def list_calendar_versions() -> list[CalendarVersion]:
    """Todas las versiones guardadas, de la más reciente a la más antigua."""
    records = db.session.scalars(
        db.select(CalendarioLaboral)
        .order_by(CalendarioLaboral.version.desc())
        .options(
            selectinload(CalendarioLaboral.horarios),
            selectinload(CalendarioLaboral.feriados),
            joinedload(CalendarioLaboral.creado_por),
        )
    )

    return [
        CalendarVersion(
            record=record,
            summary=summarize(describe_schedule(franjas_of(record))),
            holiday_count=len(record.feriados),
        )
        for record in records
    ]


def resolve_work_calendar() -> ResolvedCalendar:
    """El calendario vigente: el guardado o, si no hay ninguno, el predeterminado.

    Es la única función que decide cuál es (docs/09, 40.8).
    """
    record = get_active_calendar()

    if record is None:
        zone = app_zone()

        return ResolvedCalendar(
            clock=BusinessClock(DEMO_CALENDAR, zone),
            zone_name=current_app.config["APP_TIMEZONE"],
            record=None,
        )

    return ResolvedCalendar(
        clock=clock_for(record), zone_name=record.zona_horaria, record=record
    )


def clock_for(record: CalendarioLaboral) -> BusinessClock:
    """El reloj de una versión concreta del calendario (vigente o histórica)."""
    return BusinessClock.from_schedule(
        franjas_of(record),
        [holiday.fecha for holiday in holidays_of(record)],
        ZoneInfo(record.zona_horaria),
    )


def franjas_of(record: CalendarioLaboral) -> tuple[Franja, ...]:
    """Las franjas de una versión en el formato del motor (0 = lunes)."""
    return tuple(
        Franja(row.dia_semana - 1, row.hora_inicio, row.hora_fin)
        for row in record.horarios
    )


def holidays_of(record: CalendarioLaboral) -> tuple[Holiday, ...]:
    return tuple(Holiday(row.fecha, row.nombre) for row in record.feriados)


def default_franjas() -> tuple[Franja, ...]:
    """Las franjas del calendario por defecto."""
    inicio, fin = parse_time(DEMO_CALENDAR.inicio), parse_time(DEMO_CALENDAR.fin)

    return tuple(Franja(day, inicio, fin) for day in DEMO_CALENDAR.dias)


def describe_calendar(resolved: ResolvedCalendar) -> CalendarView:
    """Lo que las pantallas muestran del calendario vigente."""
    record = resolved.record

    if record is None:
        return CalendarView(
            version=0,
            zone_name=resolved.zone_name,
            franjas=default_franjas(),
            holidays=tuple(Holiday(day, "Feriado") for day in DEMO_CALENDAR.feriados),
            saved_by=None,
            saved_at=None,
        )

    return CalendarView(
        version=record.version,
        zone_name=record.zona_horaria,
        franjas=franjas_of(record),
        holidays=holidays_of(record),
        saved_by=record.creado_por,
        saved_at=record.fecha_creacion,
    )


# --- Descripción del horario -------------------------------------------------


def describe_schedule(franjas: Iterable[Franja]) -> list[ScheduleLine]:
    """Resume un horario agrupando los días seguidos que comparten horas.

    Por ejemplo: «Lunes a jueves · 09:00–18:00» y «Viernes · 09:00–17:00».
    """
    by_day: dict[int, list[Franja]] = {}

    for franja in sorted(franjas, key=lambda slot: (slot.dia, slot.inicio)):
        by_day.setdefault(franja.dia, []).append(franja)

    hours = {
        day: " y ".join(f"{slot.inicio:%H:%M}–{slot.fin:%H:%M}" for slot in slots)
        for day, slots in by_day.items()
    }

    lines: list[ScheduleLine] = []
    run: list[int] = []

    for day in sorted(hours):
        if run and day == run[-1] + 1 and hours[day] == hours[run[0]]:
            run.append(day)
            continue

        if run:
            lines.append(_schedule_line(run, hours))

        run = [day]

    if run:
        lines.append(_schedule_line(run, hours))

    return lines


def summarize(lines: Sequence[ScheduleLine]) -> str:
    """El horario en una sola línea (la que se muestra en listados y resúmenes)."""
    if not lines:
        return "Sin días laborales"

    return " · ".join(f"{line.days} {line.hours}" for line in lines)


def _schedule_line(run: list[int], hours: dict[int, str]) -> ScheduleLine:
    first, last = WEEKDAY_NAMES[run[0]].capitalize(), WEEKDAY_NAMES[run[-1]]

    if len(run) == 1:
        days = first
    elif len(run) == 2:
        days = f"{first} y {last}"
    else:
        days = f"{first} a {last}"

    return ScheduleLine(days=days, hours=hours[run[0]])


# --- Guardar -------------------------------------------------------------------


def save_work_calendar(
    *,
    actor: User,
    base_version: int,
    zone_name: str,
    franjas: Sequence[Franja],
    holidays: Sequence[Holiday],
    reason: str | None = None,
) -> CalendarioLaboral:
    """Guarda una versión nueva del calendario y la deja vigente.

    `base_version` es la versión con la que se abrió la pantalla (0 si no había
    ninguna guardada). Lanza `CalendarConflictError` si otra persona guardó
    mientras tanto, `NothingToChangeError` si no hay nada que guardar y
    `CalendarRuleError` si los datos no son válidos; en ningún caso queda nada
    pendiente. Registra `CALENDARIO_LABORAL_GUARDADO`. No hace commit.
    """
    if not actor.is_active:
        raise CalendarRuleError("El usuario no está activo.")

    zone_name = _clean_zone_name(zone_name)
    holidays = _clean_holidays(holidays)
    reason = clean_optional_reason(reason, CalendarRuleError)
    problems = schedule_problems(franjas, [holiday.fecha for holiday in holidays])

    if problems:
        raise CalendarRuleError(problems[0])

    # Se bloquea la versión vigente para que dos guardados simultáneos se
    # sucedan en lugar de pisarse: el segundo ya no la encuentra vigente.
    current = db.session.scalar(
        db.select(CalendarioLaboral)
        .where(CalendarioLaboral.activo.is_(True))
        .with_for_update()
    )
    current_version = 0 if current is None else current.version

    if current_version != base_version:
        raise CalendarConflictError(CONFLICT_MESSAGE)

    new_content = _snapshot(zone_name, franjas, holidays)

    if current is None:
        old_content = _snapshot(
            current_app.config["APP_TIMEZONE"], default_franjas(), ()
        )
    else:
        old_content = _snapshot(
            current.zona_horaria, franjas_of(current), holidays_of(current)
        )

        if old_content == new_content:
            raise NothingToChangeError(NOTHING_TO_SAVE_MESSAGE)

    version = CalendarioLaboral(
        version=current_version + 1,
        zona_horaria=zone_name,
        usuario_creacion_id=actor.id,
    )
    version.horarios = [
        HorarioLaboral(
            dia_semana=franja.dia + 1,
            hora_inicio=franja.inicio,
            hora_fin=franja.fin,
        )
        for franja in franjas
    ]
    version.feriados = [
        Feriado(fecha=holiday.fecha, nombre=holiday.nombre) for holiday in holidays
    ]

    try:
        with db.session.begin_nested():
            if current is not None:
                # Primero se libera el lugar de «versión vigente»: el índice
                # único no admite dos a la vez.
                current.activo = False
                db.session.flush()

            db.session.add(version)
            db.session.flush()
    except IntegrityError as error:
        # Todavía no había ninguna versión y dos personas guardaron la primera a
        # la vez: gana la restricción única y la otra se entera.
        raise CalendarConflictError(CONFLICT_MESSAGE) from error

    changed = [key for key in new_content if old_content[key] != new_content[key]]

    record_admin_event(
        AuditAction.CALENDARIO_LABORAL_GUARDADO,
        actor=actor,
        entity_type="calendario_laboral",
        entity_id=version.id,
        detail=f"Versión {version.version}",
        old_value={
            "version": current_version or None,
            **{key: old_content[key] for key in changed},
        },
        new_value={
            "version": version.version,
            **{key: new_content[key] for key in changed},
        },
        reason=reason,
    )

    return version


def _snapshot(
    zone_name: str, franjas: Iterable[Franja], holidays: Iterable[Holiday]
) -> dict:
    """El contenido de una versión en un formato que se puede comparar y auditar."""
    schedule: dict[str, str] = {}

    for franja in sorted(franjas, key=lambda slot: (slot.dia, slot.inicio)):
        name = WEEKDAY_NAMES[franja.dia]
        hours = f"{franja.inicio:%H:%M}-{franja.fin:%H:%M}"
        schedule[name] = f"{schedule[name]}, {hours}" if name in schedule else hours

    return {
        "zona_horaria": zone_name,
        "horario": schedule,
        "feriados": [
            {"fecha": holiday.fecha.isoformat(), "nombre": holiday.nombre}
            for holiday in sorted(holidays, key=lambda item: item.fecha)
        ],
    }


def _clean_zone_name(zone_name: str | None) -> str:
    zone_name = (zone_name or "").strip()

    if zone_name not in available_zone_names():
        raise CalendarRuleError(f"La zona horaria «{zone_name}» no existe.")

    return zone_name


def _clean_holidays(holidays: Sequence[Holiday]) -> list[Holiday]:
    """Recorta los nombres, rechaza los vacíos y repetidos, y ordena por fecha."""
    seen: set[date] = set()
    cleaned: list[Holiday] = []

    for holiday in holidays:
        name = blank_to_none(holiday.nombre)

        if name is None:
            raise CalendarRuleError("Todos los feriados necesitan un nombre.")

        if len(name) > MAX_HOLIDAY_NAME_LENGTH:
            raise CalendarRuleError(
                f"El nombre de un feriado no puede superar los "
                f"{MAX_HOLIDAY_NAME_LENGTH} caracteres."
            )

        if holiday.fecha in seen:
            raise CalendarRuleError(
                f"El feriado del {holiday.fecha:%d-%m-%Y} está repetido."
            )

        seen.add(holiday.fecha)
        cleaned.append(Holiday(holiday.fecha, name))

    return sorted(cleaned, key=lambda item: item.fecha)
