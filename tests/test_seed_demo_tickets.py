import hashlib
import re
from dataclasses import replace
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import update

from src.workdesk.extensions import db
from src.workdesk.models import (
    Attachment,
    Categoria,
    Comment,
    Estado,
    Notificacion,
    PeriodoSla,
    Prioridad,
    Ticket,
    TicketEvent,
    TicketHistory,
    TicketRelation,
    TicketRequester,
    TicketTechnician,
    TipoRelacionTicket,
    User,
    Validation,
)
from src.workdesk.models.ticket_history import TicketHistoryImmutableError
from src.workdesk.seeds import (
    DemoTicketsError,
    seed_catalogs,
    seed_demo_tickets,
    seed_roles,
)
from src.workdesk.seeds.demo_tickets import validate_demo_tickets
from src.workdesk.seeds.demo_tickets_data import (
    DEMO_CATEGORIES,
    DEMO_LOCATIONS,
    DEMO_TICKETS,
    MARCOLETA,
    MATTA,
    DemoAdjustment,
)
from src.workdesk.sla.periods import SlaStatus, evaluate_ticket_sla, list_periods
from src.workdesk.sla.work_calendar import (
    Holiday,
    resolve_work_calendar,
    save_work_calendar,
)
from src.workdesk.tickets.attachments import attachment_path
from src.workdesk.tickets.editing import update_ticket
from src.workdesk.tickets.service import create_ticket
from src.workdesk.worktime import Franja, WorkCalendar, parse_time
from tests.database import empty_tables
from tests.demo_data import DEMO_PASSWORD, NOW, ROLES, SOLICITANTES, ZONE, prepare


def run_command(app):
    return app.test_cli_runner().invoke(args=["seed-demo-tickets"])


def by_clave(key):
    """El ticket demo con esa clave, aunque después le hayan cambiado el título."""
    return db.session.scalar(
        db.select(Ticket)
        .join(TicketHistory, TicketHistory.ticket_id == Ticket.id)
        .where(
            TicketHistory.tipo_evento == TicketEvent.TICKET_CREADO.value,
            TicketHistory.contexto["demo_clave"].as_string() == key,
        )
    )


def user(username):
    return db.session.scalar(db.select(User).where(User.username == username))


def history_of(ticket):
    return list(
        db.session.scalars(
            db.select(TicketHistory)
            .where(TicketHistory.ticket_id == ticket.id)
            .order_by(TicketHistory.id)
        )
    )


def validations_of(ticket):
    return list(
        db.session.scalars(
            db.select(Validation)
            .where(Validation.ticket_id == ticket.id)
            .order_by(Validation.id)
        )
    )


def lifecycle_of(ticket):
    return [e for e in history_of(ticket) if e.tipo_evento in LIFECYCLE_EVENTS]


def relations_of(ticket):
    return list(
        db.session.scalars(
            db.select(TicketRelation)
            .where(
                db.or_(
                    TicketRelation.ticket_origen_id == ticket.id,
                    TicketRelation.ticket_destino_id == ticket.id,
                )
            )
            .order_by(TicketRelation.id)
        )
    )


def requesters_of(ticket):
    return list(
        db.session.scalars(
            db.select(TicketRequester)
            .where(TicketRequester.ticket_id == ticket.id)
            .order_by(TicketRequester.id)
        )
    )


# Estado al que lleva cada acción de estado implementada (independiente de la
# tabla de transiciones, para no comprobar el seed con sus propios datos).
ACTION_DESTINATION = {
    "INICIAR": "EN_PROGRESO",
    "PONER_EN_ESPERA": "EN_ESPERA",
    "REACTIVAR": "EN_PROGRESO",
    "RESOLVER": "RESUELTO",
    "CIERRE_DIRECTO": "CERRADO",
    "CONFIRMAR": "CERRADO",
    "RECHAZAR": "EN_PROGRESO",
    "CIERRE_EXCEPCIONAL": "CERRADO",
    "REABRIR": "EN_PROGRESO",
}

# Eventos que dejan la resolución, el cierre y la reapertura (y los cambios de
# estado operativos).
LIFECYCLE_EVENTS = (
    "ESTADO_CAMBIADO",
    "TICKET_RESUELTO",
    "VALIDACION_ACEPTADA",
    "VALIDACION_RECHAZADA",
    "TICKET_CERRADO",
    "TICKET_REABIERTO",
)


def final_state(demo) -> str:
    """Estado en que debe quedar un ticket demo: el del último cambio de
    estado de sus ajustes, o Nuevo si no tiene ninguno."""
    state = "NUEVO"

    for adjustment in demo.ajustes:
        # Asignar un técnico a un ticket Nuevo lo pasa a Asignado.
        if adjustment.asignar is not None and state == "NUEVO":
            state = "ASIGNADO"

        if adjustment.estado is not None:
            state = ACTION_DESTINATION[adjustment.estado]

        # Marcar un duplicado cierra el ticket.
        if adjustment.duplicado_de is not None:
            state = "CERRADO"

    return state


def initial_requesters(demo) -> list[str]:
    """Solicitantes con los que nace un ticket demo: quien crea siendo
    Solicitante es su propio solicitante; el personal indica a quiénes."""
    if ROLES[demo.creado_por] == "SOLICITANTE":
        return [demo.creado_por]

    return list(demo.solicitantes)


def final_requesters(demo) -> list[str]:
    """Solicitantes vigentes de un ticket demo tras todos sus ajustes."""
    current = initial_requesters(demo)

    for step in demo.ajustes:
        if step.retirar_solicitante is not None:
            current.remove(step.retirar_solicitante)

        if step.agregar_solicitante is not None:
            current.append(step.agregar_solicitante)

    return current


def comments_of(ticket):
    return list(
        db.session.scalars(
            db.select(Comment)
            .where(Comment.ticket_id == ticket.id)
            .order_by(Comment.id)
        )
    )


def attachments_of(ticket):
    return list(
        db.session.scalars(
            db.select(Attachment)
            .where(Attachment.ticket_id == ticket.id)
            .order_by(Attachment.id)
        )
    )


def assignments_of(ticket):
    return list(
        db.session.scalars(
            db.select(TicketTechnician)
            .where(TicketTechnician.ticket_id == ticket.id)
            .order_by(TicketTechnician.id)
        )
    )


def count(model):
    return db.session.scalar(db.select(db.func.count()).select_from(model))


def local(value):
    return value.astimezone(ZONE)


def workdays_between(start, end):
    """Días laborales (lunes a viernes) en el intervalo (start, end]."""
    return sum(
        1
        for n in range(1, (end - start).days + 1)
        if (start + timedelta(days=n)).weekday() < 5
    )


def assert_inside_the_default_calendar(moment):
    """Lunes a viernes, dentro de la jornada 09:00-18:00."""
    when = local(moment)

    assert when.weekday() < 5, when
    assert time(9, 0) <= when.time() < time(18, 0), when


def all_event_times():
    return [
        event.fecha_hora
        for demo in DEMO_TICKETS
        for event in history_of(by_clave(demo.clave))
    ]


def date_snapshot():
    """Todas las fechas de todos los tickets demo, por clave."""
    snapshot = {}

    for demo in DEMO_TICKETS:
        ticket = by_clave(demo.clave)

        snapshot[demo.clave] = (
            ticket.fecha_creacion,
            ticket.fecha_modificacion,
            [event.fecha_hora for event in history_of(ticket)],
            [
                (link.fecha_asociacion, link.fecha_retiro)
                for link in requesters_of(ticket)
            ],
            [
                (a.fecha_asignacion, a.fecha_desasignacion)
                for a in assignments_of(ticket)
            ],
            [
                (c.fecha_creacion, c.fecha_modificacion, c.fecha_eliminacion)
                for c in comments_of(ticket)
            ],
            [
                (f.fecha_subida, f.fecha_eliminacion)
                for f in attachments_of(ticket)
            ],
            ticket.fecha_resolucion,
            ticket.fecha_cierre,
            [v.fecha_validacion for v in validations_of(ticket)],
            [(r.fecha_creacion, r.fecha_desactivacion) for r in relations_of(ticket)],
        )

    return snapshot


def content_snapshot():
    """Todo lo que NO son fechas: no debe cambiar al refrescar."""
    snapshot = {}

    for demo in DEMO_TICKETS:
        ticket = by_clave(demo.clave)

        snapshot[demo.clave] = (
            ticket.id,
            ticket.public_id,
            ticket.titulo,
            ticket.descripcion,
            ticket.categoria_id,
            ticket.prioridad_id,
            ticket.ubicacion_id,
            ticket.grupo_id,
            ticket.estado_id,
            ticket.version,
            [
                (event.id, event.tipo_evento, event.actor_usuario_id, event.detalle)
                for event in history_of(ticket)
            ],
            [
                (link.solicitante_id, link.fecha_retiro is None, link.retirado_por_usuario_id)
                for link in requesters_of(ticket)
            ],
            [a.tecnico_id for a in assignments_of(ticket)],
            [
                (c.autor_usuario_id, c.tipo, c.contenido, c.activo, c.editado)
                for c in comments_of(ticket)
            ],
            [
                (f.nombre_original, f.hash, f.comentario_id, f.activo)
                for f in attachments_of(ticket)
            ],
            ticket.resolucion,
            ticket.motivo_cierre_id,
            ticket.cerrado_por_usuario_id,
            ticket.cerrado_automaticamente,
            [
                (
                    v.solicitante_id,
                    v.ciclo_resolucion,
                    v.tipo_validacion,
                    v.motivo_rechazo,
                    v.comentario_adicional,
                )
                for v in validations_of(ticket)
            ],
            [
                (
                    r.tipo.codigo,
                    r.ticket_origen_id,
                    r.ticket_destino_id,
                    r.activo,
                    r.comentario,
                    r.usuario_creacion_id,
                )
                for r in relations_of(ticket)
            ],
        )

    return snapshot


