"""Formulario del calendario laboral (docs/11, UI-022).

Valida la *forma* de lo que escribe el Administrador y la convierte en datos:

- cada día de la semana es un texto con sus franjas: «09:00-18:00», o
  «09:00-13:00, 14:00-18:00» si hay una pausa; vacío significa que ese día no
  se trabaja;
- los feriados son un texto con uno por línea: «25-12-2026 Navidad».

Un texto es más compacto que filas dinámicas, funciona sin JavaScript y admite
varias franjas por día, que es lo que permite el modelo (docs/09, 21.3). Las
reglas del calendario (conflicto de versión, nada que guardar) las aplica
`sla.work_calendar`; aquí solo se dice qué está mal escrito y dónde.
"""

import re
from collections.abc import Iterable
from datetime import date, time
from itertools import pairwise

from wtforms import StringField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, ValidationError

from ..catalogs.forms import OptionalIntegerField
from ..cleaning import strip_text
from ..users.forms import ReasonForm
from ..worktime import WEEKDAY_NAMES, Franja
from .work_calendar import (
    MAX_HOLIDAY_NAME_LENGTH,
    CalendarView,
    Holiday,
    available_zone_names,
)

MAX_ZONE_LENGTH = 64
MAX_DAY_TEXT_LENGTH = 200
MAX_HOLIDAYS_TEXT_LENGTH = 20000

# Un error de tipeo en el año (25-12-26, 25-12-2062) se detecta con un rango
# razonable.
MIN_HOLIDAY_YEAR = 2000
MAX_HOLIDAY_YEAR = 2100

# Con más problemas que estos se avisa cuántos más hay, para no tapar la
# pantalla.
MAX_REPORTED_PROBLEMS = 8

_RANGE = re.compile(r"(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})")
_DAY_FIRST = re.compile(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})")
_YEAR_FIRST = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


class HolidayErrors(ValueError):
    """Los feriados escritos tienen problemas; `messages` dice cuáles, por línea."""

    def __init__(self, messages: list[str]) -> None:
        super().__init__(" ".join(messages))
        self.messages = messages


# --- Los días: de texto a franjas y de franjas a texto ---------------------------


def parse_day(text: str | None) -> list[tuple[time, time]]:
    """Las franjas de un día escritas como «09:00-13:00, 14:00-18:00».

    Un texto vacío es un día sin trabajo. Devuelve las franjas ordenadas y lanza
    `ValueError` con el mensaje para mostrar si algo está mal escrito, una franja
    termina antes de empezar o dos se solapan.
    """
    slots: list[tuple[time, time]] = []

    for part in re.split(r"[,;]", text or ""):
        part = part.strip()

        if not part:
            continue

        match = _RANGE.fullmatch(part)

        if match is None:
            raise ValueError(
                f"«{part}» no tiene el formato HH:MM-HH:MM (por ejemplo, 09:00-18:00)."
            )

        start_hour, start_minute, end_hour, end_minute = (
            int(group) for group in match.groups()
        )

        try:
            start, end = time(start_hour, start_minute), time(end_hour, end_minute)
        except ValueError as error:
            raise ValueError(f"«{part}» tiene una hora que no existe.") from error

        if start >= end:
            raise ValueError(f"En «{part}», el inicio debe ser anterior al fin.")

        slots.append((start, end))

    slots.sort()

    for first, second in pairwise(slots):
        if first[1] > second[0]:
            raise ValueError(
                f"Las franjas «{_slot_text(first)}» y «{_slot_text(second)}» "
                "se solapan."
            )

    return slots


def format_day(slots: Iterable[tuple[time, time]]) -> str:
    """Las franjas de un día como se escriben en el formulario."""
    return ", ".join(_slot_text(slot) for slot in sorted(slots))


def _slot_text(slot: tuple[time, time]) -> str:
    return f"{slot[0]:%H:%M}-{slot[1]:%H:%M}"


# --- Los feriados: de texto a lista y de lista a texto ---------------------------


def parse_holidays(text: str | None) -> list[Holiday]:
    """Los feriados escritos uno por línea, como «25-12-2026 Navidad».

    Acepta la fecha como día-mes-año (con guiones o barras) o año-mes-día, y exige
    un nombre. Las líneas vacías se ignoran. Lanza `HolidayErrors` con un mensaje
    por línea con problemas.
    """
    holidays: list[Holiday] = []
    first_line: dict[date, int] = {}
    problems: list[str] = []

    for number, raw in enumerate((text or "").splitlines(), start=1):
        parts = raw.split(None, 1)

        if not parts:
            continue

        token = parts[0]
        name = parts[1].strip() if len(parts) > 1 else ""

        try:
            day = _parse_date(token)
        except ValueError:
            problems.append(
                f"Línea {number}: «{token}» no es una fecha válida "
                "(por ejemplo, 25-12-2026)."
            )
            continue

        if not MIN_HOLIDAY_YEAR <= day.year <= MAX_HOLIDAY_YEAR:
            problems.append(
                f"Línea {number}: el año debe estar entre {MIN_HOLIDAY_YEAR} "
                f"y {MAX_HOLIDAY_YEAR}."
            )
        elif not name:
            problems.append(f"Línea {number}: falta el nombre del feriado.")
        elif len(name) > MAX_HOLIDAY_NAME_LENGTH:
            problems.append(
                f"Línea {number}: el nombre no puede superar los "
                f"{MAX_HOLIDAY_NAME_LENGTH} caracteres."
            )
        elif day in first_line:
            problems.append(
                f"Línea {number}: el {day:%d-%m-%Y} ya está en la línea "
                f"{first_line[day]}."
            )
        else:
            first_line[day] = number
            holidays.append(Holiday(day, name))

    if problems:
        if len(problems) > MAX_REPORTED_PROBLEMS:
            hidden = len(problems) - MAX_REPORTED_PROBLEMS
            problems = [
                *problems[:MAX_REPORTED_PROBLEMS],
                f"Y {hidden} líneas más con problemas.",
            ]

        raise HolidayErrors(problems)

    return holidays


