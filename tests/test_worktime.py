from datetime import UTC, date, datetime, time, timedelta
from itertools import combinations
from zoneinfo import ZoneInfo

import pytest

from src.workdesk.worktime import (
    DEMO_CALENDAR,
    TIME_PATTERN,
    WEEKDAY_NAMES,
    BusinessClock,
    Franja,
    WorkCalendar,
    calendar_problems,
    parse_time,
    schedule_problems,
)

ZONE = ZoneInfo("America/Santiago")
CLOCK = BusinessClock(DEMO_CALENDAR, ZONE)

HOUR = 3600
WORKDAY = 9 * HOUR  # la jornada del calendario por defecto: de 09:00 a 18:00


def at(day, hour=0, minute=0, second=0, microsecond=0):
    """Un momento de noviembre de 2026, en la zona del calendario.

    La semana de referencia: lun 16, mar 17, mié 18, jue 19, vie 20, sáb 21,
    dom 22 y lun 23.
    """
    return datetime(2026, 11, day, hour, minute, second, microsecond, tzinfo=ZONE)


def clock_with(**changes):
    """Un reloj con el calendario por defecto, cambiando solo lo indicado."""
    values = {
        "dias": DEMO_CALENDAR.dias,
        "inicio": DEMO_CALENDAR.inicio,
        "fin": DEMO_CALENDAR.fin,
        "feriados": DEMO_CALENDAR.feriados,
    }
    values.update(changes)

    return BusinessClock(WorkCalendar(**values), ZONE)


# --- El calendario --------------------------------------------------------


def test_the_default_calendar_is_monday_to_friday_from_nine_to_six():
    assert DEMO_CALENDAR.dias == (0, 1, 2, 3, 4)
    assert (DEMO_CALENDAR.inicio, DEMO_CALENDAR.fin) == ("09:00", "18:00")
    assert DEMO_CALENDAR.feriados == ()
    assert calendar_problems(DEMO_CALENDAR) == []


def test_parse_time():
    assert parse_time("09:30") == time(9, 30)
    assert parse_time("00:00") == time(0, 0)
    assert parse_time("23:59") == time(23, 59)


@pytest.mark.parametrize("value", ["00:00", "09:00", "18:00", "23:59"])
def test_time_pattern_accepts_hh_mm(value):
    assert TIME_PATTERN.fullmatch(value)


@pytest.mark.parametrize(
    "value", ["9:00", "24:00", "09:60", "09:00:00", " 09:00", "09-00", ""]
)
def test_time_pattern_rejects_anything_else(value):
    assert TIME_PATTERN.fullmatch(value) is None


def test_a_calendar_with_other_days_and_holidays_is_valid():
    calendar = WorkCalendar(
        dias=(5,), inicio="00:00", fin="23:59", feriados=(date(2026, 1, 1),)
    )

    assert calendar_problems(calendar) == []


@pytest.mark.parametrize(
    ("calendar", "message"),
    [
        (WorkCalendar(dias=()), "al menos un día laboral"),
        (WorkCalendar(dias=(0, 7)), "de 0 (lunes) a 6"),
        (WorkCalendar(dias=(1, 1)), "días repetidos"),
        (WorkCalendar(inicio="9:00"), "formato HH:MM"),
        (WorkCalendar(fin="24:00"), "formato HH:MM"),
        (WorkCalendar(inicio="18:00", fin="09:00"), "anterior al fin"),
        (WorkCalendar(inicio="09:00", fin="09:00"), "anterior al fin"),
        (WorkCalendar(feriados=("2026-11-17",)), "deben ser fechas"),
    ],
)
def test_calendar_problems_say_what_is_wrong(calendar, message):
    assert any(message in problem for problem in calendar_problems(calendar))


def test_the_clock_refuses_an_invalid_calendar():
    # Sin días laborales, buscar «el siguiente día laboral» no terminaría nunca.
    with pytest.raises(ValueError, match="al menos un día laboral"):
        BusinessClock(WorkCalendar(dias=()), ZONE)


# --- Los días -------------------------------------------------------------


def test_the_working_days_are_monday_to_friday():
    week = [CLOCK.is_workday(date(2026, 11, day)) for day in range(16, 24)]

    assert week == [True, True, True, True, True, False, False, True]


def test_a_holiday_is_not_a_working_day():
    clock = clock_with(feriados=(date(2026, 11, 17),))

    assert not clock.is_workday(date(2026, 11, 17))
    assert clock.is_workday(date(2026, 11, 18))


