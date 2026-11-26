"""Los ajustes del personal: datos, prioridad, cambios de estado, grupo y asignación."""

from dataclasses import replace
from datetime import timedelta

import pytest
from sqlalchemy import update

from src.workdesk.extensions import db
from src.workdesk.models import (
    Ticket,
    TicketEvent,
    TicketHistory,
    TicketTechnician,
    User,
)
from src.workdesk.models.ticket_history import TicketHistoryImmutableError
from src.workdesk.seeds import (
    DemoTicketsError,
    seed_demo_tickets,
)
from src.workdesk.seeds.demo_tickets import validate_demo_tickets
from src.workdesk.seeds.demo_tickets_data import (
    DEMO_TICKETS,
    DemoAdjustment,
)
from tests.demo_data import NOW
from tests.seed_helpers import (
    assignments_of,
    by_clave,
    content_snapshot,
    count,
    date_snapshot,
    demo_tickets,
    events_of,
    history_of,
    log_in,
    page_text,
    user,
)

# --- Ajustes del personal -----------------------------------------------


def test_adjustments_leave_the_same_history_as_the_application(app, seeded):
    with app.app_context():
        ticket = by_clave("sistema-caido-bodega")
        events = history_of(ticket)

        assert [e.tipo_evento for e in events] == [
            "TICKET_CREADO",
            "CATEGORIA_CAMBIADA",
            "PRIORIDAD_CAMBIADA",
            "TICKET_MODIFICADO",
        ]
        assert ticket.categoria.nombre == "Redes"
        assert ticket.prioridad.codigo == "ALTA"
        assert ticket.titulo == "Bodega sin red: cable de un switch desconectado"
        # Una versión por cada escritura: categoría, prioridad y título.
        assert ticket.version == 4

        priority_event = events[2]
        assert priority_event.contexto["motivo"].startswith("No es una caída")
        assert db.session.get(User, priority_event.actor_usuario_id).username == "valentina.pizarro"


def test_a_supervisor_can_escalate_a_priority_with_a_reason(app, seeded):
    with app.app_context():
        ticket = by_clave("correo-sospechoso")
        change = history_of(ticket)[-1]

        assert ticket.prioridad.codigo == "CRITICA"
        assert change.tipo_evento == "PRIORIDAD_CAMBIADA"
        assert db.session.get(User, change.actor_usuario_id).username == "camila.rojas"


def test_the_history_is_still_immutable_after_loading_the_demo(app, seeded):
    with app.app_context():
        entry = history_of(by_clave("mouse-malo"))[0]
        entry.detalle = "Intento de modificar el historial."

        with pytest.raises(TicketHistoryImmutableError):
            db.session.flush()

        db.session.rollback()


# --- Cambios de estado ----------------------------------------------------


def state_events_of(ticket):
    return [
        event
        for event in history_of(ticket)
        if event.tipo_evento == TicketEvent.ESTADO_CAMBIADO.value
    ]






def test_state_steps_leave_the_same_history_as_the_application(app, seeded):
    with app.app_context():
        ticket = by_clave("teclado-ventas")
        events = state_events_of(ticket)

        assert [
            (e.valor_anterior["codigo"], e.valor_nuevo["codigo"]) for e in events
        ] == [
            ("NUEVO", "EN_PROGRESO"),
            ("EN_PROGRESO", "EN_ESPERA"),
            ("EN_ESPERA", "EN_PROGRESO"),
        ]
        assert [e.actor.username for e in events] == ["felipe.araya"] * 3
        assert [e.contexto["demo_paso"] for e in events] == [1, 2, 3]
        assert all(e.contexto["demo_clave"] == "teclado-ventas" for e in events)
        assert ticket.estado.codigo == "EN_PROGRESO"
        # Creado en la versión 1 y una más por cada cambio de estado.
        assert ticket.version == 4


def test_a_wait_step_keeps_its_catalog_reason_and_free_text(app, seeded):
    with app.app_context():
        (_, hold) = state_events_of(by_clave("wifi-bodega"))

        assert hold.motivo_espera.codigo == "OTRO"
        assert hold.contexto["motivo"].startswith("Hay que esperar la visita")
        assert hold.contexto["accion"] == "PONER_EN_ESPERA"
        assert hold.contexto["demo_clave"] == "wifi-bodega"

        third_party = state_events_of(by_clave("monitor-parpadea"))[1]

        assert third_party.motivo_espera.codigo == "ESPERA_TERCERO"
        assert "motivo" not in third_party.contexto


