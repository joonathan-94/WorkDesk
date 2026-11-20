"""Estados y transiciones de un ticket (docs/08, sección 34; docs/09, 12.2).

Cubre la tabla de transiciones y su seed, el servicio de cambios de estado
operativos (iniciar, poner en espera y reactivar) y sus pantallas. La
resolución, el cierre y la reapertura tienen su propio archivo
(`test_ticket_resolution.py`).
"""

import pytest
from sqlalchemy.exc import IntegrityError

from src.workdesk.extensions import db
from src.workdesk.models import (
    Estado,
    MotivoEspera,
    StateAction,
    Ticket,
    TicketEvent,
    TicketHistory,
    TransicionEstado,
    User,
)
from src.workdesk.seeds import seed_catalogs
from src.workdesk.seeds.catalogs import INITIAL_TRANSITIONS
from src.workdesk.tickets.lifecycle import (
    ACTION_BY_SLUG,
    STATE_ACTIONS,
    StateTransitionError,
    available_actions,
    change_state,
)
from src.workdesk.tickets.service import TicketRuleError
from src.workdesk.tickets.versioning import (
    TicketClosedError,
    TicketConflictError,
)
from tests.ticket_helpers import (
    login,
    make_ticket,
    plain_text,
    set_state,
    text,
)

STAFF_ROLES = ("TECNICO", "SUPERVISOR", "ADMINISTRADOR")
Action = StateAction


def state(code) -> Estado:
    return db.session.scalar(db.select(Estado).where(Estado.codigo == code))


def reason(code) -> MotivoEspera:
    return db.session.scalar(
        db.select(MotivoEspera).where(MotivoEspera.codigo == code)
    )


def get_ticket(public_id) -> Ticket:
    return db.session.scalar(
        db.select(Ticket).where(Ticket.public_id == public_id)
    )


def state_events(ticket_id) -> list[TicketHistory]:
    return list(
        db.session.scalars(
            db.select(TicketHistory)
            .where(
                TicketHistory.ticket_id == ticket_id,
                TicketHistory.tipo_evento == TicketEvent.ESTADO_CAMBIADO.value,
            )
            .order_by(TicketHistory.id)
        )
    )


def run(public_id, user_id, action, *, version=None, **kwargs):
    """Ejecuta `change_state` y confirma. Devuelve el estado nuevo."""
    ticket = get_ticket(public_id)

    new_state = change_state(
        ticket,
        actor=db.session.get(User, user_id),
        action=action,
        expected_version=ticket.version if version is None else version,
        **kwargs,
    )
    db.session.commit()

    return new_state


@pytest.fixture()
def staff(make_user, catalog):
    return make_user("TECNICO", username="tecnico")


# --- Tabla de transiciones y seed -----------------------------------------


def _all_transitions():
    return list(db.session.scalars(db.select(TransicionEstado)))


def _triples():
    return {
        (t.estado_origen.codigo, t.estado_destino.codigo, t.accion)
        for t in _all_transitions()
    }


def test_the_seed_loads_every_documented_transition(app):
    with app.app_context():
        created = seed_catalogs()["transiciones"]

        assert created == len(INITIAL_TRANSITIONS) == 20
        assert len(_all_transitions()) == 20
        assert all(t.activa for t in _all_transitions())


def test_the_seed_matches_the_flow_matrix(app):
    with app.app_context():
        seed_catalogs()
        triples = _triples()

        # Desde los cuatro estados operativos se puede resolver y cerrar
        # directamente, pero nunca desde Resuelto.
        for origin in ("NUEVO", "ASIGNADO", "EN_PROGRESO", "EN_ESPERA"):
            assert (origin, "RESUELTO", "RESOLVER") in triples
            assert (origin, "CERRADO", "CIERRE_DIRECTO") in triples

        assert not any(
            origin == "RESUELTO" and action == "CIERRE_DIRECTO"
            for origin, _, action in triples
        )

        # Resuelto se cierra por confirmación, auto-cierre o cierre excepcional.
        assert {
            action
            for origin, destination, action in triples
            if origin == "RESUELTO" and destination == "CERRADO"
        } == {"CONFIRMAR", "AUTO_CIERRE", "CIERRE_EXCEPCIONAL"}

        # Reabrir (Resuelto o Cerrado) y rechazar llevan a En progreso.
        assert ("CERRADO", "EN_PROGRESO", "REABRIR") in triples
        assert ("RESUELTO", "EN_PROGRESO", "REABRIR") in triples
        assert ("RESUELTO", "EN_PROGRESO", "RECHAZAR") in triples

        # Cerrado solo sale reabriendo; la espera solo se entra desde En progreso.
        assert {a for o, _, a in triples if o == "CERRADO"} == {"REABRIR"}
        assert {o for o, _, a in triples if a == "PONER_EN_ESPERA"} == {
            "EN_PROGRESO"
        }

        # No hay estado "Reabierto": las transiciones solo usan los seis.
        assert {o for o, _, _ in triples} | {d for _, d, _ in triples} == {
            "NUEVO",
            "ASIGNADO",
            "EN_PROGRESO",
            "EN_ESPERA",
            "RESUELTO",
            "CERRADO",
        }