def set_event_time(event, moment):
    """Simula una edición hecha a mano en `moment` (el servicio sella la hora real)."""
    db.session.execute(
        update(TicketHistory.__table__)
        .where(TicketHistory.__table__.c.id == event.id)
        .values(fecha_hora=moment)
    )
    db.session.execute(
        update(Ticket.__table__)
        .where(Ticket.__table__.c.id == event.ticket_id)
        .values(fecha_modificacion=moment)
    )
    db.session.commit()


def edit_by_hand(ticket, title, moment):
    update_ticket(
        ticket,
        actor=user("diego.soto"),
        expected_version=ticket.version,
        title=title,
        description=ticket.descripcion,
        category_id=ticket.categoria_id,
        location_id=ticket.ubicacion_id,
    )
    db.session.commit()

    event = history_of(ticket)[-1]
    set_event_time(event, moment)

    return event


# --- Datos --------------------------------------------------------------


def test_demo_data_is_valid():
    validate_demo_tickets()


def test_demo_data_has_about_forty_tickets_with_distinct_keys_and_titles():
    keys = [ticket.clave for ticket in DEMO_TICKETS]
    titles = [ticket.titulo.casefold() for ticket in DEMO_TICKETS]

    assert len(DEMO_TICKETS) >= 40
    assert len(set(keys)) == len(keys)
    assert len(set(titles)) == len(titles)


def test_demo_data_covers_the_variety_a_demonstration_needs():
    creators = {ticket.creado_por for ticket in DEMO_TICKETS}
    staff_created = [t for t in DEMO_TICKETS if ROLES[t.creado_por] != "SOLICITANTE"]

    # Todas las categorías, prioridades y ubicaciones (también "sin ubicación").
    assert {t.categoria for t in DEMO_TICKETS} == set(DEMO_CATEGORIES)
    assert {t.prioridad for t in DEMO_TICKETS} == {"BAJA", "MEDIA", "ALTA", "CRITICA"}
    assert {t.ubicacion for t in DEMO_TICKETS} == {None, *DEMO_LOCATIONS}

    # Todas las personas solicitantes y buena parte del personal.
    assert set(SOLICITANTES) <= creators
    assert len(creators - set(SOLICITANTES)) >= 4

    # El personal crea a nombre de 0, 1 y 2 solicitantes.
    assert {len(t.solicitantes) for t in staff_created} == {0, 1, 2}

    # Hay historias con ajustes posteriores y antigüedades repartidas.
    assert sum(1 for t in DEMO_TICKETS if t.ajustes) >= 5
    assert min(t.hace_dias for t in DEMO_TICKETS) == 0
    assert max(t.hace_dias for t in DEMO_TICKETS) >= 30

    # Descripciones de largos distintos, algunas de varias líneas.
    lengths = [len(t.descripcion) for t in DEMO_TICKETS]
    assert max(lengths) >= 400 and min(lengths) <= 150
    assert any("\n" in t.descripcion for t in DEMO_TICKETS)

    # Al menos un texto con caracteres que HTML interpretaría.
    assert any("<" in t.descripcion for t in DEMO_TICKETS)


def test_most_tickets_are_created_by_requesters():
    requesters = sum(1 for t in DEMO_TICKETS if ROLES[t.creado_por] == "SOLICITANTE")

    assert requesters / len(DEMO_TICKETS) >= 0.6


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"titulo": DEMO_TICKETS[0].titulo}, "título está repetido"),
        ({"clave": DEMO_TICKETS[0].clave}, "clave está repetida"),
        ({"clave": "Con Mayúsculas"}, "nombre corto"),
        ({"clave": "x" * 61}, "máximo 60"),
        ({"creado_por": "nadie.demo"}, "no es un usuario demo"),
        ({"categoria": "Software"}, "categoría desconocida"),
        ({"prioridad": "URGENTE"}, "prioridad desconocida"),
        ({"ubicacion": "Casa matriz"}, "ubicación desconocida"),
        ({"hora": "25:61"}, "HH:MM"),
        ({"hora": "08:30"}, "fuera de la jornada"),
        ({"hora": "18:00"}, "fuera de la jornada"),
        ({"hace_dias": -1}, "negativo"),
        ({"descripcion": "x" * 2001}, "supera"),
        ({"titulo": " con espacios "}, "espacios"),
        ({"solicitantes": ("diego.soto",)}, "no es un Solicitante"),
    ],
)
def test_validation_rejects_inconsistent_data(change, message):
    # Se modifica el SEGUNDO ticket para que lo repetido apunte al primero.
    broken = replace(DEMO_TICKETS[1], **change)

    with pytest.raises(DemoTicketsError, match=message):
        validate_demo_tickets((DEMO_TICKETS[0], broken))


@pytest.mark.parametrize(
    ("calendar", "message"),
    [
        (WorkCalendar(dias=()), "al menos un día laboral"),
        (WorkCalendar(dias=(0, 7)), "de 0 \\(lunes\\) a 6"),
        (WorkCalendar(dias=(1, 1)), "días repetidos"),
        (WorkCalendar(inicio="9:00"), "formato HH:MM"),
        (WorkCalendar(inicio="18:00", fin="09:00"), "anterior al fin"),
        (WorkCalendar(feriados=("2026-11-17",)), "deben ser fechas"),
    ],
)
def test_validation_rejects_an_inconsistent_calendar(calendar, message):
    with pytest.raises(DemoTicketsError, match=message):
        validate_demo_tickets((DEMO_TICKETS[0],), calendar)


def test_validation_rejects_requesters_on_a_ticket_created_by_a_requester():
    ticket = replace(DEMO_TICKETS[0], solicitantes=("paula.contreras",))

    with pytest.raises(DemoTicketsError, match="no lleva `solicitantes`"):
        validate_demo_tickets((ticket,))


@pytest.mark.parametrize(
    ("adjustment", "message"),
    [
        (DemoAdjustment(actor="paula.contreras", despues_horas=1, titulo="Otro"),
         "no es personal"),
        (DemoAdjustment(actor="diego.soto", despues_horas=0, titulo="Otro"),
         "al menos 1"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1), "no cambia nada"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1, prioridad="ALTA"),
         "exige un motivo"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1, categoria="Software"),
         "categoría desconocida"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1, estado="INVENTADA"),
         "no existe o todavía no está implementada"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1, estado="AUTO_CIERRE"),
         "no existe o todavía no está implementada"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1, estado="REACTIVAR"),
         "no es válida desde el estado NUEVO"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1, estado="PONER_EN_ESPERA"),
         "no es válida desde el estado NUEVO"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1, titulo="Otro",
                        motivo_espera="OTRO"),
         "solo van con una acción de estado"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1, estado="INICIAR",
                        motivo_espera="OTRO"),
         "solo PONER_EN_ESPERA admite"),
        (DemoAdjustment(actor="camila.rojas", despues_horas=1, grupo="Inventado"),
         "grupo desconocido"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1, grupo="Soporte Redes"),
         "lo fija un Supervisor"),
        (DemoAdjustment(actor="camila.rojas", despues_horas=1,
                        asignar="javiera.torres"),
         "no es un Técnico demo"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1,
                        asignar="valentina.pizarro"),
         "solo un Supervisor asigna a otra persona"),
    ],
)
def test_validation_rejects_inconsistent_adjustments(adjustment, message):
    ticket = replace(DEMO_TICKETS[0], ajustes=(adjustment,))

    with pytest.raises(DemoTicketsError, match=message):
        validate_demo_tickets((ticket,))


def _hold_steps(**hold):
    return (
        DemoAdjustment(actor="diego.soto", despues_horas=1, estado="INICIAR"),
        DemoAdjustment(
            actor="diego.soto",
            despues_horas=1,
            estado="PONER_EN_ESPERA",
            **hold,
        ),
    )


@pytest.mark.parametrize(
    ("hold", "message"),
    [
        ({"motivo_espera": "NO_EXISTE"}, "motivo de espera desconocido"),
        ({"motivo_espera": "ESPERA_TERCERO", "texto": "Hola"}, "admita texto libre"),
        ({"texto": "Hola"}, "admita texto libre"),
        ({"motivo_espera": "OTRO", "texto": "x" * 501}, "supera los 500"),
    ],
)
def test_validation_rejects_inconsistent_wait_data(hold, message):
    ticket = replace(DEMO_TICKETS[0], ajustes=_hold_steps(**hold))

    with pytest.raises(DemoTicketsError, match=message):
        validate_demo_tickets((ticket,))


def test_validation_accepts_a_full_operational_cycle():
    steps = _hold_steps(motivo_espera="OTRO", texto="Esperando al proveedor") + (
        DemoAdjustment(actor="diego.soto", despues_horas=1, estado="REACTIVAR"),
    )

    validate_demo_tickets((replace(DEMO_TICKETS[0], ajustes=steps),))


