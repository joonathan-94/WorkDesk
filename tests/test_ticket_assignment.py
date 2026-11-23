"""Asignación de técnicos, grupo del ticket y escalamiento (docs/06, RN-157).

Cubre el servicio (`tickets/assignment.py`), sus efectos sobre el estado y el
historial, la visibilidad por rol y las pantallas.
"""


import pytest

from src.workdesk.extensions import db
from src.workdesk.groups.service import create_group, deactivate_group
from src.workdesk.models import (
    Grupo,
    TicketEvent,
    TicketHistory,
    TicketTechnician,
    TransicionEstado,
    User,
)
from src.workdesk.tickets.assignment import (
    assign_technician,
    escalate_ticket,
    list_assignable_technicians,
    list_groups_for_ticket,
    set_group,
    unassign_technician,
)
from src.workdesk.tickets.history import describe_history_changes
from src.workdesk.tickets.service import TicketRuleError
from src.workdesk.tickets.versioning import (
    TicketClosedError,
    TicketConflictError,
)
from tests.ticket_helpers import (
    login,
    make_ticket,
    plain_text,
    run_in_threads,
    set_state,
    ticket_by_public_id,
)

STAFF = ("TECNICO", "SUPERVISOR", "ADMINISTRADOR")


# --- Ayudas -----------------------------------------------------------


@pytest.fixture()
def team(make_user, catalog):
    """Personas de todos los roles y dos técnicos."""
    return {
        "req": make_user("SOLICITANTE", username="req1", nombre="Javiera", apellido="Torres"),
        "other": make_user("SOLICITANTE", username="req2", nombre="Paula", apellido="Contreras"),
        "tec": make_user("TECNICO", username="tec1", nombre="Diego", apellido="Soto"),
        "tec2": make_user("TECNICO", username="tec2", nombre="Valentina", apellido="Pizarro"),
        "sup": make_user("SUPERVISOR", username="sup1", nombre="Camila", apellido="Rojas"),
        "admin": make_user("ADMINISTRADOR", username="admin1", nombre="Ana", apellido="Admin"),
    }


def user(team, key) -> User:
    return db.session.get(User, team[key]["id"])


def new_ticket(app, catalog, team, **kwargs):
    return make_ticket(app, catalog, team["req"]["id"], **kwargs)


def new_group(team, name="Soporte Redes") -> Grupo:
    group = create_group(actor=user(team, "admin"), nombre=name)
    db.session.commit()

    return group


def events(ticket_id, *types):
    statement = (
        db.select(TicketHistory)
        .where(TicketHistory.ticket_id == ticket_id)
        .order_by(TicketHistory.id)
    )

    if types:
        statement = statement.where(
            TicketHistory.tipo_evento.in_([t.value for t in types])
        )

    return list(db.session.scalars(statement))


def assign(public_id, team, tech="tec", actor="sup"):
    ticket = ticket_by_public_id(public_id)
    assignment = assign_technician(
        ticket,
        team[tech]["id"],
        actor=user(team, actor),
    )
    db.session.commit()

    return assignment


def state_of(public_id) -> str:
    return ticket_by_public_id(public_id).estado.codigo


# --- Servicio: asignar ------------------------------------------------


def test_assigning_the_first_technician_moves_a_new_ticket_to_assigned(
    app,
    catalog,
    team,
):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        assignment = assign(public_id, team)
        ticket = ticket_by_public_id(public_id)

        assert assignment.fecha_desasignacion is None
        assert assignment.asignado_por_usuario_id == team["sup"]["id"]
        assert ticket.estado.codigo == "ASIGNADO"
        assert ticket.version == 2

        (assigned,) = events(ticket.id, TicketEvent.TECNICO_ASIGNADO)
        (state,) = events(ticket.id, TicketEvent.ESTADO_CAMBIADO)

        assert assigned.visibilidad == "PUBLICO"
        assert assigned.valor_nuevo == {
            "usuario_id": team["tec"]["id"],
            "username": "tec1",
            "nombre": "Diego Soto",
        }
        assert assigned.contexto == {"asignacion_id": assignment.id}
        assert state.contexto == {"accion": "ASIGNAR", "derivado": True}
        assert state.valor_anterior["codigo"] == "NUEVO"
        assert state.valor_nuevo["codigo"] == "ASIGNADO"
        assert assigned.id < state.id


def test_assigning_more_technicians_does_not_change_state_or_version(
    app,
    catalog,
    team,
):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        assign(public_id, team, "tec")
        assign(public_id, team, "tec2")
        ticket = ticket_by_public_id(public_id)

        assert len(ticket.tecnicos_vigentes) == 2
        assert ticket.estado.codigo == "ASIGNADO"
        # Solo el primero subió la versión (por el estado derivado).
        assert ticket.version == 2
        assert len(events(ticket.id, TicketEvent.ESTADO_CAMBIADO)) == 1


