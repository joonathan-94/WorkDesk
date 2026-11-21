"""Períodos de SLA de los tickets (docs/09, 20.3; docs/06, RN-166).

Un ticket acumula períodos: tramos bajo unas mismas condiciones de SLA. Cambiar la
prioridad o el estado cierra el vigente y abre otro, sin reiniciar el reloj. Los
tests fijan «la hora» (`clock`) para que el tiempo laboral sea determinista:
noviembre de 2026, con el calendario por defecto (lunes a viernes de 09:00 a 18:00,
en Santiago). El lunes 16 es el primer día; el 21 y el 22 son fin de semana.

Valores de las políticas que carga `seed-catalogs` (primera respuesta, resolución y
umbral): Baja 8 h / 24 h / 80 %, Media 4 h / 12 h / 80 %, Alta 2 h / 6 h / 75 % y
Crítica 30 min / 4 h / 75 %.
"""

import threading
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from src.workdesk.extensions import db
from src.workdesk.models import (
    Comment,
    Estado,
    PeriodoSla,
    PoliticaSla,
    Prioridad,
    StateAction,
    Ticket,
    TicketHistory,
    TicketRequester,
)
from src.workdesk.models.comment import CommentType
from src.workdesk.sla import periods
from src.workdesk.sla.periods import (
    SlaStatus,
    accumulated_seconds,
    current_time,
    evaluate_ticket_sla,
    first_response_at,
    list_periods,
    rebuild_periods,
    rebuild_ticket_periods,
    reconcile_sla,
)
from src.workdesk.sla.work_calendar import save_work_calendar
from src.workdesk.tickets.comments import add_comment, delete_comment
from src.workdesk.tickets.editing import change_priority
from src.workdesk.tickets.lifecycle import change_state
from src.workdesk.tickets.service import TicketRuleError, create_ticket
from src.workdesk.tickets.versioning import TicketConflictError
from src.workdesk.worktime import Franja, parse_time
from tests.ticket_helpers import person

ZONE = ZoneInfo("America/Santiago")
HOUR = 3600


def at(day, hour=0, minute=0):
    """Un momento de noviembre de 2026 en Santiago (lun 16 ... vie 20, sáb 21)."""
    return datetime(2026, 11, day, hour, minute, tzinfo=ZONE)


# --- Auxiliares -------------------------------------------------------------


class FakeClock:
    """«La hora» que ven los períodos: se mueve a mano."""

    def __init__(self):
        self.now = at(16, 10)

    def set(self, moment):
        self.now = moment


@pytest.fixture()
def clock(app, monkeypatch):
    app.config["APP_TIMEZONE"] = "America/Santiago"
    fake = FakeClock()
    monkeypatch.setattr(periods, "current_time", lambda: fake.now)

    return fake


@pytest.fixture()
def staff(make_user, catalog):
    return make_user("TECNICO", username="tecnico")


@pytest.fixture()
def other_staff(make_user, staff):
    return make_user("TECNICO", username="otro_tecnico")


@pytest.fixture()
def requester(make_user, catalog):
    return make_user("SOLICITANTE", username="solicitante")


def priority_id(code) -> int:
    return db.session.scalar(db.select(Prioridad.id).where(Prioridad.codigo == code))


def policy_of(code) -> PoliticaSla:
    return db.session.scalar(
        db.select(PoliticaSla)
        .join(Prioridad, Prioridad.id == PoliticaSla.prioridad_id)
        .where(Prioridad.codigo == code)
    )


def new_ticket(catalog, creator_id, code="MEDIA") -> Ticket:
    ticket = create_ticket(
        actor=person(creator_id),
        title="Problema con el correo",
        description="No puedo enviar mensajes.",
        category_id=catalog["hardware"],
        priority_id=priority_id(code),
    )
    db.session.commit()

    return ticket


def act(ticket, actor_id, action, **extra) -> None:
    change_state(
        ticket,
        actor=person(actor_id),
        action=action,
        expected_version=ticket.version,
        **extra,
    )
    db.session.commit()


def set_priority(ticket, actor_id, code, reason="Cambia el impacto") -> None:
    change_priority(
        ticket,
        actor=person(actor_id),
        expected_version=ticket.version,
        priority_id=priority_id(code),
        reason=reason,
    )
    db.session.commit()


def work_on(ticket, actor_id) -> None:
    act(ticket, actor_id, StateAction.INICIAR)


def hold(ticket, actor_id) -> None:
    act(ticket, actor_id, StateAction.PONER_EN_ESPERA)


def resume(ticket, actor_id) -> None:
    act(ticket, actor_id, StateAction.REACTIVAR)


def resolve(ticket, actor_id) -> None:
    act(ticket, actor_id, StateAction.RESOLVER)


def reopen(ticket, actor_id) -> None:
    act(ticket, actor_id, StateAction.REABRIR)


def close(ticket, actor_id) -> None:
    act(ticket, actor_id, StateAction.CIERRE_DIRECTO)


def shape(period: PeriodoSla) -> tuple:
    """Lo que identifica un período, sin ids."""
    return (
        period.prioridad_id,
        period.fecha_inicio,
        period.fecha_fin,
        period.segundos_consumidos,
        period.fecha_vencimiento_respuesta,
        period.fecha_vencimiento_resolucion,
        period.pausa_en_espera,
        period.usuario_cambio_id,
        period.motivo_cambio,
    )


