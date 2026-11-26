"""Resolución, cierre y reapertura, relaciones y duplicados, y períodos de SLA."""

from dataclasses import replace
from datetime import timedelta

import pytest
from sqlalchemy import update

from src.workdesk.extensions import db
from src.workdesk.models import (
    Estado,
    Ticket,
    TicketRelation,
    TipoRelacionTicket,
)
from src.workdesk.seeds import (
    DemoTicketsError,
    seed_demo_tickets,
)
from src.workdesk.seeds.demo_tickets import validate_demo_tickets
from src.workdesk.seeds.demo_tickets_data import (
    DEMO_TICKETS,
    DemoAdjustment,
)
from src.workdesk.sla.evaluation import SlaStatus, evaluate_ticket_sla
from src.workdesk.sla.periods import list_periods
from tests.demo_data import NOW, prepare
from tests.seed_helpers import (
    ACTION_DESTINATION,
    assert_inside_the_default_calendar,
    assignments_of,
    by_clave,
    comments_of,
    history_of,
    lifecycle_of,
    log_in,
    page_text,
    relations_of,
    requesters_of,
    set_event_time,
    user,
    validations_of,
)

# --- Resolución, cierre y reapertura -------------------------------------------


def _step(actor, **values):
    return DemoAdjustment(actor=actor, despues_horas=1, **values)


def _resolution_ticket(*steps):
    """Un ticket de una Solicitante (Javiera) con estos pasos, para validar."""
    return replace(
        DEMO_TICKETS[0],
        creado_por="javiera.torres",
        solicitantes=(),
        ajustes=steps,
    )


RESOLVE = _step("diego.soto", estado="RESOLVER")
CLOSE = _step("diego.soto", estado="CIERRE_DIRECTO")


@pytest.mark.parametrize(
    ("steps", "message"),
    [
        # Quién ejecuta cada acción.
        ((RESOLVE, _step("diego.soto", estado="CONFIRMAR")),
         "la ejecuta un Solicitante demo"),
        ((RESOLVE, _step("diego.soto", estado="RECHAZAR", texto="No sirvió.")),
         "la ejecuta un Solicitante demo"),
        ((RESOLVE, _step("diego.soto", estado="CIERRE_EXCEPCIONAL", texto="x")),
         "lo ejecuta un Supervisor demo"),
        ((RESOLVE, _step("paula.contreras", estado="CONFIRMAR")),
         "no es solicitante en ese momento"),
        # Textos obligatorios y límites.
        ((RESOLVE, _step("javiera.torres", estado="RECHAZAR")), "exige un texto"),
        ((RESOLVE, _step("camila.rojas", estado="CIERRE_EXCEPCIONAL")),
         "exige un texto"),
        ((_step("diego.soto", estado="RESOLVER", texto="x" * 2001),), "supera"),
        ((_step("diego.soto", estado="INICIAR", texto="Algo."),), "no admite texto"),
        # Motivo de cierre: solo el cierre directo, y solo los que ofrece.
        ((_step("diego.soto", estado="INICIAR", motivo_cierre="CANCELACION"),),
         "solo CIERRE_DIRECTO admite motivo_cierre"),
        ((_step("diego.soto", estado="CIERRE_DIRECTO", motivo_cierre="DUPLICADO"),),
         "no elegible"),
        ((_step("diego.soto", titulo="Otro", motivo_cierre="CANCELACION"),),
         "solo van con una acción de estado"),
        # Transiciones que no existen.
        ((_step("javiera.torres", estado="CONFIRMAR"),),
         "no es válida desde el estado NUEVO"),
        ((RESOLVE, RESOLVE), "no es válida desde el estado RESUELTO"),
        # Un ticket cerrado solo admite reabrirlo, y solo.
        ((CLOSE, _step("diego.soto", comentario="Hola.")),
         "el ticket está cerrado"),
        ((CLOSE, _step("diego.soto", estado="REABRIR", comentario="Hola.")),
         "el ticket está cerrado"),
        ((CLOSE, _step("diego.soto", estado="INICIAR")), "el ticket está cerrado"),
    ],
)
def test_validation_rejects_inconsistent_resolution_steps(steps, message):
    with pytest.raises(DemoTicketsError, match=message):
        validate_demo_tickets((_resolution_ticket(*steps),))