def test_demo_data_includes_every_state_and_every_wait_reason():
    finals = {final_state(demo) for demo in DEMO_TICKETS}
    reasons = {
        step.motivo_espera
        for demo in DEMO_TICKETS
        for step in demo.ajustes
        if step.motivo_espera
    }
    cycles = [
        demo
        for demo in DEMO_TICKETS
        if [s.estado for s in demo.ajustes if s.estado]
        == ["INICIAR", "PONER_EN_ESPERA", "REACTIVAR"]
    ]

    assert finals == {
        "NUEVO",
        "ASIGNADO",
        "EN_PROGRESO",
        "EN_ESPERA",
        "RESUELTO",
        "CERRADO",
    }
    assert reasons == {
        "INFORMACION_PENDIENTE",
        "ESPERA_TERCERO",
        "APROBACION_PENDIENTE",
        "RECURSO_PENDIENTE",
        "OTRO",
    }
    assert cycles, "falta un ticket que complete iniciar, esperar y reactivar"
    assert any(
        step.texto for demo in DEMO_TICKETS for step in demo.ajustes
    ), "falta una espera con texto libre"


# --- Comando ------------------------------------------------------------


def test_command_creates_all_the_tickets(app, prepared):
    result = run_command(app)

    assert result.exit_code == 0, result.output
    assert (
        f"Tickets demo creados: {len(DEMO_TICKETS)}. Actualizados (ya existían): 0."
        in result.output
    )
    assert "Aviso" not in result.output

    with app.app_context():
        assert count(Ticket) == len(DEMO_TICKETS)


def test_command_refuses_to_run_in_production(app, prepared):
    app.config["APP_ENV"] = "production"

    result = run_command(app)

    assert result.exit_code != 0
    assert "no se cargan en producción" in result.output

    with app.app_context():
        assert count(Ticket) == 0


def test_command_asks_for_the_demo_users_first(app):
    with app.app_context():
        seed_roles()
        seed_catalogs()

    result = run_command(app)

    assert result.exit_code != 0
    assert "Ejecuta primero seed-demo." in result.output

    with app.app_context():
        assert count(Ticket) == 0


def test_command_asks_for_the_catalogs_first(app):
    result = run_command(app)

    assert result.exit_code != 0
    assert "seed-catalogs" in result.output

    with app.app_context():
        assert count(Ticket) == 0


# --- Qué crea -----------------------------------------------------------


def test_tickets_follow_the_creation_rules(app, seeded):
    with app.app_context():
        for demo in DEMO_TICKETS:
            ticket = by_clave(demo.clave)
            creator = db.session.get(User, ticket.creado_por_usuario_id)
            current = sorted(
                link.solicitante.username
                for link in requesters_of(ticket)
                if link.fecha_retiro is None
            )
            # Los de la creación: quien crea siendo Solicitante es su propio
            # solicitante; los del personal son los que indica `solicitantes`.
            # Las filas agregadas después son las que tienen su evento.
            added_later = {
                event.contexto["participacion_id"]
                for event in history_of(ticket)
                if event.tipo_evento == TicketEvent.SOLICITANTE_AGREGADO.value
            }
            at_creation = sorted(
                link.solicitante.username
                for link in requesters_of(ticket)
                if link.id not in added_later
            )

            assert creator.username == demo.creado_por
            assert ticket.estado.codigo == final_state(demo)
            assert ticket.descripcion == demo.descripcion
            assert current == sorted(final_requesters(demo))
            assert at_creation == sorted(initial_requesters(demo))


def test_catalog_values_are_resolved_by_name(app, seeded):
    with app.app_context():
        ticket = by_clave("mouse-malo")

        assert ticket.categoria.nombre == "Hardware"
        assert ticket.prioridad.codigo == "BAJA"
        assert ticket.ubicacion.nombre == MARCOLETA

        assert by_clave("contrasena-contabilidad").ubicacion is None


def test_a_demo_requester_only_sees_their_own_tickets(app, seeded):
    username = "paula.contreras"
    # Los tickets que creó o donde es solicitante vigente al terminar los
    # ajustes (quien se retira deja de ver el ticket, salvo que lo haya creado).
    expected = {
        demo.clave
        for demo in DEMO_TICKETS
        if demo.creado_por == username or username in final_requesters(demo)
    }

    client = app.test_client()
    client.post("/login", data={"username": username, "password": DEMO_PASSWORD})
    response = client.get("/tickets?vista=todos")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert len(set(re.findall(r'href="/tickets/(\d+)"', page))) == len(expected)

    with app.app_context():
        other = by_clave("pistola-lectora")

    assert client.get(f"/tickets/{other.public_id}").status_code == 404


def test_texts_are_shown_escaped(app, seeded):
    client = app.test_client()
    client.post("/login", data={"username": "diego.soto", "password": DEMO_PASSWORD})

    with app.app_context():
        ticket = by_clave("toner-bajo")

    page = client.get(f"/tickets/{ticket.public_id}").get_data(as_text=True)

    assert "&lt;NEGRO&gt;" in page
    assert "<NEGRO>" not in page


# --- La marca del seed --------------------------------------------------


def test_every_event_of_a_demo_ticket_carries_its_key_and_step(app, seeded):
    with app.app_context():
        for demo in DEMO_TICKETS:
            events = history_of(by_clave(demo.clave))
            steps = [event.contexto["demo_paso"] for event in events]

            assert all(e.contexto["demo_clave"] == demo.clave for e in events)
            assert steps[0] == 0
            assert steps == sorted(steps)
            assert max(steps) <= len(demo.ajustes)


def test_the_priority_reason_survives_next_to_the_marker(app, seeded):
    with app.app_context():
        event = history_of(by_clave("sistema-caido-bodega"))[2]

        assert event.tipo_evento == "PRIORIDAD_CAMBIADA"
        assert event.contexto["motivo"].startswith("No es una caída")
        assert event.contexto["demo_clave"] == "sistema-caido-bodega"


def test_the_marker_is_not_shown_in_the_interface(app, seeded):
    client = app.test_client()
    client.post("/login", data={"username": "diego.soto", "password": DEMO_PASSWORD})

    with app.app_context():
        ticket = by_clave("sistema-caido-bodega")

    page = client.get(f"/tickets/{ticket.public_id}").get_data(as_text=True)

    assert "demo_clave" not in page and "demo_paso" not in page


# --- Volver a ejecutarlo ------------------------------------------------


def test_running_it_again_creates_nothing_and_refreshes_the_existing(app, prepared):
    first = run_command(app)

    with app.app_context():
        tickets_after_first = count(Ticket)
        events_after_first = count(TicketHistory)

    second = run_command(app)

    assert first.exit_code == 0 and second.exit_code == 0
    assert (
        f"Tickets demo creados: 0. Actualizados (ya existían): {len(DEMO_TICKETS)}."
        in second.output
    )

    with app.app_context():
        assert count(Ticket) == tickets_after_first == len(DEMO_TICKETS)
        assert count(TicketHistory) == events_after_first


def test_refreshing_leaves_the_same_dates_when_run_on_the_same_day(app, seeded):
    with app.app_context():
        before = date_snapshot()

        result = seed_demo_tickets(now=NOW)

        assert result.refreshed == len(DEMO_TICKETS)
        assert date_snapshot() == before


def test_refreshing_never_touches_the_content_nor_the_versions(app, seeded):
    later = NOW + timedelta(days=20)

    with app.app_context():
        before = content_snapshot()

        seed_demo_tickets(now=later)

        assert content_snapshot() == before


def test_refreshing_gives_the_same_dates_as_a_fresh_load_on_the_new_day(app, prepared):
    # Cae en domingo: cambian los fines de semana que hay que esquivar.
    later = NOW + timedelta(days=11)

    with app.app_context():
        seed_demo_tickets(now=later)
        fresh = date_snapshot()

        db.session.remove()
        empty_tables()

    prepare(app)

    with app.app_context():
        seed_demo_tickets(now=NOW)
        seed_demo_tickets(now=later)
        refreshed = date_snapshot()

    assert refreshed == fresh


def test_the_refresh_moves_the_tickets_to_the_new_day(app, seeded):
    later = NOW + timedelta(days=7)  # miércoles siguiente

    with app.app_context():
        seed_demo_tickets(now=later)

        assert local(by_clave("wifi-sala-reuniones").fecha_creacion) == datetime(
            2026, 11, 25, 10, 40, tzinfo=ZONE
        )
        # Cuatro semanas laborales antes del miércoles 25.
        assert local(by_clave("mouse-malo").fecha_creacion) == datetime(
            2026, 10, 28, 12, 30, tzinfo=ZONE
        )


# --- Ediciones a mano sobre un ticket demo ------------------------------


def test_manual_edits_follow_the_ticket_and_stay_in_order(app, seeded):
    with app.app_context():
        ticket = by_clave("mouse-malo")
        manual = edit_by_hand(ticket, "mouse malo (cambiado a mano)", NOW - timedelta(hours=1))

        later = NOW + timedelta(days=5)  # lunes siguiente
        seed_demo_tickets(now=later)

        events = history_of(ticket)
        times = [event.fecha_hora for event in events]

        assert [e.id for e in events][-1] == manual.id
        assert "demo_clave" not in (events[-1].contexto or {})
        assert times == sorted(times)
        # Se desplazó lo mismo que el ticket: 14:00 del lunes siguiente.
        assert local(times[-1]) == datetime(2026, 11, 23, 14, 0, tzinfo=ZONE)
        assert ticket.fecha_modificacion == times[-1]

        # El contenido que alguien editó a mano no se toca.
        assert db.session.get(Ticket, ticket.id).titulo == "mouse malo (cambiado a mano)"


