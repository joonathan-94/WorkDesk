"""Reasignación masiva (`tickets/reassignment.py`, docs/04 RF-034 y RF-035, docs/06 RN-30,
RN-104 y RN-137 a RN-139).

Lo que debe cumplirse: mover tickets de un técnico a otros conserva todo el rastro (la
asignación anterior se cierra, no se sobrescribe; cada ticket registra el lote; una sola
auditoría resume la operación), un ticket con problemas se omite sin frenar a los demás, nada
más del ticket cambia (ni el SLA ni la versión), solo el Supervisor y el Administrador pueden, y
dos personas que reasignan a la vez no se bloquean entre sí ni duplican nada.
"""

import pytest

from src.workdesk.audit import AuditAction
from src.workdesk.extensions import db
from src.workdesk.models import (
    Notificacion,
    PeriodoSla,
    TicketHistory,
    TicketTechnician,
    User,
)
from src.workdesk.tickets.assignment import assign_technician
from src.workdesk.tickets.queries import TAB_ALL, TicketFilters, list_tickets
from src.workdesk.tickets.reassignment import distribute, reassign_tickets
from src.workdesk.tickets.service import TicketRuleError
from src.workdesk.workload import workload_overview
from tests.ticket_helpers import (
    audit_entries,
    login,
    make_ticket,
    run_in_threads,
    set_state,
    ticket_by_public_id,
)


@pytest.fixture()
def team(make_user, catalog):
    return {
        "req": make_user("SOLICITANTE", username="req1"),
        "boss": make_user("SUPERVISOR", username="jefa"),
        "boss2": make_user("SUPERVISOR", username="jefa2"),
        "admin": make_user("ADMINISTRADOR", username="admin1"),
        "origin": make_user("TECNICO", username="origen", nombre="Valentina", apellido="Pizarro"),
        "dest1": make_user("TECNICO", username="destino1", nombre="Diego", apellido="Soto"),
        "dest2": make_user("TECNICO", username="destino2", nombre="Felipe", apellido="Araya"),
    }


def who(team, key):
    return db.session.get(User, team[key]["id"])


def assigned_tickets(app, catalog, team, count=3, to="origin"):
    """Crea `count` tickets del solicitante y los asigna al técnico `to`."""
    numbers = []

    for _ in range(count):
        number = make_ticket(app, catalog, team["req"]["id"], requester_ids=[team["req"]["id"]])

        with app.app_context():
            assign_technician(ticket_by_public_id(number), team[to]["id"], actor=who(team, "boss"))
            db.session.commit()

        numbers.append(number)

    return numbers


def ids(app, numbers):
    with app.app_context():
        return [ticket_by_public_id(n).id for n in numbers]


def run(app, team, numbers, destinations=("dest1",), actor="boss", reason="Vacaciones", source="origin"):
    """Reasigna `numbers` repartiéndolos entre `destinations` y confirma."""
    with app.app_context():
        ticket_ids = [ticket_by_public_id(n).id for n in numbers]
        moves = distribute(ticket_ids, [team[d]["id"] for d in destinations])
        result = reassign_tickets(
            who(team, actor), source_id=team[source]["id"], moves=moves, reason=reason
        )
        db.session.commit()

        return (
            [m.number for m in result.moved],
            {s.number: s.reason for s in result.skipped},
            result.batch,
        )


def current_technicians(app, number):
    with app.app_context():
        return sorted(a.tecnico.username for a in ticket_by_public_id(number).tecnicos_vigentes)


# --- El reparto ----------------------------------------------------------------------------


def test_distribute_deals_the_tickets_in_turns_in_id_order():
    assert distribute([5, 3, 4, 1], [10, 20]) == [(1, 10), (3, 20), (4, 10), (5, 20)]
    assert distribute([1, 2], [7]) == [(1, 7), (2, 7)]
    assert distribute([], [7]) == []


def test_distribute_needs_a_destination():
    with pytest.raises(TicketRuleError, match="al menos un técnico"):
        distribute([1], [])


# --- Lo que se mueve ---------------------------------------------------------------------------