def shapes(ticket) -> list[tuple]:
    return [shape(p) for p in list_periods(ticket.id)]


def open_periods(ticket) -> list[PeriodoSla]:
    return [p for p in list_periods(ticket.id) if p.fecha_fin is None]


# --- Al crear el ticket ----------------------------------------------------------


def test_creating_a_ticket_opens_a_running_period_with_its_priority_policy(
    app, clock, staff, catalog
):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        (period,) = list_periods(ticket.id)

        assert period.prioridad_id == priority_id("MEDIA")
        assert period.politica_sla_id == policy_of("MEDIA").id
        assert period.fecha_inicio == at(16, 10)
        assert period.fecha_fin is None
        assert period.segundos_consumidos == 0
        assert period.tiempo_objetivo_respuesta_minutos == 240
        assert period.tiempo_objetivo_resolucion_minutos == 720
        assert period.pausa_en_espera is True
        # Sin calendario guardado se usa el de por defecto: sin fila.
        assert period.calendario_laboral_id is None
        assert period.usuario_cambio_id is None
        assert period.motivo_cambio is None
        assert period.esta_vigente
        assert not period.esta_pausado


def test_the_due_dates_are_counted_in_working_time(app, clock, staff, catalog):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        (period,) = list_periods(ticket.id)

        # Lunes 10:00 + 4 h = lunes 14:00; + 12 h = lunes 8 h y martes 4 h.
        assert period.fecha_vencimiento_respuesta == at(16, 14)
        assert period.fecha_vencimiento_resolucion == at(17, 13)


def test_a_ticket_created_on_friday_afternoon_skips_the_weekend(
    app, clock, staff, catalog
):
    with app.app_context():
        clock.set(at(20, 17))
        ticket = new_ticket(catalog, staff["id"], "CRITICA")
        (period,) = list_periods(ticket.id)

        # Crítica: 30 min y 4 h. Queda 1 h el viernes y 3 h el lunes.
        assert period.fecha_vencimiento_respuesta == at(20, 17, 30)
        assert period.fecha_vencimiento_resolucion == at(23, 12)


def test_a_ticket_created_out_of_hours_starts_counting_when_work_starts(
    app, clock, staff, catalog
):
    with app.app_context():
        clock.set(at(21, 11))  # sábado
        ticket = new_ticket(catalog, staff["id"], "CRITICA")
        (period,) = list_periods(ticket.id)

        assert period.fecha_inicio == at(21, 11)
        assert period.fecha_vencimiento_resolucion == at(23, 13)


def test_a_priority_without_an_active_policy_has_no_sla(app, clock, staff, catalog):
    with app.app_context():
        policy_of("MEDIA").activo = False
        db.session.commit()

        ticket = new_ticket(catalog, staff["id"], "MEDIA")

        assert list_periods(ticket.id) == []
        assert evaluate_ticket_sla(ticket.id) is None


def test_a_ticket_without_sla_gets_it_when_it_moves_to_a_priority_with_policy(
    app, clock, staff, catalog
):
    with app.app_context():
        policy_of("MEDIA").activo = False
        db.session.commit()
        ticket = new_ticket(catalog, staff["id"], "MEDIA")

        clock.set(at(16, 15))
        set_priority(ticket, staff["id"], "ALTA")
        (period,) = list_periods(ticket.id)

        # Empieza cuando recibe una prioridad con SLA: lo anterior no cuenta.
        assert period.prioridad_id == priority_id("ALTA")
        assert period.fecha_inicio == at(16, 15)
        # Alta: 6 h desde el lunes 15:00 son 3 h ese día y 3 h el martes.
        assert period.fecha_vencimiento_resolucion == at(17, 12)


def test_reconciling_again_changes_nothing(app, clock, staff, catalog):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        before = shapes(ticket)

        clock.set(at(16, 15))
        same = reconcile_sla(ticket, person(staff["id"]))

        assert shapes(ticket) == before
        assert same.id == list_periods(ticket.id)[0].id


def test_a_failed_creation_leaves_no_period(app, clock, staff, catalog):
    with app.app_context():
        with pytest.raises(TicketRuleError):
            create_ticket(
                actor=person(staff["id"]),
                title="",
                description="x",
                category_id=catalog["hardware"],
                priority_id=priority_id("MEDIA"),
            )

        db.session.rollback()
        assert db.session.scalar(db.select(db.func.count(PeriodoSla.id))) == 0


# --- La pausa en espera -----------------------------------------------------------


def test_putting_a_ticket_on_hold_closes_the_period_and_opens_a_paused_one(
    app, clock, staff, catalog
):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")

        clock.set(at(16, 11))
        work_on(ticket, staff["id"])
        # Empezar a trabajar no cambia el reloj.
        assert len(list_periods(ticket.id)) == 1

        clock.set(at(16, 14))
        hold(ticket, staff["id"])
        first, paused = list_periods(ticket.id)

        assert first.fecha_fin == at(16, 14)
        assert first.segundos_consumidos == 4 * HOUR
        assert paused.fecha_inicio == at(16, 14)
        assert paused.fecha_fin is None
        assert paused.esta_pausado
        assert paused.fecha_vencimiento_resolucion is None
        assert paused.fecha_vencimiento_respuesta is None
        assert paused.usuario_cambio_id == staff["id"]
        # Hereda los objetivos del período anterior.
        assert paused.tiempo_objetivo_resolucion_minutos == 720


