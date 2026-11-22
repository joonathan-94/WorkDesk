"""Indicadores de SLA en la interfaz (docs/06, RN-169; docs/11, UI-003 y UI-005).

El personal ve el SLA en el listado (insignia, filtro y orden «más urgente») y en el
detalle (tarjeta con el consumo, el vencimiento y los períodos); el Solicitante no ve
nada de eso, ni siquiera puede usar el filtro o el orden. Al bajar la prioridad con el
SLA en riesgo la pantalla advierte antes de confirmar y se avisa a los Supervisores
(RN-88).

Los tests fijan «la hora» el lunes 16 de noviembre de 2026 a las 15:30, con el
calendario por defecto (lunes a viernes de 09:00 a 18:00, en Santiago). Con las
políticas de `seed-catalogs`: Alta resuelve en 6 h (aviso a las 4 h 30 min) y Media en
12 h (aviso a las 9 h 36 min).
"""

import re

import pytest
from sqlalchemy import event

from src.workdesk.extensions import db
from src.workdesk.models import (
    Grupo,
    GrupoSupervisor,
    Notificacion,
    NotificationEvent,
    PeriodoSla,
    Ticket,
)
from src.workdesk.sla import periods
from src.workdesk.tickets.assignment import set_group
from tests.sla_helpers import (
    FakeClock,
    at,
    close,
    hold,
    new_ticket,
    resolve,
    set_priority,
    work_on,
)
from tests.ticket_helpers import login, person, plain_text

LIST = "/tickets"


# --- Auxiliares -------------------------------------------------------------------------


@pytest.fixture()
def clock(app, monkeypatch):
    app.config["APP_TIMEZONE"] = "America/Santiago"
    fake = FakeClock()
    fake.set(at(16, 15, 30))
    monkeypatch.setattr(periods, "current_time", lambda: fake.now)

    return fake


@pytest.fixture()
def staff(make_user, catalog):
    return make_user("TECNICO", username="tecnico")


@pytest.fixture()
def requester(make_user, catalog):
    return make_user("SOLICITANTE", username="solicitante")


def ticket_at(clock, catalog, staff, code, created, title):
    """Crea un ticket «a las» `created` y vuelve a la hora de las comprobaciones."""
    now = clock.now
    clock.set(created)
    ticket = new_ticket(catalog, staff["id"], code, title=title)
    clock.set(now)

    return ticket


@pytest.fixture()
def board(app, clock, catalog, staff, requester):
    """Un ticket en cada estado del SLA, a las 15:30 del lunes 16, con `requester`
    como solicitante de todos."""
    with app.app_context():
        made = {
            "vencido": ticket_at(clock, catalog, staff, "ALTA", at(16, 9), "Ticket vencido"),
            "proximo": ticket_at(clock, catalog, staff, "ALTA", at(16, 10), "Ticket proximo"),
            "dentro": ticket_at(clock, catalog, staff, "MEDIA", at(16, 10), "Ticket dentro"),
        }
        paused = ticket_at(clock, catalog, staff, "CRITICA", at(16, 10), "Ticket pausado")
        clock.set(at(16, 10, 30))
        work_on(paused, staff["id"])
        clock.set(at(16, 11))
        hold(paused, staff["id"])
        clock.set(at(16, 15, 30))
        made["pausado"] = paused
        made["cerrado"] = ticket_at(clock, catalog, staff, "ALTA", at(16, 10), "Ticket cerrado")
        clock.set(at(16, 11))
        close(made["cerrado"], staff["id"])
        clock.set(at(16, 15, 30))
        db.session.execute(
            db.update(Ticket).values(creado_por_usuario_id=requester["id"]).where(
                Ticket.id.in_([t.id for t in made.values()])
            )
        )
        db.session.commit()

        return {name: ticket.public_id for name, ticket in made.items()}


def rows_of(response) -> list[str]:
    """Los números de ticket que muestra la tabla del listado, en orden."""
    html = response.get_data(as_text=True)
    table = html.split("<tbody>")[1].split("</tbody>")[0] if "<tbody>" in html else ""

    return re.findall(r"#(\d+)\s*</a>", table)


# --- El listado -------------------------------------------------------------------------


