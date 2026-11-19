import re
from dataclasses import replace
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import update

from src.workdesk.extensions import db
from src.workdesk.models import (
    Categoria,
    Comment,
    Prioridad,
    Ticket,
    TicketEvent,
    TicketHistory,
    TicketRequester,
    TicketTechnician,
    Ubicacion,
    User,
)
from src.workdesk.models.ticket_history import TicketHistoryImmutableError
from src.workdesk.seeds import (
    DemoTicketsError,
    seed_catalogs,
    seed_demo_groups,
    seed_demo_tickets,
    seed_demo_users,
    seed_roles,
)
from src.workdesk.seeds.demo import DEMO_USERS
from src.workdesk.seeds.demo_tickets import validate_demo_tickets
from src.workdesk.seeds.demo_tickets_data import (
    DEMO_CATEGORIES,
    DEMO_LOCATIONS,
    DEMO_TICKETS,
    MARCOLETA,
    MATTA,
    DemoAdjustment,
    WorkCalendar,
)
from src.workdesk.tickets.editing import update_ticket
from src.workdesk.tickets.service import create_ticket

DEMO_PASSWORD = "ClaveDemoSegura2026"
ZONE = ZoneInfo("America/Santiago")

# Un miércoles a media tarde: deja hacia atrás un fin de semana cercano.
NOW = datetime(2026, 11, 18, 15, 0, tzinfo=ZONE)

ROLES = {demo.username: demo.rol for demo in DEMO_USERS}
SOLICITANTES = sorted(u for u, rol in ROLES.items() if rol == "SOLICITANTE")


def prepare(app, *, categories=("Redes", "Hardware", "Correo", "Impresoras"),
            locations=(MARCOLETA, MATTA)):
    """Deja la base como la tendría quien siguió el README hasta antes del seed."""
    app.config["APP_TIMEZONE"] = "America/Santiago"

    with app.app_context():
        seed_roles()
        seed_catalogs()
        seed_demo_users(DEMO_PASSWORD)
        seed_demo_groups()

        for order, name in enumerate(categories, start=1):
            db.session.add(Categoria(nombre=name, orden=order))

        for name in locations:
            db.session.add(Ubicacion(nombre=name, tipo="OFICINA"))

        db.session.commit()


@pytest.fixture()
def prepared(app):
    prepare(app)


@pytest.fixture()
def seeded(app, prepared):
    with app.app_context():
        result = seed_demo_tickets(now=NOW)

    return result


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
}


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
        (DemoAdjustment(actor="diego.soto", despues_horas=1, estado="RESOLVER"),
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


def test_demo_data_includes_every_state_reachable_today_and_every_wait_reason():
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

    assert finals == {"NUEVO", "ASIGNADO", "EN_PROGRESO", "EN_ESPERA"}
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
        db.drop_all()
        db.create_all()

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
        db.drop_all()
        db.create_all()

    prepare(app)

    with app.app_context():
        seed_demo_tickets(now=NOW, calendar=calendar)
        seed_demo_tickets(now=later, calendar=calendar)

        assert date_snapshot() == fresh


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
