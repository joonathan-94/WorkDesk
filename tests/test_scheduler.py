"""Planificador: avisos de SLA y cierre automático (docs/06, RN-58, RN-59 y RN-170;
docs/10, secciones 84 a 87).

`run-scheduler` ejecuta dos tareas que se pueden repetir sin riesgo:

- avisar **una sola vez** cuando un período de SLA en marcha alcanza su umbral o vence;
- cerrar los tickets `Resuelto` que nadie validó en `AUTO_CLOSE_HOURS` horas.

Los tests de SLA fijan «la hora» como `test_sla_periods.py` (noviembre de 2026, lunes a
viernes de 09:00 a 18:00 en Santiago) y llaman a las tareas con un `now` explícito. Un
ticket Media creado el lunes a las 10:00 llega a su umbral el martes a las 10:36 y vence
el martes a las 13:00.
"""

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update

from src import workdesk as workdesk_package
from src.workdesk import scheduler
from src.workdesk.extensions import db
from src.workdesk.models import (
    Estado,
    Notificacion,
    NotificationEvent,
    PeriodoSla,
    StateAction,
    Ticket,
    TicketHistory,
)
from src.workdesk.sla.periods import list_periods
from src.workdesk.tickets.assignment import assign_technician
from src.workdesk.tickets.history import describe_history_changes
from src.workdesk.tickets.lifecycle import close_automatically
from src.workdesk.tickets.service import list_ticket_history
from src.workdesk.tickets.storage import TEMP_DIR, remove_stale_temp_files
from tests.sla_helpers import (
    act,
    at,
    hold,
    resolve,
    resume,
    set_priority,
    work_on,
)
from tests.ticket_helpers import make_ticket, person, ticket_by_public_id

E = NotificationEvent


# --- Ayudas -------------------------------------------------------------------


@pytest.fixture()
def team(make_user):
    return {
        "req": make_user("SOLICITANTE", username="req1", nombre="Javiera", apellido="Torres"),
        "tec": make_user("TECNICO", username="tec", nombre="Diego", apellido="Soto"),
        "tec2": make_user("TECNICO", username="tec2", nombre="Camila", apellido="Rojas"),
        "sup": make_user("SUPERVISOR", username="sup", nombre="Nora", apellido="Vega"),
        "sup2": make_user("SUPERVISOR", username="sup2", nombre="Raúl", apellido="Mena"),
    }


def started_ticket(app, catalog, team, *, assigned=True, requesters=True, priority="medium"):
    """Un ticket en progreso (con su técnico y su solicitante) y su SLA en marcha.
    Devuelve su identificador público."""
    public_id = make_ticket(
        app,
        catalog,
        team["sup"]["id"],
        requester_ids=[team["req"]["id"]] if requesters else [],
        priority_id=catalog[priority],
    )

    with app.app_context():
        ticket = ticket_by_public_id(public_id)

        if assigned:
            assign_technician(ticket, team["tec"]["id"], actor=person(team["sup"]["id"]))
            db.session.commit()

        work_on(ticket, team["tec"]["id"])

    return public_id


def notices(app, team, who, *events):
    """Los avisos de una persona de esos eventos, de más antiguo a más reciente."""
    with app.app_context():
        return list(
            db.session.scalars(
                db.select(Notificacion)
                .where(
                    Notificacion.usuario_id == team[who]["id"],
                    Notificacion.tipo_evento.in_([e.value for e in events]),
                )
                .order_by(Notificacion.id)
            )
        )


def sla_notices(app, team, who):
    return notices(app, team, who, E.SLA_PROXIMO_A_VENCER, E.SLA_VENCIDO)


def breach_events(app, public_id):
    """Los eventos `SLA_VENCIDO` del historial del ticket, como diccionarios."""
    with app.app_context():
        rows = db.session.scalars(
            db.select(TicketHistory)
            .where(
                TicketHistory.ticket_id == ticket_by_public_id(public_id).id,
                TicketHistory.tipo_evento == "SLA_VENCIDO",
            )
            .order_by(TicketHistory.id)
        )

        return [
            {
                "actor_tipo": row.actor_tipo,
                "actor_usuario_id": row.actor_usuario_id,
                "visibilidad": row.visibilidad,
                "contexto": row.contexto,
            }
            for row in rows
        ]


def run_notices(app, now):
    with app.app_context():
        result, failures = scheduler.run_sla_notices(now)

    return result.warnings, result.breaches, failures


