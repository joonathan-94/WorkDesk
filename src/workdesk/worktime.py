"""Tiempo laboral: qué días y horas cuentan, y cómo se mide y se avanza en ellos.

Lo usan los datos de demostración (`seed-demo-tickets`) y lo usará el SLA: por
eso vive aquí y no dentro del seed. No usa la base de datos: quien lo necesita
le entrega qué días y a qué horas se trabaja, y una zona horaria, y obtiene un
`BusinessClock` con el que medir cuánto tiempo laboral pasó entre dos momentos
o hasta dónde llega un plazo.

Hay dos formas de describir el horario:

- `WorkCalendar`: una única jornada, igual para todos los días laborales. Es lo
  más sencillo y es el calendario por defecto (`DEMO_CALENDAR`).
- `BusinessClock.from_schedule`: una lista de `Franja`, para horarios distintos
  según el día (el viernes se sale antes) o con varias franjas en un mismo día
  (una pausa de almuerzo). Es lo que guarda el calendario laboral del
  Administrador.

Reglas que conviene tener presentes:

- Un día es laboral si tiene al menos una franja de trabajo y no es feriado.
- Cada franja incluye la hora de inicio y excluye la de fin: a las 09:00 ya se
  trabaja y a las 18:00 ya no. Una franja no cruza la medianoche.
- Los momentos son fechas con zona horaria, nunca fechas «ingenuas». El motor
  las convierte a la zona del calendario antes de calcular, así que se pueden
  pasar tal como llegan de la base de datos (en UTC).
- Todo se calcula con la hora de pared de la zona: se da por hecho que ninguna
  franja cruza un cambio de horario de verano (en Chile ocurren a medianoche).
"""

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, tzinfo
from itertools import pairwise

# Una hora en formato HH:MM, de 00:00 a 23:59.
TIME_PATTERN = re.compile(r"([01]\d|2[0-3]):[0-5]\d")

# Los días de la semana, en el orden de `date.weekday()` (0 = lunes).
WEEKDAY_NAMES = (
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
    "domingo",
)

# Una franja excluye la hora de fin, así que el último minuto en que se trabaja
# es el anterior a ella.
_LAST_MINUTE = timedelta(minutes=1)


@dataclass(frozen=True)
class WorkCalendar:
    """Los días y las horas laborales: una sola jornada, igual para todos los días.

    - `dias`: números de día de la semana, de 0 (lunes) a 6 (domingo).
    - `inicio` y `fin`: jornada en formato HH:MM; `fin` no se incluye (se puede
      trabajar a las 17:59, no a las 18:00).
    - `feriados`: fechas que no son laborales aunque caigan en un día laboral.
    """

    dias: tuple[int, ...] = (0, 1, 2, 3, 4)
    inicio: str = "09:00"
    fin: str = "18:00"
    feriados: tuple[date, ...] = ()


# Calendario por defecto: de lunes a viernes, de 09:00 a 18:00 y sin feriados.
DEMO_CALENDAR = WorkCalendar()


@dataclass(frozen=True)
class Franja:
    """Una franja de trabajo de un día de la semana.

    - `dia`: de 0 (lunes) a 6 (domingo).
    - `inicio` y `fin`: horas; `fin` no se incluye.
    """

    dia: int
    inicio: time
    fin: time


def parse_time(value: str) -> time:
    """Convierte «HH:MM» en una hora. El formato se valida antes con `TIME_PATTERN`."""
    hour, minute = (int(part) for part in value.split(":"))

    return time(hour, minute)


def calendar_problems(calendar: WorkCalendar) -> list[str]:
    """Lo que está mal en un calendario, con mensajes para mostrar a quien lo edita.

    Devuelve una lista vacía si el calendario es válido.
    """
    problems: list[str] = []

    if not calendar.dias:
        problems.append("Calendario: debe haber al menos un día laboral.")

    if any(not isinstance(d, int) or not 0 <= d <= 6 for d in calendar.dias):
        problems.append("Calendario: los días van de 0 (lunes) a 6 (domingo).")

    if len(set(calendar.dias)) != len(calendar.dias):
        problems.append("Calendario: hay días repetidos.")

    for name, value in (("inicio", calendar.inicio), ("fin", calendar.fin)):
        if not TIME_PATTERN.fullmatch(value):
            problems.append(f"Calendario: el {name} «{value}» no tiene formato HH:MM.")

    if not problems and parse_time(calendar.inicio) >= parse_time(calendar.fin):
        problems.append("Calendario: el inicio debe ser anterior al fin.")

    if any(not isinstance(holiday, date) for holiday in calendar.feriados):
        problems.append("Calendario: los feriados deben ser fechas.")

    return problems