def test_the_staff_sees_the_sla_of_every_row(app, client, staff, board):
    login(client, staff)
    html = client.get(f"{LIST}?vista=todos").get_data(as_text=True)

    assert '<th scope="col">SLA</th>' in html

    for label in ("Dentro de SLA", "Próximo a vencer", "Vencido", "Pausado"):
        assert label in html

    # Alta resuelve a las 16:00: a las 15:30 quedan 30 min de tiempo laboral.
    assert "Quedan 30 min" in plain_text(client.get(f"{LIST}?vista=todos"))


def test_a_requester_sees_nothing_of_the_sla(app, client, requester, board):
    login(client, requester)
    response = client.get(f"{LIST}?vista=todos")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert '<th scope="col">SLA</th>' not in html
    assert 'id="sla"' not in html
    assert "SLA más urgente" not in html

    for text in ("Dentro de SLA", "Próximo a vencer", "Vencido", "Pausado", "Sin SLA", "Quedan"):
        assert text not in plain_text(response)


@pytest.mark.parametrize(
    ("option", "expected"),
    [
        ("vencido", ["vencido"]),
        ("proximo", ["proximo"]),
        ("dentro", ["dentro", "cerrado"]),
        ("pausado", ["pausado"]),
    ],
)
def test_the_sla_filter_selects_that_status(app, client, staff, board, option, expected):
    login(client, staff)
    response = client.get(f"{LIST}?vista=todos&sla={option}")

    assert sorted(rows_of(response)) == sorted(board[name] for name in expected)


def test_the_sla_filter_applies_to_the_tab_counters(app, client, staff, board):
    login(client, staff)
    text = plain_text(client.get(f"{LIST}?vista=todos&sla=dentro"))

    # Dentro de plazo: uno abierto y uno cerrado (con el reloj detenido).
    assert "Todos 2" in text
    assert "Abiertos 1" in text
    assert "Cerrados 1" in text


def test_an_unknown_sla_value_is_ignored_and_the_filter_is_remembered(
    app, client, staff, board
):
    login(client, staff)

    assert len(rows_of(client.get(f"{LIST}?vista=todos&sla=inventado"))) == 5

    html = client.get(f"{LIST}?vista=todos&sla=vencido").get_data(as_text=True)

    assert re.search(r'<option\s+value="vencido"\s+selected', html)
    # Las pestañas y «Limpiar filtros» conservan el filtro aplicado.
    assert "sla=vencido" in html


def test_a_requester_cannot_filter_or_sort_by_sla(app, client, requester, board):
    login(client, requester)
    plain = rows_of(client.get(f"{LIST}?vista=todos"))

    # Ni el valor del filtro ni el orden cambian nada: el parámetro no existe para él.
    assert rows_of(client.get(f"{LIST}?vista=todos&sla=vencido")) == plain
    assert rows_of(client.get(f"{LIST}?vista=todos&sla=pausado")) == plain
    assert rows_of(client.get(f"{LIST}?vista=todos&orden=sla")) == plain
    assert len(plain) == 5


def test_the_listing_service_ignores_the_sla_for_a_requester(app, requester, board):
    from src.workdesk.sla.queries import SlaFilter
    from src.workdesk.tickets.service import TicketFilters, list_tickets

    with app.app_context():
        user = person(requester["id"])
        plain = list_tickets(user, tab="todos")
        filtered = list_tickets(user, TicketFilters(sla=SlaFilter.VENCIDO), tab="todos")
        sorted_by_sla = list_tickets(user, tab="todos", sort="sla")

        # Ni el filtro ni el orden llegan a la consulta: el servicio no depende de la ruta.
        assert plain.total == filtered.total == 5
        assert [t.id for t in sorted_by_sla.items] == [t.id for t in plain.items]


def test_the_urgency_order_puts_the_nearest_due_date_first(app, client, staff, board):
    login(client, staff)
    response = client.get(f"{LIST}?vista=todos&orden=sla")

    # Vencido (15:00), próximo (16:00), dentro (martes 13:00) y, al final, los que no
    # tienen un reloj en marcha (pausado y cerrado) por antigüedad.
    assert rows_of(response) == [
        board["vencido"],
        board["proximo"],
        board["dentro"],
        board["pausado"],
        board["cerrado"],
    ]
    assert re.search(r'<option\s+value="sla"\s+selected', response.get_data(as_text=True))
    assert "SLA más urgente" in plain_text(response)


def test_a_ticket_without_a_policy_reads_as_without_sla(app, client, staff, clock, catalog):
    from tests.sla_helpers import policy_of

    with app.app_context():
        policy_of("BAJA").activo = False
        db.session.commit()
        number = new_ticket(catalog, staff["id"], "BAJA", title="Sin politica").public_id

    login(client, staff)
    response = client.get(f"{LIST}?vista=todos&sla=sin")

    assert rows_of(response) == [number]
    assert "Sin SLA" in plain_text(response)