def test_a_calendar_can_work_on_saturdays():
    clock = clock_with(dias=(0, 1, 2, 3, 4, 5))

    assert clock.is_workday(date(2026, 11, 21))
    assert not clock.is_workday(date(2026, 11, 22))


def test_previous_and_next_working_day():
    wednesday, saturday = date(2026, 11, 18), date(2026, 11, 21)

    assert CLOCK.previous_workday(wednesday) == wednesday
    assert CLOCK.next_workday(wednesday) == wednesday
    assert CLOCK.previous_workday(saturday) == date(2026, 11, 20)
    assert CLOCK.next_workday(saturday) == date(2026, 11, 23)


def test_workdays_before_skips_the_weekend():
    monday = date(2026, 11, 23)

    # Tres días laborales antes del lunes 23: viernes, jueves y miércoles.
    assert CLOCK.workdays_before(monday, 3) == date(2026, 11, 18)
    assert CLOCK.workdays_before(monday, 0) == monday


def test_workdays_before_counts_from_the_last_working_day():
    sunday = date(2026, 11, 22)

    assert CLOCK.workdays_before(sunday, 0) == date(2026, 11, 20)
    assert CLOCK.workdays_before(sunday, 1) == date(2026, 11, 19)


def test_workdays_before_skips_holidays():
    clock = clock_with(feriados=(date(2026, 11, 17),))

    # El martes 17 es feriado: un día laboral antes del miércoles es el lunes.
    assert clock.workdays_before(date(2026, 11, 18), 1) == date(2026, 11, 16)


# --- Pasar al horario laboral ---------------------------------------------


@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        (at(18, 10, 30), at(18, 10, 30)),  # dentro de la jornada: no se mueve
        (at(18, 9, 0), at(18, 9, 0)),  # justo al abrir ya se trabaja
        (at(18, 17, 59, 59), at(18, 17, 59, 59)),
        (at(18, 0, 0), at(18, 9, 0)),  # antes de abrir: abre ese mismo día
        (at(18, 8, 59), at(18, 9, 0)),
        (at(18, 18, 0), at(19, 9, 0)),  # justo al cerrar ya no se trabaja
        (at(20, 18, 30), at(23, 9, 0)),  # viernes por la tarde: el lunes
        (at(21, 12, 0), at(23, 9, 0)),  # sábado
        (at(22, 12, 0), at(23, 9, 0)),  # domingo
    ],
)
def test_into_business_is_the_first_working_moment(moment, expected):
    assert CLOCK.into_business(moment) == expected


@pytest.mark.parametrize(
    ("limit", "expected"),
    [
        (at(18, 10, 30), at(18, 10, 30)),  # dentro de la jornada: el propio límite
        (at(18, 18, 0), at(18, 17, 59)),  # tras el cierre: el último minuto
        (at(18, 23, 0), at(18, 17, 59)),
        (at(18, 8, 0), at(17, 17, 59)),  # antes de abrir: el día anterior
        (at(23, 8, 0), at(20, 17, 59)),  # lunes antes de abrir: el viernes
        (at(21, 12, 0), at(20, 17, 59)),  # sábado
        (at(22, 23, 0), at(20, 17, 59)),  # domingo
    ],
)
def test_latest_before_is_the_last_working_moment(limit, expected):
    assert CLOCK.latest_before(limit) == expected


# --- Avanzar horas (siempre en un momento en que se trabaja) ----------------


@pytest.mark.parametrize(
    ("moment", "hours", "expected"),
    [
        (at(18, 10, 0), 2, at(18, 12, 0)),
        (at(18, 16, 0), 1, at(18, 17, 0)),
        (at(18, 16, 0), 2, at(19, 9, 0)),  # termina justo al cerrar: abre al día siguiente
        (at(18, 16, 0), 3, at(19, 10, 0)),
        (at(18, 9, 0), 9, at(19, 9, 0)),  # una jornada completa
        (at(18, 9, 0), 10, at(19, 10, 0)),
        (at(20, 17, 0), 3, at(23, 11, 0)),  # 1 h el viernes y 2 h el lunes
        (at(20, 19, 0), 1, at(23, 10, 0)),  # empieza cerrado: cuenta desde el lunes
        (at(21, 12, 0), 1, at(23, 10, 0)),  # empieza en sábado
        (at(18, 10, 0), 27, at(23, 10, 0)),  # miércoles, jueves y viernes, y 1 h más
        (at(18, 10, 0), 0, at(18, 10, 0)),
        (at(18, 8, 0), 0, at(18, 9, 0)),  # ni con 0 horas cae fuera de la jornada
    ],
)
def test_add_hours_always_lands_inside_the_working_hours(moment, hours, expected):
    assert CLOCK.add_hours(moment, hours) == expected