def schedule_problems(
    franjas: Iterable[Franja], feriados: Iterable[date] = ()
) -> list[str]:
    """Lo que está mal en un horario de franjas, con mensajes para mostrar.

    Es el equivalente de `calendar_problems` para `BusinessClock.from_schedule`:
    hace falta al menos una franja, los días van de 0 a 6, cada franja empieza
    antes de terminar y las de un mismo día no se solapan. Devuelve una lista
    vacía si el horario es válido.
    """
    problems: list[str] = []
    by_day: dict[int, list[Franja]] = {}
    franjas = tuple(franjas)

    if not franjas:
        problems.append("Calendario: debe haber al menos un día laboral.")

    for franja in franjas:
        if not isinstance(franja.dia, int) or not 0 <= franja.dia <= 6:
            message = "Calendario: los días van de 0 (lunes) a 6 (domingo)."

            if message not in problems:
                problems.append(message)
        else:
            by_day.setdefault(franja.dia, []).append(franja)

    for day, slots in sorted(by_day.items()):
        name = WEEKDAY_NAMES[day]

        if any(slot.inicio >= slot.fin for slot in slots):
            problems.append(
                f"Calendario: el inicio de una franja del {name} debe ser "
                "anterior a su fin."
            )
            continue

        slots.sort(key=lambda slot: slot.inicio)

        if any(first.fin > second.inicio for first, second in pairwise(slots)):
            problems.append(f"Calendario: hay franjas del {name} que se solapan.")

    if any(not isinstance(holiday, date) for holiday in feriados):
        problems.append("Calendario: los feriados deben ser fechas.")

    return problems