def test_a_manual_edit_is_never_left_in_the_future(app, seeded):
    with app.app_context():
        # "excel-bloqueado" cruza un fin de semana: al refrescar, el ticket se
        # desplaza más de lo que avanza el reloj.
        ticket = by_clave("excel-bloqueado")
        edit_by_hand(ticket, "excel bloqueado (a mano)", NOW - timedelta(minutes=1))

        later = NOW + timedelta(days=1)
        seed_demo_tickets(now=later)

        events = history_of(ticket)
        times = [event.fecha_hora for event in events]

        assert times == sorted(times)
        assert max(times) <= later - timedelta(minutes=1)
        assert times[-1] == later - timedelta(minutes=1)
        assert ticket.fecha_modificacion == times[-1]


# --- Identidad ----------------------------------------------------------


def test_improving_a_title_in_the_list_does_not_duplicate_the_ticket(app, seeded):
    improved = tuple(
        replace(demo, titulo="El mouse se queda pegado y el cursor se mueve solo")
        if demo.clave == "mouse-malo"
        else demo
        for demo in DEMO_TICKETS
    )

    with app.app_context():
        result = seed_demo_tickets(now=NOW, tickets=improved)

        assert result.created == 0
        assert result.refreshed == len(DEMO_TICKETS)
        assert count(Ticket) == len(DEMO_TICKETS)

        # El contenido ya cargado no se sobrescribe al volver a ejecutar.
        assert by_clave("mouse-malo").titulo == "mouse malo"


def test_adding_a_ticket_to_the_list_creates_only_the_new_one(app, seeded):
    extra = replace(
        DEMO_TICKETS[0],
        clave="ticket-nuevo-de-prueba",
        titulo="Un ticket que se agregó después a la lista",
    )

    with app.app_context():
        result = seed_demo_tickets(now=NOW, tickets=(*DEMO_TICKETS, extra))

        assert result.created == 1
        assert result.refreshed == len(DEMO_TICKETS)
        assert count(Ticket) == len(DEMO_TICKETS) + 1


def test_every_running_demo_period_has_its_warning_date(app, seeded):
    # Los períodos que abre la carga guardan cuándo alcanzan el umbral de aviso: es lo que
    # permite filtrar por «próximo a vencer» en el listado.
    with app.app_context():
        running = db.session.scalars(
            db.select(PeriodoSla).where(
                PeriodoSla.fecha_fin.is_(None),
                PeriodoSla.fecha_vencimiento_resolucion.is_not(None),
            )
        ).all()

        assert running
        assert all(p.umbral_aviso_porcentaje is not None for p in running)
        assert all(p.fecha_umbral_aviso is not None for p in running)
        assert all(
            p.fecha_inicio <= p.fecha_umbral_aviso <= p.fecha_vencimiento_resolucion
            for p in running
        )


def test_the_demo_tickets_do_not_flood_anyone_with_notifications(app, seeded):
    # Los servicios avisan al operar, pero la historia de un ticket demo es del pasado:
    # no deja avisos (los de ejemplo tienen su propio comando).
    with app.app_context():
        assert count(Notificacion) == 0

        extra = replace(
            DEMO_TICKETS[0],
            clave="ticket-nuevo-de-prueba",
            titulo="Un ticket que se agregó después a la lista",
        )
        seed_demo_tickets(now=NOW, tickets=(*DEMO_TICKETS, extra))

        assert count(Notificacion) == 0


def test_the_seed_keeps_the_notifications_of_tickets_it_did_not_create(app, seeded):
    with app.app_context():
        ticket = by_clave("mouse-malo")
        user = db.session.scalar(db.select(User).limit(1))
        db.session.add(
            Notificacion(
                usuario_id=user.id,
                ticket_id=ticket.id,
                tipo_evento="TICKET_ASIGNADO",
                mensaje="Aviso que ya existía",
            )
        )
        db.session.commit()

        extra = replace(
            DEMO_TICKETS[0],
            clave="ticket-nuevo-de-prueba",
            titulo="Un ticket que se agregó después a la lista",
        )
        seed_demo_tickets(now=NOW, tickets=(*DEMO_TICKETS, extra))

        assert count(Notificacion) == 1


def test_changing_the_age_in_the_list_moves_the_ticket(app, seeded):
    moved = tuple(
        replace(demo, hace_dias=1, hora="10:30") if demo.clave == "mouse-malo" else demo
        for demo in DEMO_TICKETS
    )

    with app.app_context():
        seed_demo_tickets(now=NOW, tickets=moved)

        assert local(by_clave("mouse-malo").fecha_creacion) == datetime(
            2026, 11, 17, 10, 30, tzinfo=ZONE
        )


def test_it_never_touches_tickets_created_by_hand(app, prepared):
    with app.app_context():
        manual = create_ticket(
            actor=user("sebastian.vargas"),
            # Mismo título y mismo autor que uno demo: aun así, no es el demo.
            title="mouse malo",
            description="Ticket creado a mano.",
            category_id=db.session.scalar(
                db.select(Categoria.id).where(Categoria.nombre == "Redes")
            ),
            priority_id=db.session.scalar(
                db.select(Prioridad.id).where(Prioridad.codigo == "BAJA")
            ),
        )
        db.session.commit()

        def snapshot():
            db.session.refresh(manual)
            return (
                manual.id,
                manual.titulo,
                manual.descripcion,
                manual.fecha_creacion,
                manual.version,
                [(e.id, e.fecha_hora, e.contexto) for e in history_of(manual)],
            )

        before = snapshot()

        first = seed_demo_tickets(now=NOW)
        second = seed_demo_tickets(now=NOW + timedelta(days=9))

        assert first.created == len(DEMO_TICKETS)
        assert second.created == 0
        assert snapshot() == before
        assert count(Ticket) == len(DEMO_TICKETS) + 1


# --- Catálogos que faltan -----------------------------------------------


def test_missing_categories_and_locations_fall_back_and_are_reported(app):
    prepare(app, categories=("Hardware", "Correo", "Impresoras"), locations=(MARCOLETA,))

    result = run_command(app)

    assert result.exit_code == 0, result.output
    assert "Aviso: Categoría «Redes» no encontrada" in result.output
    assert f"Aviso: Ubicación «{MATTA}» no encontrada" in result.output

    with app.app_context():
        # Un ticket que iba a "Redes" quedó en la categoría de respaldo...
        ticket = by_clave("wifi-sala-reuniones")
        assert ticket.categoria.codigo == "SIN_CLASIFICAR"

        # ...y uno de la sucursal que falta quedó sin ubicación.
        assert by_clave("impresora-segundo-piso").ubicacion is None
        assert count(Ticket) == len(DEMO_TICKETS)


# --- Fechas -------------------------------------------------------------


def test_dates_are_relative_to_the_load_day(app, seeded):
    with app.app_context():
        # hace_dias=0: el mismo día, a la hora indicada.
        assert local(by_clave("wifi-sala-reuniones").fecha_creacion) == datetime(
            2026, 11, 18, 10, 40, tzinfo=ZONE
        )

        # hace_dias=3 son tres DÍAS LABORALES (martes, lunes y viernes).
        assert local(by_clave("excel-bloqueado").fecha_creacion) == datetime(
            2026, 11, 13, 9, 12, tzinfo=ZONE
        )

        # hace_dias=20 son cuatro semanas laborales exactas.
        assert local(by_clave("mouse-malo").fecha_creacion) == datetime(
            2026, 10, 21, 12, 30, tzinfo=ZONE
        )

        for demo in DEMO_TICKETS:
            created = local(by_clave(demo.clave).fecha_creacion)

            assert_inside_the_default_calendar(created)
            assert workdays_between(created.date(), NOW.date()) == demo.hace_dias


def test_no_event_is_ever_in_the_future_and_everything_is_in_order(app, prepared):
    early = datetime(2026, 11, 18, 9, 0, tzinfo=ZONE)

    with app.app_context():
        seed_demo_tickets(now=early)

        # A las 9:00 aún no ha pasado ni un minuto de jornada: los tickets de
        # las 10:40 de hoy quedan al final de la jornada del día laboral anterior.
        assert local(by_clave("wifi-sala-reuniones").fecha_creacion) == datetime(
            2026, 11, 17, 17, 59, tzinfo=ZONE
        )

        for demo in DEMO_TICKETS:
            ticket = by_clave(demo.clave)
            times = [event.fecha_hora for event in history_of(ticket)]

            assert times == sorted(times)
            assert max(times) <= early
            assert ticket.fecha_creacion == times[0]

            for moment in times:
                assert_inside_the_default_calendar(moment)

            # Cada participación empieza en la creación o en su evento y, si
            # se retiró, nunca antes de empezar.
            added = {
                event.contexto["participacion_id"]: event.fecha_hora
                for event in history_of(ticket)
                if event.tipo_evento == TicketEvent.SOLICITANTE_AGREGADO.value
            }

            for link in requesters_of(ticket):
                assert link.fecha_asociacion == added.get(link.id, ticket.fecha_creacion)

                if link.fecha_retiro is not None:
                    assert link.fecha_retiro >= link.fecha_asociacion
                    assert link.fecha_retiro <= early

            # Como en la aplicación: la fecha de modificación existe si y solo
            # si algo subió la versión del ticket (agregar o retirar
            # solicitantes no lo hace) y es la de uno de sus eventos.
            assert (ticket.version > 1) is (ticket.fecha_modificacion is not None)

            if ticket.fecha_modificacion is not None:
                assert ticket.fecha_modificacion in times


