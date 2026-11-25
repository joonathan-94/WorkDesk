"""Indicadores de SLA (docs/06, RN-169; docs/10, 28.1).

Cada período guarda, además del vencimiento, **cuándo alcanza el umbral de aviso**
(`fecha_umbral_aviso`, en tiempo laboral, calculada al abrirlo). Con esas dos fechas el
estado del SLA de un ticket se puede evaluar por lotes (`evaluate_tickets_sla`, para el
listado) y expresar en SQL (`sla/queries.py`, para filtrar y ordenar antes de paginar).

Los tests fijan «la hora» (`clock`) como los de `test_sla_periods.py`: noviembre de 2026,
con el calendario por defecto (lunes a viernes de 09:00 a 18:00, en Santiago). Valores
de las políticas que carga `seed-catalogs` (primera respuesta, resolución y umbral):
Baja 8 h / 24 h / 80 %, Media 4 h / 12 h / 80 %, Alta 2 h / 6 h / 75 % y
Crítica 30 min / 4 h / 75 %.
"""

from datetime import timedelta

import pytest
from sqlalchemy import delete, event
from sqlalchemy.exc import IntegrityError

from src.workdesk.extensions import db
from src.workdesk.models import PeriodoSla, Ticket
from src.workdesk.sla.evaluation import (
    SlaStatus,
    evaluate_ticket_sla,
    evaluate_tickets_sla,
)
from src.workdesk.sla.periods import list_periods, warning_seconds
from src.workdesk.sla.queries import (
    SLA_PARTITION,
    SlaFilter,
    filter_of,
    sla_condition,
    sla_urgency_order,
)
from src.workdesk.sla.rebuild import fill_missing_warning_dates
from src.workdesk.sla.work_calendar import save_work_calendar
from src.workdesk.worktime import Franja, parse_time
from tests.sla_helpers import (
    at,
    close,
    hold,
    new_ticket,
    policy_of,
    reopen,
    resolve,
    resume,
    set_priority,
    work_on,
)
from tests.ticket_helpers import person

SECOND = timedelta(seconds=1)


# --- Auxiliares -------------------------------------------------------------------------


@pytest.fixture()
def staff(make_user, catalog):
    return make_user("TECNICO", username="tecnico")


def open_period(ticket) -> PeriodoSla:
    (period,) = [p for p in list_periods(ticket.id) if p.fecha_fin is None]

    return period


# --- La fecha de aviso se guarda al abrir el período ----------------------------------


def test_a_running_period_stores_when_the_warning_threshold_is_reached(
    app, clock, staff, catalog
):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        period = open_period(ticket)

        # 12 h de objetivo y 80 % de umbral: el aviso llega a las 9 h 36 min de tiempo
        # laboral. Desde el lunes a las 10:00 quedan 8 h ese día y 1 h 36 min el martes.
        assert period.umbral_aviso_porcentaje == 80
        assert period.fecha_umbral_aviso == at(17, 10, 36)
        assert period.fecha_vencimiento_resolucion == at(17, 13)


def test_the_warning_date_follows_the_priority_policy(app, clock, staff, catalog):
    with app.app_context():
        period = open_period(new_ticket(catalog, staff["id"], "ALTA"))

        # 6 h y 75 %: a las 4 h 30 min (el vencimiento, a las 6 h).
        assert period.umbral_aviso_porcentaje == 75
        assert period.fecha_umbral_aviso == at(16, 14, 30)
        assert period.fecha_vencimiento_resolucion == at(16, 16)


def test_a_paused_period_has_no_warning_date_but_keeps_the_threshold(
    app, clock, staff, catalog
):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        clock.set(at(16, 11))
        work_on(ticket, staff["id"])
        clock.set(at(16, 12))
        hold(ticket, staff["id"])
        paused = open_period(ticket)

        assert paused.esta_pausado
        assert paused.fecha_umbral_aviso is None
        assert paused.umbral_aviso_porcentaje == 80


def test_resuming_computes_the_warning_with_what_is_left(app, clock, staff, catalog):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        clock.set(at(16, 11))
        work_on(ticket, staff["id"])
        clock.set(at(16, 12))
        hold(ticket, staff["id"])
        clock.set(at(16, 14))
        resume(ticket, staff["id"])
        resumed = open_period(ticket)

        # Consumió 2 h (de 10:00 a 12:00): quedan 7 h 36 min hasta el aviso. Del lunes a
        # las 14:00 sirven 4 h y las 3 h 36 min restantes caen el martes.
        assert resumed.fecha_umbral_aviso == at(17, 12, 36)
        # Y 10 h hasta el vencimiento: 4 h el lunes y 6 h el martes.
        assert resumed.fecha_vencimiento_resolucion == at(17, 15)