class BusinessClock:
    """Un calendario laboral en una zona horaria: mide y avanza en tiempo laboral.

    `zone` es la zona en la que se interpretan las horas del calendario. Si el
    calendario no es válido lanza `ValueError`: con un calendario sin días
    laborales, los bucles que buscan el siguiente día laboral no terminarían
    nunca. Para un horario con franjas distintas por día se usa
    `from_schedule`.
    """

    def __init__(self, calendar: WorkCalendar, zone: tzinfo) -> None:
        problems = calendar_problems(calendar)

        if problems:
            raise ValueError(" ".join(problems))

        shift = (parse_time(calendar.inicio), parse_time(calendar.fin))

        self._setup(dict.fromkeys(calendar.dias, (shift,)), calendar.feriados, zone)

    @classmethod
    def from_schedule(
        cls,
        franjas: Iterable[Franja],
        feriados: Iterable[date],
        zone: tzinfo,
    ) -> "BusinessClock":
        """Un reloj para un horario con franjas, que pueden variar según el día.

        Un día puede tener varias franjas (una pausa de almuerzo son dos) y un
        día sin franjas no es laboral. Lanza `ValueError` si el horario no es
        válido (ver `schedule_problems`).
        """
        franjas, feriados = tuple(franjas), tuple(feriados)
        problems = schedule_problems(franjas, feriados)

        if problems:
            raise ValueError(" ".join(problems))

        week: dict[int, list[tuple[time, time]]] = {}

        for franja in sorted(franjas, key=lambda slot: (slot.dia, slot.inicio)):
            week.setdefault(franja.dia, []).append((franja.inicio, franja.fin))

        clock = cls.__new__(cls)
        clock._setup({day: tuple(slots) for day, slots in week.items()}, feriados, zone)

        return clock

    def _setup(
        self,
        week: dict[int, tuple[tuple[time, time], ...]],
        holidays: Iterable[date],
        zone: tzinfo,
    ) -> None:
        self.zone = zone
        self.holidays = set(holidays)
        # Las franjas de cada día de la semana, en orden y sin solaparse.
        self._week = week

    # --- Días -----------------------------------------------------------

    def is_workday(self, day: date) -> bool:
        return day.weekday() in self._week and day not in self.holidays

    def previous_workday(self, day: date) -> date:
        """`day` si es laboral; si no, el día laboral anterior."""
        while not self.is_workday(day):
            day -= timedelta(days=1)

        return day

    def next_workday(self, day: date) -> date:
        """`day` si es laboral; si no, el día laboral siguiente."""
        while not self.is_workday(day):
            day += timedelta(days=1)

        return day

    def workdays_before(self, day: date, count: int) -> date:
        """El día laboral que está `count` días laborales antes de `day`."""
        day = self.previous_workday(day)

        for _ in range(count):
            day = self.previous_workday(day - timedelta(days=1))

        return day

    # --- Momentos -------------------------------------------------------

    def at(self, day: date, moment: time) -> datetime:
        """La hora `moment` de `day`, en la zona del calendario."""
        return datetime.combine(day, moment, tzinfo=self.zone)

    def is_working_time(self, moment: datetime) -> bool:
        """Si en `moment` se trabaja: cae dentro de una franja de un día laboral."""
        moment = self._local(moment)

        return any(
            begin <= moment < finish for begin, finish in self._shifts(moment.date())
        )

    def into_business(self, moment: datetime) -> datetime:
        """El primer momento laboral que no es anterior a `moment`."""
        moment = self._local(moment)
        day = moment.date()

        for begin, finish in self._shifts(day):
            if moment < begin:
                return begin

            if moment < finish:
                return moment

        return self._shifts(self.next_workday(day + timedelta(days=1)))[0][0]

    def latest_before(self, limit: datetime) -> datetime:
        """El último momento laboral que no es posterior a `limit`.

        Si `limit` cae fuera de las franjas (después de una, en una pausa, o en
        un día que no es laboral), es el último minuto de la franja anterior.
        """
        limit = self._local(limit)
        day = limit.date()

        for begin, finish in reversed(self._shifts(day)):
            if limit >= finish:
                return finish - _LAST_MINUTE

            if limit >= begin:
                return limit

        day = self.previous_workday(day - timedelta(days=1))

        return self._shifts(day)[-1][1] - _LAST_MINUTE

    # --- Medir y avanzar ------------------------------------------------

    def business_seconds_between(self, start: datetime, end: datetime) -> int:
        """Los segundos laborales completos que hay entre `start` y `end`.

        Solo cuenta el tiempo que cae dentro de una franja de un día laboral:
        las noches, las pausas, los fines de semana y los feriados no suman. Si
        `end` no es posterior a `start` devuelve 0. La fracción de segundo se
        descarta.
        """
        start, end = self._local(start), self._local(end)
        total = timedelta()

        if end > start:
            for begin, finish in self._working_intervals(start):
                if begin >= end:
                    break

                total += min(finish, end) - begin

        return int(total.total_seconds())

    def add_business_seconds(self, moment: datetime, seconds: int) -> datetime:
        """El primer momento en que han corrido `seconds` segundos laborales.

        Es el cálculo de un vencimiento: el reloj solo corre dentro de las
        franjas de los días laborales (salta noches, pausas, fines de semana y
        feriados) y, si `moment` cae fuera de ellas, empieza a correr cuando
        abre la siguiente. Si el plazo se cumple justo al cerrar una franja, el
        resultado es su hora de cierre: ahí se cumplió, aunque a esa hora ya no
        se trabaje (`add_hours`, en cambio, devuelve siempre un momento en que
        sí se trabaja). Con 0 segundos devuelve `moment` sin moverlo.

        Es la operación inversa de `business_seconds_between`: midiendo desde
        `moment` hasta el resultado se obtienen exactamente `seconds`.
        """
        if seconds < 0:
            raise ValueError("Los segundos laborales a sumar no pueden ser negativos.")

        moment = self._local(moment)
        remaining = timedelta(seconds=seconds)

        if not remaining:
            return moment

        # Los tramos no se acaban (siempre hay otro día laboral más adelante),
        # así que el bucle termina con el `return`.
        for begin, finish in self._working_intervals(moment):
            available = finish - begin

            if remaining <= available:
                return begin + remaining

            remaining -= available

        raise RuntimeError("Un calendario con días laborales no se acaba nunca.")

    def add_hours(self, moment: datetime, hours: int) -> datetime:
        """Avanza `hours` horas LABORALES y cae siempre en un momento en que se trabaja.

        Salta noches, pausas, fines de semana y feriados. Si el avance termina
        justo al cerrar una franja, el resultado es la apertura de la
        siguiente. Es lo que necesita el seed para que ningún evento quede fuera
        del horario; para calcular un vencimiento está `add_business_seconds`.
        """
        moment = self.into_business(moment)

        return self.into_business(self.add_business_seconds(moment, hours * 3600))

    # --- Internos -------------------------------------------------------

    def _local(self, moment: datetime) -> datetime:
        """`moment` en la zona del calendario. Rechaza las fechas sin zona horaria."""
        if moment.tzinfo is None:
            raise ValueError(
                "El tiempo laboral se calcula con fechas con zona horaria."
            )

        return moment.astimezone(self.zone)

    def _shifts(self, day: date) -> list[tuple[datetime, datetime]]:
        """Las franjas de `day` como momentos, en orden (vacío si no es laboral)."""
        if not self.is_workday(day):
            return []

        return [
            (self.at(day, start), self.at(day, end))
            for start, end in self._week[day.weekday()]
        ]

    def _working_intervals(
        self, moment: datetime
    ) -> Iterator[tuple[datetime, datetime]]:
        """Los tramos laborales desde `moment`, en orden y sin fin.

        Cada tramo es una franja de un día laboral. El primero se recorta para
        empezar en `moment` y se omiten las franjas que ya terminaron.
        """
        day = moment.date()

        while True:
            for opening, finish in self._shifts(day):
                begin = max(opening, moment)

                if begin < finish:
                    yield begin, finish

            day += timedelta(days=1)
