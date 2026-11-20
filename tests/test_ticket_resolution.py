"""Resolución, validación del solicitante, cierre y reapertura de tickets
(docs/06, RN-53 a RN-73; docs/08, secciones 15 a 24; docs/09, 16.1).

Todas las acciones pasan por `change_state` (ver `test_ticket_state_transitions.py`
para las operativas). Aquí se prueba, sobre todo, la regla del cierre: un
ticket `CERRADO` siempre tiene fecha y motivo de cierre, y una reapertura los
limpia sin perder el historial.
"""

import threading
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from src.workdesk import create_app
from src.workdesk.extensions import db
from src.workdesk.models import (
    HistoryVisibility,
    MotivoCierre,
    StateAction,
    Ticket,
    TicketEvent,
    TicketHistory,
    User,
    Validation,
)
from src.workdesk.models.ticket_history import (
    DEFAULT_EVENT_VISIBILITY,
    TICKET_EVENT_LABELS,
)
from src.workdesk.security import (
    CLOSED_STATE,
    RESOLVED_STATE,
    can_close_directly,
    can_close_exceptionally,
    can_reopen_ticket,
    can_resolve_ticket,
    can_validate_resolution,
)
from src.workdesk.tickets.assignment import assign_technician
from src.workdesk.tickets.editing import describe_history_changes
from src.workdesk.tickets.lifecycle import (
    MAX_RESOLUTION_LENGTH,
    StateTransitionError,
    available_actions,
    change_state,
)
from src.workdesk.tickets.service import (
    CLOSED_STATE_CODE,
    TicketRuleError,
    list_ticket_history,
)
from src.workdesk.tickets.versioning import (
    TicketClosedError,
    TicketConflictError,
)
from tests.ticket_helpers import (
    login,
    make_ticket,
    plain_text,
    retire,
    set_state,
    text,
)

Action = StateAction
LIFECYCLE_EVENTS = {
    TicketEvent.TICKET_RESUELTO.value,
    TicketEvent.VALIDACION_ACEPTADA.value,
    TicketEvent.VALIDACION_RECHAZADA.value,
    TicketEvent.TICKET_CERRADO.value,
    TicketEvent.TICKET_REABIERTO.value,
    TicketEvent.ESTADO_CAMBIADO.value,
}


# --- Auxiliares -------------------------------------------------------------


def get_ticket(public_id) -> Ticket:
    return db.session.scalar(
        db.select(Ticket).where(Ticket.public_id == public_id)
    )


def act(public_id, user_id, action, *, version=None, **kwargs):
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


def lifecycle_events(public_id) -> list[TicketHistory]:
    ticket = get_ticket(public_id)

    return [
        event
        for event in db.session.scalars(
            db.select(TicketHistory)
            .where(TicketHistory.ticket_id == ticket.id)
            .order_by(TicketHistory.id)
        )
        if event.tipo_evento in LIFECYCLE_EVENTS
    ]


def event_names(public_id) -> list[str]:
    return [event.tipo_evento for event in lifecycle_events(public_id)]


def validations(public_id) -> list[Validation]:
    ticket = get_ticket(public_id)

    return list(
        db.session.scalars(
            db.select(Validation)
            .where(Validation.ticket_id == ticket.id)
            .order_by(Validation.id)
        )
    )


def close_reason(code) -> MotivoCierre:
    return db.session.scalar(
        db.select(MotivoCierre).where(MotivoCierre.codigo == code)
    )


def assert_consistent_closure(ticket):
    """La regla del cierre: CERRADO ⇒ fecha y motivo de cierre; y al revés,
    un ticket que no está cerrado no los tiene."""
    if ticket.estado.codigo == CLOSED_STATE_CODE:
        assert ticket.fecha_cierre is not None
        assert ticket.motivo_cierre_id is not None
    else:
        assert ticket.fecha_cierre is None
        assert ticket.motivo_cierre_id is None
        assert ticket.cerrado_por_usuario_id is None
        assert ticket.cerrado_automaticamente is False


@pytest.fixture()
def tech(make_user, catalog):
    return make_user("TECNICO", username="tecnico")


@pytest.fixture()
def supervisor(make_user, catalog):
    return make_user("SUPERVISOR", username="supervisor")


@pytest.fixture()
def requester(make_user, catalog):
    return make_user("SOLICITANTE", username="solicitante")


@pytest.fixture()
def other_requester(make_user, catalog):
    return make_user("SOLICITANTE", username="solicitante2")


@pytest.fixture()
def ticket_id(app, catalog, tech, requester):
    """Ticket nuevo con un solicitante, creado por el Técnico."""
    return make_ticket(app, catalog, tech["id"], requester_ids=[requester["id"]])


@pytest.fixture()
def resolved(app, ticket_id, tech):
    """El mismo ticket, ya Resuelto."""
    with app.app_context():
        act(ticket_id, tech["id"], Action.RESOLVER, text="Se reinició el equipo.")

    return ticket_id


# --- Constantes y configuración ---------------------------------------------


def test_the_policy_state_codes_match_the_catalog(app, seeded_catalogs):
    from src.workdesk.models import Estado

    with app.app_context():
        codes = set(db.session.scalars(db.select(Estado.codigo)))

    assert CLOSED_STATE == CLOSED_STATE_CODE
    assert {CLOSED_STATE, RESOLVED_STATE} <= codes


def test_the_default_reopen_window_is_thirty_days(app):
    assert app.config["REOPEN_WINDOW_DAYS"] == 30


@pytest.mark.parametrize("value", [0, -3])
def test_the_app_rejects_a_non_positive_reopen_window(value):
    config = {
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "REOPEN_WINDOW_DAYS": value,
    }

    with pytest.raises(RuntimeError, match="REOPEN_WINDOW_DAYS"):
        create_app(config)


@pytest.mark.parametrize(
    "event",
    [
        TicketEvent.TICKET_RESUELTO,
        TicketEvent.VALIDACION_ACEPTADA,
        TicketEvent.VALIDACION_RECHAZADA,
        TicketEvent.TICKET_CERRADO,
        TicketEvent.TICKET_REABIERTO,
    ],
)
def test_lifecycle_events_are_public_and_have_a_name(event):
    assert DEFAULT_EVENT_VISIBILITY[event] is HistoryVisibility.PUBLICO
    assert TICKET_EVENT_LABELS[event]


# --- Políticas ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("role", "resolve_and_close", "exceptional"),
    [
        ("SOLICITANTE", False, False),
        ("TECNICO", True, False),
        ("SUPERVISOR", True, True),
        ("ADMINISTRADOR", True, True),
    ],
)
def test_resolution_and_closing_policies_by_role(
    app,
    make_user,
    role,
    resolve_and_close,
    exceptional,
):
    person = make_user(role, username="persona")

    with app.app_context():
        user = db.session.get(User, person["id"])

        assert can_resolve_ticket(user) is resolve_and_close
        assert can_close_directly(user) is resolve_and_close
        assert can_close_exceptionally(user) is exceptional


def test_inactive_users_have_no_resolution_policy(app, make_user):
    person = make_user("SUPERVISOR", username="inactivo", activo=False)

    with app.app_context():
        user = db.session.get(User, person["id"])

        assert not can_resolve_ticket(user)
        assert not can_close_directly(user)
        assert not can_close_exceptionally(user)