def test_resuming_opens_a_period_with_what_is_left_of_the_objective(
    app, clock, staff, catalog
):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        clock.set(at(16, 11))
        work_on(ticket, staff["id"])
        clock.set(at(16, 14))
        hold(ticket, staff["id"])

        clock.set(at(17, 10))
        resume(ticket, staff["id"])
        _first, paused, running = list_periods(ticket.id)

        # El tiempo en espera no consumió nada.
        assert paused.fecha_fin == at(17, 10)
        assert paused.segundos_consumidos == 0
        assert running.fecha_inicio == at(17, 10)
        assert running.esta_vigente and not running.esta_pausado
        # Quedan 8 h de las 12 h: martes de 10:00 a 18:00.
        assert running.fecha_vencimiento_resolucion == at(17, 18)
        # La primera respuesta (4 h) ya estaba consumida: nace vencida.
        assert running.fecha_vencimiento_respuesta == at(17, 10)
        assert accumulated_seconds(ticket.id) == 4 * HOUR


def test_time_on_hold_never_counts_even_over_several_days(app, clock, staff, catalog):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        work_on(ticket, staff["id"])
        clock.set(at(16, 14))
        hold(ticket, staff["id"])

        clock.set(at(20, 10))
        snapshot = evaluate_ticket_sla(ticket.id)

        assert snapshot.status is SlaStatus.PAUSADO
        assert snapshot.consumed_seconds == 4 * HOUR
        assert snapshot.due_at is None

        resume(ticket, staff["id"])
        assert evaluate_ticket_sla(ticket.id).consumed_seconds == 4 * HOUR


def test_a_policy_that_does_not_pause_keeps_the_clock_running(
    app, clock, staff, catalog
):
    with app.app_context():
        policy_of("MEDIA").pausa_en_espera = False
        db.session.commit()
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        work_on(ticket, staff["id"])

        clock.set(at(16, 14))
        hold(ticket, staff["id"])
        (period,) = list_periods(ticket.id)

        assert period.fecha_fin is None
        assert not period.esta_pausado
        assert period.pausa_en_espera is False


def test_a_new_period_keeps_the_terms_the_ticket_already_had(
    app, clock, staff, catalog
):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        work_on(ticket, staff["id"])

        # El Administrador edita la política mientras el ticket está en curso.
        policy = policy_of("MEDIA")
        policy.tiempo_objetivo_resolucion_minutos = 60
        policy.tiempo_objetivo_respuesta_minutos = 30
        db.session.commit()

        clock.set(at(16, 14))
        hold(ticket, staff["id"])
        clock.set(at(17, 10))
        resume(ticket, staff["id"])

        for period in list_periods(ticket.id):
            assert period.tiempo_objetivo_resolucion_minutos == 720
            assert period.tiempo_objetivo_respuesta_minutos == 240


# --- Cambios de prioridad (RN-88) --------------------------------------------------------


def test_a_priority_change_keeps_what_was_consumed(app, clock, staff, catalog):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")

        clock.set(at(16, 15))
        set_priority(ticket, staff["id"], "ALTA", "Afecta a más personas")
        first, second = list_periods(ticket.id)

        assert first.fecha_fin == at(16, 15)
        assert first.segundos_consumidos == 5 * HOUR
        assert second.prioridad_id == priority_id("ALTA")
        assert second.politica_sla_id == policy_of("ALTA").id
        assert second.tiempo_objetivo_resolucion_minutos == 360
        # Alta: 6 h, ya consumió 5 h: queda 1 h.
        assert second.fecha_vencimiento_resolucion == at(16, 16)
        # La primera respuesta (2 h) ya estaba consumida: nace vencida.
        assert second.fecha_vencimiento_respuesta == at(16, 15)


def test_the_new_period_records_who_changed_the_priority_and_why(
    app, clock, staff, catalog
):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")

        clock.set(at(16, 15))
        set_priority(ticket, staff["id"], "ALTA", "Afecta a más personas")
        first, second = list_periods(ticket.id)

        assert first.usuario_cambio_id is None
        assert second.usuario_cambio_id == staff["id"]
        assert second.motivo_cambio == "Afecta a más personas"


def test_raising_the_priority_above_what_was_consumed_is_born_overdue(
    app, clock, staff, catalog
):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")

        clock.set(at(16, 15))
        set_priority(ticket, staff["id"], "CRITICA")
        _, second = list_periods(ticket.id)

        # Crítica: 4 h; ya consumió 5 h.
        assert second.fecha_vencimiento_resolucion == at(16, 15)
        assert evaluate_ticket_sla(ticket.id).status is SlaStatus.VENCIDO


def test_a_breach_is_not_erased_by_lowering_the_priority(app, clock, staff, catalog):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        clock.set(at(16, 15))
        set_priority(ticket, staff["id"], "CRITICA")

        clock.set(at(16, 16))
        set_priority(ticket, staff["id"], "BAJA")
        snapshot = evaluate_ticket_sla(ticket.id)

        # Con Baja (24 h) y 6 h consumidas quedarían 18 h...
        assert snapshot.period.fecha_vencimiento_resolucion == at(18, 16)
        assert snapshot.consumed_seconds == 6 * HOUR
        # ...pero el incumplimiento ya ocurrió y no se borra.
        assert snapshot.breached
        assert snapshot.status is SlaStatus.VENCIDO