@pytest.mark.parametrize("code", ["EN_PROGRESO", "EN_ESPERA", "RESUELTO"])
def test_assigning_in_other_states_does_not_change_state_or_version(
    app,
    catalog,
    team,
    code,
):
    public_id = new_ticket(app, catalog, team)
    set_state(app, public_id, code)

    with app.app_context():
        assign(public_id, team)
        ticket = ticket_by_public_id(public_id)

        assert ticket.estado.codigo == code
        assert ticket.version == 1
        assert events(ticket.id, TicketEvent.ESTADO_CAMBIADO) == []


def test_a_disabled_assign_transition_leaves_the_state_alone(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        db.session.scalar(
            db.select(TransicionEstado).where(
                TransicionEstado.accion == "ASIGNAR"
            )
        ).activa = False
        db.session.commit()

        assign(public_id, team)

        assert state_of(public_id) == "NUEVO"
        assert ticket_by_public_id(public_id).version == 1


def test_a_technician_can_assign_themselves(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        assignment = assign(public_id, team, "tec", actor="tec")

        assert assignment.asignado_por_usuario_id == team["tec"]["id"]


@pytest.mark.parametrize("who", ["sup", "admin", "req"])
def test_only_active_technicians_can_be_assigned(app, catalog, team, who):
    public_id = new_ticket(app, catalog, team)

    with app.app_context(), pytest.raises(TicketRuleError, match="técnico activo"):
        assign_technician(
            ticket_by_public_id(public_id),
            team[who]["id"],
            actor=user(team, "sup"),
        )


def test_an_inactive_or_unknown_technician_cannot_be_assigned(
    app,
    catalog,
    team,
    make_user,
):
    inactive = make_user("TECNICO", username="tec_off", activo=False)
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        for user_id in (inactive["id"], 99999):
            with pytest.raises(TicketRuleError, match="técnico activo"):
                assign_technician(
                    ticket_by_public_id(public_id),
                    user_id,
                    actor=user(team, "sup"),
                )


def test_a_technician_cannot_be_assigned_twice(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        assign(public_id, team)

        with pytest.raises(TicketRuleError, match="ya está asignado"):
            assign_technician(
                ticket_by_public_id(public_id),
                team["tec"]["id"],
                actor=user(team, "sup"),
            )

        db.session.rollback()

        assert len(ticket_by_public_id(public_id).tecnicos_vigentes) == 1


def test_a_closed_ticket_cannot_be_assigned(app, catalog, team):
    public_id = new_ticket(app, catalog, team)
    set_state(app, public_id, "CERRADO")

    with app.app_context(), pytest.raises(TicketClosedError, match="reabrir"):
        assign_technician(
            ticket_by_public_id(public_id),
            team["tec"]["id"],
            actor=user(team, "sup"),
        )


def test_an_inactive_actor_cannot_assign(app, catalog, team, make_user):
    inactive = make_user("SUPERVISOR", username="sup_off", activo=False)
    public_id = new_ticket(app, catalog, team)

    with app.app_context(), pytest.raises(TicketRuleError, match="no está activo"):
        assign_technician(
            ticket_by_public_id(public_id),
            team["tec"]["id"],
            actor=db.session.get(User, inactive["id"]),
        )


def test_assigning_does_not_commit(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        assign_technician(
            ticket_by_public_id(public_id),
            team["tec"]["id"],
            actor=user(team, "sup"),
        )
        db.session.rollback()

        assert state_of(public_id) == "NUEVO"
        assert ticket_by_public_id(public_id).tecnicos_vigentes == []


def test_assignable_technicians_exclude_the_ones_already_assigned(
    app,
    catalog,
    team,
    make_user,
):
    make_user("TECNICO", username="tec_off", activo=False)
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        assign(public_id, team, "tec")

        assert [
            u.username
            for u in list_assignable_technicians(ticket_by_public_id(public_id))
        ] == ["tec2"]


# --- Servicio: quitar -------------------------------------------------


def test_unassigning_closes_the_assignment_and_keeps_it(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        assignment = assign(public_id, team)
        assign(public_id, team, "tec2")
        ticket = ticket_by_public_id(public_id)

        unassign_technician(
            ticket,
            assignment.id,
            actor=user(team, "sup"),
            reason="  Cambio de turno  ",
        )
        db.session.commit()
        db.session.refresh(assignment)

        assert assignment.fecha_desasignacion is not None
        assert assignment.desasignado_por_usuario_id == team["sup"]["id"]
        assert assignment.motivo_desasignacion == "Cambio de turno"
        assert [a.tecnico_id for a in ticket_by_public_id(public_id).tecnicos_vigentes] == [
            team["tec2"]["id"]
        ]

        (removed,) = events(ticket.id, TicketEvent.TECNICO_DESASIGNADO)

        assert removed.visibilidad == "PUBLICO"
        assert removed.valor_anterior["username"] == "tec1"
        assert removed.contexto == {
            "asignacion_id": assignment.id,
            "motivo": "Cambio de turno",
        }
        # Quedan técnicos: el estado no cambia.
        assert state_of(public_id) == "ASIGNADO"


def test_removing_the_last_technician_of_an_assigned_ticket_returns_it_to_new(
    app,
    catalog,
    team,
):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        assignment = assign(public_id, team)
        ticket = ticket_by_public_id(public_id)

        unassign_technician(ticket, assignment.id, actor=user(team, "sup"))
        db.session.commit()

        ticket = ticket_by_public_id(public_id)
        back = events(ticket.id, TicketEvent.ESTADO_CAMBIADO)[-1]

        assert ticket.estado.codigo == "NUEVO"
        assert ticket.version == 3
        assert back.contexto == {"accion": "DESASIGNACION", "derivado": True}
        assert back.valor_anterior["codigo"] == "ASIGNADO"


def test_removing_the_last_technician_in_progress_keeps_the_state(
    app,
    catalog,
    team,
):
    public_id = new_ticket(app, catalog, team)
    set_state(app, public_id, "EN_PROGRESO")

    with app.app_context():
        assignment = assign(public_id, team)

        unassign_technician(
            ticket_by_public_id(public_id),
            assignment.id,
            actor=user(team, "sup"),
        )
        db.session.commit()

        assert state_of(public_id) == "EN_PROGRESO"
        assert ticket_by_public_id(public_id).version == 1


def test_a_disabled_unassign_transition_leaves_the_state_alone(
    app,
    catalog,
    team,
):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        assignment = assign(public_id, team)
        db.session.scalar(
            db.select(TransicionEstado).where(
                TransicionEstado.accion == "DESASIGNACION"
            )
        ).activa = False
        db.session.commit()

        unassign_technician(
            ticket_by_public_id(public_id),
            assignment.id,
            actor=user(team, "sup"),
        )
        db.session.commit()

        assert state_of(public_id) == "ASIGNADO"


def test_a_removed_technician_can_be_assigned_again_as_a_new_row(
    app,
    catalog,
    team,
):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        first = assign(public_id, team)
        unassign_technician(
            ticket_by_public_id(public_id),
            first.id,
            actor=user(team, "sup"),
        )
        db.session.commit()
        second = assign(public_id, team)

        assert second.id != first.id
        assert (
            db.session.scalar(db.select(db.func.count(TicketTechnician.id)))
            == 2
        )
        assert len(ticket_by_public_id(public_id).tecnicos_vigentes) == 1


def test_unassign_rejects_unknown_foreign_or_already_removed_assignments(
    app,
    catalog,
    team,
):
    first = new_ticket(app, catalog, team)
    second = new_ticket(app, catalog, team)

    with app.app_context():
        mine = assign(first, team)
        other = assign(second, team, "tec2")

        for assignment_id in (99999, other.id):
            with pytest.raises(TicketRuleError, match="ya no está asignado"):
                unassign_technician(
                    ticket_by_public_id(first),
                    assignment_id,
                    actor=user(team, "sup"),
                )

        unassign_technician(ticket_by_public_id(first), mine.id, actor=user(team, "sup"))
        db.session.commit()

        with pytest.raises(TicketRuleError, match="ya no está asignado"):
            unassign_technician(
                ticket_by_public_id(first),
                mine.id,
                actor=user(team, "sup"),
            )


def test_unassign_rejects_a_long_reason_and_closed_tickets(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        assignment = assign(public_id, team)

        with pytest.raises(TicketRuleError, match="500"):
            unassign_technician(
                ticket_by_public_id(public_id),
                assignment.id,
                actor=user(team, "sup"),
                reason="x" * 501,
            )

        db.session.rollback()
        set_state(app, public_id, "CERRADO")

        with pytest.raises(TicketClosedError):
            unassign_technician(
                ticket_by_public_id(public_id),
                assignment.id,
                actor=user(team, "sup"),
            )


# --- Servicio: grupo --------------------------------------------------


def test_set_group_changes_it_bumps_the_version_and_records_an_internal_event(
    app,
    catalog,
    team,
):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        group = new_group(team)
        ticket = ticket_by_public_id(public_id)

        changed = set_group(
            ticket,
            group.id,
            actor=user(team, "sup"),
            expected_version=ticket.version,
        )
        db.session.commit()
        ticket = ticket_by_public_id(public_id)

        assert changed is True
        assert ticket.grupo_id == group.id
        assert ticket.version == 2
        # El grupo no cambia el estado.
        assert ticket.estado.codigo == "NUEVO"

        (event,) = events(ticket.id, TicketEvent.GRUPO_CAMBIADO)

        assert event.visibilidad == "INTERNO"
        assert event.valor_anterior == {"grupo_id": None, "nombre": None}
        assert event.valor_nuevo == {"grupo_id": group.id, "nombre": "Soporte Redes"}
        assert event.detalle == "Grupo cambiado de «Sin grupo» a «Soporte Redes»."


def test_set_group_can_clear_it_and_the_same_group_is_a_no_op(
    app,
    catalog,
    team,
):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        group = new_group(team)
        sup = user(team, "sup")
        set_group(ticket_by_public_id(public_id), group.id, actor=sup, expected_version=1)
        db.session.commit()

        assert (
            set_group(ticket_by_public_id(public_id), group.id, actor=sup, expected_version=2)
            is False
        )
        assert ticket_by_public_id(public_id).version == 2

        assert (
            set_group(ticket_by_public_id(public_id), None, actor=sup, expected_version=2)
            is True
        )
        db.session.commit()

        assert ticket_by_public_id(public_id).grupo_id is None
        assert (
            set_group(ticket_by_public_id(public_id), None, actor=sup, expected_version=3)
            is False
        )


def test_set_group_rejects_inactive_unknown_groups_and_keeps_the_current_one(
    app,
    catalog,
    team,
):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        group = new_group(team)
        other = new_group(team, "Soporte Usuarios")
        sup = user(team, "sup")
        set_group(ticket_by_public_id(public_id), group.id, actor=sup, expected_version=1)
        db.session.commit()

        deactivate_group(other, actor=user(team, "admin"))
        deactivate_group(group, actor=user(team, "admin"))
        db.session.commit()

        for group_id in (other.id, 99999):
            with pytest.raises(TicketRuleError, match="no está disponible"):
                set_group(
                    ticket_by_public_id(public_id),
                    group_id,
                    actor=sup,
                    expected_version=2,
                )

        db.session.rollback()

        # El grupo actual, aunque esté desactivado, se puede conservar.
        assert (
            set_group(ticket_by_public_id(public_id), group.id, actor=sup, expected_version=2)
            is False
        )


def test_set_group_detects_a_stale_version_and_closed_tickets(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        group = new_group(team)
        sup = user(team, "sup")

        with pytest.raises(TicketConflictError):
            set_group(ticket_by_public_id(public_id), group.id, actor=sup, expected_version=7)

        db.session.rollback()
        assert ticket_by_public_id(public_id).grupo_id is None

        set_state(app, public_id, "CERRADO")

        with pytest.raises(TicketClosedError):
            set_group(ticket_by_public_id(public_id), group.id, actor=sup, expected_version=1)


def test_groups_offered_include_the_current_inactive_one(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        group = new_group(team, "Viejo")
        new_group(team, "Activo")
        sup = user(team, "sup")
        set_group(ticket_by_public_id(public_id), group.id, actor=sup, expected_version=1)
        db.session.commit()
        deactivate_group(group, actor=user(team, "admin"))
        db.session.commit()

        names = [g.nombre for g in list_groups_for_ticket(ticket_by_public_id(public_id))]

        assert names == ["Activo", "Viejo"]


# --- Servicio: escalar ------------------------------------------------


def escalate(public_id, team, *, group=None, tech=None, reason="Necesita otro nivel", version=None):
    ticket = ticket_by_public_id(public_id)
    escalate_ticket(
        ticket,
        actor=user(team, "sup"),
        expected_version=ticket.version if version is None else version,
        group_id=None if group is None else group.id,
        technician_id=None if tech is None else team[tech]["id"],
        reason=reason,
    )
    db.session.commit()


def test_escalating_to_a_group_records_one_internal_event(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        group = new_group(team)
        escalate(public_id, team, group=group)
        ticket = ticket_by_public_id(public_id)

        assert ticket.grupo_id == group.id
        assert ticket.version == 2
        assert ticket.estado.codigo == "NUEVO"

        (event,) = events(ticket.id, TicketEvent.TICKET_ESCALADO)

        assert event.visibilidad == "INTERNO"
        assert event.contexto == {"motivo": "Necesita otro nivel"}
        assert event.valor_anterior == {
            "grupo": {"grupo_id": None, "nombre": None},
            "tecnicos": [],
        }
        assert event.valor_nuevo["grupo"]["nombre"] == "Soporte Redes"
        # Un único evento: sin eventos sueltos de grupo ni de técnicos.
        assert events(ticket.id, TicketEvent.GRUPO_CAMBIADO) == []
        assert events(ticket.id, TicketEvent.TECNICO_ASIGNADO) == []


def test_escalating_to_a_technician_replaces_the_current_ones(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        first = assign(public_id, team, "tec")
        before = ticket_by_public_id(public_id).version

        escalate(public_id, team, tech="tec2")
        db.session.refresh(first)
        ticket = ticket_by_public_id(public_id)

        assert [a.tecnico_id for a in ticket.tecnicos_vigentes] == [
            team["tec2"]["id"]
        ]
        assert first.fecha_desasignacion is not None
        assert first.motivo_desasignacion == "Escalamiento."
        # Solo técnico: sube la versión igualmente (es una acción con motivo).
        assert ticket.version == before + 1

        event = events(ticket.id, TicketEvent.TICKET_ESCALADO)[-1]

        assert [t["username"] for t in event.valor_anterior["tecnicos"]] == ["tec1"]
        assert [t["username"] for t in event.valor_nuevo["tecnicos"]] == ["tec2"]


def test_escalating_to_a_technician_moves_a_new_ticket_to_assigned(
    app,
    catalog,
    team,
):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        escalate(public_id, team, tech="tec")

        assert state_of(public_id) == "ASIGNADO"
        assert len(events(ticket_by_public_id(public_id).id, TicketEvent.ESTADO_CAMBIADO)) == 1


def test_escalating_to_a_group_and_a_technician_at_once(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        group = new_group(team)
        assign(public_id, team, "tec")

        escalate(public_id, team, group=group, tech="tec2")
        ticket = ticket_by_public_id(public_id)
        event = events(ticket.id, TicketEvent.TICKET_ESCALADO)[-1]

        assert ticket.grupo_id == group.id
        assert event.valor_nuevo["grupo"]["nombre"] == "Soporte Redes"
        assert [t["username"] for t in event.valor_nuevo["tecnicos"]] == ["tec2"]
        assert describe_history_changes(event) == [
            "Grupo: — → «Soporte Redes»",
            "Técnicos: «Diego Soto» → «Valentina Pizarro»",
        ]


def test_escalation_needs_a_real_change_and_a_reason(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        group = new_group(team)
        assign(public_id, team, "tec")
        sup = user(team, "sup")

        def attempt(**kwargs):
            ticket = ticket_by_public_id(public_id)
            values = {
                "actor": sup,
                "expected_version": ticket.version,
                "group_id": None,
                "technician_id": None,
                "reason": "Motivo",
            }
            values.update(kwargs)

            return escalate_ticket(ticket, **values)

        with pytest.raises(TicketRuleError, match="ningún cambio"):
            attempt()

        # El mismo único técnico que ya tiene: tampoco hay cambio.
        with pytest.raises(TicketRuleError, match="ningún cambio"):
            attempt(technician_id=team["tec"]["id"])

        with pytest.raises(TicketRuleError, match="motivo"):
            attempt(group_id=group.id, reason="   ")

        with pytest.raises(TicketRuleError, match="500"):
            attempt(group_id=group.id, reason="x" * 501)

        db.session.rollback()

        assert events(ticket_by_public_id(public_id).id, TicketEvent.TICKET_ESCALADO) == []


def test_escalation_rejects_bad_groups_and_technicians(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        group = new_group(team)
        deactivate_group(group, actor=user(team, "admin"))
        db.session.commit()
        sup = user(team, "sup")

        for kwargs, message in (
            ({"group_id": group.id}, "no está disponible"),
            ({"group_id": 99999}, "no está disponible"),
            ({"technician_id": team["sup"]["id"]}, "técnico activo"),
            ({"technician_id": 99999}, "técnico activo"),
        ):
            ticket = ticket_by_public_id(public_id)

            with pytest.raises(TicketRuleError, match=message):
                escalate_ticket(
                    ticket,
                    actor=sup,
                    expected_version=ticket.version,
                    group_id=kwargs.get("group_id"),
                    technician_id=kwargs.get("technician_id"),
                    reason="Motivo",
                )

            db.session.rollback()


def test_escalation_detects_a_stale_version_and_closed_tickets(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        group = new_group(team)

        with pytest.raises(TicketConflictError):
            escalate(public_id, team, group=group, version=9)

        db.session.rollback()
        set_state(app, public_id, "CERRADO")

        with pytest.raises(TicketClosedError):
            escalate(public_id, team, group=group)


# --- Concurrencia -----------------------------------------------------


def test_two_simultaneous_self_assignments_of_the_same_technician(
    app,
    catalog,
    team,
):
    public_id = new_ticket(app, catalog, team)

    def attempt():
        ticket = ticket_by_public_id(public_id)
        assign_technician(ticket, team["tec"]["id"], actor=user(team, "tec"))

    outcomes = run_in_threads(app, [attempt, attempt])

    assert sorted(outcomes) == ["Ese técnico ya está asignado al ticket.", "ok"]

    with app.app_context():
        assert len(ticket_by_public_id(public_id).tecnicos_vigentes) == 1


def test_two_technicians_assigning_to_a_new_ticket_move_it_to_assigned_once(
    app,
    catalog,
    team,
):
    public_id = new_ticket(app, catalog, team)

    def attempt(key):
        def task():
            ticket = ticket_by_public_id(public_id)
            assign_technician(ticket, team[key]["id"], actor=user(team, key))

        return task

    outcomes = run_in_threads(app, [attempt("tec"), attempt("tec2")])

    assert outcomes == ["ok", "ok"]

    with app.app_context():
        ticket = ticket_by_public_id(public_id)

        assert len(ticket.tecnicos_vigentes) == 2
        assert ticket.estado.codigo == "ASIGNADO"
        assert len(events(ticket.id, TicketEvent.ESTADO_CAMBIADO)) == 1


# --- Visibilidad ------------------------------------------------------


def test_the_requester_sees_who_attends_but_not_group_or_escalation(
    client,
    app,
    catalog,
    team,
):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        group = new_group(team)
        assign(public_id, team, "tec")
        escalate(public_id, team, group=group, reason="Muy técnico")

    login(client, team["req"])
    page = plain_text(client.get(f"/tickets/{public_id}"))

    assert "Atendido por" in page
    assert "Diego Soto" in page
    assert "Técnico asignado: «Diego Soto»" in page
    assert "Grupo" not in page
    assert "Soporte Redes" not in page
    assert "Ticket escalado" not in page
    assert "Muy técnico" not in page


def test_staff_sees_technicians_group_and_the_escalation_with_its_reason(
    client,
    app,
    catalog,
    team,
):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        group = new_group(team)
        assign(public_id, team, "tec")
        escalate(public_id, team, group=group, reason="Muy técnico")

    login(client, team["tec"])
    page = plain_text(client.get(f"/tickets/{public_id}"))

    assert "Técnico Diego Soto" in page
    assert "Grupo Soporte Redes" in page
    assert "Ticket escalado" in page
    assert "Grupo: — → «Soporte Redes»" in page
    assert "Motivo: Muy técnico" in page


def test_an_unassigned_ticket_says_so_for_each_audience(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    login(client, team["req"])

    assert "Aún sin asignar" in plain_text(client.get(f"/tickets/{public_id}"))

    client.post("/logout")
    login(client, team["tec"])

    assert "Sin asignar" in plain_text(client.get(f"/tickets/{public_id}"))


def test_an_inactive_assigned_technician_is_marked_for_staff(
    client,
    app,
    catalog,
    team,
):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        assign(public_id, team, "tec")
        user(team, "tec").activo = False
        db.session.commit()

    login(client, team["sup"])

    assert "(inactivo)" in plain_text(client.get(f"/tickets/{public_id}"))


# --- Pantallas: asignarse ---------------------------------------------


def test_a_technician_assigns_and_leaves_a_ticket_from_the_detail(
    client,
    app,
    catalog,
    team,
):
    public_id = new_ticket(app, catalog, team)
    login(client, team["tec"])

    html = client.get(f"/tickets/{public_id}").get_data(as_text=True)

    assert "Asignarme" in html
    assert f"/tickets/{public_id}/assign-me" in html
    assert "Dejar ticket" not in html

    response = client.post(f"/tickets/{public_id}/assign-me", follow_redirects=True)
    content = plain_text(response)

    assert f"Te asignaste el ticket #{public_id}." in content
    assert "Dejar ticket" in content
    assert "Estado: «Nuevo» → «Asignado»" in content

    with app.app_context():
        assert state_of(public_id) == "ASIGNADO"

    again = client.post(f"/tickets/{public_id}/assign-me", follow_redirects=True)

    assert "ya está asignado" in plain_text(again)

    left = client.post(f"/tickets/{public_id}/unassign-me", follow_redirects=True)

    assert f"Dejaste de estar asignado al ticket #{public_id}." in plain_text(left)

    with app.app_context():
        assert state_of(public_id) == "NUEVO"

    nothing = client.post(f"/tickets/{public_id}/unassign-me", follow_redirects=True)

    assert "No estás asignado a este ticket." in plain_text(nothing)


@pytest.mark.parametrize("key", ["sup", "admin", "req"])
@pytest.mark.parametrize("slug", ["assign-me", "unassign-me"])
def test_only_technicians_can_self_assign(client, app, catalog, team, key, slug):
    public_id = new_ticket(app, catalog, team)
    login(client, team[key])

    assert client.post(f"/tickets/{public_id}/{slug}").status_code == 403

    with app.app_context():
        assert ticket_by_public_id(public_id).tecnicos_vigentes == []


def test_a_technician_removes_only_their_own_assignment(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        mine = assign(public_id, team, "tec").id
        theirs = assign(public_id, team, "tec2").id

    login(client, team["tec"])
    base = f"/tickets/{public_id}/assignment/technicians"

    assert client.post(f"{base}/{theirs}/remove").status_code == 403

    response = client.post(f"{base}/{mine}/remove", follow_redirects=True)

    assert "Técnico desasignado." in plain_text(response)

    with app.app_context():
        assert [
            a.tecnico_id for a in ticket_by_public_id(public_id).tecnicos_vigentes
        ] == [team["tec2"]["id"]]


# --- Pantallas: asignación y grupo (Supervisor y Administrador) -------


@pytest.mark.parametrize("key", ["tec", "req"])
def test_technicians_and_requesters_cannot_use_the_management_screens(
    client,
    app,
    catalog,
    team,
    key,
):
    public_id = new_ticket(app, catalog, team)
    login(client, team[key])
    base = f"/tickets/{public_id}"

    assert client.get(f"{base}/assignment").status_code == 403
    assert client.get(f"{base}/escalate").status_code == 403
    assert (
        client.post(
            f"{base}/assignment/technicians/add",
            data={"tecnico": team["tec2"]["id"]},
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"{base}/assignment/group",
            data={"version": 1, "grupo": ""},
        ).status_code
        == 403
    )
    assert client.post(f"{base}/escalate", data={}).status_code == 403


def test_unseen_tickets_are_404_on_every_assignment_route(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)
    login(client, team["other"])
    base = f"/tickets/{public_id}"

    for method, path in (
        ("get", "/assignment"),
        ("get", "/escalate"),
        ("post", "/assign-me"),
        ("post", "/unassign-me"),
        ("post", "/assignment/technicians/add"),
        ("post", "/assignment/technicians/1/remove"),
        ("post", "/assignment/group"),
    ):
        assert getattr(client, method)(base + path).status_code == 404, path


@pytest.mark.parametrize("key", ["sup", "admin"])
def test_a_supervisor_or_administrator_assigns_and_removes_technicians(
    client,
    app,
    catalog,
    team,
    key,
):
    public_id = new_ticket(app, catalog, team)
    login(client, team[key])
    base = f"/tickets/{public_id}"

    page = plain_text(client.get(f"{base}/assignment"))

    assert "Asignación" in page
    assert "Este ticket no tiene técnicos asignados." in page
    assert "Diego Soto" in page and "Valentina Pizarro" in page

    added = client.post(
        f"{base}/assignment/technicians/add",
        data={"tecnico": team["tec"]["id"]},
        follow_redirects=True,
    )
    content = plain_text(added)

    assert "Técnico asignado." in content
    assert "Quitar" in content

    with app.app_context():
        assignment_id = ticket_by_public_id(public_id).tecnicos_vigentes[0].id
        assert state_of(public_id) == "ASIGNADO"

    removed = client.post(
        f"{base}/assignment/technicians/{assignment_id}/remove",
        data={"motivo": "Cambio"},
        follow_redirects=True,
    )

    assert "Técnico desasignado." in plain_text(removed)

    with app.app_context():
        assert state_of(public_id) == "NUEVO"


def test_the_management_screens_reject_invalid_technicians(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)
    login(client, team["sup"])
    url = f"/tickets/{public_id}/assignment/technicians/add"

    for data in ({}, {"tecnico": ""}, {"tecnico": "abc"}, {"tecnico": team["sup"]["id"]}):
        response = client.post(url, data=data, follow_redirects=True)

        assert "Elige un técnico de la lista." in plain_text(response) or (
            "Ingresa un número entero." in plain_text(response)
        )

    with app.app_context():
        assert ticket_by_public_id(public_id).tecnicos_vigentes == []


def test_removing_an_unknown_assignment_reports_it(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)
    login(client, team["sup"])

    response = client.post(
        f"/tickets/{public_id}/assignment/technicians/99999/remove",
        follow_redirects=True,
    )

    assert "ya no está asignado" in plain_text(response)


def test_the_group_of_a_ticket_is_set_and_cleared_from_the_screen(
    client,
    app,
    catalog,
    team,
):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        group_id = new_group(team).id

    login(client, team["sup"])
    url = f"/tickets/{public_id}/assignment/group"

    page = plain_text(client.get(f"/tickets/{public_id}/assignment"))

    assert "Sin grupo" in page and "Soporte Redes" in page

    changed = client.post(
        url,
        data={"version": 1, "grupo": group_id},
        follow_redirects=True,
    )

    assert "El grupo del ticket se actualizó." in plain_text(changed)

    same = client.post(
        url,
        data={"version": 2, "grupo": group_id},
        follow_redirects=True,
    )

    assert "El ticket ya tiene ese grupo." in plain_text(same)

    cleared = client.post(
        url,
        data={"version": 2, "grupo": ""},
        follow_redirects=True,
    )

    assert "El grupo del ticket se actualizó." in plain_text(cleared)

    with app.app_context():
        assert ticket_by_public_id(public_id).grupo_id is None


def test_group_change_validations_and_conflict(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        group_id = new_group(team).id

    login(client, team["sup"])
    url = f"/tickets/{public_id}/assignment/group"

    bad_group = client.post(
        url,
        data={"version": 1, "grupo": 99999},
        follow_redirects=True,
    )
    no_version = client.post(url, data={"grupo": group_id}, follow_redirects=True)
    stale = client.post(
        url,
        data={"version": 5, "grupo": group_id},
        follow_redirects=True,
    )

    assert "Selecciona un grupo válido." in plain_text(bad_group)
    assert "No se pudo comprobar la versión" in plain_text(no_version)
    assert "Otra persona modificó este ticket" in plain_text(stale)

    with app.app_context():
        assert ticket_by_public_id(public_id).grupo_id is None


def test_the_management_screens_redirect_for_a_closed_ticket(
    client,
    app,
    catalog,
    team,
):
    public_id = new_ticket(app, catalog, team)
    set_state(app, public_id, "CERRADO")
    login(client, team["sup"])
    base = f"/tickets/{public_id}"

    for path in ("/assignment", "/escalate"):
        response = client.get(base + path, follow_redirects=True)

        assert "Un ticket cerrado no se puede modificar." in plain_text(response)

    response = client.post(
        f"{base}/assignment/technicians/add",
        data={"tecnico": team["tec"]["id"]},
        follow_redirects=True,
    )

    assert "Un ticket cerrado no se puede modificar." in plain_text(response)


def test_the_detail_offers_the_right_buttons_per_role(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    login(client, team["tec"])
    html = client.get(f"/tickets/{public_id}").get_data(as_text=True)

    assert "Asignarme" in html
    assert "assignment" not in html.replace("assignment_page", "")

    client.post("/logout")
    login(client, team["sup"])
    html = client.get(f"/tickets/{public_id}").get_data(as_text=True)

    assert "Asignarme" not in html
    assert f"/tickets/{public_id}/assignment" in html

    client.post("/logout")
    login(client, team["req"])
    html = client.get(f"/tickets/{public_id}").get_data(as_text=True)

    assert "Asignarme" not in html
    assert "/assignment" not in html


def test_no_assignment_buttons_on_a_closed_ticket(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)
    set_state(app, public_id, "CERRADO")

    for key in ("tec", "sup"):
        client.post("/logout")
        login(client, team[key])
        html = client.get(f"/tickets/{public_id}").get_data(as_text=True)

        assert "Asignarme" not in html
        assert "/assignment" not in html


def test_the_assignment_screens_belong_to_the_tickets_menu(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)
    login(client, team["sup"])

    for path in ("/assignment", "/escalate"):
        html = client.get(f"/tickets/{public_id}{path}").get_data(as_text=True)

        assert 'aria-current="page"' in html


# --- Pantalla de escalamiento -----------------------------------------


def test_the_escalation_screen_shows_the_current_state_and_choices(
    client,
    app,
    catalog,
    team,
):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        new_group(team)
        assign(public_id, team, "tec")

    login(client, team["sup"])
    html = client.get(f"/tickets/{public_id}/escalate").get_data(as_text=True)
    page = plain_text(client.get(f"/tickets/{public_id}/escalate"))

    assert "Escalar ticket" in page
    assert "Sin grupo" in page
    assert "Diego Soto" in page
    assert "Soporte Redes" in page
    assert 'name="version"' in html


def test_a_supervisor_escalates_from_the_screen(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        group_id = new_group(team).id

    login(client, team["sup"])
    response = client.post(
        f"/tickets/{public_id}/escalate",
        data={
            "version": 1,
            "grupo": group_id,
            "tecnico": team["tec2"]["id"],
            "motivo": "Requiere conocimientos de redes",
        },
        follow_redirects=True,
    )
    content = plain_text(response)

    assert f"El ticket #{public_id} fue escalado." in content
    assert "Ticket escalado" in content
    assert "Motivo: Requiere conocimientos de redes" in content

    with app.app_context():
        ticket = ticket_by_public_id(public_id)

        assert ticket.grupo_id == group_id
        assert [a.tecnico_id for a in ticket.tecnicos_vigentes] == [team["tec2"]["id"]]
        assert ticket.estado.codigo == "ASIGNADO"


def test_escalation_form_validations(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        group_id = new_group(team).id

    login(client, team["sup"])
    url = f"/tickets/{public_id}/escalate"

    no_reason = client.post(url, data={"version": 1, "grupo": group_id})
    nothing = client.post(url, data={"version": 1, "motivo": "Sin cambio"})
    bad_group = client.post(
        url,
        data={"version": 1, "grupo": 99999, "motivo": "Motivo"},
    )
    bad_tech = client.post(
        url,
        data={"version": 1, "tecnico": team["sup"]["id"], "motivo": "Motivo"},
    )
    no_version = client.post(url, data={"grupo": group_id, "motivo": "Motivo"})
    long_reason = client.post(
        url,
        data={"version": 1, "grupo": group_id, "motivo": "x" * 501},
    )

    assert "Indica el motivo del escalamiento." in plain_text(no_reason)
    assert "ningún cambio" in plain_text(nothing)
    assert "Selecciona un grupo válido." in plain_text(bad_group)
    assert "Elige un técnico de la lista." in plain_text(bad_tech)
    assert "No se pudo comprobar la versión" in plain_text(no_version)
    assert "Máximo 500 caracteres." in plain_text(long_reason)

    with app.app_context():
        assert ticket_by_public_id(public_id).grupo_id is None
        assert events(ticket_by_public_id(public_id).id, TicketEvent.TICKET_ESCALADO) == []


def test_the_escalation_form_keeps_what_was_typed(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)
    login(client, team["sup"])

    response = client.post(
        f"/tickets/{public_id}/escalate",
        data={"version": 1, "motivo": "No me pierdas"},
    )

    assert "No me pierdas" in response.get_data(as_text=True)


def test_a_stale_escalation_reports_the_conflict(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        group_id = new_group(team).id

    login(client, team["sup"])
    response = client.post(
        f"/tickets/{public_id}/escalate",
        data={"version": 9, "grupo": group_id, "motivo": "Motivo"},
        follow_redirects=True,
    )

    assert "Otra persona modificó este ticket" in plain_text(response)

    with app.app_context():
        assert ticket_by_public_id(public_id).grupo_id is None


def test_the_history_lines_describe_assignment_events(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        group = new_group(team)
        assignment = assign(public_id, team, "tec")
        ticket = ticket_by_public_id(public_id)
        set_group(
            ticket,
            group.id,
            actor=user(team, "sup"),
            expected_version=ticket.version,
        )
        unassign_technician(
            ticket_by_public_id(public_id),
            assignment.id,
            actor=user(team, "sup"),
        )
        db.session.commit()

        lines = {
            e.tipo_evento: describe_history_changes(e)
            for e in events(
                ticket.id,
                TicketEvent.TECNICO_ASIGNADO,
                TicketEvent.TECNICO_DESASIGNADO,
                TicketEvent.GRUPO_CAMBIADO,
            )
        }

        assert lines["TECNICO_ASIGNADO"] == ["Técnico asignado: «Diego Soto»"]
        assert lines["TECNICO_DESASIGNADO"] == ["Técnico desasignado: «Diego Soto»"]
        assert lines["GRUPO_CAMBIADO"] == ["Grupo: — → «Soporte Redes»"]