def age_resolution(app, public_id, hours):
    """Hace que la resolución del ticket sea de hace `hours` horas."""
    with app.app_context():
        ticket = ticket_by_public_id(public_id)
        db.session.execute(
            update(Ticket)
            .where(Ticket.id == ticket.id)
            .values(fecha_resolucion=datetime.now(UTC) - timedelta(hours=hours))
        )
        db.session.commit()


def resolved_ticket(app, catalog, team, *, hours=25, requesters=True):
    public_id = started_ticket(
        app, catalog, team, requesters=requesters, priority="medium"
    )

    with app.app_context():
        resolve(ticket_by_public_id(public_id), team["tec"]["id"])

    age_resolution(app, public_id, hours)

    return public_id


def run_close(app):
    with app.app_context():
        return scheduler.run_auto_close(datetime.now(UTC))


def state_of(app, public_id):
    with app.app_context():
        ticket = ticket_by_public_id(public_id)

        return ticket.estado.codigo


# --- Avisos de SLA: umbral ------------------------------------------------------


def test_the_warning_is_sent_when_the_threshold_is_reached(app, clock, catalog, team):
    public_id = started_ticket(app, catalog, team)

    # El umbral del ticket Media llega el martes a las 10:36.
    assert run_notices(app, at(17, 10, 35)) == (0, 0, 0)
    assert sla_notices(app, team, "tec") == []

    assert run_notices(app, at(17, 10, 36)) == (1, 0, 0)

    (notice,) = sla_notices(app, team, "tec")
    assert notice.tipo_evento == E.SLA_PROXIMO_A_VENCER.value
    assert public_id in notice.mensaje

    with app.app_context():
        assert notice.ticket_id == ticket_by_public_id(public_id).id


def test_the_warning_is_sent_only_once(app, clock, catalog, team):
    started_ticket(app, catalog, team)

    assert run_notices(app, at(17, 10, 36)) == (1, 0, 0)
    assert run_notices(app, at(17, 11)) == (0, 0, 0)
    assert run_notices(app, at(17, 12)) == (0, 0, 0)

    assert len(sla_notices(app, team, "tec")) == 1


def test_the_warning_goes_to_the_assigned_technicians_and_never_to_the_requester(
    app, clock, catalog, team
):
    started_ticket(app, catalog, team)

    run_notices(app, at(17, 10, 36))

    assert len(sla_notices(app, team, "tec")) == 1
    assert sla_notices(app, team, "req") == []
    assert sla_notices(app, team, "tec2") == []
    assert sla_notices(app, team, "sup") == []


def test_a_ticket_without_technicians_warns_every_supervisor(app, clock, catalog, team):
    started_ticket(app, catalog, team, assigned=False)

    run_notices(app, at(17, 10, 36))

    assert len(sla_notices(app, team, "sup")) == 1
    assert len(sla_notices(app, team, "sup2")) == 1
    assert sla_notices(app, team, "req") == []


# --- Avisos de SLA: vencimiento -----------------------------------------------


def test_the_breach_warns_the_technician_and_the_supervisors(app, clock, catalog, team):
    started_ticket(app, catalog, team)

    assert run_notices(app, at(17, 13)) == (0, 1, 0)

    for who in ("tec", "sup", "sup2"):
        (notice,) = sla_notices(app, team, who)
        assert notice.tipo_evento == E.SLA_VENCIDO.value

    assert sla_notices(app, team, "req") == []
    assert sla_notices(app, team, "tec2") == []


def test_the_breach_is_sent_only_once(app, clock, catalog, team):
    started_ticket(app, catalog, team)

    assert run_notices(app, at(17, 13)) == (0, 1, 0)
    assert run_notices(app, at(17, 14)) == (0, 0, 0)
    assert run_notices(app, at(20, 12)) == (0, 0, 0)

    assert len(sla_notices(app, team, "tec")) == 1


def test_a_breach_found_late_does_not_also_send_the_warning(app, clock, catalog, team):
    started_ticket(app, catalog, team)

    # El planificador no corrió entre el umbral y el vencimiento: solo importa el vencido.
    assert run_notices(app, at(17, 15)) == (0, 1, 0)
    assert [n.tipo_evento for n in sla_notices(app, team, "tec")] == [E.SLA_VENCIDO.value]


def test_the_breach_follows_a_warning_already_sent(app, clock, catalog, team):
    started_ticket(app, catalog, team)

    run_notices(app, at(17, 10, 40))
    run_notices(app, at(17, 13))

    assert [n.tipo_evento for n in sla_notices(app, team, "tec")] == [
        E.SLA_PROXIMO_A_VENCER.value,
        E.SLA_VENCIDO.value,
    ]