def test_every_action_of_the_vocabulary_is_in_the_matrix(app):
    with app.app_context():
        seed_catalogs()

        assert {a for _, _, a in _triples()} == {a.value for a in StateAction}


def test_the_seed_is_idempotent_and_keeps_a_disabled_transition(app):
    with app.app_context():
        seed_catalogs()

        transition = db.session.scalar(
            db.select(TransicionEstado).where(
                TransicionEstado.accion == Action.PONER_EN_ESPERA.value
            )
        )
        transition.activa = False
        db.session.commit()

        assert seed_catalogs()["transiciones"] == 0

        db.session.refresh(transition)

        assert transition.activa is False
        assert len(_all_transitions()) == 20


def test_seed_catalogs_command_reports_the_transitions(app):
    result = app.test_cli_runner().invoke(args=["seed-catalogs"])

    assert result.exit_code == 0
    assert "transiciones: 20" in result.output


def test_a_transition_is_unique_per_origin_destination_and_action(app):
    with app.app_context():
        seed_catalogs()

        existing = _all_transitions()[0]
        db.session.add(
            TransicionEstado(
                estado_origen_id=existing.estado_origen_id,
                estado_destino_id=existing.estado_destino_id,
                accion=existing.accion,
            )
        )

        with pytest.raises(IntegrityError):
            db.session.commit()


def test_the_same_pair_can_exist_with_different_actions(app):
    with app.app_context():
        seed_catalogs()

        # Resuelto → Cerrado ya existe con tres acciones distintas.
        pairs = [
            t
            for t in _all_transitions()
            if t.estado_origen.codigo == "RESUELTO"
            and t.estado_destino.codigo == "CERRADO"
        ]

        assert len(pairs) == 3


def test_a_transition_cannot_go_from_a_state_to_itself(app):
    with app.app_context():
        seed_catalogs()

        db.session.add(
            TransicionEstado(
                estado_origen_id=state("NUEVO").id,
                estado_destino_id=state("NUEVO").id,
                accion="INICIAR",
            )
        )

        with pytest.raises(IntegrityError):
            db.session.commit()


# --- Acciones disponibles --------------------------------------------------


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        # Un Técnico puede, desde cualquier estado abierto, resolver o cerrar
        # directamente; de un ticket Resuelto o Cerrado solo puede reabrirlo
        # (el cierre excepcional es del Supervisor y el Administrador).
        ("NUEVO", ["INICIAR", "RESOLVER", "CIERRE_DIRECTO"]),
        ("ASIGNADO", ["INICIAR", "RESOLVER", "CIERRE_DIRECTO"]),
        ("EN_PROGRESO", ["PONER_EN_ESPERA", "RESOLVER", "CIERRE_DIRECTO"]),
        ("EN_ESPERA", ["REACTIVAR", "RESOLVER", "CIERRE_DIRECTO"]),
        ("RESUELTO", ["REABRIR"]),
        ("CERRADO", ["REABRIR"]),
    ],
)
def test_available_actions_depend_on_the_current_state(
    app,
    make_user,
    catalog,
    staff,
    code,
    expected,
):
    public_id = make_ticket(app, catalog, staff["id"])
    set_state(app, public_id, code)

    with app.app_context():
        options = available_actions(
            get_ticket(public_id),
            db.session.get(User, staff["id"]),
        )

        assert [o.info.action.value for o in options] == expected


def test_available_actions_include_the_destination_state(
    app,
    catalog,
    staff,
):
    public_id = make_ticket(app, catalog, staff["id"])

    with app.app_context():
        options = {
            o.info.action: o
            for o in available_actions(
                get_ticket(public_id),
                db.session.get(User, staff["id"]),
            )
        }

        assert options[Action.INICIAR].destination.codigo == "EN_PROGRESO"
        assert options[Action.RESOLVER].destination.codigo == "RESUELTO"
        assert options[Action.CIERRE_DIRECTO].destination.codigo == "CERRADO"