def test_add_hours_keeps_the_fraction_of_a_second():
    result = CLOCK.add_hours(at(18, 10, 0, 0, 123456), 1)

    assert result == at(18, 11, 0, 0, 123456)


def test_add_hours_skips_holidays():
    clock = clock_with(feriados=(date(2026, 11, 19),))

    # Miércoles 16:00 + 3 h: 2 h ese día, el jueves es feriado y la hora que
    # falta se cumple el viernes.
    assert clock.add_hours(at(18, 16, 0), 3) == at(20, 10, 0)


def test_add_hours_never_lands_outside_the_working_hours():
    moment = at(13, 0, 5)

    for _ in range(200):
        assert CLOCK.into_business(CLOCK.into_business(moment)) == CLOCK.into_business(
            moment
        )

        for hours in (0, 1, 2, 3, 5, 8, 9, 10, 17, 18, 19, 27):
            result = CLOCK.add_hours(moment, hours)

            assert CLOCK.is_working_time(result), (moment, hours)
            assert result >= moment

        moment += timedelta(minutes=89)


# --- Medir tiempo laboral -------------------------------------------------


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        (at(18, 10, 0), at(18, 12, 30), 2 * HOUR + 1800),
        (at(18, 10, 0), at(18, 10, 0), 0),
        (at(18, 12, 0), at(18, 10, 0), 0),  # al revés: nada
        (at(18, 8, 0), at(18, 9, 30), 1800),  # lo anterior a la apertura no cuenta
        (at(18, 17, 30), at(18, 19, 0), 1800),  # ni lo posterior al cierre
        (at(18, 17, 0), at(19, 10, 0), 2 * HOUR),  # cruza la noche: 1 h + 1 h
        (at(18, 18, 0), at(19, 9, 0), 0),  # la noche entera no suma
        (at(18, 19, 0), at(19, 8, 0), 0),
        (at(20, 17, 0), at(23, 10, 0), 2 * HOUR),  # cruza el fin de semana
        (at(21, 10, 0), at(22, 15, 0), 0),  # dentro del fin de semana
        (at(18, 0, 0), at(19, 0, 0), WORKDAY),  # un día laboral completo
        (at(16, 0, 0), at(23, 0, 0), 5 * WORKDAY),  # una semana laboral
    ],
)
def test_business_seconds_between(start, end, expected):
    assert CLOCK.business_seconds_between(start, end) == expected


def test_a_holiday_adds_no_working_time():
    clock = clock_with(feriados=(date(2026, 11, 17),))

    assert clock.business_seconds_between(at(16, 0, 0), at(23, 0, 0)) == 4 * WORKDAY


def test_another_working_day_and_hours_change_what_counts():
    clock = clock_with(dias=(0, 1, 2, 3, 4, 5), inicio="08:00", fin="20:00")

    # Viernes y sábado, de 12 horas cada uno; el domingo no se trabaja.
    assert clock.business_seconds_between(at(20, 0, 0), at(23, 0, 0)) == 24 * HOUR


def test_business_seconds_drop_the_fraction_of_a_second():
    assert CLOCK.business_seconds_between(at(18, 10, 0), at(18, 10, 0, 1, 999999)) == 1
    assert (
        CLOCK.business_seconds_between(
            at(18, 10, 0, 0, 500000), at(18, 10, 0, 1, 499999)
        )
        == 0
    )


def test_a_long_span_counts_every_working_day():
    first, last = date(2026, 1, 1), date(2029, 1, 1)
    working_days = sum(
        1
        for offset in range((last - first).days)
        if (first + timedelta(days=offset)).weekday() < 5
    )

    start = datetime(2026, 1, 1, tzinfo=ZONE)
    end = datetime(2029, 1, 1, tzinfo=ZONE)

    assert CLOCK.business_seconds_between(start, end) == working_days * WORKDAY


def uniform_week(calendar):
    """Las franjas de cada día de un calendario de una sola jornada."""
    shift = (parse_time(calendar.inicio), parse_time(calendar.fin))

    return {day: [shift] for day in calendar.dias}