def test_validation_accepts_a_full_resolution_cycle():
    steps = (
        _step("diego.soto", estado="INICIAR"),
        RESOLVE,
        _step("javiera.torres", estado="RECHAZAR", texto="Sigue igual.",
              comentario="Probé de nuevo y nada."),
        _step("diego.soto", estado="RESOLVER", texto="Ahora sí."),
        _step("javiera.torres", estado="CONFIRMAR"),
        _step("diego.soto", estado="REABRIR"),
        _step("javiera.torres", comentario="Volvió a fallar."),
    )

    validate_demo_tickets((_resolution_ticket(*steps),))


def test_demo_data_covers_every_way_to_resolve_close_and_reopen():
    actions = [
        step.estado for demo in DEMO_TICKETS for step in demo.ajustes if step.estado
    ]

    for action in (
        "RESOLVER",
        "CIERRE_DIRECTO",
        "CONFIRMAR",
        "RECHAZAR",
        "CIERRE_EXCEPCIONAL",
        "REABRIR",
    ):
        assert action in actions, action

    assert any(
        step.motivo_cierre == "CANCELACION"
        for demo in DEMO_TICKETS
        for step in demo.ajustes
    )
    # Un ticket rechazado y resuelto de nuevo (dos ciclos), uno cerrado sin
    # solicitante y uno que se cerró y se reabrió.
    assert by_key_actions("escritorio-remoto-rechazado").count("RESOLVER") == 2
    assert not by_demo("aire-sala-servidores-mensual").solicitantes
    assert by_key_actions("impresora-contratos-rayas")[-1] == "REABRIR"


def by_demo(key):
    return next(demo for demo in DEMO_TICKETS if demo.clave == key)


def by_key_actions(key):
    return [step.estado for step in by_demo(key).ajustes if step.estado]


def test_a_ticket_resolved_and_waiting_for_validation(app, seeded):
    with app.app_context():
        ticket = by_clave("lector-huella-no-reconoce")
        resolved, = [e for e in lifecycle_of(ticket) if e.tipo_evento == "TICKET_RESUELTO"]

        assert ticket.estado.codigo == "RESUELTO"
        assert ticket.resolucion.startswith("Limpié el lector")
        assert ticket.fecha_resolucion == resolved.fecha_hora
        assert ticket.fecha_cierre is None
        assert ticket.motivo_cierre_id is None
        assert validations_of(ticket) == []
        assert resolved.contexto["demo_clave"] == "lector-huella-no-reconoce"
        assert resolved.contexto["ciclo"] == 1
        assert ticket.fecha_modificacion == resolved.fecha_hora


def test_a_ticket_closed_by_its_requester(app, seeded):
    with app.app_context():
        ticket = by_clave("cargador-notebook-bodega")
        events = lifecycle_of(ticket)
        (validation,) = validations_of(ticket)

        assert [e.tipo_evento for e in events if e.tipo_evento != "ESTADO_CAMBIADO"] == [
            "TICKET_RESUELTO",
            "VALIDACION_ACEPTADA",
            "TICKET_CERRADO",
        ]
        assert ticket.estado.codigo == "CERRADO"
        assert ticket.motivo_cierre.codigo == "RESOLUCION_VALIDADA"
        assert ticket.cerrado_por_usuario_id == user("ignacio.molina").id
        assert ticket.cerrado_automaticamente is False
        assert validation.tipo_validacion == "ACEPTADA"
        assert validation.comentario_adicional == "Listo, ya carga. Gracias!"

        # La fecha de cierre y la de la validación son las de sus eventos.
        closed = next(e for e in events if e.tipo_evento == "TICKET_CERRADO")
        accepted = next(e for e in events if e.tipo_evento == "VALIDACION_ACEPTADA")

        assert ticket.fecha_cierre == closed.fecha_hora
        assert validation.fecha_validacion == accepted.fecha_hora
        assert ticket.fecha_resolucion <= ticket.fecha_cierre