# --- El incumplimiento queda registrado en el historial (RN-91) ---------------------


def test_the_breach_is_recorded_in_the_ticket_history(app, clock, catalog, team):
    public_id = started_ticket(app, catalog, team)

    run_notices(app, at(17, 13))

    (event,) = breach_events(app, public_id)
    assert event["actor_tipo"] == "SISTEMA"
    assert event["actor_usuario_id"] is None
    assert event["visibilidad"] == "INTERNO"

    with app.app_context():
        (period,) = [
            p for p in list_periods(ticket_by_public_id(public_id).id) if p.fecha_fin is None
        ]
        assert event["contexto"]["periodo_id"] == period.id

    # Media: 12 h de objetivo de resolución, que vencen el martes a las 13:00.
    assert event["contexto"]["objetivo_minutos"] == 720
    assert datetime.fromisoformat(event["contexto"]["vencimiento"]) == at(17, 13)


def test_the_warning_is_not_recorded_in_the_history(app, clock, catalog, team):
    public_id = started_ticket(app, catalog, team)

    run_notices(app, at(17, 10, 36))

    assert breach_events(app, public_id) == []


def test_the_breach_is_recorded_only_once(app, clock, catalog, team):
    public_id = started_ticket(app, catalog, team)

    run_notices(app, at(17, 13))
    run_notices(app, at(17, 14))
    run_notices(app, at(20, 12))

    assert len(breach_events(app, public_id)) == 1


def test_the_breach_found_after_a_warning_is_recorded_too(app, clock, catalog, team):
    public_id = started_ticket(app, catalog, team)

    run_notices(app, at(17, 10, 40))
    assert breach_events(app, public_id) == []

    run_notices(app, at(17, 13))
    assert len(breach_events(app, public_id)) == 1


def test_the_staff_reads_the_breach_and_the_requester_never_sees_it(
    app, clock, catalog, team
):
    public_id = started_ticket(app, catalog, team)
    run_notices(app, at(17, 13))

    with app.app_context():
        ticket = ticket_by_public_id(public_id)
        seen_by_staff = [
            entry
            for entry in list_ticket_history(ticket, person(team["sup"]["id"]))
            if entry.tipo_evento == "SLA_VENCIDO"
        ]
        seen_by_requester = [
            entry
            for entry in list_ticket_history(ticket, person(team["req"]["id"]))
            if entry.tipo_evento == "SLA_VENCIDO"
        ]

        assert len(seen_by_staff) == 1
        assert describe_history_changes(seen_by_staff[0]) == [
            "Venció el objetivo de resolución de 12 h"
        ]
        assert seen_by_requester == []


def test_a_failed_breach_notice_leaves_no_history_event(
    app, clock, catalog, team, monkeypatch
):
    public_id = started_ticket(app, catalog, team)

    def broken(_ticket):
        raise RuntimeError("falla de prueba")

    monkeypatch.setattr(scheduler, "notify_sla_breach", broken)

    assert run_notices(app, at(17, 13)) == (0, 0, 1)
    assert breach_events(app, public_id) == []


def test_the_marks_are_stored_in_the_period(app, clock, catalog, team):
    public_id = started_ticket(app, catalog, team)

    run_notices(app, at(17, 13))

    with app.app_context():
        (period,) = [
            p for p in list_periods(ticket_by_public_id(public_id).id) if p.fecha_fin is None
        ]
        assert period.fecha_aviso_vencimiento_enviado == at(17, 13)
        assert period.fecha_aviso_umbral_enviado == at(17, 13)


def test_inactive_technicians_are_not_warned(app, clock, catalog, team):
    started_ticket(app, catalog, team)

    with app.app_context():
        person(team["tec"]["id"]).activo = False
        db.session.commit()

    run_notices(app, at(17, 10, 36))

    assert sla_notices(app, team, "tec") == []
    # Sin técnicos activos que avisar, el aviso no se reparte a otros: solo había uno.
    assert sla_notices(app, team, "tec2") == []


# --- Qué períodos avisan -------------------------------------------------------


def test_a_paused_ticket_does_not_warn(app, clock, catalog, team):
    public_id = started_ticket(app, catalog, team)

    with app.app_context():
        hold(ticket_by_public_id(public_id), team["tec"]["id"])

    assert run_notices(app, at(20, 12)) == (0, 0, 0)


