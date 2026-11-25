"""El interruptor general del SLA y el del cierre automático (docs/11, UI-022 y UI-023).

Con el SLA apagado WorkDesk **no muestra ni avisa nada del SLA**, pero **sigue calculando**
los períodos, de modo que al encenderlo no hay que reconstruir nada. Las pruebas recorren
las pantallas con los tickets de demostración, que tienen SLA en todos los estados.
"""

from datetime import timedelta

import pytest

from src.workdesk import scheduler, settings
from src.workdesk.audit import AuditAction
from src.workdesk.configuration import save_setting, value_of
from src.workdesk.extensions import db
from src.workdesk.models import PeriodoSla, Ticket, User
from src.workdesk.sla.periods import current_time, evaluate_tickets_sla
from src.workdesk.sla.queries import SlaFilter
from src.workdesk.tickets.queries import TicketFilters, list_tickets
from src.workdesk.workload.queries import workload_overview
from tests.demo_data import DEMO_PASSWORD
from tests.ticket_helpers import audit_entries, login, plain_text

DEMO_SUPERVISOR = {"username": "camila.rojas", "password": DEMO_PASSWORD}


def _set(app, setting, value):
    with app.app_context():
        actor = db.session.scalar(db.select(User).where(User.username == "admin_switch"))
        save_setting(setting, value, actor=actor)
        db.session.commit()


@pytest.fixture()
def administrator(make_user):
    return make_user("ADMINISTRADOR", username="admin_switch")


@pytest.fixture()
def staff(seeded, app, client, administrator):
    login(client, DEMO_SUPERVISOR)


def _html(client, url):
    response = client.get(url)

    assert response.status_code == 200, url

    return response.get_data(as_text=True)


def _any_ticket_number(app):
    with app.app_context():
        return db.session.scalar(db.select(Ticket.public_id).order_by(Ticket.id))


# --- La pantalla ---------------------------------------------------------------------------


def test_the_sla_screen_shows_the_switch_and_turns_it_off_and_on(
    app, client, make_user, seeded_catalogs
):
    admin = make_user("ADMINISTRADOR")
    login(client, admin)

    assert "Activado" in plain_text(client.get("/admin/sla"))

    confirm = client.get("/admin/sla/deactivate")
    assert "Desactivar el SLA" in plain_text(confirm)
    assert _html(client, "/admin/sla").count("Desactivar SLA") == 1

    done = client.post("/admin/sla/deactivate", data={"motivo": "Prueba"})
    assert "quedó desactivado" in plain_text(client.get(done.headers["Location"]))

    with app.app_context():
        entry = audit_entries()[-1]

        assert value_of(settings.SLA_ENABLED) is False
        assert entry.accion == AuditAction.CONFIGURACION_MODIFICADA
        assert entry.motivo == "Prueba"

    text = plain_text(client.get("/admin/sla"))
    assert "Desactivado" in text and "Activar SLA" in text

    client.post("/admin/sla/activate")

    with app.app_context():
        assert value_of(settings.SLA_ENABLED) is True


def test_asking_for_what_it_already_is_says_so_and_changes_nothing(
    app, client, make_user, seeded_catalogs
):
    login(client, make_user("ADMINISTRADOR"))

    response = client.get("/admin/sla/activate")

    assert "ya está activado" in plain_text(client.get(response.headers["Location"]))

    with app.app_context():
        assert audit_entries() == []


@pytest.mark.parametrize("role", ["SOLICITANTE", "TECNICO", "SUPERVISOR"])
def test_only_the_administrator_can_use_the_switch(client, make_user, role):
    login(client, make_user(role))

    for url in ("/admin/sla/activate", "/admin/sla/deactivate"):
        assert client.get(url).status_code == 403
        assert client.post(url).status_code == 403


# --- Lo que desaparece ----------------------------------------------------------------------

SLA_SCREENS = ["/tickets?vista=todos", "/dashboard", "/workload"]


def test_with_the_sla_on_the_screens_show_it(staff, client):
    assert 'id="sla"' in _html(client, "/tickets?vista=todos")
    assert "Fuera de SLA" in _html(client, "/dashboard")
    assert "SLA en riesgo" in _html(client, "/workload")


def test_with_the_sla_off_no_screen_mentions_it(app, staff, client):
    _set(app, settings.SLA_ENABLED, False)
    number = _any_ticket_number(app)

    for url in [*SLA_SCREENS, f"/tickets/{number}", f"/tickets/{number}/priority"]:
        html = _html(client, url)
        main = html[html.index("<main") : html.index("</main>")]

        assert "SLA" not in main, url


def test_with_the_sla_off_the_filter_and_the_order_do_nothing(app, staff, client):
    everything = _html(client, "/tickets?vista=todos")
    _set(app, settings.SLA_ENABLED, False)

    filtered = plain_text(client.get("/tickets?vista=todos&sla=vencido&orden=sla"))
    plain = plain_text(client.get("/tickets?vista=todos"))

    # El filtro no recorta el listado y el orden cae al de siempre.
    assert filtered == plain
    assert "#" in everything
    assert "Más SLA en riesgo" not in _html(client, "/workload?orden=riesgo")


def test_with_the_sla_off_the_counts_are_zero_and_nothing_is_evaluated(app, staff):
    _set(app, settings.SLA_ENABLED, False)

    with app.app_context():
        ids = list(db.session.scalars(db.select(Ticket.id)))

        assert set(evaluate_tickets_sla(ids).values()) == {None}


