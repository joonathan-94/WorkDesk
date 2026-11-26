"""Las fechas del seed: relativas al día de carga, en tiempo laboral y con el calendario guardado."""

from dataclasses import replace
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from src.workdesk.extensions import db
from src.workdesk.models import (
    Ticket,
    TicketEvent,
)
from src.workdesk.seeds import (
    DemoTicketsError,
    seed_demo_tickets,
)
from src.workdesk.seeds.demo_tickets import validate_demo_tickets
from src.workdesk.seeds.demo_tickets_data import (
    DEMO_TICKETS,
    DemoAdjustment,
)
from src.workdesk.sla.work_calendar import (
    Holiday,
    resolve_work_calendar,
    save_work_calendar,
)
from src.workdesk.worktime import Franja, WorkCalendar, parse_time
from tests.database import empty_tables
from tests.demo_data import NOW, ZONE, prepare
from tests.seed_helpers import (
    all_event_times,
    assert_inside_the_default_calendar,
    by_clave,
    count,
    date_snapshot,
    demo_tickets,
    history_of,
    local,
    requesters_of,
    user,
    workdays_between,
)

# --- Fechas -------------------------------------------------------------


def test_dates_are_relative_to_the_load_day(app, seeded):
    with app.app_context():
        # hace_dias=0: el mismo día, a la hora indicada.
        assert local(by_clave("wifi-sala-reuniones").fecha_creacion) == datetime(
            2026, 11, 18, 10, 40, tzinfo=ZONE
        )

        # hace_dias=3 son tres DÍAS LABORALES (martes, lunes y viernes).
        assert local(by_clave("excel-bloqueado").fecha_creacion) == datetime(
            2026, 11, 13, 9, 12, tzinfo=ZONE
        )

        # hace_dias=20 son cuatro semanas laborales exactas.
        assert local(by_clave("mouse-malo").fecha_creacion) == datetime(
            2026, 10, 21, 12, 30, tzinfo=ZONE
        )

        for demo in DEMO_TICKETS:
            created = local(by_clave(demo.clave).fecha_creacion)

            assert_inside_the_default_calendar(created)
            assert workdays_between(created.date(), NOW.date()) == demo.hace_dias


def test_no_event_is_ever_in_the_future_and_everything_is_in_order(app, prepared):
    early = datetime(2026, 11, 18, 9, 0, tzinfo=ZONE)

    with app.app_context():
        seed_demo_tickets(now=early)

        # A las 9:00 aún no ha pasado ni un minuto de jornada: los tickets de
        # las 10:40 de hoy quedan al final de la jornada del día laboral anterior.
        assert local(by_clave("wifi-sala-reuniones").fecha_creacion) == datetime(
            2026, 11, 17, 17, 59, tzinfo=ZONE
        )

        for demo in DEMO_TICKETS:
            ticket = by_clave(demo.clave)
            times = [event.fecha_hora for event in history_of(ticket)]

            assert times == sorted(times)
            assert max(times) <= early
            assert ticket.fecha_creacion == times[0]

            for moment in times:
                assert_inside_the_default_calendar(moment)

            # Cada participación empieza en la creación o en su evento y, si
            # se retiró, nunca antes de empezar.
            added = {
                event.contexto["participacion_id"]: event.fecha_hora
                for event in history_of(ticket)
                if event.tipo_evento == TicketEvent.SOLICITANTE_AGREGADO.value
            }

            for link in requesters_of(ticket):
                assert link.fecha_asociacion == added.get(link.id, ticket.fecha_creacion)

                if link.fecha_retiro is not None:
                    assert link.fecha_retiro >= link.fecha_asociacion
                    assert link.fecha_retiro <= early

            # Como en la aplicación: la fecha de modificación existe si y solo
            # si algo subió la versión del ticket (agregar o retirar
            # solicitantes no lo hace) y es la de uno de sus eventos.
            assert (ticket.version > 1) is (ticket.fecha_modificacion is not None)

            if ticket.fecha_modificacion is not None:
                assert ticket.fecha_modificacion in times


# --- Tiempo laboral -----------------------------------------------------


def test_nothing_falls_outside_the_working_days_and_hours(app, seeded):
    with app.app_context():
        for moment in all_event_times():
            assert_inside_the_default_calendar(moment)


def test_adjustments_run_on_working_hours_and_skip_the_night(app, seeded):
    # Creado un lunes a las 16:50: quedan 1 h 10 min de jornada y las 3 h 50 min
    # restantes de las 5 h se cumplen a la mañana siguiente.
    with app.app_context():
        events = history_of(by_clave("archivo-borrado"))

        assert local(events[0].fecha_hora) == datetime(2026, 11, 9, 16, 50, tzinfo=ZONE)
        assert local(events[1].fecha_hora) == datetime(2026, 11, 10, 12, 50, tzinfo=ZONE)