def test_a_priority_change_while_on_hold_is_born_paused(app, clock, staff, catalog):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        work_on(ticket, staff["id"])
        clock.set(at(16, 12))
        hold(ticket, staff["id"])

        clock.set(at(16, 13))
        set_priority(ticket, staff["id"], "ALTA")
        _, paused_before, paused_now = list_periods(ticket.id)

        assert paused_before.fecha_fin == at(16, 13)
        assert paused_before.segundos_consumidos == 0
        assert paused_now.prioridad_id == priority_id("ALTA")
        assert paused_now.esta_pausado
        assert paused_now.fecha_vencimiento_resolucion is None
        assert paused_now.motivo_cambio == "Cambia el impacto"

        # Al reanudar, corre con lo que le quedaba: 2 h consumidas de las 6 h de
        # Alta, o sea 4 h (3 h el lunes y 1 h el martes).
        clock.set(at(16, 15))
        resume(ticket, staff["id"])
        running = open_periods(ticket)[0]

        assert running.fecha_vencimiento_resolucion == at(17, 10)
        assert accumulated_seconds(ticket.id) == 2 * HOUR


def test_a_priority_without_a_policy_closes_the_period_and_leaves_no_sla(
    app, clock, staff, catalog
):
    with app.app_context():
        policy_of("ALTA").activo = False
        db.session.commit()
        ticket = new_ticket(catalog, staff["id"], "MEDIA")

        clock.set(at(16, 15))
        set_priority(ticket, staff["id"], "ALTA")
        (period,) = list_periods(ticket.id)

        assert period.fecha_fin == at(16, 15)
        assert period.segundos_consumidos == 5 * HOUR
        assert open_periods(ticket) == []
        # Con el ticket abierto y sin período vigente, no tiene SLA.
        assert evaluate_ticket_sla(ticket.id) is None


def test_changing_the_priority_of_a_resolved_ticket_waits_for_its_reopening(
    app, clock, staff, catalog
):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        clock.set(at(16, 12))
        resolve(ticket, staff["id"])

        clock.set(at(16, 13))
        set_priority(ticket, staff["id"], "ALTA")
        assert open_periods(ticket) == []

        clock.set(at(17, 10))
        reopen(ticket, staff["id"])
        running = open_periods(ticket)[0]

        # Al reabrir toma la política de la prioridad que tiene ahora.
        assert running.prioridad_id == priority_id("ALTA")
        assert running.tiempo_objetivo_resolucion_minutos == 360
        # Lleva 2 h consumidas de 6 h: quedan 4 h.
        assert running.fecha_vencimiento_resolucion == at(17, 14)


def test_a_later_priority_change_picks_up_the_edited_policy(
    app, clock, staff, catalog
):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        policy = policy_of("ALTA")
        policy.tiempo_objetivo_resolucion_minutos = 600
        policy.tiempo_objetivo_respuesta_minutos = 60
        db.session.commit()

        clock.set(at(16, 11))
        set_priority(ticket, staff["id"], "ALTA")
        second = open_periods(ticket)[0]

        assert second.tiempo_objetivo_resolucion_minutos == 600
        assert second.tiempo_objetivo_respuesta_minutos == 60


# --- Resolver, cerrar y reabrir ----------------------------------------------------------


def test_resolving_stops_the_clock(app, clock, staff, catalog):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")

        clock.set(at(16, 16))
        resolve(ticket, staff["id"])
        (period,) = list_periods(ticket.id)

        assert period.fecha_fin == at(16, 16)
        assert period.segundos_consumidos == 6 * HOUR
        assert open_periods(ticket) == []

        # La espera de la validación no cuenta, pase el tiempo que pase.
        clock.set(at(23, 10))
        snapshot = evaluate_ticket_sla(ticket.id)

        assert snapshot.closed
        assert snapshot.consumed_seconds == 6 * HOUR
        assert snapshot.status is SlaStatus.DENTRO


def test_a_reopened_ticket_continues_where_it_was(app, clock, staff, catalog):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        clock.set(at(16, 16))
        resolve(ticket, staff["id"])

        clock.set(at(17, 10))
        reopen(ticket, staff["id"])
        first, second = list_periods(ticket.id)

        assert second.fecha_inicio == at(17, 10)
        assert second.prioridad_id == first.prioridad_id
        assert second.usuario_cambio_id == staff["id"]
        # Llevaba 6 h de 12 h: quedan 6 h, de martes 10:00 a 16:00.
        assert second.fecha_vencimiento_resolucion == at(17, 16)
        assert accumulated_seconds(ticket.id) == 6 * HOUR


def test_closing_a_ticket_directly_closes_its_period(app, clock, staff, catalog):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")

        clock.set(at(16, 12))
        close(ticket, staff["id"])
        (period,) = list_periods(ticket.id)

        assert period.fecha_fin == at(16, 12)
        assert period.segundos_consumidos == 2 * HOUR

        clock.set(at(17, 9))
        reopen(ticket, staff["id"])
        assert len(list_periods(ticket.id)) == 2
        assert len(open_periods(ticket)) == 1