def test_the_listing_costs_the_same_queries_with_many_tickets(
    app, client, staff, clock, catalog
):
    login(client, staff)
    statements = []

    def count(conn, cursor, statement, *args):
        statements.append(statement)

    def measure():
        statements.clear()
        client.get(f"{LIST}?vista=todos&sla=dentro")

        return len(statements)

    with app.app_context():
        new_ticket(catalog, staff["id"], "MEDIA")
        event.listen(db.engine, "before_cursor_execute", count)

        try:
            one = measure()

            for _ in range(14):
                new_ticket(catalog, staff["id"], "MEDIA")

            many = measure()
        finally:
            event.remove(db.engine, "before_cursor_execute", count)

    # Una fila o quince: las mismas consultas (el SLA de la página sale por lotes).
    assert many == one


# --- El detalle -------------------------------------------------------------------------


def test_the_detail_shows_the_sla_card_to_the_staff(app, client, staff, board):
    login(client, staff)
    response = client.get(f"/tickets/{board['proximo']}")
    text = plain_text(response)

    assert 'aria-labelledby="sla-title"' in response.get_data(as_text=True)
    assert "Próximo a vencer" in text
    # 5 h 30 min de las 6 h de Alta (desde las 10:00): el 91 %.
    assert "5 h 30 min de 6 h (91 %)" in text
    assert "Vence 16-11-2026 16:00" in text
    assert "Períodos (1)" in text


def test_the_detail_card_for_an_overdue_ticket_says_by_how_much(app, client, staff, board):
    login(client, staff)
    text = plain_text(client.get(f"/tickets/{board['vencido']}"))

    # Venció a las 15:00 y son las 15:30.
    assert "Vencido" in text
    assert "Excedido en 30 min" in text


def test_the_detail_card_for_a_paused_and_a_stopped_ticket(app, client, staff, board):
    login(client, staff)

    assert "En pausa" in plain_text(client.get(f"/tickets/{board['pausado']}"))
    assert "Detenido: el ticket está resuelto o cerrado." in plain_text(
        client.get(f"/tickets/{board['cerrado']}")
    )


def test_the_detail_says_so_when_the_ticket_has_no_sla(app, client, staff, clock, catalog):
    from tests.sla_helpers import policy_of

    with app.app_context():
        policy_of("BAJA").activo = False
        db.session.commit()
        number = new_ticket(catalog, staff["id"], "BAJA").public_id

    login(client, staff)

    assert "Este ticket no tiene SLA" in plain_text(client.get(f"/tickets/{number}"))


def test_the_detail_lists_the_periods_with_the_reason_of_a_change(
    app, client, staff, clock, catalog
):
    with app.app_context():
        ticket = ticket_at(clock, catalog, staff, "MEDIA", at(16, 10), "Con cambios")
        set_priority(ticket, staff["id"], "ALTA", reason="Afecta a toda la sucursal")
        number = ticket.public_id

    login(client, staff)
    text = plain_text(client.get(f"/tickets/{number}"))

    assert "Períodos (2)" in text
    assert "Afecta a toda la sucursal" in text


def test_a_requester_never_receives_the_sla_in_the_detail(app, client, requester, board):
    login(client, requester)
    response = client.get(f"/tickets/{board['vencido']}")
    text = plain_text(response)

    assert response.status_code == 200
    assert "sla-title" not in response.get_data(as_text=True)

    for fragment in ("SLA", "Excedido", "Períodos", "Vence", "Primera respuesta"):
        assert fragment not in text


# --- La advertencia al bajar la prioridad --------------------------------------------------


def test_the_priority_screen_warns_when_the_sla_is_at_risk(app, client, staff, board):
    login(client, staff)

    for name, word in (("proximo", "próximo a vencer"), ("vencido", "vencido")):
        response = client.get(f"/tickets/{board[name]}/priority")
        html = response.get_data(as_text=True)

        assert "data-sla-warning" in html
        assert word in plain_text(response)
        assert "se avisará a los supervisores" in plain_text(response).lower()


@pytest.mark.parametrize("name", ["dentro", "pausado"])
def test_the_priority_screen_does_not_warn_when_the_sla_is_fine(
    app, client, staff, board, name
):
    login(client, staff)

    assert "data-sla-warning" not in client.get(
        f"/tickets/{board[name]}/priority"
    ).get_data(as_text=True)