# --- Tiempo laboral -----------------------------------------------------


def test_nothing_falls_outside_the_working_days_and_hours(app, seeded):
    with app.app_context():
        for moment in all_event_times():
            assert_inside_the_default_calendar(moment)


def test_adjustments_run_on_working_hours_and_skip_the_night(app, seeded):
    # Creado un lunes a las 16:50: quedan 1 h 10 min de jornada y las 3 h 50 min
    # restantes de las 5 h se cumplen a la mañana siguiente.
    with app.app_context():
        events = history_of(by_clave("archivo-borrado"))

        assert local(events[0].fecha_hora) == datetime(2026, 11, 9, 16, 50, tzinfo=ZONE)
        assert local(events[1].fecha_hora) == datetime(2026, 11, 10, 12, 50, tzinfo=ZONE)


def test_adjustments_skip_the_weekend(app, prepared):
    friday_afternoon = replace(
        DEMO_TICKETS[0],
        clave="viernes-por-la-tarde",
        titulo="Un ticket de viernes por la tarde",
        hace_dias=3,
        hora="17:00",
        ajustes=(
            DemoAdjustment(actor="diego.soto", despues_horas=3, titulo="Titulo corregido"),
        ),
    )

    with app.app_context():
        seed_demo_tickets(now=NOW, tickets=(friday_afternoon,))

        events = history_of(by_clave("viernes-por-la-tarde"))

        # Viernes 17:00 + 1 h hasta las 18:00 + 2 h el lunes desde las 9:00.
        assert local(events[0].fecha_hora) == datetime(2026, 11, 13, 17, 0, tzinfo=ZONE)
        assert local(events[1].fecha_hora) == datetime(2026, 11, 16, 11, 0, tzinfo=ZONE)


def test_a_sunday_run_counts_from_the_last_working_day(app, prepared):
    sunday = datetime(2026, 11, 29, 15, 0, tzinfo=ZONE)

    with app.app_context():
        seed_demo_tickets(now=sunday)

        assert local(by_clave("wifi-sala-reuniones").fecha_creacion) == datetime(
            2026, 11, 27, 10, 40, tzinfo=ZONE
        )

        for moment in all_event_times():
            assert_inside_the_default_calendar(moment)


def test_an_evening_run_never_places_anything_after_the_end_of_the_day(app, prepared):
    evening = datetime(2026, 11, 18, 20, 0, tzinfo=ZONE)

    with app.app_context():
        seed_demo_tickets(now=evening)

        for moment in all_event_times():
            assert_inside_the_default_calendar(moment)
            assert moment <= evening


def test_a_holiday_is_skipped_when_counting_days_and_hours(app, prepared):
    calendar = WorkCalendar(feriados=(date(2026, 11, 17),))

    with app.app_context():
        seed_demo_tickets(now=NOW, calendar=calendar)

        # Tres días laborales antes del miércoles 18, sin contar el feriado del 17.
        events = history_of(by_clave("excel-bloqueado"))
        assert local(events[0].fecha_hora) == datetime(2026, 11, 12, 9, 12, tzinfo=ZONE)

        for moment in all_event_times():
            assert local(moment).date() != date(2026, 11, 17)


def test_the_calendar_is_configurable(app, prepared):
    saturdays_too = WorkCalendar(dias=(0, 1, 2, 3, 4, 5), inicio="08:00", fin="20:00")

    with app.app_context():
        seed_demo_tickets(now=NOW, calendar=saturdays_too)

        # Con el sábado laboral, tres días laborales antes del miércoles 18 es
        # el sábado 14.
        events = history_of(by_clave("excel-bloqueado"))
        assert local(events[0].fecha_hora) == datetime(2026, 11, 14, 9, 12, tzinfo=ZONE)


def test_refreshing_equals_a_fresh_load_with_a_custom_calendar(app, prepared):
    calendar = WorkCalendar(
        inicio="08:00",
        fin="19:00",
        feriados=(date(2026, 11, 16), date(2026, 11, 26)),
    )
    later = NOW + timedelta(days=11)

    with app.app_context():
        seed_demo_tickets(now=later, calendar=calendar)
        fresh = date_snapshot()

        db.session.remove()
        empty_tables()

    prepare(app)

    with app.app_context():
        seed_demo_tickets(now=NOW, calendar=calendar)
        seed_demo_tickets(now=later, calendar=calendar)

        assert date_snapshot() == fresh


# --- El calendario laboral que guarda el Administrador ----------------------


def save_calendar(*, franjas, holidays=(), zone="America/Santiago"):
    """Guarda un calendario laboral como lo haría el Administrador.

    El servicio no comprueba el rol (lo hace la ruta), así que sirve cualquier
    persona activa del equipo demo.
    """
    save_work_calendar(
        actor=user("camila.rojas"),
        base_version=0,
        zone_name=zone,
        franjas=franjas,
        holidays=holidays,
    )
    db.session.commit()


def lunch_break_week(days=range(5)):
    """De 09:00 a 13:00 y de 14:00 a 18:00 en los días indicados."""
    return [
        Franja(day, parse_time(start), parse_time(end))
        for day in days
        for start, end in (("09:00", "13:00"), ("14:00", "18:00"))
    ]


def test_the_seed_reads_the_calendar_the_administrator_saved(app, prepared):
    with app.app_context():
        # De lunes a jueves, con pausa de almuerzo, y el martes 17 de noviembre
        # es feriado.
        save_calendar(
            franjas=lunch_break_week(range(4)),
            holidays=[Holiday(date(2026, 11, 17), "Feriado de prueba")],
        )
        clock = resolve_work_calendar().clock

        seed_demo_tickets(now=NOW)

        moments = all_event_times()

        assert moments
        for moment in moments:
            assert clock.is_working_time(moment), local(moment)
            assert local(moment).date() != date(2026, 11, 17)
        # Con el viernes sin trabajo, tampoco hay nada en viernes.
        assert all(local(moment).weekday() < 4 for moment in moments)


def test_the_seed_uses_the_zone_of_the_saved_calendar(app, prepared):
    bogota = ZoneInfo("America/Bogota")

    with app.app_context():
        save_calendar(franjas=lunch_break_week(), zone="America/Bogota")

        seed_demo_tickets(now=NOW)

        for moment in all_event_times():
            when = moment.astimezone(bogota)

            assert when.weekday() < 5, when
            assert time(9, 0) <= when.time() < time(13, 0) or time(14, 0) <= when.time() < time(18, 0), when


def test_the_seed_counts_today_in_the_zone_of_the_saved_calendar(app, prepared):
    bogota = ZoneInfo("America/Bogota")
    # Pasada la medianoche en Santiago (jueves 19, 01:00) en Bogotá todavía es la
    # noche del miércoles 18: «hoy» es el miércoles.
    after_midnight = datetime(2026, 11, 19, 1, 0, tzinfo=ZONE)
    today = replace(
        DEMO_TICKETS[0],
        clave="ticket-de-hoy",
        titulo="Un ticket de hoy",
        hace_dias=0,
        hora="10:40",
        ajustes=(),
    )

    with app.app_context():
        save_calendar(franjas=lunch_break_week(), zone="America/Bogota")

        seed_demo_tickets(now=after_midnight, tickets=(today,))

        created = by_clave("ticket-de-hoy").fecha_creacion.astimezone(bogota)

        assert created == datetime(2026, 11, 18, 10, 40, tzinfo=bogota)


def test_an_explicit_calendar_wins_over_the_saved_one(app, prepared):
    with app.app_context():
        save_calendar(franjas=lunch_break_week(range(4)))

        seed_demo_tickets(now=NOW, calendar=WorkCalendar())

        moments = all_event_times()

        # El guardado no tiene viernes y el explícito (el de por defecto) sí.
        assert any(local(moment).weekday() == 4 for moment in moments)
        for moment in moments:
            assert_inside_the_default_calendar(moment)


def test_a_creation_hour_inside_a_break_moves_to_the_next_working_moment(app, prepared):
    lunch = replace(
        DEMO_TICKETS[0],
        clave="ticket-del-almuerzo",
        titulo="Un ticket creado a la hora de almuerzo",
        hace_dias=2,
        hora="13:30",
        ajustes=(),
    )

    with app.app_context():
        save_calendar(franjas=lunch_break_week())

        seed_demo_tickets(now=NOW, tickets=(lunch,))

        # Dos días laborales antes del miércoles 18 es el lunes 16; las 13:30 caen
        # en la pausa, así que el ticket queda a las 14:00.
        assert local(by_clave("ticket-del-almuerzo").fecha_creacion) == datetime(
            2026, 11, 16, 14, 0, tzinfo=ZONE
        )