def test_resuming_does_not_repeat_a_warning_already_sent(app, clock, catalog, team):
    public_id = started_ticket(app, catalog, team)

    assert run_notices(app, at(17, 10, 40)) == (1, 0, 0)

    clock.set(at(17, 11))

    with app.app_context():
        ticket = ticket_by_public_id(public_id)
        hold(ticket, team["tec"]["id"])
        clock.set(at(17, 12))
        resume(ticket, team["tec"]["id"])

    # El período nuevo nace con el umbral ya superado, pero ya se avisó.
    assert run_notices(app, at(17, 12, 1)) == (0, 0, 0)
    assert len(sla_notices(app, team, "tec")) == 1


def test_a_resolved_ticket_stops_warning(app, clock, catalog, team):
    public_id = started_ticket(app, catalog, team)

    with app.app_context():
        resolve(ticket_by_public_id(public_id), team["tec"]["id"])

    assert run_notices(app, at(20, 12)) == (0, 0, 0)
    assert sla_notices(app, team, "tec") == []


def test_a_priority_change_opens_a_new_sla_that_can_warn_again(app, clock, catalog, team):
    # Alta: 6 h y 75 %, así que el umbral llega a las 4 h 30 min (lunes 14:30).
    public_id = started_ticket(app, catalog, team, priority="high")

    assert run_notices(app, at(16, 14, 35)) == (1, 0, 0)

    clock.set(at(16, 14, 40))

    with app.app_context():
        set_priority(ticket_by_public_id(public_id), team["sup"]["id"], "MEDIA")

    # Media es otro SLA (12 h y 80 %): lleva 4 h 40 min consumidas, su umbral llega el
    # martes a las 10:36 y vence a las 13:00. Sus avisos no se heredan de la prioridad
    # anterior: avisa otra vez.
    assert run_notices(app, at(17, 11)) == (1, 0, 0)

    assert [n.tipo_evento for n in sla_notices(app, team, "tec")] == [
        E.SLA_PROXIMO_A_VENCER.value,
        E.SLA_PROXIMO_A_VENCER.value,
    ]


def test_the_candidate_list_only_has_open_periods_with_something_pending(
    app, clock, catalog, team
):
    public_id = started_ticket(app, catalog, team)

    with app.app_context():
        assert scheduler._pending_notice_ids(at(17, 10, 35)) == []
        assert len(scheduler._pending_notice_ids(at(17, 10, 36))) == 1

    run_notices(app, at(17, 10, 36))

    with app.app_context():
        # Avisado el umbral, no queda nada hasta el vencimiento.
        assert scheduler._pending_notice_ids(at(17, 10, 37)) == []
        assert len(scheduler._pending_notice_ids(at(17, 13))) == 1

        # Un período cerrado no vuelve a aparecer aunque haya vencido.
        resolve(ticket_by_public_id(public_id), team["tec"]["id"])
        assert scheduler._pending_notice_ids(at(17, 13)) == []


def test_a_period_closed_after_it_was_found_is_not_notified(app, clock, catalog, team):
    public_id = started_ticket(app, catalog, team)

    with app.app_context():
        pending = scheduler._pending_notice_ids(at(17, 13))
        assert len(pending) == 1

        # Entre la consulta y el aviso, el ticket se resuelve y su período se cierra.
        resolve(ticket_by_public_id(public_id), team["tec"]["id"])

        assert scheduler._send_notice(pending[0], at(17, 13)) is None
        db.session.rollback()

    assert sla_notices(app, team, "tec") == []


def test_a_period_already_notified_by_another_scheduler_is_skipped(app, clock, catalog, team):
    started_ticket(app, catalog, team)

    with app.app_context():
        pending = scheduler._pending_notice_ids(at(17, 13))

        assert scheduler._send_notice(pending[0], at(17, 13)) == "breach"
        db.session.commit()

        # Otro planificador llega con la misma lista de candidatos.
        assert scheduler._send_notice(pending[0], at(17, 13)) is None
        db.session.rollback()

    assert len(sla_notices(app, team, "tec")) == 1


