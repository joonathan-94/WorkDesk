"""Qué crea el seed, su marca, volver a ejecutarlo, ediciones a mano, identidad y catálogos que faltan."""

import re
from dataclasses import replace
from datetime import datetime, timedelta

from src.workdesk.extensions import db
from src.workdesk.models import (
    Categoria,
    Notificacion,
    PeriodoSla,
    Prioridad,
    Ticket,
    TicketEvent,
    TicketHistory,
    User,
)
from src.workdesk.seeds import (
    seed_demo_tickets,
)
from src.workdesk.seeds.demo_tickets_data import (
    DEMO_TICKETS,
    MARCOLETA,
    MATTA,
)
from src.workdesk.tickets.service import create_ticket
from tests.database import empty_tables
from tests.demo_data import DEMO_PASSWORD, NOW, ZONE, prepare
from tests.seed_helpers import (
    by_clave,
    content_snapshot,
    count,
    date_snapshot,
    edit_by_hand,
    final_requesters,
    final_state,
    history_of,
    initial_requesters,
    local,
    requesters_of,
    run_command,
    user,
)

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