def test_refreshing_with_a_saved_calendar_keeps_everything_in_working_time(app, prepared):
    with app.app_context():
        save_calendar(
            franjas=lunch_break_week(),
            holidays=[Holiday(date(2026, 11, 26), "Feriado de prueba")],
        )
        clock = resolve_work_calendar().clock

        seed_demo_tickets(now=NOW)
        seed_demo_tickets(now=NOW + timedelta(days=11))

        assert count(Ticket) == len(DEMO_TICKETS)
        for moment in all_event_times():
            assert clock.is_working_time(moment), local(moment)


def test_validation_with_a_saved_calendar_does_not_compare_hours_with_one_shift():
    early = replace(DEMO_TICKETS[0], hora="07:00")

    with pytest.raises(DemoTicketsError, match="fuera de la jornada"):
        validate_demo_tickets((early,), WorkCalendar())

    # Sin una jornada única con la que compararla, la hora solo debe estar bien
    # escrita: al planificar se pasa a horario laboral.
    validate_demo_tickets((early,), None)

    with pytest.raises(DemoTicketsError, match="formato HH:MM"):
        validate_demo_tickets((replace(DEMO_TICKETS[0], hora="25:00"),), None)


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


def page_text(client, public_id) -> str:
    html = client.get(f"/tickets/{public_id}").get_data(as_text=True)

    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def log_in(app, username):
    client = app.test_client()
    client.post(
        "/login",
        data={"username": username, "password": DEMO_PASSWORD},
    )

    return client


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

        result = seed_demo_tickets(now=NOW)

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

        result = seed_demo_tickets(now=NOW)

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


# --- Solicitantes agregados y retirados ------------------------------------


def events_of(ticket, *kinds):
    return [
        event
        for event in history_of(ticket)
        if event.tipo_evento in {kind.value for kind in kinds}
    ]


def link_for(ticket, username):
    return next(
        link for link in requesters_of(ticket) if link.solicitante.username == username
    )


@pytest.mark.parametrize(
    ("adjustment", "message"),
    [
        # `excel-bloqueado` (el primero) lo crea Javiera, que es su solicitante.
        (DemoAdjustment(actor="diego.soto", despues_horas=1,
                        agregar_solicitante="felipe.araya"),
         "no es un Solicitante demo"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1,
                        retirar_solicitante="felipe.araya"),
         "no es un Solicitante demo"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1,
                        retirar_solicitante="andres.silva"),
         "no es solicitante en ese momento"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1,
                        agregar_solicitante="javiera.torres"),
         "ya es solicitante en ese momento"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1,
                        retirar_solicitante="javiera.torres",
                        agregar_solicitante="javiera.torres"),
         "retirar y agregar a la misma persona"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1,
                        agregar_solicitante="andres.silva",
                        motivo_retiro="Sin sentido"),
         "motivo_retiro solo va con retirar_solicitante"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1,
                        retirar_solicitante="javiera.torres",
                        motivo_retiro="x" * 501),
         "motivo de retiro supera los 500"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1,
                        retirar_solicitante="javiera.torres",
                        motivo_retiro=" con espacios "),
         "motivo de retiro está vacío o tiene espacios"),
        (DemoAdjustment(actor="paula.contreras", despues_horas=1,
                        agregar_solicitante="andres.silva"),
         "no es personal"),
    ],
)
def test_validation_rejects_inconsistent_requester_steps(adjustment, message):
    ticket = replace(DEMO_TICKETS[0], ajustes=(adjustment,))

    with pytest.raises(DemoTicketsError, match=message):
        validate_demo_tickets((ticket,))


def test_validation_follows_the_requesters_step_by_step():
    # Retirar a alguien y volver a agregarlo más tarde es válido...
    steps = (
        DemoAdjustment(actor="diego.soto", despues_horas=1,
                       retirar_solicitante="javiera.torres"),
        DemoAdjustment(actor="diego.soto", despues_horas=1,
                       agregar_solicitante="javiera.torres"),
    )

    validate_demo_tickets((replace(DEMO_TICKETS[0], ajustes=steps),))

    # ...y cambiar a una persona por otra en un mismo paso también.
    swap = (
        DemoAdjustment(actor="diego.soto", despues_horas=1,
                       retirar_solicitante="javiera.torres",
                       agregar_solicitante="andres.silva"),
    )

    validate_demo_tickets((replace(DEMO_TICKETS[0], ajustes=swap),))

    # Pero no agregar dos veces a la misma persona.
    twice = (
        DemoAdjustment(actor="diego.soto", despues_horas=1,
                       agregar_solicitante="andres.silva"),
        DemoAdjustment(actor="diego.soto", despues_horas=1,
                       agregar_solicitante="andres.silva"),
    )

    with pytest.raises(DemoTicketsError, match="ya es solicitante en ese momento"):
        validate_demo_tickets((replace(DEMO_TICKETS[0], ajustes=twice),))


def test_demo_data_covers_the_requester_changes():
    steps = [(demo, step) for demo in DEMO_TICKETS for step in demo.ajustes]

    # Cambiar a una persona por otra en un mismo paso.
    assert any(
        step.retirar_solicitante and step.agregar_solicitante for _, step in steps
    )
    # Agregar a quien nace en un ticket sin solicitantes (RN-12).
    assert any(
        step.agregar_solicitante and not initial_requesters(demo)
        for demo, step in steps
    )
    # Agregar a alguien y retirarlo en un paso posterior.
    def adds_then_retires(demo):
        added = set()

        for step in demo.ajustes:
            if step.retirar_solicitante in added:
                return True

            if step.agregar_solicitante is not None:
                added.add(step.agregar_solicitante)

        return False

    assert any(adds_then_retires(demo) for demo in DEMO_TICKETS)
    # Retirar a quien creó el ticket (que lo sigue viendo).
    assert any(
        step.retirar_solicitante == demo.creado_por for demo, step in steps
    )


def test_a_wrongly_associated_requester_is_replaced(app, seeded):
    with app.app_context():
        ticket = by_clave("proyector-sala-chica")
        removed = link_for(ticket, "constanza.herrera")
        added = link_for(ticket, "paula.contreras")
        felipe = user("felipe.araya")

        assert [r.solicitante.username for r in ticket.solicitantes_vigentes] == [
            "paula.contreras"
        ]
        assert removed.fecha_retiro is not None
        assert removed.retirado_por_usuario_id == felipe.id
        assert added.asociado_por_usuario_id == felipe.id

        # Primero se retira y después se agrega, con la marca de su paso.
        kinds = [e.tipo_evento for e in history_of(ticket)]

        assert kinds == ["TICKET_CREADO", "SOLICITANTE_RETIRADO", "SOLICITANTE_AGREGADO"]
        assert all(e.contexto["demo_clave"] == "proyector-sala-chica" for e in history_of(ticket))

        retired_event, added_event = history_of(ticket)[1:]

        assert retired_event.visibilidad == "INTERNO"
        assert retired_event.contexto["motivo"].startswith("Constanza solo avisó")
        assert retired_event.contexto["participacion_id"] == removed.id
        assert added_event.contexto["participacion_id"] == added.id
        # No se tocó la versión ni la fecha de modificación (como en la
        # aplicación: los solicitantes no modifican el ticket).
        assert ticket.version == 1
        assert ticket.fecha_modificacion is None
        assert ticket.estado.codigo == "NUEVO"


def test_a_requester_can_be_added_to_a_ticket_that_started_without_any(app, seeded):
    with app.app_context():
        ticket = by_clave("ups-bodega-mantencion")
        (link,) = requesters_of(ticket)
        (event,) = events_of(ticket, TicketEvent.SOLICITANTE_AGREGADO)
        created = history_of(ticket)[0]

        assert link.solicitante.username == "ignacio.molina"
        assert link.asociado_por_usuario_id == user("valentina.pizarro").id
        # Se asocia en el momento de su evento, después de crear el ticket.
        assert link.fecha_asociacion == event.fecha_hora
        assert link.fecha_asociacion > created.fecha_hora
        assert ticket.fecha_actualizacion == ticket.fecha_creacion


def test_a_requester_added_and_retired_later_keeps_both_dates(app, seeded):
    with app.app_context():
        ticket = by_clave("vpn-se-corta")
        original = link_for(ticket, "sebastian.vargas")
        guest = link_for(ticket, "andres.silva")
        (added,) = events_of(ticket, TicketEvent.SOLICITANTE_AGREGADO)
        (retired,) = events_of(ticket, TicketEvent.SOLICITANTE_RETIRADO)

        assert original.fecha_retiro is None
        assert original.fecha_asociacion == ticket.fecha_creacion
        assert guest.fecha_asociacion == added.fecha_hora
        assert guest.fecha_retiro == retired.fecha_hora
        assert guest.fecha_retiro > guest.fecha_asociacion
        assert retired.contexto["motivo"] == "Su problema era otro y se atendió por separado."
        assert [e.tipo_evento for e in history_of(ticket)] == [
            "TICKET_CREADO",
            "SOLICITANTE_AGREGADO",
            "SOLICITANTE_RETIRADO",
        ]