def test_a_rejected_ticket_is_resolved_again_in_a_second_cycle(app, seeded):
    with app.app_context():
        ticket = by_clave("escritorio-remoto-rechazado")
        (rejection,) = validations_of(ticket)
        events = lifecycle_of(ticket)
        resolutions = [e for e in events if e.tipo_evento == "TICKET_RESUELTO"]

        assert rejection.tipo_validacion == "RECHAZADA"
        assert rejection.ciclo_resolucion == 1
        assert rejection.motivo_rechazo.startswith("Sigo sin poder entrar")
        assert [e.contexto["ciclo"] for e in resolutions] == [1, 2]
        assert ticket.estado.codigo == "RESUELTO"
        assert ticket.resolucion.startswith("Restablecí la clave")
        assert ticket.fecha_resolucion == resolutions[-1].fecha_hora
        # La primera explicación sigue en el historial.
        assert resolutions[0].valor_nuevo["resolucion"].startswith("Habilité tu usuario")
        assert validations_of(ticket)[0].fecha_validacion == next(
            e.fecha_hora for e in events if e.tipo_evento == "VALIDACION_RECHAZADA"
        )


def test_a_direct_close_without_requesters_and_a_cancellation(app, seeded):
    with app.app_context():
        maintenance = by_clave("aire-sala-servidores-mensual")
        cancelled = by_clave("segundo-monitor-cancelado")

        assert maintenance.estado.codigo == "CERRADO"
        assert maintenance.motivo_cierre.codigo == "CIERRE_DIRECTO"
        assert maintenance.cerrado_por_usuario_id == user("diego.soto").id
        assert requesters_of(maintenance) == []
        assert validations_of(maintenance) == []

        assert cancelled.estado.codigo == "CERRADO"
        assert cancelled.motivo_cierre.codigo == "CANCELACION"
        (closing,) = [e for e in lifecycle_of(cancelled) if e.tipo_evento == "TICKET_CERRADO"]

        assert closing.contexto["motivo"] == "Cancelado a pedido de la solicitante."
        assert closing.contexto["accion"] == "CIERRE_DIRECTO"
        assert cancelled.fecha_cierre == closing.fecha_hora
        # El comentario del paso precede al cierre.
        assert [c.contenido[:15] for c in comments_of(cancelled)] == ["Constanza, anul"]


def test_an_exceptional_close_by_a_supervisor(app, seeded):
    with app.app_context():
        ticket = by_clave("antivirus-notebooks-bodega")

        assert ticket.estado.codigo == "CERRADO"
        assert ticket.motivo_cierre.codigo == "CIERRE_EXCEPCIONAL"
        assert ticket.cerrado_por_usuario_id == user("camila.rojas").id
        assert validations_of(ticket) == []
        assert ticket.fecha_resolucion < ticket.fecha_cierre


def test_a_reopened_ticket_has_no_closure_but_keeps_its_history(app, seeded):
    with app.app_context():
        ticket = by_clave("impresora-contratos-rayas")
        events = [e.tipo_evento for e in lifecycle_of(ticket)]

        assert ticket.estado.codigo == "EN_PROGRESO"
        assert ticket.resolucion is None
        assert ticket.fecha_resolucion is None
        assert ticket.fecha_cierre is None
        assert ticket.motivo_cierre_id is None
        assert ticket.cerrado_por_usuario_id is None
        assert events[-3:] == ["VALIDACION_ACEPTADA", "TICKET_CERRADO", "TICKET_REABIERTO"]
        # El técnico anterior se conserva y la validación también.
        assert [a.tecnico.username for a in assignments_of(ticket)] == ["felipe.araya"]
        assert [v.tipo_validacion for v in validations_of(ticket)] == ["ACEPTADA"]
        assert comments_of(ticket)[-1].autor.username == "paula.contreras"


def test_resolution_steps_leave_the_same_history_as_the_application(app, seeded):
    with app.app_context():
        for demo in DEMO_TICKETS:
            ticket = by_clave(demo.clave)
            events = [e for e in lifecycle_of(ticket) if e.tipo_evento != "ESTADO_CAMBIADO"]

            if not any(step.estado in ACTION_DESTINATION and step.estado not in (
                "INICIAR", "PONER_EN_ESPERA", "REACTIVAR"
            ) for step in demo.ajustes):
                continue

            # Cada evento lleva la marca de su ticket y de su paso y los pasos
            # van en orden.
            assert all(e.contexto["demo_clave"] == demo.clave for e in events)
            assert [e.contexto["demo_paso"] for e in events] == sorted(
                e.contexto["demo_paso"] for e in events
            )
            # Un cierre nunca deja un ticket cerrado sin fecha ni motivo.
            if ticket.estado.codigo == "CERRADO":
                assert ticket.fecha_cierre is not None
                assert ticket.motivo_cierre_id is not None