def test_state_events_are_in_order_and_never_in_the_future(app, seeded):
    with app.app_context():
        for demo in DEMO_TICKETS:
            if not any(step.estado for step in demo.ajustes):
                continue

            times = [event.fecha_hora for event in history_of(by_clave(demo.clave))]

            assert times == sorted(times)
            assert max(times) <= NOW


def test_the_requester_sees_the_state_change_but_not_the_wait_reason(
    app,
    seeded,
):
    client = log_in(app, "ignacio.molina")

    with app.app_context():
        public_id = by_clave("wifi-bodega").public_id

    plain = page_text(client, public_id)

    assert "Estado: «En progreso» → «En espera»" in plain
    assert "Motivo de espera" not in plain
    assert "proveedor de internet" not in plain


def test_staff_sees_the_wait_reason_and_text(app, seeded):
    client = log_in(app, "diego.soto")

    with app.app_context():
        public_id = by_clave("wifi-bodega").public_id

    plain = page_text(client, public_id)

    assert "Motivo de espera: Otro motivo" in plain
    assert "proveedor de internet" in plain


def test_states_need_the_transitions_loaded_first(app, prepared):
    with app.app_context():
        db.session.execute(db.text("DELETE FROM transiciones_estados"))
        db.session.commit()

        with pytest.raises(DemoTicketsError, match="seed-catalogs"):
            seed_demo_tickets(now=NOW)

        assert count(Ticket) == 0


def test_a_missing_wait_reason_only_warns_and_the_wait_has_no_reason(
    app,
    prepared,
):
    with app.app_context():
        db.session.execute(
            db.text("UPDATE motivos_espera SET activo = false WHERE codigo = 'OTRO'")
        )
        db.session.commit()

        result = seed_demo_tickets(now=NOW, tickets=demo_tickets("wifi-bodega"))

        assert any("Motivo de espera «OTRO»" in w for w in result.warnings)

        ticket = by_clave("wifi-bodega")
        hold = state_events_of(ticket)[1]

        assert ticket.estado.codigo == "EN_ESPERA"
        assert hold.motivo_espera_id is None
        assert "motivo" not in hold.contexto


def test_refreshing_does_not_touch_the_state_or_the_version(app, seeded):
    with app.app_context():
        before = content_snapshot()

        seed_demo_tickets(now=NOW + timedelta(days=3))

        assert content_snapshot() == before


# --- Grupo y asignación ----------------------------------------------------


def test_validation_simulates_the_assignment_before_the_state_action():
    # Asignar a un técnico pasa el ticket a Asignado, desde donde se puede
    # iniciar; sin la asignación, iniciar también es válido desde Nuevo, pero
    # poner en espera no.
    steps = (
        DemoAdjustment(actor="camila.rojas", despues_horas=1, asignar="diego.soto"),
        DemoAdjustment(actor="diego.soto", despues_horas=1, estado="INICIAR"),
    )

    validate_demo_tickets((replace(DEMO_TICKETS[0], ajustes=steps),))

    invalid = (
        DemoAdjustment(
            actor="camila.rojas",
            despues_horas=1,
            asignar="diego.soto",
            estado="PONER_EN_ESPERA",
        ),
    )

    with pytest.raises(DemoTicketsError, match="no es válida desde el estado ASIGNADO"):
        validate_demo_tickets((replace(DEMO_TICKETS[0], ajustes=invalid),))


def test_demo_data_covers_groups_and_assignments():
    steps = [step for demo in DEMO_TICKETS for step in demo.ajustes]
    group_only = [
        demo
        for demo in DEMO_TICKETS
        if any(s.grupo for s in demo.ajustes)
        and not any(s.asignar for s in demo.ajustes)
    ]
    two_technicians = [
        demo
        for demo in DEMO_TICKETS
        if sum(1 for s in demo.ajustes if s.asignar) >= 2
    ]

    assert {s.grupo for s in steps if s.grupo} >= {
        "Soporte Redes",
        "Soporte Usuarios",
        "Aplicaciones",
    }
    assert any(s.asignar and s.actor == s.asignar for s in steps), "falta una autoasignación"
    assert any(s.asignar and s.actor != s.asignar for s in steps), "falta una asignación por un Supervisor"
    assert group_only, "falta un ticket con grupo y sin técnico"
    assert two_technicians, "falta un ticket con dos técnicos"