def test_a_requester_cannot_open_the_priority_screen(app, client, requester, board):
    login(client, requester)

    assert client.get(f"/tickets/{board['proximo']}/priority").status_code == 403


# --- El aviso a los Supervisores (RN-88) -----------------------------------------------------


@pytest.fixture()
def supervisors(make_user, catalog):
    return {
        "in_group": make_user("SUPERVISOR", username="sup_grupo", nombre="Nora", apellido="Vega"),
        "other": make_user("SUPERVISOR", username="sup_otro", nombre="Hugo", apellido="Paz"),
        "inactive": make_user("SUPERVISOR", username="sup_inactivo", activo=False),
    }


def inbox(app, user_id):
    with app.app_context():
        return [
            (n.tipo_evento, n.mensaje)
            for n in db.session.scalars(
                db.select(Notificacion)
                .where(Notificacion.usuario_id == user_id)
                .order_by(Notificacion.id)
            )
        ]


def put_in_group(supervisors_in_group, ticket, actor):
    group = Grupo(nombre="Soporte Redes")
    db.session.add(group)
    db.session.flush()

    for supervisor in supervisors_in_group:
        db.session.add(GrupoSupervisor(grupo_id=group.id, supervisor_id=supervisor["id"]))

    db.session.commit()
    set_group(ticket, group.id, actor=person(actor["id"]), expected_version=ticket.version)
    db.session.commit()


def test_lowering_the_priority_with_the_sla_at_risk_notifies_the_group_supervisors(
    app, clock, staff, supervisors, catalog
):
    with app.app_context():
        ticket = ticket_at(clock, catalog, staff, "ALTA", at(16, 10), "Se baja")
        put_in_group([supervisors["in_group"]], ticket, staff)
        set_priority(ticket, staff["id"], "MEDIA", reason="Ya no es urgente")

    ((kind, message),) = inbox(app, supervisors["in_group"]["id"])

    assert kind == NotificationEvent.SLA_PRIORIDAD_BAJADA
    assert "Alta" in message
    assert "Media" in message
    assert "próximo a vencer" in message
    assert "Ya no es urgente" not in message
    # Los demás Supervisores y el técnico que lo hizo no reciben nada.
    assert inbox(app, supervisors["other"]["id"]) == []
    assert inbox(app, staff["id"]) == []


def test_without_a_group_every_active_supervisor_is_notified(
    app, clock, staff, supervisors, catalog
):
    with app.app_context():
        ticket = ticket_at(clock, catalog, staff, "ALTA", at(16, 9), "Sin grupo")
        set_priority(ticket, staff["id"], "MEDIA")

    for name in ("in_group", "other"):
        ((kind, message),) = inbox(app, supervisors[name]["id"])

        assert kind == NotificationEvent.SLA_PRIORIDAD_BAJADA
        assert "vencido" in message

    # Un Supervisor inactivo no recibe nada.
    assert inbox(app, supervisors["inactive"]["id"]) == []


def test_a_group_without_an_active_supervisor_falls_back_to_all_of_them(
    app, clock, staff, supervisors, catalog
):
    with app.app_context():
        ticket = ticket_at(clock, catalog, staff, "ALTA", at(16, 10), "Grupo sin responsable")
        put_in_group([supervisors["inactive"]], ticket, staff)
        set_priority(ticket, staff["id"], "MEDIA")

    assert len(inbox(app, supervisors["in_group"]["id"])) == 1
    assert len(inbox(app, supervisors["other"]["id"])) == 1


def test_the_supervisor_who_lowers_the_priority_is_not_notified_of_it(
    app, clock, staff, supervisors, catalog
):
    with app.app_context():
        ticket = ticket_at(clock, catalog, staff, "ALTA", at(16, 10), "Lo baja un supervisor")
        set_priority(ticket, supervisors["in_group"]["id"], "MEDIA")

    assert inbox(app, supervisors["in_group"]["id"]) == []
    assert len(inbox(app, supervisors["other"]["id"])) == 1