def test_closure_dates_are_in_order_and_never_in_the_future(app, seeded):
    with app.app_context():
        for demo in DEMO_TICKETS:
            ticket = by_clave(demo.clave)

            for moment in (ticket.fecha_resolucion, ticket.fecha_cierre):
                if moment is not None:
                    assert ticket.fecha_creacion <= moment <= NOW
                    assert_inside_the_default_calendar(moment)

            if ticket.fecha_resolucion and ticket.fecha_cierre:
                assert ticket.fecha_resolucion <= ticket.fecha_cierre

            for validation in validations_of(ticket):
                assert ticket.fecha_creacion <= validation.fecha_validacion <= NOW


def test_the_requester_is_asked_to_validate_a_resolved_ticket(app, seeded):
    client = log_in(app, "paula.contreras")

    with app.app_context():
        public_id = by_clave("lector-huella-no-reconoce").public_id

    plain = page_text(client, public_id)

    assert "¿Tu solicitud quedó resuelta?" in plain
    assert "Limpié el lector" in plain
    assert f"/tickets/{public_id}/status/confirm" in client.get(
        f"/tickets/{public_id}"
    ).get_data(as_text=True)


def test_staff_and_other_requesters_do_not_get_the_validation_prompt(app, seeded):
    with app.app_context():
        public_id = by_clave("lector-huella-no-reconoce").public_id

    assert "¿Tu solicitud quedó resuelta?" not in page_text(
        log_in(app, "felipe.araya"), public_id
    )
    # Otra persona sin relación con el ticket ni siquiera lo ve.
    assert log_in(app, "ignacio.molina").get(f"/tickets/{public_id}").status_code == 404


def test_what_each_role_sees_of_a_closed_and_rejected_ticket(app, seeded):
    with app.app_context():
        rejected = by_clave("escritorio-remoto-rechazado").public_id
        cancelled = by_clave("segundo-monitor-cancelado").public_id

    requester = page_text(log_in(app, "sebastian.vargas"), rejected)
    staff = page_text(log_in(app, "valentina.pizarro"), rejected)

    # El motivo del rechazo es del solicitante: lo ven los dos. La nota interna
    # del equipo, solo el personal.
    assert "Motivo del rechazo: Sigo sin poder entrar" in requester
    assert "Motivo del rechazo: Sigo sin poder entrar" in staff
    assert "La clave del servidor expiró" not in requester
    assert "La clave del servidor expiró" in staff

    # La nota con la que se cerró la cancelación es del personal.
    closed_requester = page_text(log_in(app, "constanza.herrera"), cancelled)
    closed_staff = page_text(log_in(app, "felipe.araya"), cancelled)

    assert "Cancelación" in closed_requester
    assert "Motivo: Cancelado a pedido de la solicitante." not in closed_requester
    assert "Motivo: Cancelado a pedido de la solicitante." in closed_staff


def test_a_hand_made_closure_follows_the_refresh(app, seeded):
    """Un cierre hecho a mano sobre un ticket demo sigue su evento al refrescar
    y nunca queda antes de la resolución ni en el futuro."""
    from src.workdesk.models import StateAction
    from src.workdesk.tickets.lifecycle import change_state

    with app.app_context():
        ticket = by_clave("lector-huella-no-reconoce")
        change_state(
            ticket,
            actor=user("camila.rojas"),
            action=StateAction.CIERRE_EXCEPCIONAL,
            expected_version=ticket.version,
            text="Sin respuesta de la solicitante.",
        )
        db.session.commit()

        closing = history_of(ticket)[-1]
        set_event_time(closing, NOW - timedelta(hours=1))
        db.session.execute(
            update(Ticket.__table__)
            .where(Ticket.__table__.c.id == ticket.id)
            .values(fecha_cierre=NOW - timedelta(hours=1))
        )
        db.session.commit()

        later = NOW + timedelta(days=5)
        seed_demo_tickets(now=later)
        db.session.refresh(ticket)
        closing = history_of(ticket)[-1]

        assert closing.tipo_evento == "TICKET_CERRADO"
        assert ticket.fecha_cierre == closing.fecha_hora
        assert ticket.fecha_resolucion <= ticket.fecha_cierre <= later