def test_resolving_from_the_hold_closes_the_paused_period(app, clock, staff, catalog):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        work_on(ticket, staff["id"])
        clock.set(at(16, 14))
        hold(ticket, staff["id"])

        clock.set(at(17, 11))
        resolve(ticket, staff["id"])
        _, paused = list_periods(ticket.id)

        assert paused.fecha_fin == at(17, 11)
        assert paused.segundos_consumidos == 0
        assert open_periods(ticket) == []


def test_nights_and_weekends_do_not_consume_time(app, clock, staff, catalog):
    with app.app_context():
        clock.set(at(20, 17))
        ticket = new_ticket(catalog, staff["id"], "MEDIA")

        clock.set(at(23, 10))
        resolve(ticket, staff["id"])
        (period,) = list_periods(ticket.id)

        # Viernes 17:00 a 18:00 y lunes 09:00 a 10:00.
        assert period.segundos_consumidos == 2 * HOUR


# --- El calendario con que se calculó -----------------------------------------------------


def test_each_period_closes_with_the_calendar_it_was_calculated_with(
    app, clock, staff, catalog
):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        work_on(ticket, staff["id"])

        # El Administrador guarda un calendario más corto (09:00-12:00).
        save_work_calendar(
            actor=person(staff["id"]),
            base_version=0,
            zone_name="America/Santiago",
            franjas=[Franja(d, parse_time("09:00"), parse_time("12:00")) for d in range(5)],
            holidays=[],
        )
        db.session.commit()
        version_id = db.session.scalar(
            db.text("select id from calendarios_laborales where activo")
        )

        # El período abierto con el calendario por defecto lo cierra con ese reloj.
        clock.set(at(16, 17))
        hold(ticket, staff["id"])
        first, paused = list_periods(ticket.id)

        assert first.calendario_laboral_id is None
        assert first.segundos_consumidos == 7 * HOUR
        assert paused.calendario_laboral_id == version_id

        # El período nuevo calcula con el calendario vigente al abrirlo.
        clock.set(at(17, 9, 30))
        resume(ticket, staff["id"])
        running = open_periods(ticket)[0]

        assert running.calendario_laboral_id == version_id
        # Quedan 5 h de 12 h; con 09:00-12:00: 2 h 30 min el martes y el resto el miércoles.
        assert running.fecha_vencimiento_resolucion == at(18, 11, 30)

        # Y también lo cierra con el reloj de su propio calendario: de 09:30 a
        # 13:00 solo se trabaja hasta las 12:00 (2 h 30 min, no 3 h 30 min).
        clock.set(at(17, 13))
        hold(ticket, staff["id"])
        assert list_periods(ticket.id)[2].segundos_consumidos == 2 * HOUR + 1800


# --- La primera respuesta -----------------------------------------------------------------------


def comment_at(ticket, author_id, moment, kind=CommentType.PUBLICO) -> Comment:
    comment = add_comment(ticket, actor=person(author_id), content="Hola", kind=kind)
    db.session.flush()
    db.session.execute(
        update(Comment.__table__)
        .where(Comment.__table__.c.id == comment.id)
        .values(fecha_creacion=moment)
    )
    db.session.commit()

    return comment


def test_the_first_response_is_the_first_public_comment_of_the_staff(
    app, clock, staff, other_staff, requester, catalog
):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        assert first_response_at(ticket.id) is None

        # Ni una nota interna ni lo que escribe el solicitante cuentan.
        comment_at(ticket, staff["id"], at(16, 10, 30), CommentType.INTERNO)
        assert first_response_at(ticket.id) is None

        comment_at(ticket, other_staff["id"], at(16, 12))
        comment_at(ticket, staff["id"], at(16, 13))

        assert first_response_at(ticket.id) == at(16, 12)


def test_a_deleted_comment_no_longer_counts_as_a_response(
    app, clock, staff, catalog
):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        comment = comment_at(ticket, staff["id"], at(16, 11))
        assert first_response_at(ticket.id) == at(16, 11)

        delete_comment(ticket, comment.id, actor=person(staff["id"]))
        db.session.commit()

        assert first_response_at(ticket.id) is None


def test_a_requester_comment_is_not_a_response(app, clock, staff, requester, catalog):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        db.session.add(
            TicketRequester(
                ticket_id=ticket.id,
                solicitante_id=requester["id"],
                asociado_por_usuario_id=staff["id"],
            )
        )
        db.session.commit()

        comment_at(ticket, requester["id"], at(16, 11))

        assert first_response_at(ticket.id) is None


def test_once_answered_a_new_period_does_not_set_a_response_deadline(
    app, clock, staff, catalog
):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        comment_at(ticket, staff["id"], at(16, 11))

        clock.set(at(16, 15))
        set_priority(ticket, staff["id"], "ALTA")
        _, second = list_periods(ticket.id)

        assert second.fecha_vencimiento_respuesta is None


def test_without_a_response_objective_there_is_no_response_deadline(
    app, clock, staff, catalog
):
    with app.app_context():
        policy_of("MEDIA").tiempo_objetivo_respuesta_minutos = None
        db.session.commit()

        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        (period,) = list_periods(ticket.id)

        assert period.fecha_vencimiento_respuesta is None
        assert period.fecha_vencimiento_resolucion == at(17, 13)


# --- Cómo está el SLA --------------------------------------------------------------------