def test_a_new_period_keeps_the_threshold_it_had_even_if_the_policy_changes(
    app, clock, staff, catalog
):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        policy_of("MEDIA").umbral_aviso_consumo_porcentaje = 50
        db.session.commit()
        clock.set(at(16, 11))
        work_on(ticket, staff["id"])
        clock.set(at(16, 12))
        hold(ticket, staff["id"])
        clock.set(at(16, 13))
        resume(ticket, staff["id"])

        # Las condiciones se heredan: editar la política no cambia el SLA en curso.
        assert open_period(ticket).umbral_aviso_porcentaje == 80

        # Un cambio de prioridad sí toma la política vigente de la prioridad nueva.
        policy_of("ALTA").umbral_aviso_consumo_porcentaje = 50
        db.session.commit()
        set_priority(ticket, staff["id"], "ALTA")

        assert open_period(ticket).umbral_aviso_porcentaje == 50


def test_a_policy_without_a_threshold_never_warns(app, clock, staff, catalog):
    with app.app_context():
        policy_of("ALTA").umbral_aviso_consumo_porcentaje = None
        db.session.commit()
        ticket = new_ticket(catalog, staff["id"], "ALTA")
        period = open_period(ticket)

        assert period.umbral_aviso_porcentaje is None
        assert period.fecha_umbral_aviso is None

        # Ni siquiera casi vencido: solo «dentro de plazo» hasta que vence.
        snapshot = evaluate_ticket_sla(ticket.id, now=at(16, 16) - SECOND)

        assert snapshot.status is SlaStatus.DENTRO


def test_a_period_born_past_the_warning_threshold_warns_from_the_start(
    app, clock, staff, catalog
):
    with app.app_context():
        clock.set(at(16, 9))
        ticket = new_ticket(catalog, staff["id"], "BAJA")
        clock.set(at(16, 14))
        set_priority(ticket, staff["id"], "ALTA")
        period = open_period(ticket)

        # Lleva 5 h (de 9:00 a 14:00) y el aviso de Alta está en las 4 h 30 min: ya pasó.
        assert period.fecha_inicio == at(16, 14)
        assert period.fecha_umbral_aviso == at(16, 14)
        assert evaluate_ticket_sla(ticket.id, now=at(16, 14)).status is (
            SlaStatus.PROXIMO_A_VENCER
        )


# --- El umbral exacto ---------------------------------------------------------------------


@pytest.mark.parametrize("objective", [60, 420, 3600, 21600, 43200, 86400, 61 * 60, 7 * 60])
@pytest.mark.parametrize("percent", list(range(1, 101)))
def test_the_warning_is_the_first_second_that_reaches_the_percentage(objective, percent):
    consumed = warning_seconds(objective, percent)

    # `consumido * 100 // objetivo` es el porcentaje que muestra la pantalla: el aviso llega
    # justo en el primer segundo en que lo alcanza.
    assert consumed * 100 // objective >= percent
    assert (consumed - 1) * 100 // objective < percent
    assert consumed <= objective


def test_the_warning_rounds_up_when_the_percentage_is_not_a_whole_second():
    # 7 min = 420 s; 33 % son 138,6 s: a los 138 s todavía es el 32 %.
    assert warning_seconds(420, 33) == 139


def test_a_ticket_warns_exactly_at_its_warning_date_and_expires_at_its_due_date(
    app, clock, staff, catalog
):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "ALTA")
        warn, due = at(16, 14, 30), at(16, 16)

        def status(moment):
            return evaluate_ticket_sla(ticket.id, now=moment).status

        assert status(warn - SECOND) is SlaStatus.DENTRO
        assert status(warn) is SlaStatus.PROXIMO_A_VENCER
        assert status(due - SECOND) is SlaStatus.PROXIMO_A_VENCER
        assert status(due) is SlaStatus.VENCIDO
        assert status(due + timedelta(hours=3)) is SlaStatus.VENCIDO


