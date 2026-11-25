"""La carga de trabajo del equipo (`workload/queries.py`, docs/12 fase 6, RN-26 y RN-87).

La regla central, como en los dashboards: **cada cifra coincide con el total del listado al
que enlaza**. Se comprueba con los tickets de demostración para cada técnico, cada grupo y
cada total. Lo demás: un ticket con dos técnicos cuenta en cada uno y una vez en los totales,
quién aparece (técnicos sin carga, desactivados con trabajo), la marca de carga alta, que es
solo del personal y que el número de consultas no crece con el equipo.
"""

import pytest
from sqlalchemy import event

from src.workdesk.extensions import db
from src.workdesk.models import Estado, Grupo, Prioridad, Ticket, TicketTechnician, User
from src.workdesk.sla.queries import SlaFilter
from src.workdesk.tickets.assignment import assign_technician
from src.workdesk.tickets.queries import TAB_ALL, TicketFilters, list_tickets
from src.workdesk.workload import WorkloadFilters, is_high_load, workload_overview
from tests.demo_data import NOW, SOLICITANTES
from tests.ticket_helpers import make_ticket, set_state, ticket_by_public_id


def user(username):
    return db.session.scalar(db.select(User).where(User.username == username))


def overview(**filters):
    return workload_overview(user("camila.rojas"), WorkloadFilters(**filters), now=NOW)


def total(**filters):
    """El total del listado (todas las pestañas) que ve el personal con esos filtros."""
    return list_tickets(
        user("camila.rojas"), TicketFilters(**filters), tab=TAB_ALL, now=NOW
    ).total


def state_id(code):
    return db.session.scalar(db.select(Estado.id).where(Estado.codigo == code))


def critical_id():
    return db.session.scalar(db.select(Prioridad.id).where(Prioridad.codigo == "CRITICA"))


# --- Cada cifra es el total de su listado -----------------------------------------------


def test_every_total_equals_the_list_it_links_to(seeded, app):
    with app.app_context():
        summary = overview().summary

        assert summary.active == total(active_only=True)
        assert summary.unassigned == total(active_only=True, unassigned=True)
        assert summary.critical == total(active_only=True, priority_id=critical_id())
        assert summary.near_due == total(active_only=True, sla=SlaFilter.PROXIMO)
        assert summary.overdue == total(active_only=True, sla=SlaFilter.VENCIDO)
        assert summary.at_risk == total(active_only=True, sla=SlaFilter.RIESGO)
        assert summary.in_progress == total(state_id=state_id("EN_PROGRESO"))
        assert summary.on_hold == total(state_id=state_id("EN_ESPERA"))
        assert summary.assigned == summary.active - summary.unassigned
        assert summary.unassigned_critical == total(
            active_only=True, unassigned=True, priority_id=critical_id()
        )


def test_every_technician_row_equals_the_list_filtered_by_that_technician(seeded, app):
    with app.app_context():
        rows = overview().technicians

        assert len(rows) >= 4

        for row in rows:
            who = row.user.id
            assert row.active == total(active_only=True, technician_id=who), row.user.username
            assert row.critical == total(
                active_only=True, technician_id=who, priority_id=critical_id()
            )
            assert row.near_due == total(
                active_only=True, technician_id=who, sla=SlaFilter.PROXIMO
            )
            assert row.overdue == total(
                active_only=True, technician_id=who, sla=SlaFilter.VENCIDO
            )
            assert row.in_progress == total(technician_id=who, state_id=state_id("EN_PROGRESO"))
            assert row.on_hold == total(technician_id=who, state_id=state_id("EN_ESPERA"))
            assert row.resolved == total(technician_id=who, state_id=state_id("RESUELTO"))
            assert sum(row.by_priority.values()) == row.active


def test_every_group_row_equals_the_list_filtered_by_that_group(seeded, app):
    with app.app_context():
        rows = overview().groups
        named = [row for row in rows if row.group is not None]

        assert len(named) == 3

        for row in named:
            gid = row.group.id
            assert row.active == total(active_only=True, group_id=gid), row.group.nombre
            assert row.unassigned == total(active_only=True, group_id=gid, unassigned=True)
            assert row.critical == total(
                active_only=True, group_id=gid, priority_id=critical_id()
            )
            assert row.near_due == total(active_only=True, group_id=gid, sla=SlaFilter.PROXIMO)
            assert row.overdue == total(active_only=True, group_id=gid, sla=SlaFilter.VENCIDO)

        # Con «Sin grupo», los grupos reparten exactamente los tickets activos.
        assert sum(row.active for row in rows) == overview().summary.active