def test_the_status_goes_from_within_to_near_to_overdue(app, clock, staff, catalog):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        # 12 h de objetivo y aviso al 80 % (9 h 36 min).
        expected = [
            (at(16, 10), SlaStatus.DENTRO, 0),
            (at(17, 10), SlaStatus.DENTRO, 75),
            (at(17, 10, 35), SlaStatus.DENTRO, 79),
            (at(17, 10, 36), SlaStatus.PROXIMO_A_VENCER, 80),
            (at(17, 11), SlaStatus.PROXIMO_A_VENCER, 83),
            (at(17, 12, 59), SlaStatus.PROXIMO_A_VENCER, 99),
            (at(17, 13), SlaStatus.VENCIDO, 100),
            (at(18, 9), SlaStatus.VENCIDO, 141),
        ]

        for moment, status, percent in expected:
            snapshot = evaluate_ticket_sla(ticket.id, moment)

            assert (snapshot.status, snapshot.percent) == (status, percent), moment

        snapshot = evaluate_ticket_sla(ticket.id, at(17, 11))
        assert snapshot.consumed_seconds == 10 * HOUR
        assert snapshot.remaining_seconds == 2 * HOUR
        assert snapshot.objective_seconds == 12 * HOUR
        assert snapshot.due_at == at(17, 13)
        assert not snapshot.closed


def test_without_a_warning_threshold_the_ticket_is_never_near_to_overdue(
    app, clock, staff, catalog
):
    with app.app_context():
        policy_of("MEDIA").umbral_aviso_consumo_porcentaje = None
        db.session.commit()
        ticket = new_ticket(catalog, staff["id"], "MEDIA")

        assert evaluate_ticket_sla(ticket.id, at(17, 12)).status is SlaStatus.DENTRO


def test_the_first_response_can_be_overdue_on_its_own(app, clock, staff, catalog):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")

        before = evaluate_ticket_sla(ticket.id, at(16, 13, 59))
        after = evaluate_ticket_sla(ticket.id, at(16, 14))

        assert before.response_due_at == at(16, 14)
        assert not before.response_overdue
        assert after.response_overdue
        assert after.status is SlaStatus.DENTRO

        # Contestar a tiempo lo resuelve; contestar tarde, no.
        comment_at(ticket, staff["id"], at(16, 13))
        assert not evaluate_ticket_sla(ticket.id, at(16, 15)).response_overdue


def test_a_late_answer_stays_overdue(app, clock, staff, catalog):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        comment_at(ticket, staff["id"], at(16, 16))

        snapshot = evaluate_ticket_sla(ticket.id, at(16, 17))

        assert snapshot.responded_at == at(16, 16)
        assert snapshot.response_overdue


def test_the_snapshot_of_a_ticket_that_never_had_sla_is_none(
    app, clock, staff, catalog
):
    with app.app_context():
        policy_of("MEDIA").activo = False
        db.session.commit()
        ticket = new_ticket(catalog, staff["id"], "MEDIA")

        assert evaluate_ticket_sla(ticket.id, at(16, 12)) is None


def test_the_current_time_comes_from_the_database(app):
    with app.app_context():
        moment = current_time()

        assert moment.tzinfo is not None
        assert abs((datetime.now(ZONE) - moment).total_seconds()) < 30


# --- Reconstrucción desde el historial -------------------------------------------------------


STEPS = [
    (at(16, 10), "create"),
    (at(16, 11), "start"),
    (at(16, 14), "hold"),
    (at(17, 10), "resume"),
    (at(17, 12), "priority"),
    (at(17, 15), "resolve"),
    (at(18, 10), "reopen"),
]


def run_steps(ticket, actor_id, clock=None):
    """Repite los pasos del ticket; con `clock`, a las horas de STEPS."""
    for moment, step in STEPS[1:]:
        if clock is not None:
            clock.set(moment)

        if step == "start":
            work_on(ticket, actor_id)
        elif step == "hold":
            hold(ticket, actor_id)
        elif step == "resume":
            resume(ticket, actor_id)
        elif step == "priority":
            set_priority(ticket, actor_id, "ALTA", "Más personas afectadas")
        elif step == "resolve":
            resolve(ticket, actor_id)
        elif step == "reopen":
            reopen(ticket, actor_id)


def redate(ticket) -> None:
    """Mueve los eventos del ticket a las horas de STEPS, como hace el seed."""
    ids = db.session.scalars(
        db.select(TicketHistory.id)
        .where(TicketHistory.ticket_id == ticket.id)
        .order_by(TicketHistory.id)
    ).all()
    assert len(ids) == len(STEPS)

    for event_id, (moment, _) in zip(ids, STEPS, strict=True):
        db.session.execute(
            update(TicketHistory.__table__)
            .where(TicketHistory.__table__.c.id == event_id)
            .values(fecha_hora=moment)
        )

    db.session.execute(
        update(Ticket.__table__)
        .where(Ticket.__table__.c.id == ticket.id)
        .values(fecha_creacion=STEPS[0][0])
    )
    db.session.commit()
    db.session.refresh(ticket)