def test_the_requester_has_no_available_actions(
    app,
    make_user,
    catalog,
):
    requester = make_user("SOLICITANTE")
    public_id = make_ticket(app, catalog, requester["id"])

    with app.app_context():
        assert (
            available_actions(
                get_ticket(public_id),
                db.session.get(User, requester["id"]),
            )
            == []
        )


def test_a_disabled_transition_is_not_offered(app, catalog, staff):
    public_id = make_ticket(app, catalog, staff["id"])

    with app.app_context():
        transition = db.session.scalar(
            db.select(TransicionEstado).where(
                TransicionEstado.estado_origen_id == state("NUEVO").id,
                TransicionEstado.accion == "INICIAR",
            )
        )
        transition.activa = False
        db.session.commit()

        offered = {
            o.info.action
            for o in available_actions(
                get_ticket(public_id),
                db.session.get(User, staff["id"]),
            )
        }

        assert Action.INICIAR not in offered
        assert offered == {Action.RESOLVER, Action.CIERRE_DIRECTO}


def test_every_action_is_implemented_except_the_system_and_derived_ones():
    # Asignar y quitar al último técnico son transiciones derivadas de la
    # asignación y el cierre automático lo hará el planificador (v0.5.0).
    assert set(STATE_ACTIONS) == set(Action) - {
        Action.ASIGNAR,
        Action.DESASIGNACION,
        Action.AUTO_CIERRE,
    }
    assert set(ACTION_BY_SLUG) == {
        "start",
        "hold",
        "resume",
        "resolve",
        "close",
        "confirm",
        "reject",
        "close-exceptional",
        "reopen",
    }


# --- Servicio: cambios de estado ------------------------------------------


def test_start_moves_the_ticket_to_in_progress_and_records_the_event(
    app,
    catalog,
    staff,
):
    public_id = make_ticket(app, catalog, staff["id"])

    with app.app_context():
        new_state = run(public_id, staff["id"], Action.INICIAR)
        ticket = get_ticket(public_id)

        assert new_state.codigo == "EN_PROGRESO"
        assert ticket.estado.codigo == "EN_PROGRESO"
        assert ticket.version == 2
        assert ticket.usuario_modificacion_id == staff["id"]
        assert ticket.fecha_modificacion is not None

        (event,) = state_events(ticket.id)

        assert event.estado_anterior_id == state("NUEVO").id
        assert event.estado_nuevo_id == state("EN_PROGRESO").id
        assert event.detalle == (
            "Estado cambiado de «Nuevo» a «En progreso»."
        )
        assert event.valor_anterior["codigo"] == "NUEVO"
        assert event.valor_nuevo["codigo"] == "EN_PROGRESO"
        assert event.contexto == {"accion": "INICIAR"}
        assert event.visibilidad == "PUBLICO"
        assert event.motivo_espera_id is None
        assert event.actor_usuario_id == staff["id"]


def test_an_assigned_ticket_can_also_be_started(app, catalog, staff):
    public_id = make_ticket(app, catalog, staff["id"])
    set_state(app, public_id, "ASIGNADO")

    with app.app_context():
        assert run(public_id, staff["id"], Action.INICIAR).codigo == (
            "EN_PROGRESO"
        )


def test_the_full_operational_cycle_raises_the_version_each_time(
    app,
    catalog,
    staff,
):
    public_id = make_ticket(app, catalog, staff["id"])

    with app.app_context():
        run(public_id, staff["id"], Action.INICIAR)
        run(public_id, staff["id"], Action.PONER_EN_ESPERA)
        run(public_id, staff["id"], Action.REACTIVAR)

        ticket = get_ticket(public_id)

        assert ticket.estado.codigo == "EN_PROGRESO"
        assert ticket.version == 4
        assert [
            (e.valor_anterior["codigo"], e.valor_nuevo["codigo"])
            for e in state_events(ticket.id)
        ] == [
            ("NUEVO", "EN_PROGRESO"),
            ("EN_PROGRESO", "EN_ESPERA"),
            ("EN_ESPERA", "EN_PROGRESO"),
        ]


def test_hold_without_a_reason_is_valid(app, catalog, staff):
    public_id = make_ticket(app, catalog, staff["id"])
    set_state(app, public_id, "EN_PROGRESO")

    with app.app_context():
        run(public_id, staff["id"], Action.PONER_EN_ESPERA)

        (event,) = state_events(get_ticket(public_id).id)

        assert event.motivo_espera_id is None
        assert event.contexto == {"accion": "PONER_EN_ESPERA"}