def test_the_tickets_pass_to_the_destinations_and_the_old_assignment_is_kept(app, catalog, team):
    numbers = assigned_tickets(app, catalog, team, count=4)
    moved, skipped, _ = run(app, team, numbers, ("dest1", "dest2"))

    assert sorted(moved) == sorted(numbers) and skipped == {}
    assert current_technicians(app, numbers[0]) == ["destino1"]
    assert current_technicians(app, numbers[1]) == ["destino2"]

    with app.app_context():
        for number in numbers:
            ticket = ticket_by_public_id(number)
            old = [a for a in ticket.tecnicos if a.tecnico.username == "origen"]

            assert len(old) == 1
            assert old[0].fecha_desasignacion is not None
            assert old[0].desasignado_por_usuario_id == team["boss"]["id"]
            assert old[0].motivo_desasignacion == "Reasignación masiva: Vacaciones"


def test_each_ticket_records_who_why_and_the_batch(app, catalog, team):
    [number] = assigned_tickets(app, catalog, team, count=1)
    _, _, batch = run(app, team, [number], reason="Licencia médica")

    with app.app_context():
        events = {
            e.tipo_evento: e
            for e in db.session.scalars(
                db.select(TicketHistory).where(
                    TicketHistory.ticket_id == ticket_by_public_id(number).id,
                    TicketHistory.tipo_evento.in_(["TECNICO_DESASIGNADO", "TECNICO_ASIGNADO"]),
                    TicketHistory.contexto["lote"].astext == batch,
                )
            )
        }

        assert set(events) == {"TECNICO_DESASIGNADO", "TECNICO_ASIGNADO"}

        for event in events.values():
            assert event.actor_usuario_id == team["boss"]["id"]
            assert event.contexto["motivo"] == "Licencia médica"
            assert event.contexto["reasignacion_masiva"] is True

        assert events["TECNICO_DESASIGNADO"].valor_anterior["username"] == "origen"
        assert events["TECNICO_ASIGNADO"].valor_nuevo["username"] == "destino1"


def test_nothing_else_of_the_ticket_changes(app, catalog, team):
    [number] = assigned_tickets(app, catalog, team, count=1)

    with app.app_context():
        ticket = ticket_by_public_id(number)
        before = (ticket.version, ticket.fecha_modificacion, ticket.estado_id, ticket.grupo_id)
        requesters = sorted(r.id for r in ticket.solicitantes_vigentes)
        periods = sorted((p.id, p.fecha_fin, p.segundos_consumidos) for p in db.session.scalars(
            db.select(PeriodoSla).where(PeriodoSla.ticket_id == ticket.id)))

    run(app, team, [number])

    with app.app_context():
        ticket = ticket_by_public_id(number)

        assert (ticket.version, ticket.fecha_modificacion, ticket.estado_id, ticket.grupo_id) == before
        assert sorted(r.id for r in ticket.solicitantes_vigentes) == requesters
        assert sorted((p.id, p.fecha_fin, p.segundos_consumidos) for p in db.session.scalars(
            db.select(PeriodoSla).where(PeriodoSla.ticket_id == ticket.id))) == periods


def test_an_assigned_ticket_stays_assigned(app, catalog, team):
    [number] = assigned_tickets(app, catalog, team, count=1)
    run(app, team, [number])

    with app.app_context():
        assert ticket_by_public_id(number).estado.codigo == "ASIGNADO"
        assert db.session.scalar(
            db.select(db.func.count(TicketHistory.id)).where(
                TicketHistory.ticket_id == ticket_by_public_id(number).id,
                TicketHistory.tipo_evento == "ESTADO_CAMBIADO",
            )
        ) == 1  # solo el de la asignación original: nada nuevo por la reasignación


def test_a_destination_that_already_attends_the_ticket_only_removes_the_origin(app, catalog, team):
    [number] = assigned_tickets(app, catalog, team, count=1)

    with app.app_context():
        assign_technician(ticket_by_public_id(number), team["dest1"]["id"], actor=who(team, "boss"))
        db.session.commit()

    moved, _, batch = run(app, team, [number])

    assert moved == [number]
    assert current_technicians(app, number) == ["destino1"]

    with app.app_context():
        kinds = db.session.scalars(
            db.select(TicketHistory.tipo_evento).where(
                TicketHistory.contexto["lote"].astext == batch
            )
        ).all()

        assert kinds == ["TECNICO_DESASIGNADO"]