def brute_force_seconds(week, holidays, start, end):
    """Cuenta minuto a minuto, sin ninguna de las ideas del motor.

    `week` dice qué franjas (inicio, fin) tiene cada día de la semana.
    """
    total = 0
    minute = start

    while minute < end:
        day = minute.date()
        shifts = [] if day in holidays else week.get(day.weekday(), [])

        if any(opening <= minute.time() < closing for opening, closing in shifts):
            total += 60

        minute += timedelta(minutes=1)

    return total


@pytest.mark.parametrize(
    "calendar",
    [
        DEMO_CALENDAR,
        WorkCalendar(
            dias=(0, 1, 2, 3, 4, 5),
            inicio="08:30",
            fin="19:15",
            feriados=(date(2026, 11, 17), date(2026, 11, 21)),
        ),
    ],
    ids=["default", "saturdays-and-holidays"],
)
def test_measuring_matches_a_minute_by_minute_count(calendar):
    clock = BusinessClock(calendar, ZONE)
    week = uniform_week(calendar)
    start = at(13, 0, 3)

    for _ in range(14):
        for minutes in (0, 1, 59, 600, 1441, 3000, 4321):
            end = start + timedelta(minutes=minutes)

            assert clock.business_seconds_between(start, end) == brute_force_seconds(
                week, calendar.feriados, start, end
            ), (start, end)

        start += timedelta(hours=11, minutes=37)


def test_measurements_add_up_across_any_split():
    # Treinta momentos irregulares repartidos en nueve días, con fines de semana.
    points = [at(14, 3, 0) + timedelta(seconds=n * 26_237) for n in range(30)]

    for first, second, third in combinations(points, 3):
        whole = CLOCK.business_seconds_between(first, third)
        parts = CLOCK.business_seconds_between(
            first, second
        ) + CLOCK.business_seconds_between(second, third)

        assert whole == parts, (first, second, third)


# --- Sumar tiempo laboral (un vencimiento) ----------------------------------


@pytest.mark.parametrize(
    ("moment", "seconds", "expected"),
    [
        (at(18, 10, 0), 0, at(18, 10, 0)),
        (at(18, 10, 0), HOUR, at(18, 11, 0)),
        (at(18, 10, 0), 1, at(18, 10, 0, 1)),
        (at(18, 17, 0), 2 * HOUR, at(19, 10, 0)),  # 1 h hoy y 1 h mañana
        (at(18, 17, 0), HOUR + 1, at(19, 9, 0, 1)),  # un segundo más: ya es mañana
        (at(20, 17, 0), 3 * HOUR, at(23, 11, 0)),  # cruza el fin de semana
        (at(18, 19, 0), HOUR, at(19, 10, 0)),  # empieza cerrado: corre desde que abre
        (at(21, 12, 0), HOUR, at(23, 10, 0)),
        (at(18, 10, 0), 27 * HOUR, at(23, 10, 0)),
        (at(18, 8, 0), 0, at(18, 8, 0)),  # sin tiempo que sumar no se mueve
    ],
)
def test_add_business_seconds(moment, seconds, expected):
    assert CLOCK.add_business_seconds(moment, seconds) == expected


def test_a_deadline_met_exactly_at_closing_time_is_the_closing_time():
    # El plazo se cumple a las 18:00 aunque a esa hora ya no se trabaje.
    assert CLOCK.add_business_seconds(at(18, 16, 0), 2 * HOUR) == at(18, 18, 0)
    assert CLOCK.add_business_seconds(at(18, 9, 0), WORKDAY) == at(18, 18, 0)

    # `add_hours`, en cambio, busca un momento en que se pueda trabajar.
    assert CLOCK.add_hours(at(18, 16, 0), 2) == at(19, 9, 0)


def test_a_holiday_is_skipped_when_adding_working_time():
    clock = clock_with(feriados=(date(2026, 11, 17),))

    # Lunes 17:00: 1 h ese día, el martes es feriado y la otra hora es el miércoles.
    assert clock.add_business_seconds(at(16, 17, 0), 2 * HOUR) == at(18, 10, 0)


def test_adding_time_in_another_calendar():
    clock = clock_with(dias=(0, 1, 2, 3, 4, 5), inicio="08:00", fin="20:00")

    # Viernes 19:00: 1 h ese día y 2 h el sábado desde las 08:00.
    assert clock.add_business_seconds(at(20, 19, 0), 3 * HOUR) == at(21, 10, 0)


def test_adding_a_negative_amount_is_an_error():
    with pytest.raises(ValueError, match="negativos"):
        CLOCK.add_business_seconds(at(18, 10, 0), -1)