def test_a_hand_made_reopening_keeps_the_ticket_without_closure_dates(app, seeded):
    from src.workdesk.models import StateAction
    from src.workdesk.tickets.lifecycle import change_state

    with app.app_context():
        ticket = by_clave("cargador-notebook-bodega")
        change_state(
            ticket,
            actor=user("diego.soto"),
            action=StateAction.REABRIR,
            expected_version=ticket.version,
        )
        db.session.commit()

        seed_demo_tickets(now=NOW + timedelta(days=5))
        db.session.refresh(ticket)

        assert ticket.estado.codigo == "EN_PROGRESO"
        assert ticket.fecha_cierre is None
        assert ticket.fecha_resolucion is None
        assert ticket.motivo_cierre_id is None


# --- Relaciones y duplicados ---------------------------------------------------


def _older(**values):
    """Un ticket de una Solicitante, antiguo, para usar como principal."""
    return replace(
        DEMO_TICKETS[0],
        clave="principal-viejo",
        titulo="Ticket principal antiguo",
        creado_por="javiera.torres",
        solicitantes=(),
        hace_dias=20,
        hora="10:00",
        ajustes=(),
        **values,
    )


def _newer(*steps, **values):
    return replace(
        DEMO_TICKETS[0],
        clave="ticket-nuevo",
        titulo="Ticket nuevo",
        creado_por="javiera.torres",
        solicitantes=(),
        hace_dias=2,
        hora="10:00",
        ajustes=steps,
        **values,
    )


def _relation_step(actor="diego.soto", **values):
    return DemoAdjustment(actor=actor, despues_horas=1, **values)


@pytest.mark.parametrize(
    ("steps", "message"),
    [
        ((_relation_step(relacionar="inexistente"),),
         "debe ser la clave de un ticket que aparezca antes"),
        ((_relation_step(duplicado_de="ticket-nuevo"),),
         "debe ser la clave de un ticket que aparezca antes"),
        ((_relation_step(relacionar="principal-viejo"),
          _relation_step(relacionar="principal-viejo")),
         "ya se relacionó con"),
        ((_relation_step(duplicado_de="principal-viejo", estado="INICIAR"),),
         "no puede ir con `estado`"),
        # Tras marcarlo como duplicado el ticket está cerrado.
        ((_relation_step(duplicado_de="principal-viejo"),
          _relation_step(comentario="Hola.")),
         "el ticket está cerrado"),
        ((_relation_step(duplicado_de="principal-viejo"),
          _relation_step(relacionar="principal-viejo")),
         "el ticket está cerrado"),
        # Un Resuelto no se cierra de forma directa.
        ((_relation_step(estado="RESOLVER"),
          _relation_step(duplicado_de="principal-viejo")),
         "no se puede marcar como duplicado desde el estado RESUELTO"),
        # Solo el personal relaciona.
        ((_relation_step(actor="javiera.torres", relacionar="principal-viejo"),),
         "no es personal"),
    ],
)
def test_validation_rejects_inconsistent_relation_steps(steps, message):
    with pytest.raises(DemoTicketsError, match=message):
        validate_demo_tickets((_older(), _newer(*steps)))


def test_validation_rejects_a_principal_that_is_newer_than_the_ticket():
    newer_principal = replace(_older(), hace_dias=1)

    with pytest.raises(DemoTicketsError, match="es más reciente"):
        validate_demo_tickets(
            (newer_principal, _newer(_relation_step(relacionar="principal-viejo")))
        )


def test_validation_rejects_chains_of_duplicates():
    first = replace(_newer(_relation_step(duplicado_de="principal-viejo")),
                    clave="duplicado-uno", titulo="Duplicado uno", hace_dias=10)
    second = replace(_newer(_relation_step(duplicado_de="duplicado-uno")),
                     clave="duplicado-dos", titulo="Duplicado dos")

    with pytest.raises(DemoTicketsError, match="ya es un duplicado de otro"):
        validate_demo_tickets((_older(), first, second))


