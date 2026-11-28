"""Tickets «sin actividad reciente» (RN-27, RF-036): la definición, el filtro del listado y
la carga de trabajo.

Sin actividad reciente es un ticket en trabajo en el que nadie del personal hizo nada en los
últimos `INACTIVE_TICKET_DAYS` días. Lo del solicitante y lo del sistema no cuenta.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update

from src.workdesk import settings
from src.workdesk.extensions import db
from src.workdesk.models import CommentType, TicketEvent, TicketHistory, User
from src.workdesk.tickets.assignment import assign_technician
from src.workdesk.tickets.comments import add_comment
from src.workdesk.tickets.queries import TAB_ALL, TicketFilters, list_tickets
from src.workdesk.tickets.service import record_ticket_event
from src.workdesk.workload.queries import workload_overview
from tests.ticket_helpers import login, make_ticket, set_state, ticket_by_public_id

AGO_30_DAYS = datetime.now(UTC) - timedelta(days=30)


@pytest.fixture()
def accounts(app, catalog, make_user):
    return {
        "requester": make_user("SOLICITANTE", "pide_ayuda"),
        "technician": make_user("TECNICO", "tecnico_lento"),
        "supervisor": make_user("SUPERVISOR", "supervisa"),
    }


@pytest.fixture()
def people(accounts):
    return {role: account["id"] for role, account in accounts.items()}


def _ticket(app, catalog, people):
    """Un ticket del solicitante, creado hace 30 días y con todo su historial de entonces."""
    public_id = make_ticket(app, catalog, people["requester"], [people["requester"]])
    _age_history(app, public_id, AGO_30_DAYS)

    return public_id


def _age_history(app, public_id, moment):
    """Lleva la creación del ticket y todo su historial a `moment`. El historial no se modifica
    desde la aplicación; aquí se envejece a propósito."""
    with app.app_context():
        ticket = ticket_by_public_id(public_id)
        ticket.fecha_creacion = moment
        db.session.execute(
            update(TicketHistory.__table__)
            .where(TicketHistory.__table__.c.ticket_id == ticket.id)
            .values(fecha_hora=moment)
        )
        db.session.commit()


def _inactive(app, user_id) -> list[str]:
    with app.app_context():
        page = list_tickets(db.session.get(User, user_id), TicketFilters(inactive=True), tab=TAB_ALL)

        return [ticket.public_id for ticket in page.items]


def _comment(app, public_id, author_id, kind=CommentType.PUBLICO):
    with app.app_context():
        add_comment(
            ticket_by_public_id(public_id),
            actor=db.session.get(User, author_id),
            content="¿Alguna novedad?",
            kind=kind,
        )
        db.session.commit()


# --- La definición ----------------------------------------------------------------------


def test_a_ticket_nobody_on_the_staff_touched_is_inactive(app, catalog, people):
    public_id = _ticket(app, catalog, people)

    assert _inactive(app, people["supervisor"]) == [public_id]


def test_a_recent_staff_action_makes_it_active_again(app, catalog, people):
    public_id = _ticket(app, catalog, people)
    _comment(app, public_id, people["technician"], CommentType.INTERNO)

    assert _inactive(app, people["supervisor"]) == []


def test_a_requester_asking_again_is_not_activity_of_the_team(app, catalog, people):
    """Justo el ticket que hay que mirar: pregunta y nadie del equipo responde."""
    public_id = _ticket(app, catalog, people)
    _comment(app, public_id, people["requester"])

    assert _inactive(app, people["supervisor"]) == [public_id]


def test_a_system_event_is_not_activity(app, catalog, people):
    public_id = _ticket(app, catalog, people)

    with app.app_context():
        record_ticket_event(ticket_by_public_id(public_id), TicketEvent.SLA_VENCIDO, actor=None)
        db.session.commit()

    assert _inactive(app, people["supervisor"]) == [public_id]


def test_the_number_of_days_is_the_one_in_force(app, catalog, people):
    public_id = make_ticket(app, catalog, people["requester"], [people["requester"]])
    _comment(app, public_id, people["technician"])
    _age_history(app, public_id, datetime.now(UTC) - timedelta(days=8))

    assert _inactive(app, people["supervisor"]) == [public_id]

    app.config[settings.INACTIVE_TICKET_DAYS.key] = 10

    assert _inactive(app, people["supervisor"]) == []


def test_zero_days_switches_the_mark_off(app, catalog, people):
    _ticket(app, catalog, people)
    app.config[settings.INACTIVE_TICKET_DAYS.key] = 0

    assert _inactive(app, people["supervisor"]) == []


def test_a_new_ticket_nobody_has_touched_yet_is_not_counted(app, catalog, people):
    """Que nadie lo haya tocado todavía ya lo dicen «Sin asignar» y el SLA: «sin actividad
    reciente» es un ticket con más días que el plazo."""
    make_ticket(app, catalog, people["requester"], [people["requester"]])

    assert _inactive(app, people["supervisor"]) == []


def test_a_ticket_on_hold_still_counts_but_resolved_or_closed_do_not(app, catalog, people):
    waiting, resolved, closed = (_ticket(app, catalog, people) for _ in range(3))
    set_state(app, waiting, "EN_ESPERA")
    set_state(app, resolved, "RESUELTO")
    set_state(app, closed, "CERRADO")

    assert _inactive(app, people["supervisor"]) == [waiting]


def test_a_requester_cannot_use_the_filter(app, catalog, people):
    """Como el SLA, es información del equipo: para un Solicitante el filtro no existe."""
    _ticket(app, catalog, people)
    make_ticket(app, catalog, people["requester"], [people["requester"]])

    assert len(_inactive(app, people["requester"])) == 2


# --- El listado -------------------------------------------------------------------------


def test_the_list_offers_the_filter_to_the_staff_with_its_days(app, client, catalog, people, accounts):
    public_id = _ticket(app, catalog, people)
    fresh = make_ticket(app, catalog, people["requester"], [people["requester"]], title="Pantalla negra")
    login(client, accounts["supervisor"])

    page = client.get("/tickets?vista=todos&sin_actividad=1").get_data(as_text=True)

    assert "Sin actividad del equipo en 7 días" in page
    assert f"#{public_id}" in page
    assert f"#{fresh}" not in page
    # Las pestañas, la paginación y la exportación conservan el filtro.
    assert "sin_actividad=1" in page


def test_the_requester_does_not_see_the_filter(app, client, catalog, people, accounts):
    _ticket(app, catalog, people)
    login(client, accounts["requester"])

    page = client.get("/tickets?sin_actividad=1").get_data(as_text=True)

    assert "Sin actividad del equipo" not in page


# --- La carga de trabajo ----------------------------------------------------------------


def test_the_workload_counts_it_for_each_technician_group_and_in_total(app, catalog, people):
    public_id = make_ticket(app, catalog, people["requester"], [people["requester"]])

    with app.app_context():
        assign_technician(
            ticket_by_public_id(public_id),
            people["technician"],
            actor=db.session.get(User, people["supervisor"]),
        )
        db.session.commit()

    assert _inactive(app, people["supervisor"]) == []

    _age_history(app, public_id, AGO_30_DAYS)

    with app.app_context():
        overview = workload_overview(db.session.get(User, people["supervisor"]))

    row = next(row for row in overview.technicians if row.user.id == people["technician"])

    assert overview.inactive_days == 7
    assert overview.summary.inactive == 1
    assert row.inactive == 1
    assert sum(group.inactive for group in overview.groups) == 1


def test_the_workload_screen_shows_it_only_while_the_mark_is_on(app, client, catalog, people, accounts):
    _ticket(app, catalog, people)
    login(client, accounts["supervisor"])

    assert "Sin actividad reciente" in client.get("/workload").get_data(as_text=True)

    app.config[settings.INACTIVE_TICKET_DAYS.key] = 0
    page = client.get("/workload").get_data(as_text=True)

    assert "Sin actividad reciente" not in page
    assert "Sin actividad</th>" not in page


def test_the_days_are_set_in_the_workload_settings_screen(app, client, make_user):
    login(client, make_user("ADMINISTRADOR", "admin_carga"))

    page = client.get("/admin/settings/operacion").get_data(as_text=True)

    assert "Días sin actividad para marcar un ticket" in page