def test_only_a_current_requester_validates_the_resolution(
    app,
    make_user,
    catalog,
    tech,
    requester,
    other_requester,
    ticket_id,
):
    creator = make_user("SOLICITANTE", username="creador")
    own = make_ticket(app, catalog, creator["id"])
    retired_id = make_ticket(
        app, catalog, tech["id"], requester_ids=[other_requester["id"]]
    )
    retire(app, retired_id, other_requester["id"])

    with app.app_context():
        def can(person, public_id):
            return can_validate_resolution(
                db.session.get(User, person["id"]), get_ticket(public_id)
            )

        assert can(requester, ticket_id)
        # No es solicitante de ese ticket.
        assert not can(other_requester, ticket_id)
        # El creador que no figura como solicitante no responde por él.
        assert not can(creator, own)
        # Un solicitante retirado deja de responder por el ticket.
        assert not can(other_requester, retired_id)
        # Ni el personal valida por el solicitante.
        assert not can(tech, ticket_id)


def test_reopening_policy_for_staff_and_requesters(
    app,
    supervisor,
    tech,
    requester,
    other_requester,
    ticket_id,
):
    set_state(app, ticket_id, "CERRADO")

    with app.app_context():
        ticket = get_ticket(ticket_id)
        closed_at = ticket.fecha_cierre
        within = closed_at + timedelta(days=30)
        after = closed_at + timedelta(days=30, seconds=1)

        def can(person, now):
            return can_reopen_ticket(
                db.session.get(User, person["id"]),
                ticket,
                now=now,
                window_days=30,
            )

        # El personal reabre siempre, también fuera de plazo.
        assert can(tech, after)
        assert can(supervisor, after)
        # El solicitante, solo dentro del plazo (el límite exacto cuenta).
        assert can(requester, within)
        assert not can(requester, after)
        # Otra persona sin relación con el ticket no puede.
        assert not can(other_requester, within)


def test_a_requester_cannot_reopen_a_resolved_ticket(
    app,
    requester,
    resolved,
):
    # Un ticket Resuelto no se «reabre»: se rechaza la solución.
    with app.app_context():
        assert not can_reopen_ticket(
            db.session.get(User, requester["id"]),
            get_ticket(resolved),
        )


def test_the_reopen_window_comes_from_the_configuration(
    app,
    requester,
    ticket_id,
):
    set_state(app, ticket_id, "CERRADO")

    with app.app_context():
        ticket = get_ticket(ticket_id)
        user = db.session.get(User, requester["id"])
        later = ticket.fecha_cierre + timedelta(days=40)

        assert not can_reopen_ticket(user, ticket, now=later)

        app.config["REOPEN_WINDOW_DAYS"] = 60

        assert can_reopen_ticket(user, ticket, now=later)


def test_a_retired_requester_cannot_reopen(app, tech, requester, ticket_id):
    set_state(app, ticket_id, "CERRADO")
    retire(app, ticket_id, requester["id"])

    with app.app_context():
        assert not can_reopen_ticket(
            db.session.get(User, requester["id"]),
            get_ticket(ticket_id),
        )


# --- Base de datos: validaciones -----------------------------------------------


def _validation(ticket, person_id, **values):
    defaults = {
        "ticket_id": ticket.id,
        "solicitante_id": person_id,
        "ciclo_resolucion": 1,
        "tipo_validacion": "ACEPTADA",
    }
    defaults.update(values)

    return Validation(**defaults)


@pytest.mark.parametrize(
    "values",
    [
        {"tipo_validacion": "OTRA"},
        {"ciclo_resolucion": 0},
        # Un rechazo siempre explica por qué.
        {"tipo_validacion": "RECHAZADA", "motivo_rechazo": None},
        {"tipo_validacion": "RECHAZADA", "motivo_rechazo": "   "},
    ],
)
def test_the_database_rejects_invalid_validations(
    app,
    requester,
    ticket_id,
    values,
):
    with app.app_context():
        db.session.add(
            _validation(get_ticket(ticket_id), requester["id"], **values)
        )

        with pytest.raises(IntegrityError):
            db.session.commit()


def test_a_requester_validates_once_per_cycle_but_again_in_the_next(
    app,
    requester,
    ticket_id,
):
    with app.app_context():
        ticket = get_ticket(ticket_id)
        db.session.add(_validation(ticket, requester["id"]))
        db.session.commit()

        db.session.add(_validation(ticket, requester["id"], ciclo_resolucion=2))
        db.session.commit()

        db.session.add(_validation(ticket, requester["id"]))

        with pytest.raises(IntegrityError):
            db.session.commit()


# --- Resolver --------------------------------------------------------------------


@pytest.mark.parametrize("origin", ["NUEVO", "ASIGNADO", "EN_PROGRESO", "EN_ESPERA"])
def test_a_ticket_can_be_resolved_from_every_open_state(
    app,
    tech,
    ticket_id,
    origin,
):
    set_state(app, ticket_id, origin)

    with app.app_context():
        new_state = act(
            ticket_id, tech["id"], Action.RESOLVER, text="Quedó funcionando."
        )
        ticket = get_ticket(ticket_id)

        assert new_state.codigo == RESOLVED_STATE
        assert ticket.estado.codigo == RESOLVED_STATE
        assert ticket.resolucion == "Quedó funcionando."
        assert ticket.fecha_resolucion is not None
        assert_consistent_closure(ticket)


def test_resolving_records_one_public_event_with_the_cycle(
    app,
    tech,
    ticket_id,
):
    with app.app_context():
        act(ticket_id, tech["id"], Action.RESOLVER, text="Listo.")
        ticket = get_ticket(ticket_id)
        (event,) = lifecycle_events(ticket_id)

        assert ticket.version == 2
        assert event.tipo_evento == "TICKET_RESUELTO"
        assert event.visibilidad == "PUBLICO"
        assert event.actor_usuario_id == tech["id"]
        assert event.estado_anterior_id != event.estado_nuevo_id
        assert event.valor_anterior["codigo"] == "NUEVO"
        assert event.valor_nuevo["codigo"] == "RESUELTO"
        assert event.valor_nuevo["resolucion"] == "Listo."
        assert event.valor_nuevo["ciclo"] == 1
        assert event.contexto == {"accion": "RESOLVER", "ciclo": 1}


def test_the_resolution_text_is_optional(app, tech, ticket_id):
    with app.app_context():
        act(ticket_id, tech["id"], Action.RESOLVER)

        assert get_ticket(ticket_id).resolucion is None


def test_a_resolution_of_exactly_the_limit_is_accepted(app, tech, ticket_id):
    with app.app_context():
        act(ticket_id, tech["id"], Action.RESOLVER, text="x" * MAX_RESOLUTION_LENGTH)

        assert len(get_ticket(ticket_id).resolucion) == MAX_RESOLUTION_LENGTH


def test_a_resolution_over_the_limit_is_rejected(app, tech, ticket_id):
    with app.app_context():
        ticket = get_ticket(ticket_id)

        with pytest.raises(TicketRuleError, match="2000"):
            change_state(
                ticket,
                actor=db.session.get(User, tech["id"]),
                action=Action.RESOLVER,
                expected_version=ticket.version,
                text="x" * (MAX_RESOLUTION_LENGTH + 1),
            )

        db.session.rollback()

        assert get_ticket(ticket_id).estado.codigo == "NUEVO"