def test_adjustments_skip_the_weekend(app, prepared):
    friday_afternoon = replace(
        DEMO_TICKETS[0],
        clave="viernes-por-la-tarde",
        titulo="Un ticket de viernes por la tarde",
        hace_dias=3,
        hora="17:00",
        ajustes=(
            DemoAdjustment(actor="diego.soto", despues_horas=3, titulo="Titulo corregido"),
        ),
    )

    with app.app_context():
        seed_demo_tickets(now=NOW, tickets=(friday_afternoon,))

        events = history_of(by_clave("viernes-por-la-tarde"))

        # Viernes 17:00 + 1 h hasta las 18:00 + 2 h el lunes desde las 9:00.
        assert local(events[0].fecha_hora) == datetime(2026, 11, 13, 17, 0, tzinfo=ZONE)
        assert local(events[1].fecha_hora) == datetime(2026, 11, 16, 11, 0, tzinfo=ZONE)


def test_a_sunday_run_counts_from_the_last_working_day(app, prepared):
    sunday = datetime(2026, 11, 29, 15, 0, tzinfo=ZONE)

    with app.app_context():
        seed_demo_tickets(now=sunday)

        assert local(by_clave("wifi-sala-reuniones").fecha_creacion) == datetime(
            2026, 11, 27, 10, 40, tzinfo=ZONE
        )

        for moment in all_event_times():
            assert_inside_the_default_calendar(moment)


def test_an_evening_run_never_places_anything_after_the_end_of_the_day(app, prepared):
    evening = datetime(2026, 11, 18, 20, 0, tzinfo=ZONE)

    with app.app_context():
        seed_demo_tickets(now=evening)

        for moment in all_event_times():
            assert_inside_the_default_calendar(moment)
            assert moment <= evening


def test_a_holiday_is_skipped_when_counting_days_and_hours(app, prepared):
    calendar = WorkCalendar(feriados=(date(2026, 11, 17),))

    with app.app_context():
        seed_demo_tickets(now=NOW, calendar=calendar)

        # Tres días laborales antes del miércoles 18, sin contar el feriado del 17.
        events = history_of(by_clave("excel-bloqueado"))
        assert local(events[0].fecha_hora) == datetime(2026, 11, 12, 9, 12, tzinfo=ZONE)

        for moment in all_event_times():
            assert local(moment).date() != date(2026, 11, 17)


def test_the_calendar_is_configurable(app, prepared):
    saturdays_too = WorkCalendar(dias=(0, 1, 2, 3, 4, 5), inicio="08:00", fin="20:00")

    with app.app_context():
        # Solo se mira este ticket (que todo cae dentro del calendario lo comprueban, con
        # los 108, las pruebas de calendario de arriba).
        seed_demo_tickets(now=NOW, calendar=saturdays_too, tickets=demo_tickets("excel-bloqueado"))

        # Con el sábado laboral, tres días laborales antes del miércoles 18 es
        # el sábado 14.
        events = history_of(by_clave("excel-bloqueado"))
        assert local(events[0].fecha_hora) == datetime(2026, 11, 14, 9, 12, tzinfo=ZONE)


def test_refreshing_equals_a_fresh_load_with_a_custom_calendar(app, prepared):
    calendar = WorkCalendar(
        inicio="08:00",
        fin="19:00",
        feriados=(date(2026, 11, 16), date(2026, 11, 26)),
    )
    later = NOW + timedelta(days=11)

    with app.app_context():
        seed_demo_tickets(now=later, calendar=calendar)
        fresh = date_snapshot()

        db.session.remove()
        empty_tables()

    prepare(app)

    with app.app_context():
        seed_demo_tickets(now=NOW, calendar=calendar)
        seed_demo_tickets(now=later, calendar=calendar)

        assert date_snapshot() == fresh


# --- El calendario laboral que guarda el Administrador ----------------------


def save_calendar(*, franjas, holidays=(), zone="America/Santiago"):
    """Guarda un calendario laboral como lo haría el Administrador.

    El servicio no comprueba el rol (lo hace la ruta), así que sirve cualquier
    persona activa del equipo demo.
    """
    save_work_calendar(
        actor=user("camila.rojas"),
        base_version=0,
        zone_name=zone,
        franjas=franjas,
        holidays=holidays,
    )
    db.session.commit()


def lunch_break_week(days=range(5)):
    """De 09:00 a 13:00 y de 14:00 a 18:00 en los días indicados."""
    return [
        Franja(day, parse_time(start), parse_time(end))
        for day in days
        for start, end in (("09:00", "13:00"), ("14:00", "18:00"))
    ]