def test_validation_accepts_relations_and_duplicates():
    related = replace(
        _newer(_relation_step(relacionar="principal-viejo")),
        clave="relacionado", titulo="Relacionado",
    )
    duplicated = replace(
        _newer(_relation_step(duplicado_de="principal-viejo")),
        clave="duplicado", titulo="Duplicado",
    )

    validate_demo_tickets((_older(), related, duplicated))


def test_demo_data_covers_duplicates_and_relations():
    steps = [
        (demo.clave, step)
        for demo in DEMO_TICKETS
        for step in demo.ajustes
    ]
    duplicates = [k for k, step in steps if step.duplicado_de]
    related = [k for k, step in steps if step.relacionar]
    principals = [step.duplicado_de for _, step in steps if step.duplicado_de]

    assert len(duplicates) >= 2
    assert related
    # Un principal con más de un duplicado.
    assert len(principals) != len(set(principals))


def test_a_ticket_marked_as_duplicate_is_closed_and_linked(app, seeded):
    with app.app_context():
        ticket = by_clave("wifi-bodega-otra-vez")
        principal = by_clave("wifi-bodega")
        (relation,) = relations_of(ticket)

        assert ticket.estado.codigo == "CERRADO"
        assert ticket.motivo_cierre.codigo == "DUPLICADO"
        assert ticket.cerrado_por_usuario_id == user("felipe.araya").id
        assert ticket.fecha_cierre is not None
        assert relation.tipo.codigo == "DUPLICADO"
        assert (relation.ticket_origen_id, relation.ticket_destino_id) == (
            ticket.id,
            principal.id,
        )
        # El comentario público precede al cierre.
        assert comments_of(ticket)[0].contenido.startswith("Ignacio, esto ya lo")


def test_a_duplicate_leaves_the_history_of_the_application(app, seeded):
    with app.app_context():
        ticket = by_clave("internet-bodega-sigue-mal")
        events = [e for e in history_of(ticket) if e.tipo_evento != "COMENTARIO_AGREGADO"]
        names = [e.tipo_evento for e in events]

        assert names == ["TICKET_CREADO", "RELACION_AGREGADA", "TICKET_CERRADO"]
        added, closing = events[1], events[2]

        assert added.visibilidad == "INTERNO"
        assert closing.visibilidad == "PUBLICO"
        assert closing.contexto["duplicado_de"] == by_clave("wifi-bodega").public_id
        assert closing.contexto["demo_clave"] == "internet-bodega-sigue-mal"
        assert closing.contexto["demo_paso"] == 1
        # Los dos eventos de la relación llevan la marca del seed.
        assert added.contexto["demo_clave"] == "internet-bodega-sigue-mal"


def test_the_principal_is_untouched_and_lists_its_duplicates(app, seeded):
    from src.workdesk.tickets.relations import KIND_PRINCIPAL_OF, list_relations

    with app.app_context():
        principal = by_clave("wifi-bodega")
        kinds = {v.other.public_id: v.kind for v in list_relations(principal)}

        assert kinds == {
            by_clave("wifi-bodega-otra-vez").public_id: KIND_PRINCIPAL_OF,
            by_clave("internet-bodega-sigue-mal").public_id: KIND_PRINCIPAL_OF,
        }
        # Sigue como antes (En espera) y sin eventos de relación propios.
        assert principal.estado.codigo == "EN_ESPERA"
        assert not any(
            e.tipo_evento.startswith("RELACION") for e in history_of(principal)
        )


def test_related_tickets_stay_open_and_are_linked(app, seeded):
    with app.app_context():
        printer = by_clave("impresora-notebook-nuevo")
        wifi = by_clave("wifi-reuniones-sigue-cayendo")
        (printer_relation,) = relations_of(printer)
        (wifi_relation,) = relations_of(wifi)
        other_printer = by_clave("impresora-proyectos-a-nombre-de")

        assert printer.estado.codigo == "EN_PROGRESO"
        assert wifi.estado.codigo == "NUEVO"
        assert printer_relation.tipo.codigo == "RELACIONADO"
        # El par se guarda con el id menor primero.
        low, high = sorted((printer.id, other_printer.id))

        assert (printer_relation.ticket_origen_id, printer_relation.ticket_destino_id) == (
            low,
            high,
        )
        assert wifi_relation.activo
        # La relación se ve también desde el otro ticket.
        assert relations_of(other_printer) == [printer_relation]