def test_a_stopped_ticket_that_used_most_of_its_time_is_not_about_to_expire(
    app, clock, staff, catalog
):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "ALTA")
        clock.set(at(16, 15, 20))
        resolve(ticket, staff["id"])
        snapshot = evaluate_ticket_sla(ticket.id, now=at(16, 15, 30))

        # Llevaba 5 h 20 min de 6 h (el 88 %), pero su reloj está detenido: ya no hay nada
        # «próximo a vencer».
        assert snapshot.percent == 88
        assert snapshot.closed
        assert snapshot.status is SlaStatus.DENTRO


def test_a_period_without_a_warning_date_never_reads_as_about_to_expire(
    app, clock, staff, catalog
):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "ALTA")
        open_period(ticket).fecha_umbral_aviso = None
        db.session.commit()

        # Es lo que tienen los períodos anteriores a esta versión hasta `sla-rebuild`.
        snapshot = evaluate_ticket_sla(ticket.id, now=at(16, 15, 30))

        assert snapshot.percent == 91
        assert snapshot.status is SlaStatus.DENTRO


# --- Restricciones de la base de datos ----------------------------------------------------


@pytest.mark.parametrize(
    "changes",
    [
        {"umbral_aviso_porcentaje": 0},
        {"umbral_aviso_porcentaje": 101},
        {"umbral_aviso_porcentaje": -5},
        # Después del vencimiento.
        {"fecha_umbral_aviso": at(16, 16) + SECOND},
        # Antes del inicio.
        {"fecha_umbral_aviso": at(16, 10) - SECOND},
    ],
)
def test_the_database_rejects_an_impossible_warning(app, clock, staff, catalog, changes):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "ALTA")
        period = open_period(ticket)

        for field, value in changes.items():
            setattr(period, field, value)

        with pytest.raises(IntegrityError):
            db.session.flush()

        db.session.rollback()


def test_the_database_rejects_a_warning_date_on_a_paused_period(app, clock, staff, catalog):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "ALTA")
        clock.set(at(16, 11))
        work_on(ticket, staff["id"])
        clock.set(at(16, 12))
        hold(ticket, staff["id"])
        paused = open_period(ticket)
        paused.fecha_umbral_aviso = at(16, 13)

        with pytest.raises(IntegrityError):
            db.session.flush()

        db.session.rollback()


def test_the_database_accepts_a_warning_exactly_at_the_start_and_at_the_due_date(
    app, clock, staff, catalog
):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "ALTA")
        period = open_period(ticket)

        period.fecha_umbral_aviso = period.fecha_inicio
        db.session.flush()
        period.fecha_umbral_aviso = period.fecha_vencimiento_resolucion
        db.session.flush()


# --- Los escenarios ------------------------------------------------------------------------


@pytest.fixture()
def scenarios(app, clock, staff, catalog):
    """Tickets en cada situación que importa para el estado del SLA. Todos los
    eventos ocurren el lunes 16 entre las 09:00 y las 15:30."""
    made = {}
    me = staff["id"]

    with app.app_context():

        def create(name, code, moment):
            clock.set(moment)
            made[name] = new_ticket(catalog, me, code)

            return made[name]

        create("dentro", "MEDIA", at(16, 10))
        create("alta", "ALTA", at(16, 10))

        ticket = create("pausado", "CRITICA", at(16, 10))
        clock.set(at(16, 10, 30))
        work_on(ticket, me)
        clock.set(at(16, 11))
        hold(ticket, me)

        ticket = create("resuelto", "ALTA", at(16, 10))
        clock.set(at(16, 11))
        resolve(ticket, me)

        # Se resuelve después de vencer (a las 15:00).
        ticket = create("resuelto_vencido", "ALTA", at(16, 9))
        clock.set(at(16, 15, 20))
        resolve(ticket, me)

        ticket = create("reabierto", "ALTA", at(16, 10))
        clock.set(at(16, 12))
        resolve(ticket, me)
        clock.set(at(16, 13, 30))
        reopen(ticket, me)

        # Sube de prioridad con más consumo que el objetivo nuevo: nace vencido.
        ticket = create("sube_vencido", "BAJA", at(16, 9))
        clock.set(at(16, 14))
        set_priority(ticket, me, "CRITICA")

        # Lo mismo, pero con el ticket en espera: nace pausado y ya consumido de más.
        ticket = create("pausado_vencido", "BAJA", at(16, 9))
        clock.set(at(16, 9, 30))
        work_on(ticket, me)
        clock.set(at(16, 14))
        hold(ticket, me)
        clock.set(at(16, 14, 10))
        set_priority(ticket, me, "CRITICA")

        # Venció y después bajó de prioridad: el incumplimiento no se borra.
        ticket = create("baja_tras_vencer", "ALTA", at(16, 9))
        clock.set(at(16, 15, 10))
        set_priority(ticket, me, "MEDIA")

        ticket = create("cerrado", "ALTA", at(16, 10))
        clock.set(at(16, 11))
        close(ticket, me)

        ticket = create("cerrado_pausado", "CRITICA", at(16, 10))
        clock.set(at(16, 10, 10))
        work_on(ticket, me)
        clock.set(at(16, 10, 20))
        hold(ticket, me)
        clock.set(at(16, 11))
        close(ticket, me)

        # Los que no tienen un período vigente con su estado: sin política, sin períodos
        # (anteriores al SLA) y sin fecha de aviso (anteriores a esta versión).
        ticket = create("sin_periodos", "MEDIA", at(16, 10))
        db.session.execute(delete(PeriodoSla).where(PeriodoSla.ticket_id == ticket.id))

        ticket = create("sin_aviso", "MEDIA", at(16, 10))
        open_period(ticket).fecha_umbral_aviso = None

        policy_of("BAJA").activo = False
        db.session.commit()
        create("sin_politica", "BAJA", at(16, 10))

        return {name: ticket.id for name, ticket in made.items()}