def test_the_seed_reads_the_calendar_the_administrator_saved(app, prepared):
    with app.app_context():
        # De lunes a jueves, con pausa de almuerzo, y el martes 17 de noviembre
        # es feriado.
        save_calendar(
            franjas=lunch_break_week(range(4)),
            holidays=[Holiday(date(2026, 11, 17), "Feriado de prueba")],
        )
        clock = resolve_work_calendar().clock

        seed_demo_tickets(now=NOW)

        moments = all_event_times()

        assert moments
        for moment in moments:
            assert clock.is_working_time(moment), local(moment)
            assert local(moment).date() != date(2026, 11, 17)
        # Con el viernes sin trabajo, tampoco hay nada en viernes.
        assert all(local(moment).weekday() < 4 for moment in moments)


def test_the_seed_uses_the_zone_of_the_saved_calendar(app, prepared):
    bogota = ZoneInfo("America/Bogota")

    with app.app_context():
        save_calendar(franjas=lunch_break_week(), zone="America/Bogota")

        seed_demo_tickets(now=NOW)

        for moment in all_event_times():
            when = moment.astimezone(bogota)

            assert when.weekday() < 5, when
            assert time(9, 0) <= when.time() < time(13, 0) or time(14, 0) <= when.time() < time(18, 0), when


def test_the_seed_counts_today_in_the_zone_of_the_saved_calendar(app, prepared):
    bogota = ZoneInfo("America/Bogota")
    # Pasada la medianoche en Santiago (jueves 19, 01:00) en Bogotá todavía es la
    # noche del miércoles 18: «hoy» es el miércoles.
    after_midnight = datetime(2026, 11, 19, 1, 0, tzinfo=ZONE)
    today = replace(
        DEMO_TICKETS[0],
        clave="ticket-de-hoy",
        titulo="Un ticket de hoy",
        hace_dias=0,
        hora="10:40",
        ajustes=(),
    )

    with app.app_context():
        save_calendar(franjas=lunch_break_week(), zone="America/Bogota")

        seed_demo_tickets(now=after_midnight, tickets=(today,))

        created = by_clave("ticket-de-hoy").fecha_creacion.astimezone(bogota)

        assert created == datetime(2026, 11, 18, 10, 40, tzinfo=bogota)


def test_an_explicit_calendar_wins_over_the_saved_one(app, prepared):
    with app.app_context():
        save_calendar(franjas=lunch_break_week(range(4)))

        seed_demo_tickets(now=NOW, calendar=WorkCalendar())

        moments = all_event_times()

        # El guardado no tiene viernes y el explícito (el de por defecto) sí.
        assert any(local(moment).weekday() == 4 for moment in moments)
        for moment in moments:
            assert_inside_the_default_calendar(moment)


def test_a_creation_hour_inside_a_break_moves_to_the_next_working_moment(app, prepared):
    lunch = replace(
        DEMO_TICKETS[0],
        clave="ticket-del-almuerzo",
        titulo="Un ticket creado a la hora de almuerzo",
        hace_dias=2,
        hora="13:30",
        ajustes=(),
    )

    with app.app_context():
        save_calendar(franjas=lunch_break_week())

        seed_demo_tickets(now=NOW, tickets=(lunch,))

        # Dos días laborales antes del miércoles 18 es el lunes 16; las 13:30 caen
        # en la pausa, así que el ticket queda a las 14:00.
        assert local(by_clave("ticket-del-almuerzo").fecha_creacion) == datetime(
            2026, 11, 16, 14, 0, tzinfo=ZONE
        )


def test_refreshing_with_a_saved_calendar_keeps_everything_in_working_time(app, prepared):
    with app.app_context():
        save_calendar(
            franjas=lunch_break_week(),
            holidays=[Holiday(date(2026, 11, 26), "Feriado de prueba")],
        )
        clock = resolve_work_calendar().clock

        seed_demo_tickets(now=NOW)
        seed_demo_tickets(now=NOW + timedelta(days=11))

        assert count(Ticket) == len(DEMO_TICKETS)
        for moment in all_event_times():
            assert clock.is_working_time(moment), local(moment)


def test_validation_with_a_saved_calendar_does_not_compare_hours_with_one_shift():
    early = replace(DEMO_TICKETS[0], hora="07:00")

    with pytest.raises(DemoTicketsError, match="fuera de la jornada"):
        validate_demo_tickets((early,), WorkCalendar())

    # Sin una jornada única con la que compararla, la hora solo debe estar bien
    # escrita: al planificar se pasa a horario laboral.
    validate_demo_tickets((early,), None)

    with pytest.raises(DemoTicketsError, match="formato HH:MM"):
        validate_demo_tickets((replace(DEMO_TICKETS[0], hora="25:00"),), None)