def test_hold_with_a_catalog_reason_keeps_it_in_the_history(
    app,
    catalog,
    staff,
):
    public_id = make_ticket(app, catalog, staff["id"])
    set_state(app, public_id, "EN_PROGRESO")

    with app.app_context():
        third_party = reason("ESPERA_TERCERO")

        run(
            public_id,
            staff["id"],
            Action.PONER_EN_ESPERA,
            wait_reason_id=third_party.id,
        )

        (event,) = state_events(get_ticket(public_id).id)

        assert event.motivo_espera_id == third_party.id
        assert "motivo" not in event.contexto


def test_hold_with_free_text_on_a_reason_that_allows_it(app, catalog, staff):
    public_id = make_ticket(app, catalog, staff["id"])
    set_state(app, public_id, "EN_PROGRESO")

    with app.app_context():
        run(
            public_id,
            staff["id"],
            Action.PONER_EN_ESPERA,
            wait_reason_id=reason("OTRO").id,
            text="  Esperando la visita del proveedor  ",
        )

        (event,) = state_events(get_ticket(public_id).id)

        assert event.contexto == {
            "accion": "PONER_EN_ESPERA",
            "motivo": "Esperando la visita del proveedor",
        }


@pytest.mark.parametrize(
    ("reason_code", "text", "message"),
    [
        ("ESPERA_TERCERO", "Texto", "admita texto libre"),
        (None, "Texto", "admita texto libre"),
        ("OTRO", "x" * 501, "no puede superar los 500"),
    ],
)
def test_free_text_rules_when_putting_a_ticket_on_hold(
    app,
    catalog,
    staff,
    reason_code,
    text,
    message,
):
    public_id = make_ticket(app, catalog, staff["id"])
    set_state(app, public_id, "EN_PROGRESO")

    with app.app_context():
        ticket = get_ticket(public_id)
        reason_id = None if reason_code is None else reason(reason_code).id

        with pytest.raises(TicketRuleError, match=message):
            change_state(
                ticket,
                actor=db.session.get(User, staff["id"]),
                action=Action.PONER_EN_ESPERA,
                expected_version=ticket.version,
                wait_reason_id=reason_id,
                text=text,
            )

        db.session.rollback()

        ticket = get_ticket(public_id)

        assert ticket.estado.codigo == "EN_PROGRESO"
        assert ticket.version == 1
        assert state_events(ticket.id) == []


def test_an_inactive_or_unknown_wait_reason_is_rejected(app, catalog, staff):
    public_id = make_ticket(app, catalog, staff["id"])
    set_state(app, public_id, "EN_PROGRESO")

    with app.app_context():
        inactive = reason("RECURSO_PENDIENTE")
        inactive.activo = False
        db.session.commit()

        for reason_id in (inactive.id, 99999):
            ticket = get_ticket(public_id)

            with pytest.raises(TicketRuleError, match="no está disponible"):
                change_state(
                    ticket,
                    actor=db.session.get(User, staff["id"]),
                    action=Action.PONER_EN_ESPERA,
                    expected_version=ticket.version,
                    wait_reason_id=reason_id,
                )

            db.session.rollback()


@pytest.mark.parametrize(
    ("code", "action"),
    [("NUEVO", Action.INICIAR), ("EN_ESPERA", Action.REACTIVAR)],
)
def test_actions_other_than_hold_do_not_accept_a_wait_reason(
    app,
    catalog,
    staff,
    code,
    action,
):
    public_id = make_ticket(app, catalog, staff["id"])
    set_state(app, public_id, code)

    with app.app_context():
        ticket = get_ticket(public_id)

        for extra in ({"wait_reason_id": reason("OTRO").id}, {"text": "x"}):
            with pytest.raises(TicketRuleError, match="no admite"):
                change_state(
                    ticket,
                    actor=db.session.get(User, staff["id"]),
                    action=action,
                    expected_version=ticket.version,
                    **extra,
                )

            db.session.rollback()


@pytest.mark.parametrize(
    ("code", "action"),
    [
        ("NUEVO", Action.PONER_EN_ESPERA),
        ("NUEVO", Action.REACTIVAR),
        ("EN_PROGRESO", Action.INICIAR),
        ("EN_PROGRESO", Action.REACTIVAR),
        ("EN_ESPERA", Action.INICIAR),
        ("EN_ESPERA", Action.PONER_EN_ESPERA),
        ("RESUELTO", Action.INICIAR),
        ("RESUELTO", Action.REACTIVAR),
    ],
)
def test_an_action_not_valid_from_the_current_state_is_rejected(
    app,
    catalog,
    staff,
    code,
    action,
):
    public_id = make_ticket(app, catalog, staff["id"])
    set_state(app, public_id, code)

    with app.app_context():
        ticket = get_ticket(public_id)

        with pytest.raises(StateTransitionError):
            change_state(
                ticket,
                actor=db.session.get(User, staff["id"]),
                action=action,
                expected_version=ticket.version,
            )

        db.session.rollback()

        ticket = get_ticket(public_id)

        assert ticket.estado.codigo == code
        assert ticket.version == 1
        assert state_events(ticket.id) == []