def test_rebuilding_from_the_history_gives_what_live_calculation_gave(
    app, clock, staff, catalog
):
    with app.app_context():
        clock.set(STEPS[0][0])
        live = new_ticket(catalog, staff["id"], "MEDIA")
        run_steps(live, staff["id"], clock)
        expected = shapes(live)

        # El mismo recorrido, hecho a la hora real, con el historial movido después.
        clock_now = clock.now
        replayed = new_ticket(catalog, staff["id"], "MEDIA")
        run_steps(replayed, staff["id"])
        redate(replayed)
        clock.set(clock_now)

        count = rebuild_ticket_periods(replayed)
        db.session.commit()

        # Creación, espera, reanudación, cambio de prioridad y reapertura.
        assert count == len(expected) == 5
        assert shapes(replayed) == expected


def test_a_rebuilt_period_keeps_its_response_deadline_if_the_answer_came_later(
    app, clock, staff, catalog
):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        # El historial se mueve al lunes: creado a las 10:00 y respondido a las 12:00,
        # o sea, la respuesta es posterior al inicio del período.
        db.session.execute(
            update(TicketHistory.__table__)
            .where(TicketHistory.__table__.c.ticket_id == ticket.id)
            .values(fecha_hora=at(16, 10))
        )
        db.session.execute(
            update(Ticket.__table__)
            .where(Ticket.__table__.c.id == ticket.id)
            .values(fecha_creacion=at(16, 10))
        )
        db.session.commit()
        db.session.refresh(ticket)
        comment_at(ticket, staff["id"], at(16, 12))

        rebuild_ticket_periods(ticket)
        (period,) = list_periods(ticket.id)

        assert period.fecha_vencimiento_respuesta == at(16, 14)


def test_rebuilding_a_ticket_without_periods_creates_them(app, clock, staff, catalog):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        db.session.execute(db.delete(PeriodoSla))
        db.session.commit()
        assert list_periods(ticket.id) == []

        assert rebuild_ticket_periods(ticket) == 1
        (period,) = list_periods(ticket.id)

        assert period.prioridad_id == priority_id("MEDIA")
        assert period.fecha_fin is None


def test_rebuilding_replaces_the_existing_periods(app, clock, staff, catalog):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        old_id = list_periods(ticket.id)[0].id

        rebuild_ticket_periods(ticket)
        db.session.commit()

        assert [p.id for p in list_periods(ticket.id)] != [old_id]
        assert len(list_periods(ticket.id)) == 1


def test_the_rebuilt_clock_always_agrees_with_the_state_of_the_ticket(
    app, clock, staff, catalog
):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")

        # El estado se cambió a mano, sin eventos: el ticket manda.
        resolved = db.session.scalar(db.select(Estado.id).where(Estado.codigo == "RESUELTO"))
        db.session.execute(
            update(Ticket.__table__)
            .where(Ticket.__table__.c.id == ticket.id)
            .values(estado_id=resolved)
        )
        db.session.commit()
        db.session.refresh(ticket)

        rebuild_ticket_periods(ticket)

        assert open_periods(ticket) == []
        assert len(list_periods(ticket.id)) == 1


def test_only_the_tickets_without_periods_are_rebuilt_by_default(
    app, clock, staff, catalog
):
    with app.app_context():
        with_sla = new_ticket(catalog, staff["id"], "MEDIA")
        without = new_ticket(catalog, staff["id"], "MEDIA")
        db.session.execute(
            db.delete(PeriodoSla).where(PeriodoSla.ticket_id == without.id)
        )
        db.session.commit()
        kept_id = list_periods(with_sla.id)[0].id

        result = rebuild_periods()
        db.session.commit()

        assert (result.tickets, result.periods) == (1, 1)
        assert list_periods(with_sla.id)[0].id == kept_id
        assert len(list_periods(without.id)) == 1


def test_rebuilding_everything_or_one_ticket(app, clock, staff, catalog):
    with app.app_context():
        first = new_ticket(catalog, staff["id"], "MEDIA")
        second = new_ticket(catalog, staff["id"], "ALTA")
        kept_id = list_periods(first.id)[0].id

        only_second = rebuild_periods(only_missing=False, public_id=second.public_id)

        assert (only_second.tickets, only_second.periods) == (1, 1)
        assert list_periods(first.id)[0].id == kept_id

        everything = rebuild_periods(only_missing=False)

        assert (everything.tickets, everything.periods) == (2, 2)
        assert list_periods(first.id)[0].id != kept_id


# --- Restricciones de la base de datos ---------------------------------------------------------


def raw_period(ticket, **values) -> PeriodoSla:
    data = {
        "ticket_id": ticket.id,
        "prioridad_id": priority_id("MEDIA"),
        "tiempo_objetivo_resolucion_minutos": 720,
        "pausa_en_espera": True,
        "fecha_inicio": at(16, 10),
    }
    data.update(values)

    return PeriodoSla(**data)


def test_a_ticket_cannot_have_two_open_periods(app, clock, staff, catalog):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        db.session.add(raw_period(ticket))

        with pytest.raises(IntegrityError):
            db.session.flush()

        db.session.rollback()


def test_closed_periods_do_not_count_as_open(app, clock, staff, catalog):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        db.session.execute(
            update(PeriodoSla.__table__)
            .where(PeriodoSla.__table__.c.ticket_id == ticket.id)
            .values(fecha_fin=at(16, 12))
        )
        db.session.add(raw_period(ticket, fecha_inicio=at(16, 12)))
        db.session.add(raw_period(ticket, fecha_inicio=at(16, 13), fecha_fin=at(16, 14)))
        db.session.commit()

        assert len(list_periods(ticket.id)) == 3