def test_the_filters_restrict_what_is_counted(seeded, app):
    with app.app_context():
        group = db.session.scalar(db.select(Grupo).where(Grupo.nombre == "Soporte Redes"))
        filtered = overview(group_id=group.id)

        assert filtered.summary.active == total(active_only=True, group_id=group.id)
        assert filtered.summary.critical == total(
            active_only=True, group_id=group.id, priority_id=critical_id()
        )

        by_priority = overview(priority_id=critical_id())

        assert by_priority.summary.active == by_priority.summary.critical
        assert by_priority.summary.active == total(
            active_only=True, priority_id=critical_id()
        )

        in_progress = overview(state_id=state_id("EN_PROGRESO"))

        assert in_progress.summary.active == in_progress.summary.in_progress
        assert overview(state_id=state_id("CERRADO")).summary.active == 0


# --- Un ticket con varios técnicos ---------------------------------------------------------


def test_a_ticket_with_two_technicians_counts_for_each_and_once_in_the_totals(seeded, app):
    with app.app_context():
        active_assignments = db.session.scalar(
            db.select(db.func.count(TicketTechnician.id))
            .join(Ticket, Ticket.id == TicketTechnician.ticket_id)
            .join(Estado, Estado.id == Ticket.estado_id)
            .where(
                TicketTechnician.fecha_desasignacion.is_(None),
                Estado.codigo.not_in(["RESUELTO", "CERRADO"]),
            )
        )
        data = overview()
        per_technician = sum(row.active for row in data.technicians)

        assert per_technician == active_assignments
        assert per_technician > data.summary.assigned
        # Los técnicos con trabajo se cuentan una vez cada uno.
        assert data.summary.technicians_with_work == sum(
            1 for row in data.technicians if row.active
        )


# --- Quién aparece -----------------------------------------------------------------------------


@pytest.fixture()
def team(make_user, catalog):
    return {
        "boss": make_user("SUPERVISOR", username="jefa"),
        "idle": make_user("TECNICO", username="sin_carga"),
        "busy": make_user("TECNICO", username="ocupado"),
        "gone": make_user("TECNICO", username="retirado"),
        "req": make_user("SOLICITANTE", username="req"),
    }


def assign(app, number, technician, boss):
    with app.app_context():
        assign_technician(
            ticket_by_public_id(number),
            technician["id"],
            actor=db.session.get(User, boss["id"]),
        )
        db.session.commit()


def deactivate(app, who):
    with app.app_context():
        db.session.get(User, who["id"]).activo = False
        db.session.commit()


def staff_overview(app, boss):
    with app.app_context():
        return workload_overview(db.session.get(User, boss["id"]))


def test_an_active_technician_without_tickets_appears_with_zero_load(app, team, catalog):
    with app.app_context():
        data = workload_overview(db.session.get(User, team["boss"]["id"]))
        names = {row.user.username: row for row in data.technicians}

        assert names["sin_carga"].active == 0
        assert names["ocupado"].active == 0
        assert data.summary.active == 0
        assert data.groups == []


def test_a_deactivated_technician_appears_only_while_they_keep_active_work(
    app, team, catalog
):
    first = make_ticket(app, catalog, team["req"]["id"])
    second = make_ticket(app, catalog, team["req"]["id"])
    assign(app, first, team["gone"], team["boss"])
    assign(app, second, team["gone"], team["boss"])
    deactivate(app, team["gone"])

    with app.app_context():
        rows = {
            row.user.username: row
            for row in workload_overview(db.session.get(User, team["boss"]["id"])).technicians
        }

        assert rows["retirado"].active == 2
        assert rows["retirado"].user.activo is False

    set_state(app, first, "CERRADO")
    set_state(app, second, "CERRADO")

    with app.app_context():
        names = {
            row.user.username
            for row in workload_overview(db.session.get(User, team["boss"]["id"])).technicians
        }

        assert "retirado" not in names
        assert "sin_carga" in names


def test_resolved_tickets_are_not_active_work_but_are_counted_apart(app, team, catalog):
    number = make_ticket(app, catalog, team["req"]["id"])
    assign(app, number, team["busy"], team["boss"])
    set_state(app, number, "RESUELTO")

    with app.app_context():
        data = workload_overview(db.session.get(User, team["boss"]["id"]))
        row = next(r for r in data.technicians if r.user.username == "ocupado")

        assert (row.active, row.resolved) == (0, 1)
        assert data.summary.active == 0


def test_a_technician_does_not_count_a_ticket_after_being_unassigned(app, team, catalog):
    number = make_ticket(app, catalog, team["req"]["id"])
    assign(app, number, team["busy"], team["boss"])

    with app.app_context():
        link = db.session.scalar(db.select(TicketTechnician))
        link.fecha_desasignacion = link.fecha_asignacion
        db.session.commit()

        data = workload_overview(db.session.get(User, team["boss"]["id"]))

        assert next(r for r in data.technicians if r.user.username == "ocupado").active == 0
        assert data.summary.unassigned == 1