def test_an_inactive_origin_technician_can_be_emptied(app, catalog, team):
    numbers = assigned_tickets(app, catalog, team, count=2)

    with app.app_context():
        who(team, "origin").activo = False
        db.session.commit()

    moved, skipped, _ = run(app, team, numbers)

    assert sorted(moved) == sorted(numbers) and skipped == {}


def test_the_administrator_can_also_reassign(app, catalog, team):
    numbers = assigned_tickets(app, catalog, team, count=1)

    assert run(app, team, numbers, actor="admin")[0] == numbers


# --- Lo que se omite ----------------------------------------------------------------------------


def test_a_closed_ticket_is_skipped_and_the_rest_are_moved(app, catalog, team):
    first, second, third = assigned_tickets(app, catalog, team, count=3)
    set_state(app, second, "CERRADO")

    moved, skipped, _ = run(app, team, [first, second, third])

    assert sorted(moved) == sorted([first, third])
    assert skipped == {second: "El ticket está cerrado."}
    assert current_technicians(app, second) == ["origen"]


def test_a_ticket_no_longer_assigned_to_the_origin_is_skipped(app, catalog, team):
    first, second = assigned_tickets(app, catalog, team, count=2)
    other = assigned_tickets(app, catalog, team, count=1, to="dest2")[0]

    moved, skipped, _ = run(app, team, [first, other, second])

    assert sorted(moved) == sorted([first, second])
    assert "ya no está asignado" in skipped[other]
    assert current_technicians(app, other) == ["destino2"]


def test_a_missing_ticket_is_reported_not_fatal(app, catalog, team):
    [number] = assigned_tickets(app, catalog, team, count=1)

    with app.app_context():
        result = reassign_tickets(
            who(team, "boss"),
            source_id=team["origin"]["id"],
            moves=[(ticket_by_public_id(number).id, team["dest1"]["id"]), (999999, team["dest1"]["id"])],
            reason="Vacaciones",
        )

        assert [m.number for m in result.moved] == [number]
        assert [s.number for s in result.skipped] == ["999999"]


# --- Errores que detienen todo ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"reason": ""}, "motivo"),
        ({"reason": "   "}, "motivo"),
        ({"reason": "x" * 501}, "500"),
        ({"moves": []}, "al menos un ticket"),
        ({"source": 999999}, "origen no existe"),
        ({"dest": "origin"}, "mismo de origen"),
        ({"dest": "boss"}, "activos"),
        ({"dup": True}, "dos veces"),
    ],
)
def test_invalid_requests_stop_everything_and_change_nothing(app, catalog, team, kwargs, message):
    numbers = assigned_tickets(app, catalog, team, count=2)

    with app.app_context():
        ticket_ids = [ticket_by_public_id(n).id for n in numbers]
        dest = team[kwargs.get("dest", "dest1")]["id"]
        moves = kwargs.get("moves", [(ticket_ids[0], dest), (ticket_ids[1], dest)])

        if kwargs.get("dup"):
            moves = [(ticket_ids[0], dest), (ticket_ids[0], dest)]

        with pytest.raises(TicketRuleError, match=message):
            reassign_tickets(
                who(team, "boss"),
                source_id=kwargs.get("source", team["origin"]["id"]),
                moves=moves,
                reason=kwargs.get("reason", "Vacaciones"),
            )

        db.session.rollback()

    assert all(current_technicians(app, n) == ["origen"] for n in numbers)

    with app.app_context():
        assert [e for e in audit_entries() if e.accion == AuditAction.REASIGNACION_MASIVA.value] == []


def test_an_inactive_destination_is_rejected(app, catalog, team):
    [number] = assigned_tickets(app, catalog, team, count=1)

    with app.app_context():
        who(team, "dest1").activo = False
        db.session.commit()

        with pytest.raises(TicketRuleError, match="activos"):
            reassign_tickets(
                who(team, "boss"),
                source_id=team["origin"]["id"],
                moves=[(ticket_by_public_id(number).id, team["dest1"]["id"])],
                reason="Vacaciones",
            )


@pytest.mark.parametrize("role", ["origin", "req"])
def test_only_supervisors_and_administrators_can_reassign(app, catalog, team, role):
    [number] = assigned_tickets(app, catalog, team, count=1)

    with app.app_context(), pytest.raises(PermissionError):
        reassign_tickets(
            who(team, role),
            source_id=team["origin"]["id"],
            moves=[(ticket_by_public_id(number).id, team["dest1"]["id"])],
            reason="Vacaciones",
        )