def test_relation_dates_follow_their_events(app, seeded):
    with app.app_context():
        for key in (
            "wifi-bodega-otra-vez",
            "internet-bodega-sigue-mal",
            "impresora-notebook-nuevo",
            "wifi-reuniones-sigue-cayendo",
        ):
            ticket = by_clave(key)
            (relation,) = relations_of(ticket)
            added = next(
                e for e in history_of(ticket) if e.tipo_evento == "RELACION_AGREGADA"
            )

            assert relation.fecha_creacion == added.fecha_hora
            assert ticket.fecha_creacion <= relation.fecha_creacion <= NOW

        # El cierre de un duplicado lleva la fecha del evento de cierre, no la
        # de la relación (aunque comparten `relacion_id`).
        ticket = by_clave("wifi-bodega-otra-vez")
        closing = next(e for e in history_of(ticket) if e.tipo_evento == "TICKET_CERRADO")

        assert ticket.fecha_cierre == closing.fecha_hora


def test_staff_sees_the_relations_and_the_requester_does_not(app, seeded):
    with app.app_context():
        duplicate_id = by_clave("wifi-bodega-otra-vez").public_id
        principal_title = by_clave("wifi-bodega").titulo

    staff = page_text(log_in(app, "felipe.araya"), duplicate_id)

    assert "Relaciones (1)" in staff
    assert "Duplicado de" in staff and principal_title in staff

    requester = page_text(log_in(app, "ignacio.molina"), duplicate_id)

    assert "Relaciones" not in requester
    assert principal_title not in requester
    # Sí ve que el ticket se cerró como duplicado.
    assert "Duplicado" in requester


def test_refreshing_keeps_the_relations_and_their_dates_in_order(app, seeded):
    with app.app_context():
        before = {k: relations_of(by_clave(k))[0].id for k in (
            "wifi-bodega-otra-vez", "impresora-notebook-nuevo",
        )}
        seed_demo_tickets(now=NOW + timedelta(days=4))

        for key, relation_id in before.items():
            (relation,) = relations_of(by_clave(key))
            added = next(
                e for e in history_of(by_clave(key)) if e.tipo_evento == "RELACION_AGREGADA"
            )

            assert relation.id == relation_id
            assert relation.fecha_creacion == added.fecha_hora


def test_a_hand_made_relation_removal_follows_the_refresh(app, seeded):
    from src.workdesk.tickets.relations import remove_relation

    with app.app_context():
        ticket = by_clave("wifi-reuniones-sigue-cayendo")
        (relation,) = relations_of(ticket)

        remove_relation(ticket, relation.id, actor=user("diego.soto"))
        db.session.commit()

        removal = history_of(ticket)[-1]
        set_event_time(removal, NOW - timedelta(minutes=30))
        db.session.execute(
            update(TicketRelation.__table__)
            .where(TicketRelation.__table__.c.id == relation.id)
            .values(fecha_desactivacion=NOW - timedelta(minutes=30))
        )
        db.session.commit()

        later = NOW + timedelta(days=5)
        seed_demo_tickets(now=later)
        db.session.refresh(relation)
        removal = history_of(ticket)[-1]

        assert removal.tipo_evento == "RELACION_ELIMINADA"
        assert relation.activo is False
        assert relation.fecha_desactivacion == removal.fecha_hora
        assert relation.fecha_creacion <= relation.fecha_desactivacion <= later


def test_the_command_asks_for_the_relation_types_first(app):
    prepare(app)

    with app.app_context():
        db.session.execute(db.delete(TipoRelacionTicket))
        db.session.commit()

        with pytest.raises(DemoTicketsError, match="tipos de relación"):
            seed_demo_tickets(now=NOW)

        assert db.session.scalar(db.select(db.func.count(Ticket.id))) == 0