@pytest.mark.parametrize(
    "action",
    [
        Action.ASIGNAR,
        Action.DESASIGNACION,
        Action.AUTO_CIERRE,
    ],
)
def test_actions_without_an_implementation_yet_are_rejected(
    app,
    catalog,
    staff,
    action,
):
    public_id = make_ticket(app, catalog, staff["id"])

    with app.app_context():
        ticket = get_ticket(public_id)

        with pytest.raises(StateTransitionError, match="todavía no"):
            change_state(
                ticket,
                actor=db.session.get(User, staff["id"]),
                action=action,
                expected_version=ticket.version,
            )


def test_an_unknown_action_is_rejected(app, catalog, staff):
    public_id = make_ticket(app, catalog, staff["id"])

    with app.app_context():
        ticket = get_ticket(public_id)

        with pytest.raises(ValueError):
            change_state(
                ticket,
                actor=db.session.get(User, staff["id"]),
                action="INVENTADA",
                expected_version=ticket.version,
            )


def test_a_disabled_transition_is_rejected(app, catalog, staff):
    public_id = make_ticket(app, catalog, staff["id"])

    with app.app_context():
        db.session.scalar(
            db.select(TransicionEstado).where(
                TransicionEstado.estado_origen_id == state("NUEVO").id,
                TransicionEstado.accion == "INICIAR",
            )
        ).activa = False
        db.session.commit()

        ticket = get_ticket(public_id)

        with pytest.raises(StateTransitionError):
            change_state(
                ticket,
                actor=db.session.get(User, staff["id"]),
                action=Action.INICIAR,
                expected_version=ticket.version,
            )


def test_a_closed_ticket_cannot_change_state(app, catalog, staff):
    public_id = make_ticket(app, catalog, staff["id"])
    set_state(app, public_id, "CERRADO")

    with app.app_context():
        ticket = get_ticket(public_id)

        with pytest.raises(TicketClosedError, match="reabrir"):
            change_state(
                ticket,
                actor=db.session.get(User, staff["id"]),
                action=Action.INICIAR,
                expected_version=ticket.version,
            )


def test_a_stale_version_is_a_conflict_and_changes_nothing(
    app,
    make_user,
    catalog,
    staff,
):
    other = make_user("SUPERVISOR", username="otro")
    public_id = make_ticket(app, catalog, staff["id"])

    with app.app_context():
        stale = get_ticket(public_id).version

        # Otra persona cambia el estado primero.
        run(public_id, other["id"], Action.INICIAR)

        ticket = get_ticket(public_id)

        with pytest.raises(TicketConflictError):
            change_state(
                ticket,
                actor=db.session.get(User, staff["id"]),
                action=Action.PONER_EN_ESPERA,
                expected_version=stale,
            )

        db.session.rollback()

        ticket = get_ticket(public_id)

        assert ticket.estado.codigo == "EN_PROGRESO"
        assert ticket.version == 2
        assert len(state_events(ticket.id)) == 1


def test_the_second_person_with_a_fresh_version_gets_a_transition_error(
    app,
    make_user,
    catalog,
    staff,
):
    other = make_user("SUPERVISOR", username="otro")
    public_id = make_ticket(app, catalog, staff["id"])

    with app.app_context():
        run(public_id, staff["id"], Action.INICIAR)

        ticket = get_ticket(public_id)

        # Misma acción, versión actual: ya no es válida desde En progreso.
        with pytest.raises(StateTransitionError):
            change_state(
                ticket,
                actor=db.session.get(User, other["id"]),
                action=Action.INICIAR,
                expected_version=ticket.version,
            )