def test_an_inactive_supervisor_cannot_reassign(app, catalog, team):
    [number] = assigned_tickets(app, catalog, team, count=1)

    with app.app_context():
        who(team, "boss").activo = False
        db.session.commit()

        # Un usuario inactivo ya no tiene ningún permiso.
        with pytest.raises(PermissionError):
            reassign_tickets(
                who(team, "boss"),
                source_id=team["origin"]["id"],
                moves=[(ticket_by_public_id(number).id, team["dest1"]["id"])],
                reason="Vacaciones",
            )


# --- Auditoría y avisos ---------------------------------------------------------------------------------


def test_one_audit_entry_summarises_the_operation(app, catalog, team):
    first, second, third = assigned_tickets(app, catalog, team, count=3)
    set_state(app, third, "CERRADO")
    _, _, batch = run(app, team, [first, second, third], ("dest1", "dest2"), reason="Renuncia")

    with app.app_context():
        entries = [e for e in audit_entries() if e.accion == "REASIGNACION_MASIVA"]

        assert len(entries) == 1
        entry = entries[0]

        assert entry.actor_usuario_id == team["boss"]["id"]
        assert (entry.entidad_tipo, entry.entidad_id) == ("tecnico", team["origin"]["id"])
        assert entry.motivo == "Renuncia"
        assert sorted(entry.valor_anterior["tickets"]) == sorted([first, second])
        assert entry.valor_nuevo["lote"] == batch
        assert entry.valor_nuevo["destinos"] == {"destino1": [first], "destino2": [second]}
        assert list(entry.valor_nuevo["omitidos"]) == [third]


def test_nothing_is_audited_when_nothing_moved(app, catalog, team):
    [number] = assigned_tickets(app, catalog, team, count=1)
    set_state(app, number, "CERRADO")

    moved, _, _ = run(app, team, [number])

    assert moved == []

    with app.app_context():
        assert [e for e in audit_entries() if e.accion == "REASIGNACION_MASIVA"] == []


def notices(app, username):
    with app.app_context():
        return list(
            db.session.execute(
                db.select(Notificacion.titulo, Notificacion.mensaje, Notificacion.ticket_id)
                .join(User, User.id == Notificacion.usuario_id)
                .where(User.username == username, Notificacion.tipo_evento == "TICKET_REASIGNADO")
            )
        )


def test_technicians_get_one_summary_each_and_requesters_one_per_ticket(app, catalog, team):
    numbers = assigned_tickets(app, catalog, team, count=3)
    run(app, team, numbers, ("dest1", "dest2"), reason="Motivo reservado")

    one = notices(app, "destino1")
    two = notices(app, "destino2")
    origin = notices(app, "origen")

    assert len(one) == 1 and "2 tickets" in one[0].mensaje and "Valentina Pizarro" in one[0].mensaje
    assert len(two) == 1 and "1 ticket" in two[0].mensaje
    assert len(origin) == 1 and "3 tickets" in origin[0].mensaje
    assert notices(app, "jefa") == []

    with app.app_context():
        cambios = db.session.scalar(
            db.select(db.func.count(Notificacion.id))
            .join(User, User.id == Notificacion.usuario_id)
            .where(User.username == "req1", Notificacion.titulo == "Tu ticket cambió de técnico")
        )

        assert cambios == 3

        everything = " ".join(
            m or "" for m in db.session.scalars(db.select(Notificacion.mensaje))
        )

        assert "Motivo reservado" not in everything


def test_the_requester_does_not_see_the_reason_in_the_ticket(app, client, catalog, team):
    [number] = assigned_tickets(app, catalog, team, count=1)
    run(app, team, [number], reason="Motivo reservado")
    login(client, team["req"])

    page = client.get(f"/tickets/{number}").get_data(as_text=True)

    assert "Motivo reservado" not in page
    assert "Diego Soto" in page


# --- Concurrencia -------------------------------------------------------------------------------------------