def test_adding_time_in_two_steps_equals_adding_it_at_once():
    moment = at(13, 0, 5)

    for _ in range(40):
        for first, second in ((HOUR, 2 * HOUR), (WORKDAY, 1), (0, 5 * HOUR), (59, 41)):
            in_steps = CLOCK.add_business_seconds(
                CLOCK.add_business_seconds(moment, first), second
            )

            assert in_steps == CLOCK.add_business_seconds(moment, first + second)

        moment += timedelta(minutes=397)


def test_adding_and_measuring_are_inverse_operations():
    moment = at(13, 0, 5)

    for _ in range(300):
        for seconds in (1, 59, HOUR, WORKDAY, WORKDAY + 1, 2 * WORKDAY, 40 * HOUR + 17):
            result = CLOCK.add_business_seconds(moment, seconds)

            assert CLOCK.business_seconds_between(moment, result) == seconds
            # Y es el primer instante en que se cumple: un segundo antes aún falta uno.
            before = result - timedelta(seconds=1)
            assert CLOCK.business_seconds_between(moment, before) == seconds - 1

        moment += timedelta(minutes=97)


# --- Zonas horarias --------------------------------------------------------


def test_moments_in_another_zone_are_converted_to_the_calendar_zone():
    # Así llegan las fechas de la base de datos: en UTC.
    early = at(18, 7, 0).astimezone(UTC)  # antes de abrir, aunque en UTC parezca de día
    late = at(18, 17, 30).astimezone(UTC)  # se trabaja, aunque en UTC ya «cerró»

    assert CLOCK.into_business(early) == at(18, 9, 0)
    assert CLOCK.into_business(late) == at(18, 17, 30)
    assert CLOCK.latest_before(early) == at(17, 17, 59)
    assert CLOCK.business_seconds_between(at(18, 9, 0).astimezone(UTC), late) == (
        8 * HOUR + 1800
    )
    assert CLOCK.add_hours(at(18, 8, 0).astimezone(UTC), 1) == at(18, 10, 0)


def test_the_result_is_in_the_calendar_zone():
    result = CLOCK.add_business_seconds(at(18, 9, 0).astimezone(UTC), HOUR)

    assert result == at(18, 10, 0)
    assert result.tzinfo is ZONE


def test_dates_without_a_time_zone_are_rejected():
    naive = at(18, 10, 0).replace(tzinfo=None)

    with pytest.raises(ValueError, match="zona horaria"):
        CLOCK.into_business(naive)

    with pytest.raises(ValueError, match="zona horaria"):
        CLOCK.latest_before(naive)

    with pytest.raises(ValueError, match="zona horaria"):
        CLOCK.add_hours(naive, 1)

    with pytest.raises(ValueError, match="zona horaria"):
        CLOCK.add_business_seconds(naive, 1)

    with pytest.raises(ValueError, match="zona horaria"):
        CLOCK.business_seconds_between(naive, at(18, 12, 0))

    with pytest.raises(ValueError, match="zona horaria"):
        CLOCK.business_seconds_between(at(18, 10, 0), naive)


def test_a_daylight_saving_change_over_the_weekend_does_not_move_the_working_hours():
    # El viernes 4 de septiembre de 2026 Chile está en UTC-4 y el lunes 7 en
    # UTC-3: el fin de semana trae el cambio al horario de verano.
    friday = datetime(2026, 9, 4, 17, 0, tzinfo=ZONE)
    monday = datetime(2026, 9, 7, 10, 0, tzinfo=ZONE)
    assert friday.utcoffset() != monday.utcoffset()

    # El motor trabaja con la hora de pared: la jornada sigue siendo de 09:00 a
    # 18:00 antes y después del cambio.
    assert CLOCK.business_seconds_between(friday, monday) == 2 * HOUR
    assert CLOCK.add_business_seconds(friday, 2 * HOUR) == monday


# --- Franjas por día --------------------------------------------------------


def franja(day, start, end):
    return Franja(day, parse_time(start), parse_time(end))


# De lunes a jueves con pausa de almuerzo (09:00-13:00 y 14:00-18:00), el viernes
# corrido de 09:00 a 14:00 y sin fines de semana.
LUNCH_SCHEDULE = (
    *(franja(day, "09:00", "13:00") for day in range(4)),
    *(franja(day, "14:00", "18:00") for day in range(4)),
    franja(4, "09:00", "14:00"),
)
LUNCH_CLOCK = BusinessClock.from_schedule(LUNCH_SCHEDULE, (), ZONE)