def test_two_planners_at_once_send_one_notice(app, clock, catalog, team, monkeypatch):
    started_ticket(app, catalog, team)

    real = scheduler.notify_sla_breach

    def slow(ticket):
        # Da tiempo a que el otro planificador lea el mismo período antes de que este
        # confirme: solo el bloqueo de la fila evita el aviso doble.
        time.sleep(0.5)
        real(ticket)

    monkeypatch.setattr(scheduler, "notify_sla_breach", slow)

    with app.app_context():
        pending = scheduler._pending_notice_ids(at(17, 13))

    barrier = threading.Barrier(2)
    outcomes = []

    def run():
        with app.app_context():
            barrier.wait(timeout=10)

            try:
                outcomes.append(scheduler._send_notice(pending[0], at(17, 13)))
                db.session.commit()
            finally:
                db.session.remove()

    threads = [threading.Thread(target=run) for _ in range(2)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join(timeout=30)

    assert sorted(o or "" for o in outcomes) == ["", "breach"]
    assert len(sla_notices(app, team, "tec")) == 1


def test_a_notice_and_a_state_change_on_the_same_ticket_do_not_deadlock(
    app, clock, catalog, team, monkeypatch
):
    # Una persona cambia el estado del ticket justo mientras el planificador está
    # avisando de su SLA. Los cambios de estado bloquean primero el ticket y después su
    # período; si el planificador bloqueara en el orden contrario (el período y luego,
    # al guardar el aviso, el ticket por la clave foránea), cada uno esperaría al otro y
    # PostgreSQL abortaría a uno de los dos: un error para quien estaba trabajando.
    public_id = started_ticket(app, catalog, team)

    real = scheduler.notify_sla_breach
    inside = threading.Event()

    def slow(ticket):
        # El planificador ya tiene sus bloqueos; la otra persona actúa ahora.
        inside.set()
        time.sleep(0.5)
        real(ticket)

    monkeypatch.setattr(scheduler, "notify_sla_breach", slow)

    with app.app_context():
        (period_id,) = scheduler._pending_notice_ids(at(17, 13))

    def send_notice():
        with app.app_context():
            try:
                scheduler._send_notice(period_id, at(17, 13))
                db.session.commit()
            finally:
                db.session.remove()

    def change_the_state():
        with app.app_context():
            try:
                assert inside.wait(timeout=10)
                hold(ticket_by_public_id(public_id), team["tec"]["id"])
            finally:
                db.session.remove()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(send_notice), pool.submit(change_the_state)]

        # `result()` vuelve a lanzar lo que haya fallado en el hilo (un bloqueo mutuo, por
        # ejemplo), así que el test falla con el error real.
        for future in futures:
            future.result(timeout=30)

    assert state_of(app, public_id) == "EN_ESPERA"
    assert len(sla_notices(app, team, "tec")) == 1


def test_one_failure_does_not_stop_the_other_notices(app, clock, catalog, team, monkeypatch):
    first = started_ticket(app, catalog, team)
    second = started_ticket(app, catalog, team)

    real = scheduler.notify_sla_warning
    calls = []

    def flaky(ticket):
        calls.append(ticket.public_id)

        if ticket.public_id == first:
            raise RuntimeError("falla de prueba")

        real(ticket)

    monkeypatch.setattr(scheduler, "notify_sla_warning", flaky)

    assert run_notices(app, at(17, 10, 36)) == (1, 0, 1)
    assert calls == [first, second]

    # El que falló no quedó marcado: se reintenta en la próxima pasada.
    monkeypatch.setattr(scheduler, "notify_sla_warning", real)
    assert run_notices(app, at(17, 10, 37)) == (1, 0, 0)

    with app.app_context():
        marked = db.session.scalars(
            db.select(PeriodoSla.fecha_aviso_umbral_enviado).where(
                PeriodoSla.fecha_fin.is_(None)
            )
        ).all()
        assert all(mark is not None for mark in marked)


# --- Cierre automático ---------------------------------------------------------


def test_an_unvalidated_ticket_is_closed_after_the_wait(app, catalog, team):
    public_id = resolved_ticket(app, catalog, team, hours=25)

    assert run_close(app) == (1, 0)

    with app.app_context():
        ticket = ticket_by_public_id(public_id)
        assert ticket.estado.codigo == "CERRADO"
        assert ticket.cerrado_automaticamente is True
        assert ticket.cerrado_por_usuario_id is None
        assert ticket.fecha_cierre is not None
        assert ticket.motivo_cierre.codigo == "INACTIVIDAD"


def test_a_ticket_still_inside_the_wait_is_not_closed(app, catalog, team):
    public_id = resolved_ticket(app, catalog, team, hours=23)

    assert run_close(app) == (0, 0)
    assert state_of(app, public_id) == "RESUELTO"