def format_holidays(holidays: Iterable[Holiday]) -> str:
    """Los feriados como se escriben en el formulario, uno por línea."""
    return "\n".join(
        f"{holiday.fecha:%d-%m-%Y} {holiday.nombre}"
        for holiday in sorted(holidays, key=lambda item: item.fecha)
    )


def _parse_date(token: str) -> date:
    if match := _DAY_FIRST.fullmatch(token):
        day, month, year = (int(group) for group in match.groups())
    elif match := _YEAR_FIRST.fullmatch(token):
        year, month, day = (int(group) for group in match.groups())
    else:
        raise ValueError(token)

    return date(year, month, day)


# --- El formulario ------------------------------------------------------------------


def _day_field(number: int) -> StringField:
    return StringField(
        WEEKDAY_NAMES[number].capitalize(),
        filters=[strip_text],
        validators=[
            Optional(),
            Length(
                max=MAX_DAY_TEXT_LENGTH,
                message=f"Máximo {MAX_DAY_TEXT_LENGTH} caracteres.",
            ),
        ],
    )


class WorkCalendarForm(ReasonForm):
    """El calendario laboral completo: zona horaria, horario de cada día y feriados.

    Hereda el motivo opcional de `ReasonForm`. Tras validar, `franjas` y
    `holidays` tienen los datos ya convertidos y `general_errors` los problemas
    que no pertenecen a un campo (por ejemplo, ningún día laboral).
    """

    zona_horaria = StringField(
        "Zona horaria",
        filters=[strip_text],
        validators=[
            DataRequired(message="Ingresa la zona horaria."),
            Length(
                max=MAX_ZONE_LENGTH,
                message=f"Máximo {MAX_ZONE_LENGTH} caracteres.",
            ),
        ],
    )

    dia_0 = _day_field(0)
    dia_1 = _day_field(1)
    dia_2 = _day_field(2)
    dia_3 = _day_field(3)
    dia_4 = _day_field(4)
    dia_5 = _day_field(5)
    dia_6 = _day_field(6)

    feriados = TextAreaField(
        "Feriados",
        validators=[
            Optional(),
            Length(
                max=MAX_HOLIDAYS_TEXT_LENGTH,
                message=f"Máximo {MAX_HOLIDAYS_TEXT_LENGTH} caracteres.",
            ),
        ],
    )

    # La versión con la que se abrió la pantalla (0 si no había ninguna guardada):
    # sin ella no se puede comprobar que nadie más haya guardado mientras tanto.
    version_base = OptionalIntegerField("Versión")

    def validate_zona_horaria(self, field):
        if field.data not in available_zone_names():
            raise ValidationError(f"La zona horaria «{field.data}» no existe.")

    def validate_version_base(self, field):
        if field.data is None or field.data < 0:
            raise ValidationError(
                "No se pudo comprobar la versión del calendario. Recarga la página."
            )

    def day_fields(self) -> list[tuple[int, StringField]]:
        """Los siete días en orden, con su número (0 = lunes)."""
        return [(number, getattr(self, f"dia_{number}")) for number in range(7)]

    def validate(self, extra_validators=None):
        valid = super().validate(extra_validators)

        self.franjas: list[Franja] = []
        self.holidays: list[Holiday] = []
        self.general_errors: list[str] = []

        for number, field in self.day_fields():
            try:
                slots = parse_day(field.data)
            except ValueError as error:
                field.errors = [*field.errors, str(error)]
                valid = False
            else:
                self.franjas.extend(Franja(number, *slot) for slot in slots)

        try:
            self.holidays = parse_holidays(self.feriados.data)
        except HolidayErrors as error:
            self.feriados.errors = [*self.feriados.errors, *error.messages]
            valid = False

        if valid and not self.franjas:
            self.general_errors.append(
                "Escribe el horario de al menos un día: sin días laborales el reloj "
                "del SLA nunca correría."
            )
            valid = False

        return valid


def calendar_form_data(view: CalendarView) -> dict:
    """Los valores con los que se rellena el formulario para un calendario."""
    slots_by_day: dict[int, list[tuple[time, time]]] = {n: [] for n in range(7)}

    for franja in view.franjas:
        slots_by_day[franja.dia].append((franja.inicio, franja.fin))

    data = {
        "zona_horaria": view.zone_name,
        "feriados": format_holidays(view.holidays),
        "version_base": view.version,
    }
    data.update(
        {f"dia_{number}": format_day(slots) for number, slots in slots_by_day.items()}
    )

    return data