# Un horario a propósito incómodo: el lunes con almuerzo, un martes de un solo
# minuto, el miércoles sin trabajo, un jueves casi completo, un viernes de
# madrugada y de noche y un sábado de una hora. El martes 24 y el sábado 28 de
# noviembre son feriados.
IRREGULAR_SCHEDULE = (
    franja(0, "08:00", "12:00"),
    franja(0, "13:00", "17:30"),
    franja(1, "10:00", "10:01"),
    franja(3, "09:00", "23:59"),
    franja(4, "00:00", "06:00"),
    franja(4, "22:00", "23:59"),
    franja(5, "10:00", "11:00"),
)
IRREGULAR_HOLIDAYS = (date(2026, 11, 24), date(2026, 11, 28))
IRREGULAR_CLOCK = BusinessClock.from_schedule(
    IRREGULAR_SCHEDULE, IRREGULAR_HOLIDAYS, ZONE
)

# (reloj, horario, feriados, primer momento de los recorridos)
SHIFT_CLOCKS = [
    pytest.param(LUNCH_CLOCK, LUNCH_SCHEDULE, (), at(13, 0, 3), id="lunch-break"),
    pytest.param(
        IRREGULAR_CLOCK,
        IRREGULAR_SCHEDULE,
        IRREGULAR_HOLIDAYS,
        at(21, 0, 3),
        id="irregular",
    ),
]


def week_of(schedule):
    """Las franjas (inicio, fin) de cada día de la semana de un horario."""
    week = {}

    for slot in schedule:
        week.setdefault(slot.dia, []).append((slot.inicio, slot.fin))

    return week


def test_the_weekday_names_follow_the_python_order():
    assert len(WEEKDAY_NAMES) == 7
    assert WEEKDAY_NAMES[date(2026, 11, 16).weekday()] == "lunes"
    assert WEEKDAY_NAMES[date(2026, 11, 22).weekday()] == "domingo"


def test_a_valid_schedule_has_no_problems():
    adjacent = [franja(0, "09:00", "13:00"), franja(0, "13:00", "18:00")]

    assert schedule_problems(LUNCH_SCHEDULE) == []
    assert schedule_problems(IRREGULAR_SCHEDULE, IRREGULAR_HOLIDAYS) == []
    # Una franja puede empezar justo donde termina la anterior.
    assert schedule_problems(adjacent) == []


@pytest.mark.parametrize(
    ("franjas", "holidays", "message"),
    [
        ([], (), "al menos un día laboral"),
        ([Franja(7, time(9), time(18))], (), "de 0 (lunes) a 6"),
        ([Franja(-1, time(9), time(18))], (), "de 0 (lunes) a 6"),
        ([franja(1, "18:00", "09:00")], (), "franja del martes"),
        ([franja(1, "09:00", "09:00")], (), "anterior a su fin"),
        (
            [franja(2, "09:00", "13:00"), franja(2, "12:59", "18:00")],
            (),
            "franjas del miércoles que se solapan",
        ),
        ([franja(0, "09:00", "18:00")], ("2026-11-17",), "deben ser fechas"),
    ],
)
def test_schedule_problems_say_what_is_wrong(franjas, holidays, message):
    problems = schedule_problems(franjas, holidays)

    assert any(message in problem for problem in problems)


def test_from_schedule_refuses_an_invalid_schedule():
    with pytest.raises(ValueError, match="al menos un día laboral"):
        BusinessClock.from_schedule([], (), ZONE)

    with pytest.raises(ValueError, match="se solapan"):
        BusinessClock.from_schedule(
            [franja(2, "09:00", "13:00"), franja(2, "12:00", "18:00")], (), ZONE
        )


def test_the_order_of_the_shifts_does_not_matter():
    shuffled = BusinessClock.from_schedule(reversed(LUNCH_SCHEDULE), (), ZONE)
    moment = at(13, 0, 7)

    for _ in range(60):
        assert shuffled.into_business(moment) == LUNCH_CLOCK.into_business(moment)
        assert shuffled.latest_before(moment) == LUNCH_CLOCK.latest_before(moment)
        assert shuffled.add_hours(moment, 7) == LUNCH_CLOCK.add_hours(moment, 7)

        moment += timedelta(minutes=71)