def test_the_wait_comes_from_the_configuration(app, catalog, team):
    public_id = resolved_ticket(app, catalog, team, hours=25)
    app.config["AUTO_CLOSE_HOURS"] = 48

    assert run_close(app) == (0, 0)
    assert state_of(app, public_id) == "RESUELTO"

    app.config["AUTO_CLOSE_HOURS"] = 24

    assert run_close(app) == (1, 0)


def test_a_resolved_ticket_without_requesters_is_closed_too(app, catalog, team):
    public_id = resolved_ticket(app, catalog, team, requesters=False)

    assert run_close(app) == (1, 0)
    assert state_of(app, public_id) == "CERRADO"


def test_only_resolved_tickets_are_closed(app, catalog, team):
    working = started_ticket(app, catalog, team)

    assert run_close(app) == (0, 0)
    assert state_of(app, working) == "EN_PROGRESO"


def test_running_it_twice_closes_once(app, catalog, team):
    public_id = resolved_ticket(app, catalog, team)

    assert run_close(app) == (1, 0)
    assert run_close(app) == (0, 0)

    with app.app_context():
        closings = db.session.scalars(
            db.select(TicketHistory).where(
                TicketHistory.ticket_id == ticket_by_public_id(public_id).id,
                TicketHistory.tipo_evento == "TICKET_CERRADO",
            )
        ).all()
        assert len(closings) == 1


def test_the_closing_is_recorded_as_the_system(app, catalog, team):
    public_id = resolved_ticket(app, catalog, team)
    run_close(app)

    with app.app_context():
        ticket = ticket_by_public_id(public_id)
        (event,) = db.session.scalars(
            db.select(TicketHistory).where(
                TicketHistory.ticket_id == ticket.id,
                TicketHistory.tipo_evento == "TICKET_CERRADO",
            )
        ).all()

        assert event.actor_tipo == "SISTEMA"
        assert event.actor_usuario_id is None
        assert event.visibilidad == "PUBLICO"
        assert event.contexto["accion"] == "AUTO_CIERRE"
        assert event.contexto["motivo_cierre"] == "INACTIVIDAD"
        assert db.session.get(Estado, event.estado_anterior_id).codigo == "RESUELTO"
        assert db.session.get(Estado, event.estado_nuevo_id).codigo == "CERRADO"
        assert ticket.usuario_modificacion_id is None


def test_the_requester_and_the_technician_are_told(app, catalog, team):
    resolved_ticket(app, catalog, team)
    run_close(app)

    for who in ("req", "tec"):
        (notice,) = notices(app, team, who, E.TICKET_CERRADO)
        assert notice.titulo == "Ticket cerrado automáticamente"

    # Los demás no tienen por qué enterarse.
    assert notices(app, team, "sup", E.TICKET_CERRADO) == []
    assert notices(app, team, "tec2", E.TICKET_CERRADO) == []


def test_the_requester_never_sees_internal_information_in_the_notice(app, catalog, team):
    resolved_ticket(app, catalog, team)
    run_close(app)

    (notice,) = notices(app, team, "req", E.TICKET_CERRADO)

    assert "INACTIVIDAD" not in notice.mensaje
    assert "Sistema" not in notice.mensaje


def test_closing_stops_the_sla_clock(app, catalog, team):
    public_id = resolved_ticket(app, catalog, team)
    run_close(app)

    with app.app_context():
        assert all(
            p.fecha_fin is not None for p in list_periods(ticket_by_public_id(public_id).id)
        )


def test_an_automatically_closed_ticket_can_be_reopened(app, catalog, team):
    public_id = resolved_ticket(app, catalog, team)
    run_close(app)

    with app.app_context():
        ticket = ticket_by_public_id(public_id)
        act(ticket, team["tec"]["id"], StateAction.REABRIR)

        ticket = ticket_by_public_id(public_id)
        assert ticket.estado.codigo == "EN_PROGRESO"
        assert ticket.cerrado_automaticamente is False
        assert ticket.fecha_cierre is None
        assert ticket.motivo_cierre_id is None


def test_the_detail_page_shows_an_automatic_closing(app, client, catalog, team):
    public_id = resolved_ticket(app, catalog, team)
    run_close(app)

    from tests.ticket_helpers import login, text

    login(client, team["sup"])
    page = text(client.get(f"/tickets/{public_id}"))

    assert "Cerrado" in page
    assert "Inactividad" in page


# --- El plazo se comprueba dentro de la transacción ---------------------------