def test_turning_it_back_on_shows_the_sla_again(app, staff, client):
    _set(app, settings.SLA_ENABLED, False)
    _set(app, settings.SLA_ENABLED, True)

    assert "Fuera de SLA" in _html(client, "/dashboard")


# --- El planificador -------------------------------------------------------------------------


def _pending_marks(app):
    with app.app_context():
        return db.session.scalar(
            db.select(db.func.count(PeriodoSla.id)).where(
                PeriodoSla.fecha_aviso_vencimiento_enviado.is_(None),
                PeriodoSla.fecha_vencimiento_resolucion.is_not(None),
                PeriodoSla.fecha_fin.is_(None),
                PeriodoSla.fecha_vencimiento_resolucion <= db.func.now(),
            )
        )


def test_the_scheduler_does_not_notify_while_off_and_does_when_back(app, staff):
    pending = _pending_marks(app)
    assert pending > 0

    _set(app, settings.SLA_ENABLED, False)

    with app.app_context():
        notices, failures = scheduler.run_sla_notices()

    assert (notices.warnings, notices.breaches, failures) == (0, 0, 0)
    assert _pending_marks(app) == pending

    _set(app, settings.SLA_ENABLED, True)

    with app.app_context():
        notices, failures = scheduler.run_sla_notices()

    assert notices.breaches == pending
    assert failures == 0


def test_the_periods_keep_being_calculated_while_off(app, client, staff):
    _set(app, settings.SLA_ENABLED, False)

    with app.app_context():
        before = db.session.scalar(db.select(db.func.count(PeriodoSla.id)))
        ticket = db.session.scalar(
            db.select(Ticket)
            .join(PeriodoSla, PeriodoSla.ticket_id == Ticket.id)
            .where(PeriodoSla.fecha_fin.is_(None))
            .order_by(Ticket.id)
        )
        number, version = ticket.public_id, ticket.version
        priority = db.session.scalar(
            db.text("SELECT id FROM prioridades WHERE codigo = 'CRITICA'")
        )
        if ticket.prioridad_id == priority:
            priority = db.session.scalar(
                db.text("SELECT id FROM prioridades WHERE codigo = 'BAJA'")
            )

    response = client.post(
        f"/tickets/{number}/priority",
        data={"prioridad": priority, "motivo": "Cambio de prueba", "version": version},
    )

    assert response.status_code == 302

    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(PeriodoSla.id))) > before


# --- El cierre automático --------------------------------------------------------------------


def test_the_automatic_close_can_be_turned_off(app, staff):
    _set(app, settings.AUTO_CLOSE_ENABLED, False)

    with app.app_context():
        later = current_time() + timedelta(days=60)

        assert scheduler.run_auto_close(later) == (0, 0)

    _set(app, settings.AUTO_CLOSE_ENABLED, True)

    with app.app_context():
        closed, failures = scheduler.run_auto_close(later)

    assert closed > 0
    assert failures == 0


# --- La frecuencia del planificador -----------------------------------------------------------


def test_a_running_scheduler_follows_the_interval_chosen_by_the_administrator(
    app, administrator
):
    waits = []

    def change_after_first_wait(seconds):
        waits.append(seconds)

        if len(waits) == 1:
            _set(app, settings.SCHEDULER_INTERVAL_SECONDS, 90)

    with app.app_context():
        scheduler.run_loop(
            lambda: value_of(settings.SCHEDULER_INTERVAL_SECONDS),
            should_stop=lambda: len(waits) >= 2,
            sleep=change_after_first_wait,
        )

    assert waits == [60, 90]


def test_the_loop_survives_an_interval_that_cannot_be_read(app):
    waits = []

    def broken():
        raise RuntimeError("sin base de datos")

    with app.app_context():
        scheduler.run_loop(
            broken, should_stop=lambda: len(waits) >= 1, sleep=waits.append
        )

    assert waits == [60]


# --- Las barreras del servicio -----------------------------------------------------------
# La pantalla ya oculta lo mismo, así que estas se comprueban donde viven: cualquier otro
# código que llame al servicio no debe poder filtrar ni contar por un SLA apagado.


def _supervisor():
    return db.session.scalar(db.select(User).where(User.username == "camila.rojas"))


def test_the_listing_service_ignores_the_sla_filter_while_off(app, staff):
    filters = TicketFilters(sla=SlaFilter.VENCIDO)

    with app.app_context():
        filtered = list_tickets(_supervisor(), filters, tab="todos", per_page=500).total

    _set(app, settings.SLA_ENABLED, False)

    with app.app_context():
        everything = list_tickets(_supervisor(), filters, tab="todos", per_page=500).total
        unfiltered = list_tickets(
            _supervisor(), TicketFilters(), tab="todos", per_page=500
        ).total

    assert filtered < everything == unfiltered


def test_the_workload_service_counts_no_sla_while_off(app, staff):
    with app.app_context():
        before = workload_overview(_supervisor()).summary

    assert before.overdue > 0

    _set(app, settings.SLA_ENABLED, False)

    with app.app_context():
        summary = workload_overview(_supervisor()).summary

    assert (summary.overdue, summary.near_due, summary.at_risk) == (0, 0, 0)
    assert summary.active == before.active