def test_a_schedule_with_one_shift_per_day_equals_the_uniform_calendar():
    same = BusinessClock.from_schedule(
        [franja(day, "09:00", "18:00") for day in range(5)], (), ZONE
    )
    moment = at(13, 0, 7)

    for _ in range(120):
        assert same.into_business(moment) == CLOCK.into_business(moment)
        assert same.latest_before(moment) == CLOCK.latest_before(moment)

        for hours in (0, 1, 5, 9, 27):
            assert same.add_hours(moment, hours) == CLOCK.add_hours(moment, hours)

        for seconds in (0, 1, HOUR, WORKDAY, 40 * HOUR + 17):
            assert same.add_business_seconds(
                moment, seconds
            ) == CLOCK.add_business_seconds(moment, seconds)

            later = moment + timedelta(seconds=3 * seconds)
            assert same.business_seconds_between(
                moment, later
            ) == CLOCK.business_seconds_between(moment, later)

        moment += timedelta(minutes=83)


@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        (at(18, 9, 0), True),
        (at(18, 12, 59), True),
        (at(18, 13, 0), False),  # la hora de fin de una franja no se incluye
        (at(18, 13, 30), False),  # pausa de almuerzo
        (at(18, 14, 0), True),
        (at(18, 17, 59), True),
        (at(18, 18, 0), False),
        (at(20, 13, 59), True),  # el viernes se trabaja hasta las 14:00
        (at(20, 14, 0), False),
        (at(21, 10, 0), False),  # sábado
    ],
)
def test_is_working_time_follows_every_shift(moment, expected):
    assert LUNCH_CLOCK.is_working_time(moment) is expected


def test_is_working_time_converts_to_the_calendar_zone():
    # Las 10:30 de Santiago, expresadas en UTC como llegan de la base de datos.
    assert CLOCK.is_working_time(at(18, 10, 30).astimezone(UTC))
    assert not CLOCK.is_working_time(at(18, 7, 0).astimezone(UTC))


def test_a_day_without_shifts_is_not_a_working_day():
    assert not IRREGULAR_CLOCK.is_workday(date(2026, 11, 18))  # miércoles
    assert not IRREGULAR_CLOCK.is_workday(date(2026, 11, 22))  # domingo
    assert not IRREGULAR_CLOCK.is_workday(date(2026, 11, 24))  # martes feriado
    assert IRREGULAR_CLOCK.is_workday(date(2026, 11, 17))  # martes
    assert IRREGULAR_CLOCK.is_workday(date(2026, 11, 23))  # lunes


@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        (at(18, 10, 30), at(18, 10, 30)),
        (at(18, 13, 0), at(18, 14, 0)),  # justo al empezar la pausa
        (at(18, 13, 30), at(18, 14, 0)),
        (at(18, 8, 0), at(18, 9, 0)),
        (at(18, 18, 0), at(19, 9, 0)),
        (at(20, 10, 0), at(20, 10, 0)),
        (at(20, 14, 0), at(23, 9, 0)),  # el viernes cierra a las 14:00: el lunes
        (at(21, 12, 0), at(23, 9, 0)),
    ],
)
def test_into_business_skips_the_break(moment, expected):
    assert LUNCH_CLOCK.into_business(moment) == expected


@pytest.mark.parametrize(
    ("limit", "expected"),
    [
        (at(18, 10, 30), at(18, 10, 30)),
        (at(18, 13, 30), at(18, 12, 59)),  # en la pausa: el último minuto de la mañana
        (at(18, 14, 30), at(18, 14, 30)),
        (at(18, 20, 0), at(18, 17, 59)),
        (at(18, 8, 0), at(17, 17, 59)),
        (at(23, 8, 0), at(20, 13, 59)),  # lunes antes de abrir: el viernes cierra a las 14:00
        (at(21, 12, 0), at(20, 13, 59)),
        (at(20, 14, 30), at(20, 13, 59)),
    ],
)
def test_latest_before_finds_the_last_minute_of_the_previous_shift(limit, expected):
    assert LUNCH_CLOCK.latest_before(limit) == expected