def test_groups_and_assignments_leave_the_same_history_as_the_application(
    app,
    seeded,
):
    with app.app_context():
        ticket = by_clave("disco-lleno-servidor")
        (assignment,) = assignments_of(ticket)
        events = history_of(ticket)
        kinds = [e.tipo_evento for e in events]

        assert ticket.grupo.nombre == "Soporte Redes"
        assert assignment.tecnico.username == "valentina.pizarro"
        assert assignment.asignado_por_usuario_id == user("camila.rojas").id
        assert assignment.fecha_desasignacion is None
        assert ticket.estado.codigo == "ASIGNADO"
        # Creación, grupo, técnico y el cambio de estado que provoca asignar.
        assert kinds == [
            "TICKET_CREADO",
            "GRUPO_CAMBIADO",
            "TECNICO_ASIGNADO",
            "ESTADO_CAMBIADO",
        ]
        assert all(e.contexto["demo_clave"] == "disco-lleno-servidor" for e in events)
        assert {e.contexto["demo_paso"] for e in events[1:]} == {1}
        # El grupo sube la versión y el estado derivado también.
        assert ticket.version == 3


def test_a_group_without_technician_leaves_the_ticket_new(app, seeded):
    with app.app_context():
        ticket = by_clave("cobertura-wifi-reuniones")

        assert ticket.grupo.nombre == "Soporte Redes"
        assert assignments_of(ticket) == []
        assert ticket.estado.codigo == "NUEVO"


def test_two_technicians_and_a_self_assignment(app, seeded):
    with app.app_context():
        ticket = by_clave("mouse-inalambrico")
        assignments = assignments_of(ticket)

        assert [a.tecnico.username for a in assignments] == [
            "felipe.araya",
            "diego.soto",
        ]
        assert [a.asignado_por_usuario_id for a in assignments] == [
            user("matias.fuentes").id,
            user("diego.soto").id,
        ]
        # Solo el primero movió el estado.
        assert ticket.estado.codigo == "ASIGNADO"
        assert (
            len(
                [
                    e
                    for e in history_of(ticket)
                    if e.tipo_evento == "ESTADO_CAMBIADO"
                ]
            )
            == 1
        )


def test_an_assignment_carries_the_date_of_its_event(app, seeded):
    with app.app_context():
        for demo in DEMO_TICKETS:
            ticket = by_clave(demo.clave)

            for assignment in assignments_of(ticket):
                event = next(
                    e
                    for e in history_of(ticket)
                    if e.tipo_evento == "TECNICO_ASIGNADO"
                    and e.contexto.get("asignacion_id") == assignment.id
                )

                assert assignment.fecha_asignacion == event.fecha_hora


def test_the_requester_sees_who_attends_but_not_the_group(app, seeded):
    client = log_in(app, "sebastian.vargas")

    with app.app_context():
        public_id = by_clave("teams-no-conecta").public_id

    plain = page_text(client, public_id)

    assert "Atendido por" in plain
    assert "Diego Soto" in plain
    assert "Técnico asignado: «Diego Soto»" in plain

    other = log_in(app, "javiera.torres")

    with app.app_context():
        grouped = by_clave("sistema-contable-lento").public_id

    plain = page_text(other, grouped)

    assert "Atendido por" in plain
    assert "Aplicaciones" not in plain
    assert "Grupo" not in plain


def test_staff_sees_the_group_and_the_technicians(app, seeded):
    client = log_in(app, "camila.rojas")

    with app.app_context():
        public_id = by_clave("sistema-contable-lento").public_id

    plain = page_text(client, public_id)

    assert "Grupo Aplicaciones" in plain
    assert "Técnico Francisca Muñoz" in plain
    assert "Grupo: — → «Aplicaciones»" in plain


