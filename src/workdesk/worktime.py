"""Tiempo laboral: qué días y horas cuentan, y cómo se mide y se avanza en ellos.

Lo usan los datos de demostración (`seed-demo-tickets`) y lo usará el SLA: por
eso vive aquí y no dentro del seed. No usa la base de datos: quien lo necesita
le entrega un `WorkCalendar` (qué días y a qué horas se trabaja) y una zona
horaria, y obtiene un `BusinessClock` con el que medir cuánto tiempo laboral
pasó entre dos momentos o hasta dónde llega un plazo.

Reglas que conviene tener presentes:

- Un día es laboral si su día de la semana está en `dias` y no es feriado.
- La jornada incluye la hora de inicio y excluye la de fin: a las 09:00 ya se
  trabaja y a las 18:00 ya no.
- Los momentos son fechas con zona horaria, nunca fechas «ingenuas». El motor
  las convierte a la zona del calendario antes de calcular, así que se pueden
  pasar tal como llegan de la base de datos (en UTC).
- Todo se calcula con la hora de pared de la zona: se da por hecho que ninguna
  jornada cruza un cambio de horario de verano (en Chile ocurren a medianoche).
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, tzinfo

# Una hora en formato HH:MM, de 00:00 a 23:59.
TIME_PATTERN = re.compile(r"([01]\d|2[0-3]):[0-5]\d")

# La jornada excluye la hora de fin, así que el último minuto en que se trabaja
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


class BusinessClock:
    """Un calendario laboral en una zona horaria: mide y avanza en tiempo laboral.

    `zone` es la zona en la que se interpretan las horas del calendario. Si el
    calendario no es válido lanza `ValueError`: con un calendario sin días
    laborales, los bucles que buscan el siguiente día laboral no terminarían
    nunca.
    """

    def __init__(self, calendar: WorkCalendar, zone: tzinfo) -> None:
        problems = calendar_problems(calendar)

        if problems:
            raise ValueError(" ".join(problems))

        self.zone = zone
        self.days = set(calendar.dias)
        self.holidays = set(calendar.feriados)
        self.start = parse_time(calendar.inicio)
        self.end = parse_time(calendar.fin)

    # --- Días -----------------------------------------------------------

    def is_workday(self, day: date) -> bool:
        return day.weekday() in self.days and day not in self.holidays

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

    def into_business(self, moment: datetime) -> datetime:
        """El primer momento laboral que no es anterior a `moment`."""
        moment = self._local(moment)
        day = moment.date()

        if self.is_workday(day):
            if moment.time() < self.start:
                return self.at(day, self.start)

            if moment.time() < self.end:
                return moment

        return self.at(self.next_workday(day + timedelta(days=1)), self.start)

    def latest_before(self, limit: datetime) -> datetime:
        """El último momento laboral que no es posterior a `limit`.

        Si `limit` ya pasó el cierre, o cae en un día que no es laboral, es el
        último minuto de la jornada anterior.
        """
        limit = self._local(limit)
        day = limit.date()

        if self.is_workday(day):
            if self.start <= limit.time() < self.end:
                return limit

            if limit.time() >= self.end:
                return self.at(day, self.end) - _LAST_MINUTE

        day = self.previous_workday(day - timedelta(days=1))

        return self.at(day, self.end) - _LAST_MINUTE

    # --- Medir y avanzar ------------------------------------------------

    def business_seconds_between(self, start: datetime, end: datetime) -> int:
        """Los segundos laborales completos que hay entre `start` y `end`.

        Solo cuenta el tiempo que cae dentro de la jornada de un día laboral:
        las noches, los fines de semana y los feriados no suman. Si `end` no es
        posterior a `start` devuelve 0. La fracción de segundo se descarta.
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

        Es el cálculo de un vencimiento: el reloj solo corre dentro de la
        jornada de los días laborales (salta noches, fines de semana y
        feriados) y, si `moment` cae fuera de ella, empieza a correr cuando
        abre. Si el plazo se cumple justo al cerrar, el resultado es la hora de
        cierre: ahí se cumplió, aunque a esa hora ya no se trabaje (`add_hours`,
        en cambio, devuelve siempre un momento en que sí se trabaja). Con 0
        segundos devuelve `moment` sin moverlo.

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

    def add_hours(self, moment: datetime, hours: int) -> datetime:
        """Avanza `hours` horas LABORALES y cae siempre en un momento en que se trabaja.

        Salta noches, fines de semana y feriados. Si el avance termina justo al
        cerrar la jornada, el resultado es la apertura del siguiente día
        laboral. Es lo que necesita el seed para que ningún evento quede fuera
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

    def _working_intervals(
        self, moment: datetime
    ) -> Iterator[tuple[datetime, datetime]]:
        """Los tramos laborales desde `moment`, en orden y sin fin.

        Cada tramo es la jornada de un día laboral. El primero se recorta para
        empezar en `moment` y se omite si ese día ya cerró.
        """
        day = moment.date()

        while True:
            if self.is_workday(day):
                begin = max(self.at(day, self.start), moment)
                finish = self.at(day, self.end)

                if begin < finish:
                    yield begin, finish

            day += timedelta(days=1)