@pytest.mark.parametrize(
    ("moment", "hours", "expected"),
    [
        (at(18, 12, 0), 1, at(18, 14, 0)),  # termina justo al empezar la pausa
        (at(18, 12, 0), 2, at(18, 15, 0)),  # 1 h antes y 1 h después del almuerzo
        (at(18, 17, 0), 1, at(19, 9, 0)),
        (at(19, 12, 0), 6, at(20, 10, 0)),  # 1 h + 4 h el jueves y 1 h el viernes
        (at(20, 13, 0), 2, at(23, 10, 0)),  # 1 h el viernes y 1 h el lunes
        (at(18, 13, 30), 1, at(18, 15, 0)),  # empieza en la pausa: corre desde las 14:00
    ],
)
def test_add_hours_crosses_the_break(moment, hours, expected):
    assert LUNCH_CLOCK.add_hours(moment, hours) == expected


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        (at(18, 12, 0), at(18, 15, 0), 2 * HOUR),  # la pausa no suma
        (at(18, 13, 0), at(18, 14, 0), 0),
        (at(18, 9, 0), at(18, 18, 0), 8 * HOUR),
        (at(18, 0, 0), at(19, 0, 0), 8 * HOUR),
        (at(20, 0, 0), at(21, 0, 0), 5 * HOUR),  # el viernes, de 09:00 a 14:00
        (at(16, 0, 0), at(23, 0, 0), 37 * HOUR),  # cuatro días de 8 h y un viernes de 5 h
        (at(20, 13, 0), at(23, 10, 0), 2 * HOUR),
    ],
)
def test_business_seconds_between_with_a_break(start, end, expected):
    assert LUNCH_CLOCK.business_seconds_between(start, end) == expected


@pytest.mark.parametrize(
    ("moment", "seconds", "expected"),
    [
        (at(18, 12, 0), HOUR, at(18, 13, 0)),  # vence justo al empezar la pausa
        (at(18, 12, 0), HOUR + 1, at(18, 14, 0, 1)),  # un segundo más: tras el almuerzo
        (at(18, 17, 0), HOUR, at(18, 18, 0)),
        (at(18, 9, 0), 8 * HOUR, at(18, 18, 0)),
        (at(20, 13, 0), 3 * HOUR, at(23, 11, 0)),
        (at(18, 13, 30), HOUR, at(18, 15, 0)),  # empieza en la pausa
    ],
)
def test_add_business_seconds_with_a_break(moment, seconds, expected):
    assert LUNCH_CLOCK.add_business_seconds(moment, seconds) == expected


@pytest.mark.parametrize(("clock", "schedule", "holidays", "first"), SHIFT_CLOCKS)
def test_measuring_with_shifts_matches_a_minute_by_minute_count(
    clock, schedule, holidays, first
):
    week = week_of(schedule)
    start = first

    for _ in range(14):
        for minutes in (0, 1, 59, 600, 1441, 3000, 4321):
            end = start + timedelta(minutes=minutes)

            assert clock.business_seconds_between(start, end) == brute_force_seconds(
                week, holidays, start, end
            ), (start, end)

        start += timedelta(hours=11, minutes=37)


@pytest.mark.parametrize(("clock", "schedule", "holidays", "first"), SHIFT_CLOCKS)
def test_adding_and_measuring_are_inverse_operations_with_shifts(
    clock, schedule, holidays, first
):
    moment = first

    for _ in range(150):
        for seconds in (1, 59, HOUR, WORKDAY, WORKDAY + 1, 2 * WORKDAY, 40 * HOUR + 17):
            result = clock.add_business_seconds(moment, seconds)

            assert clock.business_seconds_between(moment, result) == seconds
            # Y es el primer instante en que se cumple.
            before = result - timedelta(seconds=1)
            assert clock.business_seconds_between(moment, before) == seconds - 1

        moment += timedelta(minutes=97)


@pytest.mark.parametrize(("clock", "schedule", "holidays", "first"), SHIFT_CLOCKS)
def test_the_moment_helpers_never_land_outside_the_shifts(
    clock, schedule, holidays, first
):
    moment = first

    for _ in range(200):
        into = clock.into_business(moment)
        assert clock.is_working_time(into)
        assert into >= moment
        assert clock.into_business(into) == into

        latest = clock.latest_before(moment)
        assert clock.is_working_time(latest)
        assert latest <= moment

        for hours in (0, 1, 2, 5, 9, 27):
            result = clock.add_hours(moment, hours)

            assert clock.is_working_time(result), (moment, hours)
            assert result >= moment

        moment += timedelta(minutes=89)


@pytest.mark.parametrize(("clock", "schedule", "holidays", "first"), SHIFT_CLOCKS)
def test_measurements_with_shifts_add_up_across_any_split(
    clock, schedule, holidays, first
):
    points = [first + timedelta(seconds=n * 26_237) for n in range(30)]

    for start, middle, end in combinations(points, 3):
        whole = clock.business_seconds_between(start, end)
        parts = clock.business_seconds_between(
            start, middle
        ) + clock.business_seconds_between(middle, end)

        assert whole == parts, (start, middle, end)