@pytest.mark.parametrize(
    ("code", "created", "new_code"),
    [
        # Subir la prioridad no avisa.
        ("MEDIA", at(16, 10), "ALTA"),
        # Dentro de plazo: bajar no es un riesgo.
        ("ALTA", at(16, 15), "MEDIA"),
    ],
)
def test_other_priority_changes_notify_nobody(
    app, clock, staff, supervisors, catalog, code, created, new_code
):
    with app.app_context():
        ticket = ticket_at(clock, catalog, staff, code, created, "Cambio normal")
        set_priority(ticket, staff["id"], new_code)

    for name in ("in_group", "other"):
        assert inbox(app, supervisors[name]["id"]) == []


def test_raising_the_priority_with_the_sla_at_risk_notifies_nobody(
    app, clock, staff, supervisors, catalog
):
    with app.app_context():
        # Vencido (Alta resuelve a las 15:00) y sube a Crítica: no es bajar.
        ticket = ticket_at(clock, catalog, staff, "ALTA", at(16, 9), "Sube con SLA vencido")
        set_priority(ticket, staff["id"], "CRITICA")

    for name in ("in_group", "other"):
        assert inbox(app, supervisors[name]["id"]) == []


def test_lowering_the_priority_of_a_ticket_without_sla_notifies_nobody(
    app, clock, staff, supervisors, catalog
):
    from tests.sla_helpers import policy_of

    with app.app_context():
        policy_of("ALTA").activo = False
        db.session.commit()
        ticket = ticket_at(clock, catalog, staff, "ALTA", at(16, 9), "Sin SLA")
        set_priority(ticket, staff["id"], "MEDIA")

    assert inbox(app, supervisors["in_group"]["id"]) == []


def test_a_priority_change_from_the_screen_notifies_the_supervisors(
    app, client, clock, staff, supervisors, catalog
):
    with app.app_context():
        ticket = ticket_at(clock, catalog, staff, "ALTA", at(16, 9), "Desde la pantalla")
        number, version = ticket.public_id, ticket.version
        from tests.sla_helpers import priority_id

        new_priority = priority_id("MEDIA")

    login(client, staff)
    response = client.post(
        f"/tickets/{number}/priority",
        data={"version": version, "prioridad": new_priority, "motivo": "Se acordó con el usuario"},
    )

    assert response.status_code == 302
    assert len(inbox(app, supervisors["in_group"]["id"])) == 1


def test_the_supervisor_notice_rolls_back_with_the_change(
    app, clock, staff, supervisors, catalog
):
    from src.workdesk.tickets.editing import change_priority
    from tests.sla_helpers import priority_id

    with app.app_context():
        ticket = ticket_at(clock, catalog, staff, "ALTA", at(16, 10), "Se revierte")
        change_priority(
            ticket,
            actor=person(staff["id"]),
            expected_version=ticket.version,
            priority_id=priority_id("MEDIA"),
            reason="Prueba",
        )
        db.session.rollback()

    assert inbox(app, supervisors["in_group"]["id"]) == []


# --- Los comandos y la carga de demostración -----------------------------------------------


def test_sla_rebuild_completes_the_missing_warning_dates(app, clock, staff, catalog):
    with app.app_context():
        ticket = new_ticket(catalog, staff["id"], "MEDIA")
        period = db.session.scalar(db.select(PeriodoSla).where(PeriodoSla.ticket_id == ticket.id))
        original = period.fecha_umbral_aviso
        period.fecha_umbral_aviso = None
        db.session.commit()
        period_id = period.id

    result = app.test_cli_runner().invoke(args=["sla-rebuild"])

    assert result.exit_code == 0
    assert "Fechas de aviso completadas: 1." in result.output

    with app.app_context():
        assert db.session.get(PeriodoSla, period_id).fecha_umbral_aviso == original

    assert "Fechas de aviso completadas: 0." in (
        app.test_cli_runner().invoke(args=["sla-rebuild"]).output
    )


def test_sla_status_shows_the_warning_date(app, clock, staff, catalog):
    with app.app_context():
        clock.set(at(16, 10))
        number = new_ticket(catalog, staff["id"], "MEDIA").public_id

    output = app.test_cli_runner().invoke(args=["sla-status", number]).output

    assert "Aviso al 80 %: 17-11-2026 10:36" in output


def test_a_stopped_ticket_keeps_its_last_period_for_the_card(app, client, staff, clock, catalog):
    with app.app_context():
        ticket = ticket_at(clock, catalog, staff, "ALTA", at(16, 10), "Resuelto")
        clock.set(at(16, 11))
        resolve(ticket, staff["id"])
        number = ticket.public_id

    login(client, staff)

    assert "Períodos (1)" in plain_text(client.get(f"/tickets/{number}"))