def test_a_ticket_validated_after_it_was_found_is_not_closed_again(app, catalog, team):
    public_id = resolved_ticket(app, catalog, team)

    with app.app_context():
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        assert scheduler._pending_close_ids(cutoff) == [ticket_by_public_id(public_id).id]

        # Mientras tanto el solicitante lo rechaza: vuelve al trabajo.
        act(ticket_by_public_id(public_id), team["req"]["id"], StateAction.RECHAZAR, text="No sirvió")

        assert close_automatically(ticket_by_public_id(public_id), resolved_before=cutoff) is False
        db.session.rollback()

    assert state_of(app, public_id) == "EN_PROGRESO"


def test_the_deadline_is_checked_inside_the_closing(app, catalog, team):
    public_id = resolved_ticket(app, catalog, team, hours=1)

    with app.app_context():
        ticket = ticket_by_public_id(public_id)
        cutoff = datetime.now(UTC) - timedelta(hours=24)

        # Se resolvió hace una hora: antes del límite de hace 24 h no es, aunque
        # alguien lo haya encontrado en una lista.
        assert close_automatically(ticket, resolved_before=cutoff) is False
        db.session.rollback()

    assert state_of(app, public_id) == "RESUELTO"


def test_the_close_candidates_only_have_resolved_tickets(app, catalog, team):
    resolved = resolved_ticket(app, catalog, team, hours=30)
    validated = resolved_ticket(app, catalog, team, hours=30)

    with app.app_context():
        act(ticket_by_public_id(validated), team["req"]["id"], StateAction.CONFIRMAR)
        cutoff = datetime.now(UTC) - timedelta(hours=24)

        # El validado conserva su fecha de resolución, pero ya está cerrado.
        assert scheduler._pending_close_ids(cutoff) == [ticket_by_public_id(resolved).id]


def test_a_ticket_resolved_again_gets_a_new_wait(app, catalog, team):
    public_id = resolved_ticket(app, catalog, team, hours=30)

    with app.app_context():
        act(ticket_by_public_id(public_id), team["req"]["id"], StateAction.RECHAZAR, text="No sirvió")
        resolve(ticket_by_public_id(public_id), team["tec"]["id"])

    # La nueva resolución es de hace un instante: todavía no toca cerrarlo.
    assert run_close(app) == (0, 0)
    assert state_of(app, public_id) == "RESUELTO"


def test_a_disabled_transition_prevents_the_closing(app, catalog, team):
    from src.workdesk.models import TransicionEstado

    public_id = resolved_ticket(app, catalog, team)

    with app.app_context():
        db.session.execute(
            update(TransicionEstado)
            .where(TransicionEstado.accion == StateAction.AUTO_CIERRE.value)
            .values(activa=False)
        )
        db.session.commit()

    assert run_close(app) == (0, 0)
    assert state_of(app, public_id) == "RESUELTO"


def test_one_failure_does_not_stop_the_other_closings(app, catalog, team, monkeypatch):
    first = resolved_ticket(app, catalog, team)
    second = resolved_ticket(app, catalog, team)

    real = scheduler.close_automatically

    def flaky(ticket, **kwargs):
        if ticket.public_id == first:
            raise RuntimeError("falla de prueba")

        return real(ticket, **kwargs)

    monkeypatch.setattr(scheduler, "close_automatically", flaky)

    assert run_close(app) == (1, 1)
    assert state_of(app, first) == "RESUELTO"
    assert state_of(app, second) == "CERRADO"


# --- run_once, el bucle y la configuración ------------------------------------


def test_run_once_does_both_tasks(app, clock, catalog, team):
    started_ticket(app, catalog, team)
    resolved = resolved_ticket(app, catalog, team)

    with app.app_context():
        # `now` es simulado: la resolución se fecha respecto de esa hora.
        db.session.execute(
            update(Ticket)
            .where(Ticket.id == ticket_by_public_id(resolved).id)
            .values(fecha_resolucion=at(14, 10))
        )
        db.session.commit()
        result = scheduler.run_once(at(17, 13))

    assert result.breaches == 1
    assert result.closed == 1
    assert result.failures == 0
    assert state_of(app, resolved) == "CERRADO"


def test_the_loop_runs_and_waits_between_passes(app):
    passes = []
    sleeps = []

    def should_stop():
        return len(passes) >= 3

    with app.app_context():
        scheduler.run_loop(
            45,
            should_stop=should_stop,
            sleep=sleeps.append,
            on_result=passes.append,
        )

    assert len(passes) == 3
    assert sleeps == [45, 45]