def test_the_demonstration_has_work_in_every_corner(seeded, app):
    with app.app_context():
        data = overview()
        names = {row.group.nombre for row in data.groups if row.group}

        assert names == {"Soporte Redes", "Soporte Usuarios", "Aplicaciones"}
        assert any(row.group is None for row in data.groups)
        assert data.summary.unassigned >= 4
        assert data.summary.critical >= 3
        assert data.summary.overdue >= 1
        assert data.summary.on_hold >= 2
        assert data.summary.technicians_with_work >= 4


# --- Carga alta (RN-26: solo informa) ---------------------------------------------------------


@pytest.mark.parametrize(
    ("active", "threshold", "expected"),
    [(9, 10, False), (10, 10, True), (11, 10, True), (50, 0, False), (0, 0, False), (1, 1, True)],
)
def test_the_high_load_mark(active, threshold, expected):
    assert is_high_load(active, threshold) is expected


def test_the_threshold_comes_from_the_configuration(seeded, app):
    with app.app_context():
        busiest = max(row.active for row in overview().technicians)

        app.config["WORKLOAD_HIGH_ACTIVE_TICKETS"] = busiest
        data = overview()

        assert data.high_threshold == busiest
        assert data.summary.high_load_technicians == sum(
            1 for row in data.technicians if row.active >= busiest
        )
        assert all(row.high == (row.active >= busiest) for row in data.technicians)

        app.config["WORKLOAD_HIGH_ACTIVE_TICKETS"] = 0
        off = overview()

        assert not any(row.high for row in off.technicians)
        assert off.summary.high_load_technicians == 0


def test_the_default_threshold_is_ten(app):
    assert app.config["WORKLOAD_HIGH_ACTIVE_TICKETS"] == 10


def test_a_negative_threshold_does_not_start_the_app():
    from src import workdesk as workdesk_package

    with pytest.raises(RuntimeError, match="WORKLOAD_HIGH_ACTIVE_TICKETS"):
        workdesk_package.create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret-key",
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "WORKLOAD_HIGH_ACTIVE_TICKETS": -1,
            }
        )


def test_high_load_never_blocks_an_assignment(app, team, catalog):
    app.config["WORKLOAD_HIGH_ACTIVE_TICKETS"] = 1

    for _ in range(3):
        assign(app, make_ticket(app, catalog, team["req"]["id"]), team["busy"], team["boss"])

    with app.app_context():
        data = workload_overview(db.session.get(User, team["boss"]["id"]))
        row = next(r for r in data.technicians if r.user.username == "ocupado")

        assert row.active == 3 and row.high


# --- Solo el personal ---------------------------------------------------------------------------


@pytest.mark.parametrize("username", SOLICITANTES)
def test_a_requester_cannot_see_the_workload(seeded, app, username):
    with app.app_context(), pytest.raises(PermissionError):
        workload_overview(user(username), now=NOW)


@pytest.mark.parametrize("username", ["diego.soto", "camila.rojas"])
def test_a_technician_sees_the_whole_team(seeded, app, username):
    with app.app_context():
        data = workload_overview(user(username), now=NOW)

        assert data.summary.active == overview().summary.active
        assert len(data.technicians) == len(overview().technicians)


def test_an_inactive_user_cannot_see_the_workload(seeded, app):
    with app.app_context():
        who = user("camila.rojas")
        who.activo = False

        with pytest.raises(PermissionError):
            workload_overview(who, now=NOW)

        db.session.rollback()


# --- Consultas -------------------------------------------------------------------------------------


def count_queries(app, call):
    statements = []

    def record(conn, cursor, statement, *args):
        statements.append(statement)

    with app.app_context():
        event.listen(db.engine, "before_cursor_execute", record)

        try:
            call()
        finally:
            event.remove(db.engine, "before_cursor_execute", record)

    return len(statements)


def test_the_number_of_queries_does_not_depend_on_the_size_of_the_team(
    seeded, app, make_user
):
    def run():
        workload_overview(user("camila.rojas"), now=NOW)

    before = count_queries(app, run)

    for index in range(30):
        make_user("TECNICO", username=f"extra{index}")

    after = count_queries(app, run)

    assert before == after
    # Siete de la carga de trabajo y una más: la configuración (el umbral de carga alta),
    # que la primera lectura de la petición trae de la base de datos.
    assert before == 8, before

    with app.app_context():
        assert len(overview().technicians) >= 34