def test_the_creator_keeps_seeing_the_ticket_after_being_retired(app, seeded):
    with app.app_context():
        ticket = by_clave("impresora-proyectos-a-nombre-de")
        public_id = ticket.public_id

        assert link_for(ticket, "constanza.herrera").fecha_retiro is not None
        assert [r.solicitante.username for r in ticket.solicitantes_vigentes] == [
            "andres.silva"
        ]

    # Constanza sigue viéndolo porque lo creó; Andrés porque es el solicitante.
    for username in ("constanza.herrera", "andres.silva"):
        client = log_in(app, username)

        assert client.get(f"/tickets/{public_id}").status_code == 200, username
        assert f'href="/tickets/{public_id}"' in client.get(
            "/tickets?vista=todos"
        ).get_data(as_text=True), username

    # Quien no tiene relación con el ticket, no.
    assert log_in(app, "paula.contreras").get(f"/tickets/{public_id}").status_code == 404


def test_a_retired_requester_who_did_not_create_the_ticket_loses_access(app, seeded):
    with app.app_context():
        public_id = by_clave("proyector-sala-chica").public_id

    assert log_in(app, "constanza.herrera").get(f"/tickets/{public_id}").status_code == 404
    assert log_in(app, "paula.contreras").get(f"/tickets/{public_id}").status_code == 200


def test_the_requester_events_are_only_for_staff_in_the_demo(app, seeded):
    with app.app_context():
        public_id = by_clave("proyector-sala-chica").public_id

    requester = page_text(log_in(app, "paula.contreras"), public_id)

    assert "Ticket creado" in requester
    assert "Solicitante agregado" not in requester
    assert "Solicitante retirado" not in requester
    assert "Constanza Herrera" not in requester
    assert "la sala la tenía reservada Paula" not in requester

    staff = page_text(log_in(app, "felipe.araya"), public_id)

    assert "Solicitante retirado: «Constanza Herrera»" in staff
    assert "Solicitante agregado: «Paula Contreras»" in staff
    assert "Motivo: Constanza solo avisó por teléfono; la sala la tenía reservada Paula." in staff
    assert "Solicitante Gestionar" in staff


def test_requester_dates_follow_a_refresh_in_order(app, seeded):
    with app.app_context():
        first = date_snapshot()

        seed_demo_tickets(now=NOW + timedelta(days=3))

        assert date_snapshot() != first

        for demo in DEMO_TICKETS:
            ticket = by_clave(demo.clave)
            added = {
                e.contexto["participacion_id"]: e.fecha_hora
                for e in events_of(ticket, TicketEvent.SOLICITANTE_AGREGADO)
            }
            retired = {
                e.contexto["participacion_id"]: e.fecha_hora
                for e in events_of(ticket, TicketEvent.SOLICITANTE_RETIRADO)
            }

            for link in requesters_of(ticket):
                assert link.fecha_asociacion == added.get(link.id, ticket.fecha_creacion)

                if link.id in retired:
                    assert link.fecha_retiro == retired[link.id]
                    assert link.fecha_retiro >= link.fecha_asociacion
                else:
                    assert link.fecha_retiro is None


def test_a_hand_made_requester_change_follows_the_refresh(app, seeded):
    from src.workdesk.tickets.requesters import add_requester, remove_requester

    later = NOW + timedelta(days=3)

    with app.app_context():
        ticket = by_clave("proyector-sala-chica")
        diego = user("diego.soto")

        # A mano: se suma a Javiera y después se retira a Paula.
        added = add_requester(ticket, user("javiera.torres").id, actor=diego)
        db.session.commit()
        remove_requester(
            ticket,
            link_for(ticket, "paula.contreras").id,
            actor=diego,
            reason="A mano",
        )
        db.session.commit()

        seed_demo_tickets(now=later)

        ticket = by_clave("proyector-sala-chica")
        events = history_of(ticket)
        times = [e.fecha_hora for e in events]
        hand_added = events_of(ticket, TicketEvent.SOLICITANTE_AGREGADO)[-1]
        hand_removed = events_of(ticket, TicketEvent.SOLICITANTE_RETIRADO)[-1]

        # Los eventos hechos a mano siguen en orden y no quedan en el futuro.
        assert times == sorted(times)
        assert max(times) <= later - timedelta(minutes=1)
        # Y sus participaciones los acompañan, con el retiro nunca antes de empezar.
        db.session.refresh(added)
        paula = link_for(ticket, "paula.contreras")

        assert added.fecha_asociacion == hand_added.fecha_hora
        assert paula.fecha_retiro == hand_removed.fecha_hora
        assert paula.fecha_retiro >= paula.fecha_asociacion


# --- Comentarios y notas internas ------------------------------------------


@pytest.mark.parametrize(
    ("adjustment", "message"),
    [
        # `excel-bloqueado` (el primero) lo crea Javiera, que es su solicitante.
        (DemoAdjustment(actor="paula.contreras", despues_horas=1, comentario="Hola"),
         "no es solicitante ni creó el ticket"),
        (DemoAdjustment(actor="javiera.torres", despues_horas=1, comentario="Hola",
                        titulo="Otro título"),
         "no es personal"),
        (DemoAdjustment(actor="javiera.torres", despues_horas=1, nota_interna="Secreto"),
         "no es personal"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1, comentario="x" * 5001),
         "comentario supera los 5000"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1, nota_interna="y" * 5001),
         "nota interna supera los 5000"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1, comentario=" con espacios "),
         "comentario está vacío o tiene espacios"),
    ],
)
def test_validation_rejects_inconsistent_comment_steps(adjustment, message):
    ticket = replace(DEMO_TICKETS[0], ajustes=(adjustment,))

    with pytest.raises(DemoTicketsError, match=message):
        validate_demo_tickets((ticket,))


def test_validation_accepts_the_creator_and_a_current_requester_commenting():
    # Javiera crea `excel-bloqueado`; en el ticket comenta quien es solicitante
    # en ese momento, aunque se haya agregado después.
    creator = (
        DemoAdjustment(actor="javiera.torres", despues_horas=1, comentario="Gracias"),
    )
    added = (
        DemoAdjustment(actor="diego.soto", despues_horas=1, agregar_solicitante="andres.silva"),
        DemoAdjustment(actor="andres.silva", despues_horas=1, comentario="A mí también me pasa"),
    )

    validate_demo_tickets((replace(DEMO_TICKETS[0], ajustes=creator),))
    validate_demo_tickets((replace(DEMO_TICKETS[0], ajustes=added),))

    # Pero no después de retirarlo.
    retired = added + (
        DemoAdjustment(actor="diego.soto", despues_horas=1, retirar_solicitante="andres.silva"),
        DemoAdjustment(actor="andres.silva", despues_horas=1, comentario="Sigo aquí"),
    )

    with pytest.raises(DemoTicketsError, match="no es solicitante ni creó el ticket"):
        validate_demo_tickets((replace(DEMO_TICKETS[0], ajustes=retired),))


def test_demo_data_covers_the_comment_cases():
    steps = [step for demo in DEMO_TICKETS for step in demo.ajustes]

    assert any(s.comentario and ROLES[s.actor] != "SOLICITANTE" for s in steps)
    assert any(s.comentario and ROLES[s.actor] == "SOLICITANTE" for s in steps), (
        "falta un comentario de un Solicitante"
    )
    assert any(s.nota_interna for s in steps), "falta una nota interna"
    assert any(s.comentario and s.nota_interna for s in steps), "falta un paso con ambas"
    assert any(s.comentario and s.estado for s in steps), (
        "falta un comentario junto a un cambio de estado"
    )
    # Un ticket con más notas que comentarios públicos: el Solicitante ve poco.
    assert any(
        sum(1 for s in demo.ajustes if s.nota_interna)
        > sum(1 for s in demo.ajustes if s.comentario)
        for demo in DEMO_TICKETS
    )


def test_a_conversation_leaves_the_same_history_as_the_application(app, seeded):
    with app.app_context():
        ticket = by_clave("intranet-credenciales")
        comments = comments_of(ticket)
        events = history_of(ticket)
        notes = [
            e
            for e in events
            if e.tipo_evento == "COMENTARIO_AGREGADO" and e.visibilidad == "INTERNO"
        ]

        # Dentro de un paso, el comentario público va antes que la nota.
        assert [(c.autor.username, c.tipo) for c in comments] == [
            ("felipe.araya", "PUBLICO"),
            ("sebastian.vargas", "PUBLICO"),
            ("felipe.araya", "PUBLICO"),
            ("felipe.araya", "INTERNO"),
        ]
        assert [e.tipo_evento for e in events].count("COMENTARIO_AGREGADO") == 4
        assert len(notes) == 1
        assert all(e.contexto["demo_clave"] == "intranet-credenciales" for e in events)
        assert ticket.estado.codigo == "EN_PROGRESO"


def test_comments_alone_do_not_modify_the_ticket(app, seeded):
    with app.app_context():
        ticket = by_clave("teclado-derrame-rrhh")

        assert len(comments_of(ticket)) == 3
        assert ticket.version == 1
        assert ticket.fecha_modificacion is None
        assert ticket.fecha_actualizacion == ticket.fecha_creacion


def test_each_comment_carries_the_date_of_its_event(app, seeded):
    with app.app_context():
        for demo in DEMO_TICKETS:
            ticket = by_clave(demo.clave)
            published = {
                e.contexto["comentario_id"]: e.fecha_hora
                for e in history_of(ticket)
                if e.tipo_evento == "COMENTARIO_AGREGADO"
            }

            for comment in comments_of(ticket):
                assert comment.fecha_creacion == published[comment.id], demo.clave
                assert comment.fecha_creacion >= ticket.fecha_creacion