def test_two_supervisors_reassigning_the_same_tickets_do_not_block_or_duplicate(app, catalog, team):
    numbers = assigned_tickets(app, catalog, team, count=6)
    ticket_ids = ids(app, numbers)
    results = []

    def attempt(actor, dest, order):
        def task():
            result = reassign_tickets(
                db.session.get(User, team[actor]["id"]),
                source_id=team["origin"]["id"],
                moves=[(i, team[dest]["id"]) for i in order],
                reason="Vacaciones",
            )
            results.append((actor, len(result.moved), len(result.skipped)))

        return task

    outcomes = run_in_threads(
        app,
        # La segunda persona los pide en el orden contrario: sin bloquear siempre por id se
        # esperarían mutuamente.
        [
            attempt("boss", "dest1", ticket_ids),
            attempt("boss2", "dest2", list(reversed(ticket_ids))),
        ],
    )

    assert outcomes == ["ok", "ok"]
    # Cada ticket lo movió exactamente una de las dos personas.
    assert sum(moved for _, moved, _ in results) == 6
    assert sum(skipped for _, _, skipped in results) == 6

    with app.app_context():
        for number in numbers:
            ticket = ticket_by_public_id(number)

            assert len(ticket.tecnicos_vigentes) == 1
            assert ticket.tecnicos_vigentes[0].tecnico.username in ("destino1", "destino2")

        open_assignments = db.session.scalar(
            db.select(db.func.count(TicketTechnician.id)).where(
                TicketTechnician.tecnico_id == team["origin"]["id"],
                TicketTechnician.fecha_desasignacion.is_(None),
            )
        )

        assert open_assignments == 0


# --- Con los datos de demostración ------------------------------------------------------------------------------


def test_emptying_a_demonstration_technician_leaves_a_consistent_workload(seeded, app):
    with app.app_context():
        staff = db.session.scalar(db.select(User).where(User.username == "camila.rojas"))
        origin = db.session.scalar(db.select(User).where(User.username == "valentina.pizarro"))
        destinations = [
            db.session.scalar(db.select(User.id).where(User.username == name))
            for name in ("diego.soto", "felipe.araya")
        ]

        mine = list(
            db.session.scalars(
                list_tickets_ids(staff, origin.id)
            )
        )
        before = workload_overview(staff)
        row = next(r for r in before.technicians if r.user.id == origin.id)

        assert row.active > 0

        result = reassign_tickets(
            staff, source_id=origin.id, moves=distribute(mine, destinations), reason="Vacaciones"
        )
        db.session.commit()

        after = workload_overview(staff)
        new_row = next(r for r in after.technicians if r.user.id == origin.id)

        assert result.skipped == [] or all("cerrado" in s.reason for s in result.skipped)
        assert new_row.active == 0
        assert after.summary.unassigned == before.summary.unassigned
        # Nada se perdió: lo que dejó el origen lo recibieron los destinos.
        gained = sum(
            r.active - next(b for b in before.technicians if b.user.id == r.user.id).active
            for r in after.technicians
            if r.user.id in destinations
        )
        assert gained >= 1


def list_tickets_ids(staff, technician_id):
    """Los ids de los tickets que `technician_id` tiene asignados ahora (cualquier estado)."""
    return db.select(TicketTechnician.ticket_id).where(
        TicketTechnician.tecnico_id == technician_id,
        TicketTechnician.fecha_desasignacion.is_(None),
    )


def test_the_listing_follows_the_reassignment(seeded, app):
    with app.app_context():
        staff = db.session.scalar(db.select(User).where(User.username == "camila.rojas"))
        origin = db.session.scalar(db.select(User).where(User.username == "valentina.pizarro"))
        destination = db.session.scalar(db.select(User).where(User.username == "diego.soto"))
        mine = list(db.session.scalars(list_tickets_ids(staff, origin.id)))

        reassign_tickets(
            staff, source_id=origin.id, moves=distribute(mine, [destination.id]), reason="Licencia"
        )
        db.session.commit()

        assert list_tickets(staff, TicketFilters(technician_id=origin.id, active_only=True), tab=TAB_ALL).total == 0
        assert (
            list_tickets(staff, TicketFilters(technician_id=destination.id), tab=TAB_ALL).total
            >= len(mine) - 1
        )


def test_a_ticket_without_technician_is_skipped_with_a_clear_message(app, catalog, team):
    number = make_ticket(app, catalog, team["req"]["id"])
    moved, skipped, _ = run(app, team, [number])

    assert moved == [] and "ya no está asignado" in skipped[number]