def moments_to_check(ids):
    """La rejilla de momentos en que se compara: cada media hora de lunes a jueves y los
    bordes (un segundo antes, en y después) de cada fecha guardada."""
    moments = set()
    start = at(16, 15, 30)

    for step in range(3 * 24 * 2):
        moments.add(start + timedelta(minutes=30 * step))

    for period in db.session.scalars(
        db.select(PeriodoSla).where(PeriodoSla.ticket_id.in_(ids))
    ):
        for date in (
            period.fecha_umbral_aviso,
            period.fecha_vencimiento_resolucion,
            period.fecha_fin,
        ):
            if date is not None:
                moments.update({date - SECOND, date, date + SECOND})

    return sorted(m for m in moments if m >= at(16, 15, 30))


# --- La evaluación por lotes -----------------------------------------------------------------


def test_the_batch_gives_the_same_result_as_one_ticket_at_a_time(app, scenarios):
    with app.app_context():
        ids = list(scenarios.values())

        for now in (at(16, 15, 30), at(16, 16, 30), at(17, 10, 36), at(17, 13), at(19, 9)):
            batch = evaluate_tickets_sla(ids, now)

            assert set(batch) == set(ids)

            for ticket_id in ids:
                single = evaluate_tickets_sla([ticket_id], now)[ticket_id]

                assert batch[ticket_id] == single


def test_evaluate_ticket_sla_is_the_batch_for_one_ticket(app, scenarios):
    with app.app_context():
        ticket_id = scenarios["alta"]
        now = at(16, 15, 30)

        assert evaluate_ticket_sla(ticket_id, now) == evaluate_tickets_sla([ticket_id], now)[
            ticket_id
        ]


def test_the_scenarios_cover_every_status_and_a_ticket_without_sla(app, scenarios):
    with app.app_context():
        found = {
            filter_of(snapshot)
            for snapshot in evaluate_tickets_sla(scenarios.values(), at(16, 15, 30)).values()
        }

        assert found == set(SLA_PARTITION)


def test_the_expected_status_of_each_scenario(app, scenarios):
    with app.app_context():
        now = at(16, 15, 30)
        result = evaluate_tickets_sla(scenarios.values(), now)

        def status(name):
            snapshot = result[scenarios[name]]

            return None if snapshot is None else snapshot.status

        # Media: 12 h, aviso a las 9 h 36 min: lleva 5 h 30 min.
        assert status("dentro") is SlaStatus.DENTRO
        # Alta: venció a las 16:00 y el aviso fue a las 14:30.
        assert status("alta") is SlaStatus.PROXIMO_A_VENCER
        assert status("pausado") is SlaStatus.PAUSADO
        assert status("resuelto") is SlaStatus.DENTRO
        assert status("resuelto_vencido") is SlaStatus.VENCIDO
        assert status("reabierto") is SlaStatus.DENTRO
        assert status("sube_vencido") is SlaStatus.VENCIDO
        assert status("pausado_vencido") is SlaStatus.VENCIDO
        assert status("baja_tras_vencer") is SlaStatus.VENCIDO
        assert status("cerrado") is SlaStatus.DENTRO
        assert status("cerrado_pausado") is SlaStatus.DENTRO
        assert status("sin_periodos") is None
        assert status("sin_politica") is None
        # Sin fecha de aviso nunca llega a «próximo a vencer».
        assert status("sin_aviso") is SlaStatus.DENTRO