def test_the_requester_sees_the_public_conversation_but_never_the_notes(app, seeded):
    client = log_in(app, "sebastian.vargas")

    with app.app_context():
        public_id = by_clave("intranet-credenciales").public_id

    html = client.get(f"/tickets/{public_id}").get_data(as_text=True)
    plain = " ".join(re.sub(r"<[^>]+>", " ", html).split())

    assert "Actividad (3)" in plain
    assert "Ya forzamos la sincronización" in plain
    assert "¿Es por eso?" in plain
    assert "sincroniza las credenciales" not in html
    assert "NOTA INTERNA" not in html
    assert "Solo visible para soporte" not in html


def test_a_requester_sees_one_comment_where_staff_wrote_two_notes(app, seeded):
    client = log_in(app, "ignacio.molina")

    with app.app_context():
        public_id = by_clave("switch-bodega-puertos").public_id

    html = client.get(f"/tickets/{public_id}").get_data(as_text=True)
    plain = " ".join(re.sub(r"<[^>]+>", " ", html).split())

    assert "Actividad (1)" in plain
    assert "cambiar unos cables en la bodega" in plain
    assert "errores CRC" not in html
    assert "NOTA INTERNA" not in html


def test_staff_sees_the_notes_marked_as_internal(app, seeded):
    client = log_in(app, "camila.rojas")

    with app.app_context():
        public_id = by_clave("switch-bodega-puertos").public_id

    plain = page_text(client, public_id)

    assert "Actividad (3)" in plain
    assert "errores CRC en los puertos 3 y 4" in plain
    assert plain.count("NOTA INTERNA") == 2
    assert "Solo visible para soporte" in plain


def test_comment_dates_follow_a_refresh(app, seeded):
    with app.app_context():
        first = date_snapshot()

        seed_demo_tickets(now=NOW + timedelta(days=3))

        assert date_snapshot() != first

        for demo in DEMO_TICKETS:
            ticket = by_clave(demo.clave)
            published = {
                e.contexto["comentario_id"]: e.fecha_hora
                for e in history_of(ticket)
                if e.tipo_evento == "COMENTARIO_AGREGADO"
            }

            for comment in comments_of(ticket):
                assert comment.fecha_creacion == published[comment.id], demo.clave


def test_a_hand_made_edit_and_deletion_follow_the_refresh_in_order(app, seeded):
    from src.workdesk.tickets.comments import delete_comment, edit_comment

    later = NOW + timedelta(days=3)

    with app.app_context():
        ticket = by_clave("wifi-visitas-clave")
        first, second, *_ = comments_of(ticket)
        camila = user("camila.rojas")

        # A mano: se corrige un comentario y se elimina otro.
        edit_comment(ticket, first.id, actor=camila, content="Texto corregido a mano")
        db.session.commit()
        delete_comment(ticket, second.id, actor=camila)
        db.session.commit()

        seed_demo_tickets(now=later)

        ticket = by_clave("wifi-visitas-clave")
        events = history_of(ticket)
        times = [e.fecha_hora for e in events]
        edit = next(e for e in events if e.tipo_evento == "COMENTARIO_EDITADO")
        deletion = next(e for e in events if e.tipo_evento == "COMENTARIO_ELIMINADO")

        db.session.refresh(first)
        db.session.refresh(second)

        # Los eventos hechos a mano siguen en orden y no quedan en el futuro...
        assert times == sorted(times)
        assert max(times) <= later - timedelta(minutes=1)
        # ...y el comentario los acompaña, sin perder lo que se escribió.
        assert first.fecha_modificacion == edit.fecha_hora
        assert second.fecha_eliminacion == deletion.fecha_hora
        assert first.fecha_modificacion >= first.fecha_creacion
        assert first.contenido == "Texto corregido a mano"
        assert second.activo is False


def test_refresh_keeps_the_comments(app, seeded):
    with app.app_context():
        before = content_snapshot()

        seed_demo_tickets(now=NOW + timedelta(days=3))

        assert content_snapshot() == before


# --- Adjuntos ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("adjustment", "message"),
    [
        (DemoAdjustment(actor="diego.soto", despues_horas=1, adjunto=("virus.exe", "MZ")),
         "debe terminar en .txt, .log o .csv"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1, adjunto=("imagen.png", "x")),
         "debe terminar en .txt, .log o .csv"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1, adjunto=("vacio.txt", "  ")),
         "está vacío"),
        # Un Solicitante solo adjunta a su propio comentario.
        (DemoAdjustment(actor="javiera.torres", despues_horas=1, adjunto=("a.txt", "x")),
         "no es personal"),
    ],
)
def test_validation_rejects_inconsistent_attachment_steps(adjustment, message):
    ticket = replace(DEMO_TICKETS[0], ajustes=(adjustment,))

    with pytest.raises(DemoTicketsError, match=message):
        validate_demo_tickets((ticket,))


def test_a_requester_can_attach_a_file_to_their_comment():
    step = DemoAdjustment(
        actor="javiera.torres",
        despues_horas=1,
        comentario="Adjunto el log",
        adjunto=("log.log", "contenido"),
    )

    validate_demo_tickets((replace(DEMO_TICKETS[0], ajustes=(step,)),))


def test_the_files_hang_from_the_right_comment_and_exist_on_disk(app, seeded):
    with app.app_context():
        log_ticket = by_clave("error-sistema-contable-log")
        log, diagnosis = attachments_of(log_ticket)
        comments = comments_of(log_ticket)
        csv = attachments_of(by_clave("inventario-notebooks-csv"))[0]

        # El del Solicitante, a su comentario público; el del equipo, al
        # comentario público de su paso (no a la nota).
        assert log.comentario_id == comments[0].id
        assert diagnosis.comentario_id == comments[1].id
        assert comments[1].tipo == "PUBLICO"
        # El del tercer ticket es del ticket, sin comentario.
        assert csv.comentario_id is None

        for item in (log, diagnosis, csv):
            path = attachment_path(item)

            assert path.is_file()
            assert hashlib.sha256(path.read_bytes()).hexdigest() == item.hash
            assert item.tamano_bytes == path.stat().st_size


def test_a_requester_downloads_their_ticket_files(app, seeded):
    client = log_in(app, "javiera.torres")

    with app.app_context():
        ticket = by_clave("error-sistema-contable-log")
        public_id = ticket.public_id
        item = attachments_of(ticket)[0]
        item_id = item.id

    response = client.get(f"/tickets/{public_id}/attachments/{item_id}/download")

    assert response.status_code == 200
    assert b"acceso denegado" in response.data
    assert "attachment" in response.headers["Content-Disposition"]


def test_each_file_carries_the_date_of_its_event(app, seeded):
    with app.app_context():
        for demo in DEMO_TICKETS:
            ticket = by_clave(demo.clave)
            uploaded = {
                e.contexto["archivo_id"]: e.fecha_hora
                for e in history_of(ticket)
                if e.tipo_evento == "ARCHIVO_ADJUNTADO"
            }

            for item in attachments_of(ticket):
                assert item.fecha_subida == uploaded[item.id], demo.clave


def test_file_dates_follow_a_refresh_and_the_files_stay(app, seeded):
    with app.app_context():
        before = date_snapshot()
        paths = [attachment_path(f) for f in db.session.scalars(db.select(Attachment))]

        seed_demo_tickets(now=NOW + timedelta(days=3))

        assert date_snapshot() != before
        assert all(p.is_file() for p in paths)
        assert len(db.session.scalars(db.select(Attachment)).all()) == len(paths)

        for demo in DEMO_TICKETS:
            ticket = by_clave(demo.clave)
            uploaded = {
                e.contexto["archivo_id"]: e.fecha_hora
                for e in history_of(ticket)
                if e.tipo_evento == "ARCHIVO_ADJUNTADO"
            }

            for item in attachments_of(ticket):
                assert item.fecha_subida == uploaded[item.id], demo.clave


def test_running_the_seed_again_does_not_duplicate_files(app, seeded):
    with app.app_context():
        files = sorted(Path(app.config["UPLOADS_DIR"]).rglob("*"))
        files = [f for f in files if f.is_file()]

        seed_demo_tickets(now=NOW + timedelta(days=1))

        again = [f for f in Path(app.config["UPLOADS_DIR"]).rglob("*") if f.is_file()]

        assert len(again) == len(files) == 3


def test_a_hand_made_file_deletion_follows_the_refresh(app, seeded):
    from src.workdesk.tickets.attachments import delete_attachment

    later = NOW + timedelta(days=3)

    with app.app_context():
        ticket = by_clave("inventario-notebooks-csv")
        item = attachments_of(ticket)[0]

        delete_attachment(ticket, item.id, actor=user("camila.rojas"))
        db.session.commit()

        seed_demo_tickets(now=later)

        events = history_of(by_clave("inventario-notebooks-csv"))
        removal = next(e for e in events if e.tipo_evento == "ARCHIVO_ELIMINADO")

        db.session.refresh(item)

        assert item.fecha_eliminacion == removal.fecha_hora
        assert item.fecha_eliminacion >= item.fecha_subida
        assert max(e.fecha_hora for e in events) <= later - timedelta(minutes=1)


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
        assert "Nuevo → Resuelto (Resolver)" in message
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