@pytest.mark.parametrize(
    "values",
    [
        {"fecha_fin": at(16, 9)},
        {"segundos_consumidos": -1},
        {"tiempo_objetivo_resolucion_minutos": 0},
        {"tiempo_objetivo_respuesta_minutos": 0},
    ],
)
def test_the_database_rejects_invalid_periods(app, clock, staff, catalog, values):
    with app.app_context():
        policy_of("MEDIA").activo = False
        db.session.commit()
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        db.session.add(raw_period(ticket, **values))

        with pytest.raises(IntegrityError):
            db.session.flush()

        db.session.rollback()


def test_the_database_accepts_the_limits(app, clock, staff, catalog):
    with app.app_context():
        policy_of("MEDIA").activo = False
        db.session.commit()
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        db.session.add(
            raw_period(
                ticket,
                fecha_fin=at(16, 10),
                tiempo_objetivo_respuesta_minutos=1,
                tiempo_objetivo_resolucion_minutos=1,
            )
        )
        db.session.commit()

        period = list_periods(ticket.id)[0]

        assert period.segundos_consumidos == 0
        assert period.politica_sla_id is None
        assert period.usuario_cambio_id is None


def test_a_policy_with_periods_cannot_be_deleted(app, clock, staff, catalog):
    with app.app_context():
        new_ticket(catalog, staff["id"], "MEDIA")

        db.session.delete(policy_of("MEDIA"))

        with pytest.raises(IntegrityError):
            db.session.flush()

        db.session.rollback()


# --- Dos personas a la vez ---------------------------------------------------------------------


def test_two_priority_changes_at_once_leave_consistent_periods(
    app, staff, other_staff, catalog
):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        ticket_id, version = ticket.id, ticket.version
        baja, alta = priority_id("BAJA"), priority_id("ALTA")

    barrier = threading.Barrier(2)
    outcomes = []

    def run(user_id, target):
        with app.app_context():
            barrier.wait(timeout=10)

            try:
                change_priority(
                    db.session.get(Ticket, ticket_id),
                    actor=person(user_id),
                    expected_version=version,
                    priority_id=target,
                    reason="Cambio simultáneo",
                )
                db.session.commit()
                outcomes.append("cambió")
            except TicketConflictError:
                db.session.rollback()
                outcomes.append("conflicto")
            finally:
                db.session.remove()

    threads = [
        threading.Thread(target=run, args=(staff["id"], baja)),
        threading.Thread(target=run, args=(other_staff["id"], alta)),
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join(timeout=30)

    assert sorted(outcomes) == ["cambió", "conflicto"]

    with app.app_context():
        found = list_periods(ticket_id)

        assert len(found) == 2
        assert [p.fecha_fin is None for p in found] == [False, True]


# --- Los comandos ------------------------------------------------------------------------------


def test_sla_status_describes_the_periods_of_a_ticket(app, staff, catalog):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        number = ticket.public_id

    result = app.test_cli_runner().invoke(args=["sla-status", number])

    assert result.exit_code == 0, result.output
    assert f"Ticket #{number}" in result.output
    assert "prioridad Media" in result.output
    assert "SLA: dentro de plazo" in result.output
    assert "de 12 h" in result.output
    assert "Períodos:" in result.output
    assert "1. " in result.output and "vigente" in result.output


def test_sla_status_of_a_ticket_without_sla(app, staff, catalog):
    with app.app_context():
        policy_of("MEDIA").activo = False
        db.session.commit()
        number = new_ticket(catalog, staff["id"], "MEDIA").public_id

    result = app.test_cli_runner().invoke(args=["sla-status", f"#{number}"])

    assert result.exit_code == 0
    assert "ninguno" in result.output


def test_sla_status_of_an_unknown_ticket_fails(app):
    result = app.test_cli_runner().invoke(args=["sla-status", "99999"])

    assert result.exit_code != 0
    assert "No existe el ticket 99999" in result.output


def test_sla_rebuild_command_reports_what_it_did(app, staff, catalog):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        db.session.execute(db.delete(PeriodoSla))
        db.session.commit()
        number = ticket.public_id

    runner = app.test_cli_runner()
    first = runner.invoke(args=["sla-rebuild"])
    second = runner.invoke(args=["sla-rebuild"])
    forced = runner.invoke(args=["sla-rebuild", "--all"])
    single = runner.invoke(args=["sla-rebuild", "--all", "--ticket", f"#{number}"])

    assert "Tickets recalculados: 1. Períodos de SLA: 1." in first.output
    # Ya tiene períodos: por defecto no se toca.
    assert "Tickets recalculados: 0. Períodos de SLA: 0." in second.output
    assert "Tickets recalculados: 1. Períodos de SLA: 1." in forced.output
    assert "Tickets recalculados: 1. Períodos de SLA: 1." in single.output


def test_sla_rebuild_all_is_refused_in_production(app):
    app.config["APP_ENV"] = "production"
    runner = app.test_cli_runner()

    refused = runner.invoke(args=["sla-rebuild", "--all"])
    allowed = runner.invoke(args=["sla-rebuild"])

    assert refused.exit_code != 0
    assert "No se recalculan todos los períodos en producción" in refused.output
    assert allowed.exit_code == 0