def test_an_unknown_or_repeated_id_and_an_empty_list(app, scenarios):
    with app.app_context():
        ticket_id = scenarios["dentro"]
        result = evaluate_tickets_sla([ticket_id, ticket_id, 987654], at(16, 15, 30))

        assert set(result) == {ticket_id, 987654}
        assert result[987654] is None
        assert evaluate_tickets_sla([], at(16, 15, 30)) == {}


def test_evaluating_many_tickets_costs_the_same_number_of_queries_as_one(app, scenarios):
    with app.app_context():
        ids = list(scenarios.values())
        statements = []

        def count(conn, cursor, statement, *args):
            statements.append(statement)

        def measure(selection):
            db.session.expire_all()
            statements.clear()
            evaluate_tickets_sla(selection, at(16, 15, 30))

            return len(statements)

        event.listen(db.engine, "before_cursor_execute", count)

        try:
            one = measure(ids[:1])
            all_of_them = measure(ids)
        finally:
            event.remove(db.engine, "before_cursor_execute", count)

        assert len(ids) == 14
        # Los períodos, los estados, las primeras respuestas y el calendario: no depende
        # de cuántos tickets se evalúen.
        assert all_of_them <= one + 2
        assert all_of_them <= 8


def test_tickets_with_different_calendars_are_evaluated_with_their_own(
    app, clock, staff, catalog
):
    with app.app_context():
        first = new_ticket(catalog, staff["id"], "ALTA")
        # Un calendario nuevo con jornadas de 09:00 a 13:00: el período del primer ticket
        # sigue con el calendario por defecto con que se calculó.
        save_work_calendar(
            actor=person(staff["id"]),
            base_version=0,
            zone_name="America/Santiago",
            franjas=[Franja(day, parse_time("09:00"), parse_time("13:00")) for day in range(5)],
            holidays=[],
            reason=None,
        )
        db.session.commit()
        second = new_ticket(catalog, staff["id"], "ALTA")
        result = evaluate_tickets_sla([first.id, second.id], at(16, 12))

        # Las dos llevan 2 h desde las 10:00 (las dos jornadas cubren esas horas)...
        assert result[first.id].consumed_seconds == 2 * 3600
        assert result[second.id].consumed_seconds == 2 * 3600
        # ...pero el vencimiento (6 h) cambia: 8 h útiles el lunes frente a 3 h y 3 h el martes.
        assert result[first.id].due_at == at(16, 16)
        assert result[second.id].due_at == at(17, 12)
        assert open_period(first).calendario_laboral_id is None
        assert open_period(second).calendario_laboral_id is not None


# --- Las condiciones SQL son el equivalente exacto de la evaluación -----------------------


def sql_selection(option, now, ids):
    return set(
        db.session.scalars(
            db.select(Ticket.id).where(Ticket.id.in_(ids), sla_condition(option, now))
        )
    )


def test_the_sql_conditions_select_exactly_what_the_evaluation_says(app, scenarios):
    with app.app_context():
        ids = list(scenarios.values())
        checked = 0

        for now in moments_to_check(ids):
            expected = {option: set() for option in SLA_PARTITION}

            for ticket_id, snapshot in evaluate_tickets_sla(ids, now).items():
                expected[filter_of(snapshot)].add(ticket_id)

            for option in SLA_PARTITION:
                assert sql_selection(option, now, ids) == expected[option], (option, now)

            checked += 1

        assert checked > 150


def test_every_ticket_is_in_exactly_one_option_of_the_filter(app, scenarios):
    with app.app_context():
        ids = list(scenarios.values())

        for now in (at(16, 15, 30), at(16, 16), at(17, 10, 36), at(17, 13), at(20, 12)):
            selections = [sql_selection(option, now, ids) for option in SLA_PARTITION]

            assert sum(len(selection) for selection in selections) == len(ids)
            assert set().union(*selections) == set(ids)