def test_a_missing_group_only_warns_and_the_ticket_has_no_group(app, prepared):
    with app.app_context():
        db.session.execute(
            db.text("UPDATE grupos SET activo = false WHERE nombre = 'Soporte Redes'")
        )
        db.session.commit()

        result = seed_demo_tickets(now=NOW, tickets=demo_tickets("disco-lleno-servidor"))

        assert any("Grupo «Soporte Redes»" in w for w in result.warnings)

        ticket = by_clave("disco-lleno-servidor")

        assert ticket.grupo_id is None
        # La asignación del mismo paso sí se hizo.
        assert ticket.estado.codigo == "ASIGNADO"


def test_assignment_dates_follow_a_refresh(app, seeded):
    # Que un refresco da lo mismo que una carga nueva ese día lo comprueba el
    # test general de fechas (el snapshot incluye las asignaciones); aquí se
    # comprueba además que cada asignación sigue siendo la de su evento.
    with app.app_context():
        first = date_snapshot()

        seed_demo_tickets(now=NOW + timedelta(days=3))

        assert date_snapshot() != first

        for demo in DEMO_TICKETS:
            ticket = by_clave(demo.clave)

            for assignment in assignments_of(ticket):
                event = next(
                    e
                    for e in history_of(ticket)
                    if e.tipo_evento == "TECNICO_ASIGNADO"
                    and e.contexto.get("asignacion_id") == assignment.id
                )

                assert assignment.fecha_asignacion == event.fecha_hora


def test_a_hand_made_unassignment_follows_the_refresh_in_order(app, seeded):
    from src.workdesk.tickets.assignment import unassign_technician

    with app.app_context():
        ticket = by_clave("mouse-inalambrico")
        first = assignments_of(ticket)[0]

        unassign_technician(ticket, first.id, actor=user("matias.fuentes"))
        db.session.commit()

        seed_demo_tickets(now=NOW + timedelta(days=3))
        db.session.refresh(first)

        assert first.fecha_desasignacion is not None
        assert first.fecha_desasignacion >= first.fecha_asignacion


def test_an_assignment_closed_by_a_hand_made_escalation_follows_the_refresh(
    app,
    seeded,
):
    # El escalamiento cierra la asignación del seed y crea otra en la misma
    # transacción que su evento, que no lleva `asignacion_id`. Al refrescar, la
    # asignación del seed se mueve a la nueva fecha: su cierre debe moverse con
    # el evento y nunca quedar antes (restricción de la base de datos).
    from src.workdesk.tickets.assignment import escalate_ticket

    with app.app_context():
        ticket = by_clave("disco-lleno-servidor")
        first = assignments_of(ticket)[0]
        escalate_ticket(
            ticket,
            actor=user("camila.rojas"),
            expected_version=ticket.version,
            group_id=None,
            technician_id=user("diego.soto").id,
            reason="A mano",
        )
        db.session.commit()

        # Se simula que ocurrió una hora después de la asignación del seed (el
        # servicio sella la hora real).
        moment = first.fecha_asignacion + timedelta(hours=1)
        escalation = events_of(ticket, TicketEvent.TICKET_ESCALADO)[0]
        second = next(a for a in assignments_of(ticket) if a.id != first.id)

        db.session.execute(
            update(TicketHistory.__table__)
            .where(TicketHistory.__table__.c.id == escalation.id)
            .values(fecha_hora=moment)
        )
        db.session.execute(
            update(TicketTechnician.__table__)
            .where(TicketTechnician.__table__.c.id == first.id)
            .values(fecha_desasignacion=moment)
        )
        db.session.execute(
            update(TicketTechnician.__table__)
            .where(TicketTechnician.__table__.c.id == second.id)
            .values(fecha_asignacion=moment)
        )
        db.session.commit()

        seed_demo_tickets(now=NOW + timedelta(days=3))

        db.session.refresh(first)
        db.session.refresh(second)
        db.session.refresh(escalation)

        assert first.fecha_desasignacion >= first.fecha_asignacion
        assert first.fecha_desasignacion == escalation.fecha_hora
        assert second.fecha_asignacion == escalation.fecha_hora
        assert second.fecha_desasignacion is None


def test_refresh_keeps_the_group_and_the_assignments(app, seeded):
    with app.app_context():
        before = content_snapshot()

        seed_demo_tickets(now=NOW + timedelta(days=3))

        assert content_snapshot() == before