def test_a_failed_pass_does_not_stop_the_loop(app, monkeypatch):
    attempts = []

    def flaky_run_once():
        attempts.append(1)

        if len(attempts) == 1:
            raise RuntimeError("falla de prueba")

        return scheduler.SchedulerResult()

    monkeypatch.setattr(scheduler, "run_once", flaky_run_once)

    with app.app_context():
        scheduler.run_loop(
            1,
            should_stop=lambda: len(attempts) >= 3,
            sleep=lambda _seconds: None,
        )

    assert len(attempts) == 3


@pytest.mark.parametrize("name", ["AUTO_CLOSE_HOURS", "SCHEDULER_INTERVAL_SECONDS"])
@pytest.mark.parametrize("value", [0, -5])
def test_the_app_rejects_a_non_positive_scheduler_setting(name, value):
    config = {
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        name: value,
    }

    with pytest.raises(RuntimeError, match=name):
        workdesk_package.create_app(config)


def test_the_defaults_are_a_day_and_a_minute(app):
    assert app.config["AUTO_CLOSE_HOURS"] == 24
    assert app.config["SCHEDULER_INTERVAL_SECONDS"] == 60


# --- El comando ---------------------------------------------------------------


def test_the_command_runs_once_and_reports(app, catalog, team):
    resolved_ticket(app, catalog, team)

    result = app.test_cli_runner().invoke(args=["run-scheduler", "--once"])

    assert result.exit_code == 0
    assert "Tickets cerrados automáticamente: 1" in result.output
    assert "Errores: 0" in result.output


def test_the_command_can_be_repeated_without_effect(app, catalog, team):
    resolved_ticket(app, catalog, team)
    runner = app.test_cli_runner()

    runner.invoke(args=["run-scheduler", "--once"])
    second = runner.invoke(args=["run-scheduler", "--once"])

    assert second.exit_code == 0
    assert "SLA próximo a vencer: 0. SLA vencido: 0. Tickets cerrados automáticamente: 0" in (
        second.output
    )


def test_the_command_fails_when_an_element_failed(app, catalog, team, monkeypatch):
    resolved_ticket(app, catalog, team)

    def broken(ticket, **kwargs):
        raise RuntimeError("falla de prueba")

    monkeypatch.setattr(scheduler, "close_automatically", broken)

    result = app.test_cli_runner().invoke(args=["run-scheduler", "--once"])

    assert result.exit_code != 0
    assert "Errores: 1" in result.output


def test_the_command_rejects_a_non_positive_interval(app):
    result = app.test_cli_runner().invoke(args=["run-scheduler", "--interval", "0"])

    assert result.exit_code != 0


# --- Restos de subidas cortadas ---------------------------------------------------------


def _temp_file(app, name, *, age_seconds):
    """Un archivo en `_tmp` con la antigüedad indicada."""
    folder = os.path.join(app.config["UPLOADS_DIR"], TEMP_DIR)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name)

    with open(path, "wb") as handle:
        handle.write(b"resto")

    moment = time.time() - age_seconds
    os.utime(path, (moment, moment))

    return path


def test_the_scheduler_removes_temp_uploads_left_by_a_cut_upload(app):
    old = _temp_file(app, "resto-viejo", age_seconds=2 * 3600)
    recent = _temp_file(app, "subida-en-curso", age_seconds=30)

    with app.app_context():
        scheduler.run_once()

    # Una subida que está ocurriendo ahora mismo no se toca.
    assert not os.path.exists(old)
    assert os.path.exists(recent)


def test_cleaning_with_no_temp_folder_does_nothing(app):
    assert remove_stale_temp_files(app.config["UPLOADS_DIR"] + "-inexistente") == 0


def test_the_age_limit_is_exclusive_of_what_is_still_young(app):
    just_under = _temp_file(app, "casi", age_seconds=3500)
    just_over = _temp_file(app, "pasado", age_seconds=3700)

    assert remove_stale_temp_files(app.config["UPLOADS_DIR"]) == 1
    assert os.path.exists(just_under)
    assert not os.path.exists(just_over)


def test_a_cleaning_failure_does_not_stop_the_scheduler(app, monkeypatch):
    def broken(_root):
        raise PermissionError("sin permiso")

    monkeypatch.setattr(scheduler, "remove_stale_temp_files", broken)

    with app.app_context():
        result = scheduler.run_once()

    assert result.failures == 0