def test_a_resolved_ticket_cannot_be_resolved_again(app, tech, resolved):
    with app.app_context():
        ticket = get_ticket(resolved)

        with pytest.raises(StateTransitionError):
            change_state(
                ticket,
                actor=db.session.get(User, tech["id"]),
                action=Action.RESOLVER,
                expected_version=ticket.version,
            )


def test_resolving_does_not_touch_the_technicians(
    app,
    make_user,
    tech,
    ticket_id,
):
    other = make_user("TECNICO", username="otro_tecnico")

    with app.app_context():
        ticket = get_ticket(ticket_id)
        assign_technician(ticket, other["id"], actor=db.session.get(User, tech["id"]))
        db.session.commit()
        act(ticket_id, tech["id"], Action.RESOLVER)

        assert [
            a.tecnico_id for a in get_ticket(ticket_id).tecnicos_vigentes
        ] == [other["id"]]


def test_resolving_with_a_stale_version_is_a_conflict(app, tech, ticket_id):
    with app.app_context():
        ticket = get_ticket(ticket_id)

        with pytest.raises(TicketConflictError):
            change_state(
                ticket,
                actor=db.session.get(User, tech["id"]),
                action=Action.RESOLVER,
                expected_version=ticket.version + 5,
            )


# --- Cierre directo -------------------------------------------------------------


@pytest.mark.parametrize("origin", ["NUEVO", "ASIGNADO", "EN_PROGRESO", "EN_ESPERA"])
def test_a_direct_close_works_from_every_open_state(
    app,
    tech,
    ticket_id,
    origin,
):
    set_state(app, ticket_id, origin)

    with app.app_context():
        new_state = act(ticket_id, tech["id"], Action.CIERRE_DIRECTO)
        ticket = get_ticket(ticket_id)

        assert new_state.codigo == CLOSED_STATE
        assert ticket.fecha_cierre is not None
        assert ticket.motivo_cierre.codigo == "CIERRE_DIRECTO"
        assert ticket.cerrado_por_usuario_id == tech["id"]
        assert ticket.cerrado_automaticamente is False
        assert ticket.fecha_resolucion is None
        assert_consistent_closure(ticket)


def test_a_direct_close_is_recorded_as_a_distinct_event(
    app,
    tech,
    ticket_id,
):
    with app.app_context():
        act(
            ticket_id,
            tech["id"],
            Action.CIERRE_DIRECTO,
            text="Mantención programada.",
        )
        (event,) = lifecycle_events(ticket_id)

        assert event.tipo_evento == "TICKET_CERRADO"
        assert event.visibilidad == "PUBLICO"
        assert event.valor_anterior["codigo"] == "NUEVO"
        assert event.valor_nuevo["codigo"] == "CERRADO"
        assert event.valor_nuevo["motivo_cierre"]["codigo"] == "CIERRE_DIRECTO"
        assert event.contexto == {
            "accion": "CIERRE_DIRECTO",
            "motivo": "Mantención programada.",
            "motivo_cierre": "CIERRE_DIRECTO",
        }


def test_a_cancellation_is_a_direct_close_with_that_reason(
    app,
    tech,
    ticket_id,
):
    with app.app_context():
        act(
            ticket_id,
            tech["id"],
            Action.CIERRE_DIRECTO,
            close_reason_id=close_reason("CANCELACION").id,
        )

        assert get_ticket(ticket_id).motivo_cierre.codigo == "CANCELACION"


@pytest.mark.parametrize(
    "code",
    [
        # Cada uno tiene su propio camino: confirmación, flujo de duplicados,
        # cierre automático y cierre excepcional.
        "RESOLUCION_VALIDADA",
        "DUPLICADO",
        "INACTIVIDAD",
        "CIERRE_EXCEPCIONAL",
    ],
)
def test_a_direct_close_cannot_use_a_reason_of_another_path(
    app,
    tech,
    ticket_id,
    code,
):
    with app.app_context():
        ticket = get_ticket(ticket_id)

        with pytest.raises(TicketRuleError, match="no está disponible"):
            change_state(
                ticket,
                actor=db.session.get(User, tech["id"]),
                action=Action.CIERRE_DIRECTO,
                expected_version=ticket.version,
                close_reason_id=close_reason(code).id,
            )


def test_a_direct_close_rejects_inactive_or_unknown_reasons(
    app,
    tech,
    ticket_id,
):
    with app.app_context():
        close_reason("CANCELACION").activo = False
        db.session.commit()
        ticket = get_ticket(ticket_id)

        for reason_id in (close_reason("CANCELACION").id, 999999):
            with pytest.raises(TicketRuleError, match="no está disponible"):
                change_state(
                    ticket,
                    actor=db.session.get(User, tech["id"]),
                    action=Action.CIERRE_DIRECTO,
                    expected_version=ticket.version,
                    close_reason_id=reason_id,
                )


def test_a_direct_close_needs_its_default_reason_to_be_active(
    app,
    tech,
    ticket_id,
):
    with app.app_context():
        close_reason("CIERRE_DIRECTO").activo = False
        db.session.commit()
        ticket = get_ticket(ticket_id)

        with pytest.raises(TicketRuleError, match="Administrador"):
            change_state(
                ticket,
                actor=db.session.get(User, tech["id"]),
                action=Action.CIERRE_DIRECTO,
                expected_version=ticket.version,
            )


def test_a_direct_close_is_not_available_from_resolved(app, tech, resolved):
    with app.app_context():
        ticket = get_ticket(resolved)

        with pytest.raises(StateTransitionError):
            change_state(
                ticket,
                actor=db.session.get(User, tech["id"]),
                action=Action.CIERRE_DIRECTO,
                expected_version=ticket.version,
            )


@pytest.mark.parametrize(
    "action",
    [Action.INICIAR, Action.RESOLVER, Action.CONFIRMAR, Action.REABRIR],
)
def test_actions_that_do_not_close_reject_a_close_reason(
    app,
    tech,
    ticket_id,
    action,
):
    with app.app_context():
        ticket = get_ticket(ticket_id)

        with pytest.raises(TicketRuleError):
            change_state(
                ticket,
                actor=db.session.get(User, tech["id"]),
                action=action,
                expected_version=ticket.version,
                close_reason_id=close_reason("CANCELACION").id,
            )


# --- Confirmar ------------------------------------------------------------------


def test_confirming_closes_the_ticket_with_the_validated_reason(
    app,
    requester,
    resolved,
):
    with app.app_context():
        new_state = act(resolved, requester["id"], Action.CONFIRMAR)
        ticket = get_ticket(resolved)

        assert new_state.codigo == CLOSED_STATE
        assert ticket.motivo_cierre.codigo == "RESOLUCION_VALIDADA"
        assert ticket.cerrado_por_usuario_id == requester["id"]
        assert ticket.cerrado_automaticamente is False
        # La resolución sigue siendo parte del ticket cerrado.
        assert ticket.resolucion == "Se reinició el equipo."
        assert ticket.fecha_resolucion is not None
        assert_consistent_closure(ticket)