def test_two_simultaneous_changes_produce_a_single_transition(
    app,
    make_user,
    catalog,
    staff,
):
    """Dos personas inician el mismo ticket a la vez desde la misma versión.

    La fila del ticket se bloquea: la segunda espera a la primera y, al
    volver a leerla, ya no encuentra la versión que esperaba. Solo una
    transición y un evento de historial.
    """
    import threading

    other = make_user("SUPERVISOR", username="otro")
    public_id = make_ticket(app, catalog, staff["id"])
    barrier = threading.Barrier(2)
    outcomes = []

    def attempt(user_id):
        with app.app_context():
            ticket = get_ticket(public_id)
            user = db.session.get(User, user_id)
            barrier.wait(timeout=10)

            try:
                change_state(
                    ticket,
                    actor=user,
                    action=Action.INICIAR,
                    expected_version=1,
                )
                db.session.commit()
                outcomes.append("ok")
            except TicketRuleError as error:
                db.session.rollback()
                outcomes.append(type(error).__name__)
            finally:
                db.session.remove()

    threads = [
        threading.Thread(target=attempt, args=(user_id,))
        for user_id in (staff["id"], other["id"])
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join(timeout=30)

    assert sorted(outcomes) == ["TicketConflictError", "ok"]

    with app.app_context():
        ticket = get_ticket(public_id)

        assert ticket.estado.codigo == "EN_PROGRESO"
        assert ticket.version == 2
        assert len(state_events(ticket.id)) == 1


def test_an_inactive_actor_cannot_change_the_state(app, make_user, catalog, staff):
    inactive = make_user("TECNICO", username="inactivo", activo=False)
    public_id = make_ticket(app, catalog, staff["id"])

    with app.app_context():
        ticket = get_ticket(public_id)

        with pytest.raises(TicketRuleError, match="no está activo"):
            change_state(
                ticket,
                actor=db.session.get(User, inactive["id"]),
                action=Action.INICIAR,
                expected_version=ticket.version,
            )


def test_change_state_does_not_commit(app, catalog, staff):
    public_id = make_ticket(app, catalog, staff["id"])

    with app.app_context():
        ticket = get_ticket(public_id)
        change_state(
            ticket,
            actor=db.session.get(User, staff["id"]),
            action=Action.INICIAR,
            expected_version=ticket.version,
        )
        db.session.rollback()

        ticket = get_ticket(public_id)

        assert ticket.estado.codigo == "NUEVO"
        assert ticket.version == 1
        assert state_events(ticket.id) == []


# --- Pantallas -------------------------------------------------------------


def start_url(public_id, slug="start"):
    return f"/tickets/{public_id}/status/{slug}"


def current_version(app, public_id) -> int:
    with app.app_context():
        return get_ticket(public_id).version


def current_state(app, public_id) -> str:
    with app.app_context():
        return get_ticket(public_id).estado.codigo


@pytest.mark.parametrize("role_code", STAFF_ROLES)
def test_every_staff_role_can_start_a_ticket(
    client,
    app,
    make_user,
    catalog,
    role_code,
):
    user = make_user(role_code, username="persona")
    public_id = make_ticket(app, catalog, user["id"])
    login(client, user)

    response = client.post(
        start_url(public_id),
        data={"version": current_version(app, public_id)},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert f"El ticket #{public_id} pasó a «En progreso»." in text(response)
    assert current_state(app, public_id) == "EN_PROGRESO"


def test_the_confirmation_screen_shows_the_states_and_the_version(
    client,
    app,
    catalog,
    staff,
):
    public_id = make_ticket(app, catalog, staff["id"])
    login(client, staff)

    response = client.get(start_url(public_id))
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Iniciar trabajo" in text(response)
    assert "Nuevo" in html and "En progreso" in html
    assert 'name="version"' in html
    assert 'value="1"' in html
    # Iniciar no pide motivo de espera.
    assert "Motivo de espera" not in html


def test_the_hold_screen_offers_the_active_wait_reasons(
    client,
    app,
    catalog,
    staff,
):
    public_id = make_ticket(app, catalog, staff["id"])
    set_state(app, public_id, "EN_PROGRESO")

    with app.app_context():
        reason("RECURSO_PENDIENTE").activo = False
        db.session.commit()

    login(client, staff)
    content = text(client.get(start_url(public_id, "hold")))

    assert "Motivo de espera" in content
    assert "Sin motivo" in content
    assert "Información pendiente" in content
    assert "Otro motivo" in content
    assert "Recurso pendiente" not in content


def test_hold_with_a_reason_and_text_is_visible_only_to_staff(
    client,
    app,
    make_user,
    catalog,
    staff,
):
    requester = make_user("SOLICITANTE", username="ana")
    public_id = make_ticket(
        app,
        catalog,
        staff["id"],
        requester_ids=[requester["id"]],
    )
    set_state(app, public_id, "EN_PROGRESO")

    with app.app_context():
        other_id = reason("OTRO").id

    login(client, staff)
    response = client.post(
        start_url(public_id, "hold"),
        data={
            "version": current_version(app, public_id),
            "motivo_espera": other_id,
            "texto": "Falta el repuesto importado",
        },
        follow_redirects=True,
    )

    as_staff = plain_text(response)

    assert f"El ticket #{public_id} pasó a «En espera»." in as_staff
    assert "Estado cambiado" in as_staff
    assert "Estado: «En progreso» → «En espera»" in as_staff
    assert "Motivo de espera: Otro motivo" in as_staff
    assert "Motivo: Falta el repuesto importado" in as_staff

    client.post("/logout")
    login(client, requester)
    as_requester = plain_text(client.get(f"/tickets/{public_id}"))

    assert "Estado: «En progreso» → «En espera»" in as_requester
    assert "Motivo de espera" not in as_requester
    assert "Otro motivo" not in as_requester
    assert "Falta el repuesto importado" not in as_requester


def test_reactivate_returns_the_ticket_to_in_progress(
    client,
    app,
    catalog,
    staff,
):
    public_id = make_ticket(app, catalog, staff["id"])
    set_state(app, public_id, "EN_ESPERA")
    login(client, staff)

    response = client.post(
        start_url(public_id, "resume"),
        data={"version": current_version(app, public_id)},
        follow_redirects=True,
    )

    assert f"El ticket #{public_id} pasó a «En progreso»." in text(response)
    assert current_state(app, public_id) == "EN_PROGRESO"


def test_the_requester_cannot_open_or_use_the_state_screens(
    client,
    app,
    make_user,
    catalog,
):
    requester = make_user("SOLICITANTE")
    public_id = make_ticket(app, catalog, requester["id"])
    login(client, requester)

    for slug in ("start", "hold", "resume"):
        assert client.get(start_url(public_id, slug)).status_code == 403
        assert (
            client.post(
                start_url(public_id, slug),
                data={"version": 1},
            ).status_code
            == 403
        )

    assert current_state(app, public_id) == "NUEVO"
    assert current_version(app, public_id) == 1


def test_a_ticket_the_user_cannot_see_is_a_404_not_a_403(
    client,
    app,
    make_user,
    catalog,
):
    owner = make_user("SOLICITANTE", username="dueno")
    stranger = make_user("SOLICITANTE", username="ajeno")
    public_id = make_ticket(app, catalog, owner["id"])
    login(client, stranger)

    assert client.get(start_url(public_id)).status_code == 404
    assert client.post(start_url(public_id), data={"version": 1}).status_code == 404


def test_unknown_actions_and_tickets_are_404_for_staff(
    client,
    app,
    catalog,
    staff,
):
    public_id = make_ticket(app, catalog, staff["id"])
    login(client, staff)

    assert client.get(start_url(public_id, "explode")).status_code == 404
    assert client.get("/tickets/99999/status/start").status_code == 404
    assert client.get("/tickets/abc/status/start").status_code == 404


def test_an_action_not_valid_now_goes_back_to_the_detail_with_a_notice(
    client,
    app,
    catalog,
    staff,
):
    public_id = make_ticket(app, catalog, staff["id"])
    set_state(app, public_id, "EN_PROGRESO")
    login(client, staff)

    get_response = client.get(start_url(public_id), follow_redirects=True)
    post_response = client.post(
        start_url(public_id),
        data={"version": current_version(app, public_id)},
        follow_redirects=True,
    )

    message = "Esta acción no está disponible para el estado actual del ticket."

    assert message in text(get_response)
    assert message in text(post_response)
    assert current_state(app, public_id) == "EN_PROGRESO"
    assert current_version(app, public_id) == 1


def test_a_closed_ticket_redirects_with_a_notice(client, app, catalog, staff):
    public_id = make_ticket(app, catalog, staff["id"])
    set_state(app, public_id, "CERRADO")
    login(client, staff)

    response = client.get(start_url(public_id), follow_redirects=True)

    assert "Un ticket cerrado no se puede modificar." in text(response)


def test_a_stale_form_reports_the_conflict_and_changes_nothing(
    client,
    app,
    make_user,
    catalog,
    staff,
):
    other = make_user("SUPERVISOR", username="otro")
    public_id = make_ticket(app, catalog, staff["id"])
    stale = current_version(app, public_id)

    with app.app_context():
        run(public_id, other["id"], Action.INICIAR)

    login(client, staff)
    response = client.post(
        start_url(public_id, "hold"),
        data={"version": stale},
        follow_redirects=True,
    )

    # Poner en espera sigue siendo válido desde En progreso: lo que falla es
    # la versión. Se avisa y se vuelve a abrir la pantalla con los datos
    # actuales.
    content = text(response)

    assert "Otra persona modificó este ticket" in content
    assert current_state(app, public_id) == "EN_PROGRESO"
    assert current_version(app, public_id) == 2

    with app.app_context():
        assert len(state_events(get_ticket(public_id).id)) == 1


def test_a_missing_or_invalid_version_is_rejected(client, app, catalog, staff):
    public_id = make_ticket(app, catalog, staff["id"])
    login(client, staff)

    missing = client.post(start_url(public_id), data={})
    zero = client.post(start_url(public_id), data={"version": "0"})

    assert "No se pudo comprobar la versión del ticket" in text(missing)
    assert "No se pudo comprobar la versión del ticket" in text(zero)
    assert current_state(app, public_id) == "NUEVO"


def test_the_form_validates_the_wait_reason_and_the_text_length(
    client,
    app,
    catalog,
    staff,
):
    public_id = make_ticket(app, catalog, staff["id"])
    set_state(app, public_id, "EN_PROGRESO")
    login(client, staff)

    bad_reason = client.post(
        start_url(public_id, "hold"),
        data={"version": 1, "motivo_espera": "99999"},
    )
    long_text = client.post(
        start_url(public_id, "hold"),
        data={"version": 1, "texto": "x" * 501},
    )
    free_text_without_reason = client.post(
        start_url(public_id, "hold"),
        data={"version": 1, "texto": "Hola"},
    )

    assert "Selecciona un motivo de la lista." in text(bad_reason)
    assert "Máximo 500 caracteres." in text(long_text)
    assert "admita texto libre" in text(free_text_without_reason)
    assert current_state(app, public_id) == "EN_PROGRESO"


def test_the_form_without_javascript_keeps_what_was_typed(
    client,
    app,
    catalog,
    staff,
):
    public_id = make_ticket(app, catalog, staff["id"])
    set_state(app, public_id, "EN_PROGRESO")
    login(client, staff)

    response = client.post(
        start_url(public_id, "hold"),
        data={"version": 1, "texto": "Texto que no debe perderse"},
    )

    assert "Texto que no debe perderse" in response.get_data(as_text=True)


# --- Detalle del ticket ----------------------------------------------------


@pytest.mark.parametrize(
    ("code", "label", "slug"),
    [
        ("NUEVO", "Iniciar trabajo", "start"),
        ("ASIGNADO", "Iniciar trabajo", "start"),
        ("EN_PROGRESO", "Poner en espera", "hold"),
        ("EN_ESPERA", "Reactivar", "resume"),
    ],
)
def test_the_detail_offers_the_valid_state_action(
    client,
    app,
    catalog,
    staff,
    code,
    label,
    slug,
):
    public_id = make_ticket(app, catalog, staff["id"])
    set_state(app, public_id, code)
    login(client, staff)

    html = client.get(f"/tickets/{public_id}").get_data(as_text=True)

    assert label in text_of(html)
    assert f'href="/tickets/{public_id}/status/{slug}"' in html

    other_slugs = {"start", "hold", "resume"} - {slug}

    for other in other_slugs:
        assert f"/status/{other}" not in html


def text_of(html: str) -> str:
    return " ".join(html.split())


@pytest.mark.parametrize("code", ["RESUELTO", "CERRADO"])
def test_the_detail_offers_only_reopening_for_resolved_or_closed(
    client,
    app,
    catalog,
    staff,
    code,
):
    public_id = make_ticket(app, catalog, staff["id"])
    set_state(app, public_id, code)
    login(client, staff)

    html = client.get(f"/tickets/{public_id}").get_data(as_text=True)

    assert f"/tickets/{public_id}/status/reopen" in html

    for slug in ("start", "hold", "resume", "resolve", "close"):
        assert f"/status/{slug}" not in html


def test_the_requester_does_not_see_state_actions(
    client,
    app,
    make_user,
    catalog,
):
    requester = make_user("SOLICITANTE")
    public_id = make_ticket(app, catalog, requester["id"])
    login(client, requester)

    assert "/status/" not in client.get(f"/tickets/{public_id}").get_data(
        as_text=True
    )


def test_the_state_screen_belongs_to_the_tickets_menu(
    client,
    app,
    catalog,
    staff,
):
    public_id = make_ticket(app, catalog, staff["id"])
    login(client, staff)

    html = client.get(start_url(public_id)).get_data(as_text=True)

    assert 'aria-current="page"' in html
    assert "Tickets" in text_of(html)