def test_at_risk_is_the_union_of_close_to_due_and_overdue(app, scenarios):
    with app.app_context():
        ids = list(scenarios.values())

        for now in moments_to_check(ids):
            at_risk = sql_selection(SlaFilter.RIESGO, now, ids)

            assert at_risk == sql_selection(SlaFilter.PROXIMO, now, ids) | sql_selection(
                SlaFilter.VENCIDO, now, ids
            )


def test_a_ticket_that_changes_option_over_time_does_it_at_its_dates(
    app, clock, staff, catalog
):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "ALTA")
        warn, due = at(16, 14, 30), at(16, 16)

        def option_at(moment):
            return next(
                option
                for option in SLA_PARTITION
                if sql_selection(option, moment, [ticket.id])
            )

        assert option_at(warn - SECOND) is SlaFilter.DENTRO
        assert option_at(warn) is SlaFilter.PROXIMO
        assert option_at(due - SECOND) is SlaFilter.PROXIMO
        assert option_at(due) is SlaFilter.VENCIDO


def test_the_urgency_order_puts_the_nearest_due_date_first_and_the_rest_last(
    app, scenarios
):
    with app.app_context():
        ids = list(scenarios.values())
        ordered = list(
            db.session.scalars(
                db.select(Ticket.id).where(Ticket.id.in_(ids)).order_by(*sla_urgency_order())
            )
        )
        due_by_ticket = {
            ticket_id: next(
                (
                    p.fecha_vencimiento_resolucion
                    for p in list_periods(ticket_id)
                    if p.fecha_fin is None
                ),
                None,
            )
            for ticket_id in ids
        }
        with_clock = [t for t in ordered if due_by_ticket[t] is not None]
        without_clock = [t for t in ordered if due_by_ticket[t] is None]

        # Primero los que tienen reloj en marcha, por vencimiento; después los demás.
        assert ordered == with_clock + without_clock
        assert [due_by_ticket[t] for t in with_clock] == sorted(
            due_by_ticket[t] for t in with_clock
        )
        assert len(without_clock) >= 4


# --- El relleno de las fechas de aviso --------------------------------------------------------


def test_filling_the_missing_warning_dates_restores_the_one_computed_at_opening(
    app, clock, staff, catalog
):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        period = open_period(ticket)
        original = period.fecha_umbral_aviso
        period.fecha_umbral_aviso = None
        db.session.commit()

        assert fill_missing_warning_dates() == 1
        assert open_period(ticket).fecha_umbral_aviso == original
        # Es idempotente.
        assert fill_missing_warning_dates() == 0


def test_filling_takes_into_account_what_the_ticket_already_consumed(
    app, clock, staff, catalog
):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        clock.set(at(16, 11))
        work_on(ticket, staff["id"])
        clock.set(at(16, 12))
        hold(ticket, staff["id"])
        clock.set(at(16, 14))
        resume(ticket, staff["id"])
        period = open_period(ticket)
        original = period.fecha_umbral_aviso
        period.fecha_umbral_aviso = None
        db.session.commit()

        assert fill_missing_warning_dates() == 1
        assert open_period(ticket).fecha_umbral_aviso == original == at(17, 12, 36)


def test_filling_leaves_closed_paused_and_thresholdless_periods_alone(
    app, clock, staff, catalog
):
    with app.app_context():
        closed = new_ticket(catalog, staff["id"], "ALTA")
        clock.set(at(16, 11))
        resolve(closed, staff["id"])
        paused = new_ticket(catalog, staff["id"], "ALTA")
        clock.set(at(16, 11, 10))
        work_on(paused, staff["id"])
        clock.set(at(16, 11, 20))
        hold(paused, staff["id"])
        no_threshold = new_ticket(catalog, staff["id"], "ALTA")
        period = open_period(no_threshold)
        period.umbral_aviso_porcentaje = None
        period.fecha_umbral_aviso = None
        db.session.commit()
        before = [(p.id, p.fecha_umbral_aviso) for p in db.session.scalars(
            db.select(PeriodoSla).order_by(PeriodoSla.id)
        )]

        assert fill_missing_warning_dates() == 0
        assert [(p.id, p.fecha_umbral_aviso) for p in db.session.scalars(
            db.select(PeriodoSla).order_by(PeriodoSla.id)
        )] == before