def test_confirming_records_the_validation_and_the_closing(
    app,
    requester,
    resolved,
):
    with app.app_context():
        act(resolved, requester["id"], Action.CONFIRMAR, text="Todo bien, gracias.")
        (validation,) = validations(resolved)
        events = lifecycle_events(resolved)

        assert validation.tipo_validacion == "ACEPTADA"
        assert validation.ciclo_resolucion == 1
        assert validation.solicitante_id == requester["id"]
        assert validation.comentario_adicional == "Todo bien, gracias."
        assert validation.motivo_rechazo is None
        assert validation.fecha_validacion is not None

        # Primero la respuesta del solicitante y después lo que provoca.
        assert [e.tipo_evento for e in events] == [
            "TICKET_RESUELTO",
            "VALIDACION_ACEPTADA",
            "TICKET_CERRADO",
        ]
        assert events[1].contexto["validacion_id"] == validation.id
        assert events[2].contexto["accion"] == "CONFIRMAR"
        assert events[2].contexto["motivo_cierre"] == "RESOLUCION_VALIDADA"
        assert events[2].actor_usuario_id == requester["id"]


def test_any_one_requester_is_enough_to_close(
    app,
    catalog,
    tech,
    requester,
    other_requester,
):
    public_id = make_ticket(
        app,
        catalog,
        tech["id"],
        requester_ids=[requester["id"], other_requester["id"]],
    )

    with app.app_context():
        act(public_id, tech["id"], Action.RESOLVER)
        act(public_id, other_requester["id"], Action.CONFIRMAR)

        assert get_ticket(public_id).estado.codigo == CLOSED_STATE

        # El otro solicitante ya no puede responder: el ticket está cerrado.
        ticket = get_ticket(public_id)

        with pytest.raises(TicketClosedError):
            change_state(
                ticket,
                actor=db.session.get(User, requester["id"]),
                action=Action.CONFIRMAR,
                expected_version=ticket.version,
            )


def test_only_a_current_requester_can_confirm(
    app,
    catalog,
    tech,
    requester,
    other_requester,
    resolved,
):
    with app.app_context():
        ticket = get_ticket(resolved)

        for person in (tech, other_requester):
            with pytest.raises(StateTransitionError, match="No puedes"):
                change_state(
                    ticket,
                    actor=db.session.get(User, person["id"]),
                    action=Action.CONFIRMAR,
                    expected_version=ticket.version,
                )

        db.session.rollback()

    # Un solicitante retirado tampoco.
    retire(app, resolved, requester["id"])

    with app.app_context():
        ticket = get_ticket(resolved)

        with pytest.raises(StateTransitionError, match="No puedes"):
            change_state(
                ticket,
                actor=db.session.get(User, requester["id"]),
                action=Action.CONFIRMAR,
                expected_version=ticket.version,
            )


def test_confirming_needs_a_resolved_ticket(app, requester, ticket_id):
    with app.app_context():
        ticket = get_ticket(ticket_id)

        with pytest.raises(StateTransitionError, match="no está disponible"):
            change_state(
                ticket,
                actor=db.session.get(User, requester["id"]),
                action=Action.CONFIRMAR,
                expected_version=ticket.version,
            )


def test_confirming_still_works_if_the_validated_reason_is_deactivated(
    app,
    requester,
    resolved,
):
    # El motivo es estructural: desactivarlo en el catálogo no puede impedir
    # que un solicitante cierre su ticket.
    with app.app_context():
        close_reason("RESOLUCION_VALIDADA").activo = False
        db.session.commit()
        act(resolved, requester["id"], Action.CONFIRMAR)

        assert get_ticket(resolved).estado.codigo == CLOSED_STATE