def test_the_command_asks_to_enable_the_transitions_it_needs(app):
    """Si el Administrador deshabilitó transiciones que la demostración
    recorre, se detiene antes de cargar nada y dice cuáles son."""
    from src.workdesk.models import TransicionEstado

    prepare(app)

    with app.app_context():
        resolve = db.session.scalar(
            db.select(TransicionEstado).where(
                TransicionEstado.accion == "RESOLVER",
                TransicionEstado.estado_origen.has(codigo="NUEVO"),
            )
        )
        resolve.activa = False
        db.session.commit()

        with pytest.raises(DemoTicketsError) as error:
            seed_demo_tickets(now=NOW)

        message = str(error.value)

        assert "transiciones deshabilitadas" in message
        assert "de Nuevo a Resuelto (Resolver)" in message
        assert "Estados y transiciones" in message
        assert db.session.scalar(db.select(db.func.count(Ticket.id))) == 0

        # Con la transición habilitada de nuevo, carga con normalidad.
        resolve.activa = True
        db.session.commit()
        seed_demo_tickets(now=NOW)

        assert db.session.scalar(db.select(db.func.count(Ticket.id))) == len(DEMO_TICKETS)


def test_renaming_the_states_does_not_affect_the_demo(app):
    """La demostración trabaja con los códigos de los estados, no con sus
    nombres: un Administrador que los renombró puede cargarla igual."""
    prepare(app)

    with app.app_context():
        from src.workdesk.models import Estado

        for index, state in enumerate(db.session.scalars(db.select(Estado)), start=1):
            state.nombre_visible = f"Estado {index}"

        db.session.commit()
        result = seed_demo_tickets(now=NOW)

        assert result.created == len(DEMO_TICKETS)


# --- Períodos de SLA -------------------------------------------------------------


def sla_picture() -> dict[str, list[tuple]]:
    """Los períodos de cada ticket demo, sin ids, por clave."""
    picture = {}

    for demo in DEMO_TICKETS:
        ticket = by_clave(demo.clave)
        picture[demo.clave] = [
            (
                p.prioridad_id,
                p.fecha_inicio,
                p.fecha_fin,
                p.segundos_consumidos,
                p.fecha_vencimiento_respuesta,
                p.fecha_vencimiento_resolucion,
                p.usuario_cambio_id,
            )
            for p in list_periods(ticket.id)
        ]

    return picture


def test_every_demo_ticket_has_sla_periods_that_follow_its_state(app, seeded):
    with app.app_context():
        for demo in DEMO_TICKETS:
            ticket = by_clave(demo.clave)
            found = list_periods(ticket.id)
            state = db.session.get(Estado, ticket.estado_id).codigo
            open_ones = [p for p in found if p.fecha_fin is None]

            assert found, demo.clave
            assert len(open_ones) <= 1, demo.clave

            if state in ("RESUELTO", "CERRADO"):
                # Resuelto o cerrado: el reloj está detenido.
                assert open_ones == [], demo.clave
            elif state == "EN_ESPERA":
                assert [p.esta_pausado for p in open_ones] == [True], demo.clave
            else:
                assert [p.esta_pausado for p in open_ones] == [False], demo.clave


def test_the_demo_tickets_show_every_kind_of_sla_state(app, seeded):
    with app.app_context():
        statuses = {
            evaluate_ticket_sla(by_clave(demo.clave).id, NOW).status
            for demo in DEMO_TICKETS
        }

        assert {SlaStatus.DENTRO, SlaStatus.VENCIDO, SlaStatus.PAUSADO} <= statuses


def test_the_first_period_of_a_demo_ticket_starts_when_it_was_created(app, seeded):
    with app.app_context():
        for demo in DEMO_TICKETS:
            ticket = by_clave(demo.clave)

            assert list_periods(ticket.id)[0].fecha_inicio == ticket.fecha_creacion


def test_running_the_seed_again_leaves_the_same_sla_periods(app, seeded):
    with app.app_context():
        before = sla_picture()

        seed_demo_tickets(now=NOW)

        assert sla_picture() == before


def test_the_demo_periods_move_with_the_tickets_to_a_new_day(app, seeded):
    with app.app_context():
        before = sla_picture()["wifi-bodega"]

        seed_demo_tickets(now=NOW + timedelta(days=7))
        after = sla_picture()["wifi-bodega"]

        # Los períodos siguen a las fechas del ticket: una semana después, todo se
        # corre una semana y el consumo es el mismo.
        assert [row[3] for row in after] == [row[3] for row in before]
        assert after[0][1] == before[0][1] + timedelta(days=7)
