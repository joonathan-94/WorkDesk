"""Los datos de demostración y el comando `seed-demo-tickets`."""

from dataclasses import replace

import pytest

from src.workdesk.models import (
    Ticket,
)
from src.workdesk.seeds import (
    DemoTicketsError,
    seed_catalogs,
    seed_roles,
)
from src.workdesk.seeds.demo_tickets import validate_demo_tickets
from src.workdesk.seeds.demo_tickets_data import (
    DEMO_CATEGORIES,
    DEMO_LOCATIONS,
    DEMO_TICKETS,
    DemoAdjustment,
)
from src.workdesk.worktime import WorkCalendar
from tests.demo_data import ROLES, SOLICITANTES
from tests.seed_helpers import count, final_state, run_command

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