def test_two_requesters_confirming_at_once_close_the_ticket_once(
    app,
    catalog,
    tech,
    requester,
    other_requester,
):
    public_id = make_ticket(
        app,
        catalog,
        tech["id"],
        requester_ids=[requester["id"], other_requester["id"]],
    )

    with app.app_context():
        act(public_id, tech["id"], Action.RESOLVER)
        version = get_ticket(public_id).version

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
                    action=Action.CONFIRMAR,
                    expected_version=version,
                )
                db.session.commit()
                outcomes.append("ok")
            except TicketRuleError as error:
                db.session.rollback()
                outcomes.append(type(error).__name__)
            finally:
                db.session.remove()

    threads = [
        threading.Thread(target=attempt, args=(person["id"],))
        for person in (requester, other_requester)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join(timeout=30)

    assert sorted(outcomes) == ["TicketClosedError", "ok"]

    with app.app_context():
        assert len(validations(public_id)) == 1
        assert event_names(public_id).count("TICKET_CERRADO") == 1


# --- Rechazar --------------------------------------------------------------------


def test_rejecting_reopens_the_work_and_clears_the_resolution(
    app,
    requester,
    resolved,
):
    with app.app_context():
        new_state = act(
            resolved,
            requester["id"],
            Action.RECHAZAR,
            text="Sigue sin imprimir.",
        )
        ticket = get_ticket(resolved)

        assert new_state.codigo == "EN_PROGRESO"
        assert ticket.resolucion is None
        assert ticket.fecha_resolucion is None
        assert_consistent_closure(ticket)


def test_rejecting_records_the_reason_and_both_events(
    app,
    requester,
    resolved,
):
    with app.app_context():
        act(resolved, requester["id"], Action.RECHAZAR, text="Sigue sin imprimir.")
        (validation,) = validations(resolved)
        events = lifecycle_events(resolved)

        assert validation.tipo_validacion == "RECHAZADA"
        assert validation.motivo_rechazo == "Sigue sin imprimir."
        assert [e.tipo_evento for e in events] == [
            "TICKET_RESUELTO",
            "VALIDACION_RECHAZADA",
            "TICKET_REABIERTO",
        ]
        assert events[1].contexto["motivo_rechazo"] == "Sigue sin imprimir."
        assert events[2].contexto["accion"] == "RECHAZAR"
        assert events[2].contexto["desde"] == "RESUELTO"
        assert events[2].valor_nuevo["codigo"] == "EN_PROGRESO"
        # El motivo del rechazo no es del personal: no va en `motivo`.
        assert "motivo" not in events[1].contexto


def test_a_rejection_needs_an_explanation(app, requester, resolved):
    with app.app_context():
        ticket = get_ticket(resolved)

        for empty in (None, "", "   "):
            with pytest.raises(TicketRuleError, match="por qué"):
                change_state(
                    ticket,
                    actor=db.session.get(User, requester["id"]),
                    action=Action.RECHAZAR,
                    expected_version=ticket.version,
                    text=empty,
                )

        assert get_ticket(resolved).estado.codigo == RESOLVED_STATE
        assert validations(resolved) == []


def test_rejecting_keeps_the_technicians(
    app,
    make_user,
    tech,
    requester,
    ticket_id,
):
    other = make_user("TECNICO", username="otro_tecnico")

    with app.app_context():
        ticket = get_ticket(ticket_id)
        assign_technician(ticket, other["id"], actor=db.session.get(User, tech["id"]))
        db.session.commit()
        act(ticket_id, tech["id"], Action.RESOLVER)
        act(ticket_id, requester["id"], Action.RECHAZAR, text="No funciona.")

        assert [
            a.tecnico_id for a in get_ticket(ticket_id).tecnicos_vigentes
        ] == [other["id"]]


def test_each_resolution_opens_a_new_cycle(app, tech, requester, resolved):
    with app.app_context():
        act(resolved, requester["id"], Action.RECHAZAR, text="Falta algo.")
        act(resolved, tech["id"], Action.RESOLVER, text="Ahora sí.")
        act(resolved, requester["id"], Action.CONFIRMAR)

        first, second = validations(resolved)

        assert (first.ciclo_resolucion, first.tipo_validacion) == (1, "RECHAZADA")
        assert (second.ciclo_resolucion, second.tipo_validacion) == (2, "ACEPTADA")

        resolutions = [
            e for e in lifecycle_events(resolved) if e.tipo_evento == "TICKET_RESUELTO"
        ]

        assert [e.valor_nuevo["ciclo"] for e in resolutions] == [1, 2]
        # La primera explicación sobrevive en el historial.
        assert resolutions[0].valor_nuevo["resolucion"] == "Se reinició el equipo."
        assert get_ticket(resolved).resolucion == "Ahora sí."


# --- Cierre excepcional ----------------------------------------------------------


def test_a_supervisor_can_close_a_resolved_ticket_exceptionally(
    app,
    supervisor,
    resolved,
):
    with app.app_context():
        new_state = act(
            resolved,
            supervisor["id"],
            Action.CIERRE_EXCEPCIONAL,
            text="El solicitante no responde.",
        )
        ticket = get_ticket(resolved)
        event = lifecycle_events(resolved)[-1]

        assert new_state.codigo == CLOSED_STATE
        assert ticket.motivo_cierre.codigo == "CIERRE_EXCEPCIONAL"
        assert ticket.cerrado_por_usuario_id == supervisor["id"]
        assert_consistent_closure(ticket)

        assert event.tipo_evento == "TICKET_CERRADO"
        assert event.contexto == {
            "accion": "CIERRE_EXCEPCIONAL",
            "motivo": "El solicitante no responde.",
            "motivo_cierre": "CIERRE_EXCEPCIONAL",
        }
        # No hay validación del solicitante.
        assert validations(resolved) == []


def test_an_exceptional_close_needs_a_reason(app, supervisor, resolved):
    with app.app_context():
        ticket = get_ticket(resolved)

        with pytest.raises(TicketRuleError, match="excepcional"):
            change_state(
                ticket,
                actor=db.session.get(User, supervisor["id"]),
                action=Action.CIERRE_EXCEPCIONAL,
                expected_version=ticket.version,
                text=" ",
            )


def test_a_technician_cannot_close_exceptionally(app, tech, resolved):
    with app.app_context():
        ticket = get_ticket(resolved)

        with pytest.raises(StateTransitionError, match="No puedes"):
            change_state(
                ticket,
                actor=db.session.get(User, tech["id"]),
                action=Action.CIERRE_EXCEPCIONAL,
                expected_version=ticket.version,
                text="Por mi cuenta.",
            )


def test_an_exceptional_close_is_only_for_resolved_tickets(
    app,
    supervisor,
    ticket_id,
):
    with app.app_context():
        ticket = get_ticket(ticket_id)

        with pytest.raises(StateTransitionError, match="no está disponible"):
            change_state(
                ticket,
                actor=db.session.get(User, supervisor["id"]),
                action=Action.CIERRE_EXCEPCIONAL,
                expected_version=ticket.version,
                text="Sin pasar por Resuelto.",
            )


def test_a_resolved_ticket_without_requesters_is_closed_exceptionally(
    app,
    catalog,
    tech,
    supervisor,
):
    # Sin solicitante nadie puede confirmar y el cierre automático llega en
    # v0.5.0: hasta entonces lo cierra el Supervisor o el Administrador.
    public_id = make_ticket(app, catalog, tech["id"])

    with app.app_context():
        act(public_id, tech["id"], Action.RESOLVER)
        ticket = get_ticket(public_id)

        assert {
            o.info.action
            for o in available_actions(ticket, db.session.get(User, tech["id"]))
        } == {Action.REABRIR}
        assert {
            o.info.action
            for o in available_actions(
                ticket, db.session.get(User, supervisor["id"])
            )
        } == {Action.CIERRE_EXCEPCIONAL, Action.REABRIR}


# --- Reabrir ---------------------------------------------------------------------


def _close_by_confirmation(app, public_id, requester):
    with app.app_context():
        act(public_id, requester["id"], Action.CONFIRMAR)


def test_staff_reopening_a_closed_ticket_clears_the_closure(
    app,
    tech,
    requester,
    resolved,
):
    _close_by_confirmation(app, resolved, requester)

    with app.app_context():
        assert get_ticket(resolved).fecha_cierre is not None

        new_state = act(resolved, tech["id"], Action.REABRIR)
        ticket = get_ticket(resolved)

        assert new_state.codigo == "EN_PROGRESO"
        assert ticket.resolucion is None
        assert ticket.fecha_resolucion is None
        assert ticket.cerrado_por_usuario_id is None
        assert_consistent_closure(ticket)

        reopened = lifecycle_events(resolved)[-1]

        assert reopened.tipo_evento == "TICKET_REABIERTO"
        assert reopened.visibilidad == "PUBLICO"
        assert reopened.contexto == {"accion": "REABRIR", "desde": "CERRADO"}
        assert reopened.valor_anterior["codigo"] == "CERRADO"
        assert reopened.valor_nuevo["codigo"] == "EN_PROGRESO"


def test_reopening_keeps_the_history_of_the_closure(
    app,
    tech,
    requester,
    resolved,
):
    _close_by_confirmation(app, resolved, requester)

    with app.app_context():
        act(resolved, tech["id"], Action.REABRIR)

        assert event_names(resolved) == [
            "TICKET_RESUELTO",
            "VALIDACION_ACEPTADA",
            "TICKET_CERRADO",
            "TICKET_REABIERTO",
        ]
        # La validación anterior se conserva.
        assert [v.tipo_validacion for v in validations(resolved)] == ["ACEPTADA"]


def test_reopening_keeps_the_previous_technicians(
    app,
    make_user,
    tech,
    ticket_id,
):
    other = make_user("TECNICO", username="otro_tecnico")

    with app.app_context():
        ticket = get_ticket(ticket_id)
        assign_technician(ticket, other["id"], actor=db.session.get(User, tech["id"]))
        db.session.commit()
        act(ticket_id, tech["id"], Action.CIERRE_DIRECTO)
        act(ticket_id, tech["id"], Action.REABRIR)

        ticket = get_ticket(ticket_id)

        assert ticket.estado.codigo == "EN_PROGRESO"
        assert [a.tecnico_id for a in ticket.tecnicos_vigentes] == [other["id"]]


def test_staff_can_reopen_a_resolved_ticket(app, tech, resolved):
    with app.app_context():
        act(resolved, tech["id"], Action.REABRIR)
        ticket = get_ticket(resolved)

        assert ticket.estado.codigo == "EN_PROGRESO"
        assert ticket.resolucion is None
        assert ticket.fecha_resolucion is None
        assert_consistent_closure(ticket)
        # No es una validación del solicitante.
        assert validations(resolved) == []


def test_a_requester_reopens_a_closed_ticket_within_the_window(
    app,
    requester,
    resolved,
):
    _close_by_confirmation(app, resolved, requester)

    with app.app_context():
        act(resolved, requester["id"], Action.REABRIR)

        assert get_ticket(resolved).estado.codigo == "EN_PROGRESO"


def test_a_requester_cannot_reopen_after_the_window(app, requester, resolved):
    _close_by_confirmation(app, resolved, requester)

    with app.app_context():
        ticket = get_ticket(resolved)
        ticket.fecha_cierre = datetime.now(UTC) - timedelta(days=31)
        db.session.commit()
        ticket = get_ticket(resolved)

        with pytest.raises(StateTransitionError, match="No puedes"):
            change_state(
                ticket,
                actor=db.session.get(User, requester["id"]),
                action=Action.REABRIR,
                expected_version=ticket.version,
            )


def test_staff_can_reopen_after_the_window(app, tech, requester, resolved):
    _close_by_confirmation(app, resolved, requester)

    with app.app_context():
        ticket = get_ticket(resolved)
        ticket.fecha_cierre = datetime.now(UTC) - timedelta(days=400)
        db.session.commit()

        act(resolved, tech["id"], Action.REABRIR)

        assert get_ticket(resolved).estado.codigo == "EN_PROGRESO"


def test_an_open_ticket_cannot_be_reopened(app, tech, ticket_id):
    with app.app_context():
        ticket = get_ticket(ticket_id)

        with pytest.raises(StateTransitionError, match="no está disponible"):
            change_state(
                ticket,
                actor=db.session.get(User, tech["id"]),
                action=Action.REABRIR,
                expected_version=ticket.version,
            )


def test_a_closed_ticket_still_rejects_everything_but_reopening(
    app,
    tech,
    ticket_id,
):
    with app.app_context():
        act(ticket_id, tech["id"], Action.CIERRE_DIRECTO)
        ticket = get_ticket(ticket_id)

        for action in (Action.INICIAR, Action.RESOLVER, Action.CIERRE_DIRECTO):
            with pytest.raises(TicketClosedError):
                change_state(
                    ticket,
                    actor=db.session.get(User, tech["id"]),
                    action=action,
                    expected_version=ticket.version,
                )


def test_a_reopened_ticket_can_be_resolved_and_closed_again(
    app,
    tech,
    requester,
    ticket_id,
):
    with app.app_context():
        act(ticket_id, tech["id"], Action.CIERRE_DIRECTO)
        first_close = get_ticket(ticket_id).fecha_cierre

        act(ticket_id, tech["id"], Action.REABRIR)
        act(ticket_id, tech["id"], Action.RESOLVER, text="Segunda vez.")

        ticket = get_ticket(ticket_id)

        assert ticket.estado.codigo == RESOLVED_STATE
        assert ticket.fecha_cierre is None
        assert_consistent_closure(ticket)

        act(ticket_id, requester["id"], Action.CONFIRMAR)
        ticket = get_ticket(ticket_id)

        assert ticket.estado.codigo == CLOSED_STATE
        assert ticket.motivo_cierre.codigo == "RESOLUCION_VALIDADA"
        assert ticket.fecha_cierre >= first_close
        assert_consistent_closure(ticket)


def test_every_closing_path_leaves_the_ticket_consistent(
    app,
    catalog,
    tech,
    supervisor,
    requester,
):
    """La regla del cierre en los tres caminos que cierran un ticket."""
    paths = {
        "directo": lambda p: act(p, tech["id"], Action.CIERRE_DIRECTO),
        "confirmacion": lambda p: (
            act(p, tech["id"], Action.RESOLVER),
            act(p, requester["id"], Action.CONFIRMAR),
        ),
        "excepcional": lambda p: (
            act(p, tech["id"], Action.RESOLVER),
            act(p, supervisor["id"], Action.CIERRE_EXCEPCIONAL, text="Motivo."),
        ),
    }

    for name, close in paths.items():
        public_id = make_ticket(
            app,
            catalog,
            tech["id"],
            requester_ids=[requester["id"]],
            title=f"Cierre {name}",
        )

        with app.app_context():
            close(public_id)
            ticket = get_ticket(public_id)

            assert ticket.estado.codigo == CLOSED_STATE, name
            assert ticket.fecha_cierre is not None, name
            assert ticket.motivo_cierre_id is not None, name
            assert ticket.cerrado_por_usuario_id is not None, name

            act(public_id, tech["id"], Action.REABRIR)

            assert_consistent_closure(get_ticket(public_id))


def test_an_inactive_actor_cannot_resolve_or_close(app, make_user, ticket_id):
    inactive = make_user("TECNICO", username="inactivo", activo=False)

    with app.app_context():
        ticket = get_ticket(ticket_id)

        with pytest.raises(TicketRuleError, match="no está activo"):
            change_state(
                ticket,
                actor=db.session.get(User, inactive["id"]),
                action=Action.CIERRE_DIRECTO,
                expected_version=ticket.version,
            )


def test_the_service_does_not_commit(app, tech, ticket_id):
    with app.app_context():
        ticket = get_ticket(ticket_id)
        change_state(
            ticket,
            actor=db.session.get(User, tech["id"]),
            action=Action.CIERRE_DIRECTO,
            expected_version=ticket.version,
        )
        db.session.rollback()

        ticket = get_ticket(ticket_id)

        assert ticket.estado.codigo == "NUEVO"
        assert_consistent_closure(ticket)


# --- Historial: lo que ve cada rol ---------------------------------------------


def test_the_requester_receives_every_lifecycle_event(
    app,
    tech,
    requester,
    resolved,
):
    with app.app_context():
        act(resolved, requester["id"], Action.RECHAZAR, text="No sirvió.")
        act(resolved, tech["id"], Action.CIERRE_DIRECTO)

        history = list_ticket_history(
            get_ticket(resolved), db.session.get(User, requester["id"])
        )
        names = [h.tipo_evento for h in history]

        for event in (
            "TICKET_RESUELTO",
            "VALIDACION_RECHAZADA",
            "TICKET_REABIERTO",
            "TICKET_CERRADO",
        ):
            assert event in names


def test_history_lines_describe_the_lifecycle_events(
    app,
    tech,
    requester,
    resolved,
):
    with app.app_context():
        act(resolved, requester["id"], Action.CONFIRMAR)
        act(resolved, tech["id"], Action.REABRIR)

        lines = {
            e.tipo_evento: describe_history_changes(e)
            for e in lifecycle_events(resolved)
        }

        assert lines["TICKET_RESUELTO"] == [
            "Estado: «Nuevo» → «Resuelto»",
            "Resolución: «Se reinició el equipo.»",
        ]
        assert lines["TICKET_CERRADO"] == [
            "Estado: «Resuelto» → «Cerrado»",
            "Motivo de cierre: «Resolución validada»",
        ]
        assert lines["TICKET_REABIERTO"] == ["Estado: «Cerrado» → «En progreso»"]
        assert lines["VALIDACION_ACEPTADA"] == []


# --- Pantallas -------------------------------------------------------------------


def url(public_id, slug):
    return f"/tickets/{public_id}/status/{slug}"


def version_of(app, public_id) -> int:
    with app.app_context():
        return get_ticket(public_id).version


def state_of(app, public_id) -> str:
    with app.app_context():
        return get_ticket(public_id).estado.codigo


def test_the_technician_sees_resolve_and_close_buttons(
    client,
    tech,
    ticket_id,
):
    login(client, tech)
    html = client.get(f"/tickets/{ticket_id}").get_data(as_text=True)

    assert url(ticket_id, "resolve") in html
    assert url(ticket_id, "close") in html
    # Las acciones del solicitante no son botones del personal.
    assert url(ticket_id, "confirm") not in html
    assert url(ticket_id, "reject") not in html
    assert "¿Tu solicitud quedó resuelta?" not in html


def test_resolving_through_the_screen(client, app, tech, ticket_id):
    login(client, tech)

    screen = client.get(url(ticket_id, "resolve"))

    assert screen.status_code == 200
    assert "Explicación de la solución" in text(screen)

    response = client.post(
        url(ticket_id, "resolve"),
        data={"version": version_of(app, ticket_id), "texto": "Cable cambiado."},
        follow_redirects=True,
    )
    page = plain_text(response)

    assert f"El ticket #{ticket_id} quedó «Resuelto», pendiente de validación." in page
    assert state_of(app, ticket_id) == RESOLVED_STATE
    # La explicación aparece en su tarjeta y la fecha en el resumen.
    assert "Resolución" in page
    assert "Cable cambiado." in page
    assert "Resuelto" in page


def test_a_resolution_over_the_limit_is_an_error_in_the_screen(
    client,
    app,
    tech,
    ticket_id,
):
    login(client, tech)
    response = client.post(
        url(ticket_id, "resolve"),
        data={
            "version": version_of(app, ticket_id),
            "texto": "x" * (MAX_RESOLUTION_LENGTH + 1),
        },
    )

    assert response.status_code == 200
    assert f"Máximo {MAX_RESOLUTION_LENGTH} caracteres." in text(response)
    assert state_of(app, ticket_id) == "NUEVO"


def test_the_direct_close_screen_offers_only_its_two_reasons(
    client,
    tech,
    ticket_id,
):
    login(client, tech)
    page = plain_text(client.get(url(ticket_id, "close")))

    assert "Cierre directo" in page
    assert "Cancelación" in page

    for other in ("Duplicado", "Inactividad", "Resolución validada", "Cierre excepcional"):
        assert other not in page


def test_closing_directly_through_the_screen(client, app, tech, ticket_id):
    login(client, tech)

    with app.app_context():
        reason_id = close_reason("CANCELACION").id

    response = client.post(
        url(ticket_id, "close"),
        data={
            "version": version_of(app, ticket_id),
            "motivo_cierre": reason_id,
            "texto": "Ya no se necesita.",
        },
        follow_redirects=True,
    )
    page = plain_text(response)

    assert f"El ticket #{ticket_id} quedó «Cerrado»." in page
    assert state_of(app, ticket_id) == CLOSED_STATE
    # El resumen indica cuándo y por qué se cerró.
    assert "Cerrado" in page and "Cancelación" in page

    with app.app_context():
        assert get_ticket(ticket_id).motivo_cierre.codigo == "CANCELACION"


def test_the_direct_close_defaults_to_its_standard_reason(
    client,
    app,
    tech,
    ticket_id,
):
    login(client, tech)
    client.post(
        url(ticket_id, "close"),
        data={"version": version_of(app, ticket_id)},
    )

    with app.app_context():
        assert get_ticket(ticket_id).motivo_cierre.codigo == "CIERRE_DIRECTO"


def test_a_close_reason_from_another_path_is_rejected_in_the_screen(
    client,
    app,
    tech,
    ticket_id,
):
    login(client, tech)

    with app.app_context():
        duplicate = close_reason("DUPLICADO").id

    response = client.post(
        url(ticket_id, "close"),
        data={"version": version_of(app, ticket_id), "motivo_cierre": duplicate},
    )

    assert response.status_code == 200
    assert "Selecciona un motivo de la lista." in text(response)
    assert state_of(app, ticket_id) == "NUEVO"


def test_the_requester_sees_the_validation_prompt_when_resolved(
    client,
    requester,
    resolved,
):
    login(client, requester)
    response = client.get(f"/tickets/{resolved}")
    html = response.get_data(as_text=True)
    page = plain_text(response)

    assert "El equipo indicó que tu solicitud está resuelta." in page
    assert "¿Tu solicitud quedó resuelta?" in page
    assert "No, necesito más ayuda" in page
    assert "Sí, está resuelto" in page
    assert url(resolved, "confirm") in html
    assert url(resolved, "reject") in html
    # La explicación de la solución está a la vista para revisarla.
    assert "Se reinició el equipo." in page


def test_the_validation_prompt_is_only_for_a_requester_of_a_resolved_ticket(
    client,
    app,
    make_user,
    catalog,
    tech,
    requester,
    other_requester,
    ticket_id,
):
    prompt = "¿Tu solicitud quedó resuelta?"

    # Un solicitante con el ticket aún sin resolver: no hay nada que validar.
    login(client, requester)
    assert prompt not in plain_text(client.get(f"/tickets/{ticket_id}"))
    client.post("/logout")

    # El personal no valida por el solicitante.
    with app.app_context():
        act(ticket_id, tech["id"], Action.RESOLVER)

    login(client, tech)
    assert prompt not in plain_text(client.get(f"/tickets/{ticket_id}"))
    client.post("/logout")

    # Un solicitante retirado deja de ver el ticket (404), así que tampoco el aviso.
    retire(app, ticket_id, requester["id"])
    login(client, requester)
    assert client.get(f"/tickets/{ticket_id}").status_code == 404


def test_confirming_through_the_screen(client, app, requester, resolved):
    login(client, requester)

    screen = client.get(url(resolved, "confirm"))

    assert screen.status_code == 200
    assert "Al confirmar, el ticket se cierra." in text(screen)

    response = client.post(
        url(resolved, "confirm"),
        data={"version": version_of(app, resolved)},
        follow_redirects=True,
    )
    page = plain_text(response)

    assert f"Gracias. El ticket #{resolved} quedó «Cerrado»." in page
    assert state_of(app, resolved) == CLOSED_STATE
    assert "Resolución validada" in page
    # Cerrado: el aviso ya no se ofrece y sí reabrir, dentro del plazo.
    assert "¿Tu solicitud quedó resuelta?" not in page
    assert url(resolved, "reopen") in response.get_data(as_text=True)


def test_rejecting_through_the_screen_needs_an_explanation(
    client,
    app,
    requester,
    resolved,
):
    login(client, requester)

    screen = client.get(url(resolved, "reject"))

    assert "¿Qué falta por resolver?" in text(screen)

    empty = client.post(
        url(resolved, "reject"),
        data={"version": version_of(app, resolved), "texto": ""},
    )

    assert empty.status_code == 200
    assert "Cuéntanos por qué no quedó resuelto." in text(empty)
    assert state_of(app, resolved) == RESOLVED_STATE

    response = client.post(
        url(resolved, "reject"),
        data={"version": version_of(app, resolved), "texto": "Sigue fallando."},
        follow_redirects=True,
    )
    page = plain_text(response)

    assert f"Enviamos tu respuesta. El ticket #{resolved} volvió a «En progreso»." in page
    assert state_of(app, resolved) == "EN_PROGRESO"
    # El solicitante ve el motivo de su propio rechazo en el historial.
    assert "Motivo del rechazo: Sigue fallando." in page


def test_staff_see_the_rejection_reason_and_the_closing_notes(
    client,
    app,
    tech,
    requester,
    resolved,
):
    with app.app_context():
        act(resolved, requester["id"], Action.RECHAZAR, text="Sigue fallando.")
        act(
            resolved,
            tech["id"],
            Action.CIERRE_DIRECTO,
            text="Nota solo para el equipo.",
        )

    login(client, tech)
    staff_page = plain_text(client.get(f"/tickets/{resolved}"))

    assert "Motivo del rechazo: Sigue fallando." in staff_page
    assert "Motivo: Nota solo para el equipo." in staff_page
    client.post("/logout")

    # El Solicitante ve el rechazo (es suyo) pero no la nota del personal.
    login(client, requester)
    requester_page = plain_text(client.get(f"/tickets/{resolved}"))

    assert "Motivo del rechazo: Sigue fallando." in requester_page
    assert "Nota solo para el equipo." not in requester_page
    assert "Ticket cerrado" in requester_page


def test_the_requester_cannot_use_the_staff_state_screens(
    client,
    app,
    requester,
    resolved,
):
    login(client, requester)

    for slug in ("start", "hold", "resume", "resolve", "close", "close-exceptional"):
        assert client.get(url(resolved, slug)).status_code == 403
        assert (
            client.post(
                url(resolved, slug), data={"version": 2, "texto": "x"}
            ).status_code
            == 403
        )

    assert state_of(app, resolved) == RESOLVED_STATE


def test_staff_cannot_use_the_requester_screens(client, app, tech, resolved):
    login(client, tech)

    for slug in ("confirm", "reject"):
        assert client.get(url(resolved, slug)).status_code == 403
        assert (
            client.post(
                url(resolved, slug),
                data={"version": version_of(app, resolved), "texto": "x"},
            ).status_code
            == 403
        )

    assert state_of(app, resolved) == RESOLVED_STATE


def test_a_stranger_gets_a_404_on_every_new_screen(
    client,
    other_requester,
    resolved,
):
    login(client, other_requester)

    for slug in ("confirm", "reject", "resolve", "close", "reopen", "close-exceptional"):
        assert client.get(url(resolved, slug)).status_code == 404
        assert client.post(url(resolved, slug), data={"version": 2}).status_code == 404


def test_only_a_supervisor_can_open_the_exceptional_close(
    client,
    app,
    tech,
    supervisor,
    resolved,
):
    login(client, tech)
    assert client.get(url(resolved, "close-exceptional")).status_code == 403
    client.post("/logout")

    login(client, supervisor)
    screen = client.get(url(resolved, "close-exceptional"))

    assert screen.status_code == 200
    assert "Motivo del cierre excepcional" in text(screen)

    empty = client.post(
        url(resolved, "close-exceptional"),
        data={"version": version_of(app, resolved), "texto": ""},
    )

    assert "Explica por qué se cierra de forma excepcional." in text(empty)
    assert state_of(app, resolved) == RESOLVED_STATE

    response = client.post(
        url(resolved, "close-exceptional"),
        data={"version": version_of(app, resolved), "texto": "No responde."},
        follow_redirects=True,
    )

    assert "(cierre excepcional)" in plain_text(response)
    assert state_of(app, resolved) == CLOSED_STATE


def test_staff_reopen_a_closed_ticket_through_the_screen(
    client,
    app,
    tech,
    requester,
    resolved,
):
    _close_by_confirmation(app, resolved, requester)
    login(client, tech)

    detail = client.get(f"/tickets/{resolved}")

    assert url(resolved, "reopen") in detail.get_data(as_text=True)
    assert client.get(url(resolved, "reopen")).status_code == 200

    response = client.post(
        url(resolved, "reopen"),
        data={"version": version_of(app, resolved)},
        follow_redirects=True,
    )

    assert f"El ticket #{resolved} se reabrió y está «En progreso»." in plain_text(
        response
    )
    assert state_of(app, resolved) == "EN_PROGRESO"


def test_a_requester_reopens_through_the_screen_within_the_window(
    client,
    app,
    requester,
    resolved,
):
    _close_by_confirmation(app, resolved, requester)
    login(client, requester)

    response = client.post(
        url(resolved, "reopen"),
        data={"version": version_of(app, resolved)},
        follow_redirects=True,
    )

    assert state_of(app, resolved) == "EN_PROGRESO"
    # Reabierto, puede explicar la situación con un comentario público.
    assert "Publicar" in plain_text(response)


def test_a_requester_cannot_reopen_after_the_window_in_the_interface(
    client,
    app,
    requester,
    resolved,
):
    _close_by_confirmation(app, resolved, requester)

    with app.app_context():
        get_ticket(resolved).fecha_cierre = datetime.now(UTC) - timedelta(days=45)
        db.session.commit()

    login(client, requester)
    html = client.get(f"/tickets/{resolved}").get_data(as_text=True)

    assert url(resolved, "reopen") not in html
    assert client.get(url(resolved, "reopen")).status_code == 403
    assert (
        client.post(
            url(resolved, "reopen"), data={"version": version_of(app, resolved)}
        ).status_code
        == 403
    )
    assert state_of(app, resolved) == CLOSED_STATE

    # Con un plazo mayor vuelve a poder.
    app.config["REOPEN_WINDOW_DAYS"] = 60

    assert client.get(url(resolved, "reopen")).status_code == 200


def test_a_closed_ticket_still_refuses_the_other_screens(
    client,
    app,
    tech,
    ticket_id,
):
    with app.app_context():
        act(ticket_id, tech["id"], Action.CIERRE_DIRECTO)

    login(client, tech)

    for slug in ("start", "resolve", "close"):
        response = client.get(url(ticket_id, slug), follow_redirects=True)

        assert "Un ticket cerrado no se puede modificar." in plain_text(response)

    assert state_of(app, ticket_id) == CLOSED_STATE


def test_a_stale_version_in_the_screen_is_a_conflict(client, app, tech, ticket_id):
    login(client, tech)
    response = client.post(
        url(ticket_id, "close"),
        data={"version": 99},
        follow_redirects=True,
    )

    assert "Otra persona modificó este ticket" in plain_text(response)
    assert state_of(app, ticket_id) == "NUEVO"


def test_an_action_that_no_longer_applies_redirects_with_a_notice(
    client,
    app,
    requester,
    ticket_id,
):
    # El ticket aún no está Resuelto: no hay nada que confirmar.
    login(client, requester)
    response = client.get(url(ticket_id, "confirm"), follow_redirects=True)

    assert "Esta acción no está disponible para el estado actual del ticket." in plain_text(
        response
    )
    assert state_of(app, ticket_id) == "NUEVO"


def test_the_closed_summary_shows_when_and_why(client, app, tech, ticket_id):
    with app.app_context():
        act(ticket_id, tech["id"], Action.CIERRE_DIRECTO)

    login(client, tech)
    page = plain_text(client.get(f"/tickets/{ticket_id}"))

    assert "Cerrado" in page
    assert "Cierre directo" in page
