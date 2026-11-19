"""Solicitantes de un ticket tras crearlo (docs/06, RN-158).

Cubre el servicio (`tickets/requesters.py`), el historial que genera, quién
ve el ticket cuando cambian los solicitantes y las pantallas.
"""

import threading

import pytest

from src.workdesk.extensions import db
from src.workdesk.models import (
    HistoryVisibility,
    Ticket,
    TicketEvent,
    TicketHistory,
    TicketRequester,
    User,
)
from src.workdesk.models.ticket_history import (
    DEFAULT_EVENT_VISIBILITY,
    TICKET_EVENT_LABELS,
)
from src.workdesk.security import can_view_ticket
from src.workdesk.tickets.editing import describe_history_changes, update_ticket
from src.workdesk.tickets.requesters import (
    add_requester,
    list_addable_requesters,
    remove_requester,
)
from src.workdesk.tickets.service import (
    TAB_ALL,
    TicketFilters,
    TicketRuleError,
    list_ticket_history,
    list_tickets,
)
from src.workdesk.tickets.versioning import TicketClosedError
from tests.ticket_helpers import login, make_ticket, plain_text, set_state

STAFF = ("tec", "sup", "admin")


# --- Ayudas -----------------------------------------------------------


@pytest.fixture()
def team(make_user, catalog):
    """Tres Solicitantes y una persona de cada rol del personal."""
    return {
        "req": make_user("SOLICITANTE", username="req1", nombre="Javiera", apellido="Torres"),
        "other": make_user("SOLICITANTE", username="req2", nombre="Paula", apellido="Contreras"),
        "third": make_user("SOLICITANTE", username="req3", nombre="Matías", apellido="Fuentes"),
        "tec": make_user("TECNICO", username="tec1", nombre="Diego", apellido="Soto"),
        "sup": make_user("SUPERVISOR", username="sup1", nombre="Camila", apellido="Rojas"),
        "admin": make_user("ADMINISTRADOR", username="admin1", nombre="Ana", apellido="Admin"),
    }


def user(team, key) -> User:
    return db.session.get(User, team[key]["id"])


def get_ticket(public_id) -> Ticket:
    return db.session.scalar(
        db.select(Ticket).where(Ticket.public_id == public_id)
    )


def staff_ticket(app, catalog, team, requesters=("req",), **kwargs):
    """Ticket creado por el Técnico, con los solicitantes indicados."""
    return make_ticket(
        app,
        catalog,
        team["tec"]["id"],
        requester_ids=[team[key]["id"] for key in requesters],
        **kwargs,
    )


def own_ticket(app, catalog, team):
    """Ticket que crea el propio Solicitante `req` (queda como su solicitante)."""
    return make_ticket(
        app,
        catalog,
        team["req"]["id"],
        requester_ids=[team["req"]["id"]],
    )


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


def current_ids(public_id) -> list[int]:
    """Ids de los usuarios que son solicitantes vigentes del ticket."""
    return [r.solicitante_id for r in get_ticket(public_id).solicitantes_vigentes]


def link_of(public_id, team, who) -> TicketRequester:
    """Participación vigente de la persona en el ticket."""
    return next(
        r
        for r in get_ticket(public_id).solicitantes_vigentes
        if r.solicitante_id == team[who]["id"]
    )


def add(public_id, team, who="other", actor="sup") -> TicketRequester:
    link = add_requester(
        get_ticket(public_id),
        team[who]["id"],
        actor=user(team, actor),
    )
    db.session.commit()

    return link


def remove(public_id, participation_id, team, actor="sup", reason=None):
    remove_requester(
        get_ticket(public_id),
        participation_id,
        actor=user(team, actor),
        reason=reason,
    )
    db.session.commit()


# --- Vocabulario ------------------------------------------------------


def test_the_requester_events_are_internal_and_have_a_name():
    for event in (
        TicketEvent.SOLICITANTE_AGREGADO,
        TicketEvent.SOLICITANTE_RETIRADO,
    ):
        assert DEFAULT_EVENT_VISIBILITY[event] is HistoryVisibility.INTERNO
        assert TICKET_EVENT_LABELS[event]


# --- Servicio: agregar ------------------------------------------------


def test_adding_a_requester_associates_them_and_records_an_internal_event(
    app,
    catalog,
    team,
):
    public_id = staff_ticket(app, catalog, team)

    with app.app_context():
        link = add(public_id, team)
        ticket = get_ticket(public_id)

        assert link.fecha_retiro is None
        assert link.asociado_por_usuario_id == team["sup"]["id"]
        assert current_ids(public_id) == [team["req"]["id"], team["other"]["id"]]

        # Es aditivo: no sube la versión ni cuenta como una modificación.
        assert ticket.version == 1
        assert ticket.fecha_modificacion is None
        assert ticket.usuario_modificacion_id is None

        (event,) = events(ticket.id, TicketEvent.SOLICITANTE_AGREGADO)

        assert event.visibilidad == "INTERNO"
        assert event.actor_usuario_id == team["sup"]["id"]
        assert event.detalle == "Solicitante agregado: Paula Contreras."
        assert event.valor_anterior is None
        assert event.valor_nuevo == {
            "usuario_id": team["other"]["id"],
            "username": "req2",
            "nombre": "Paula Contreras",
        }
        assert event.contexto == {"participacion_id": link.id}


def test_staff_of_every_role_can_add_a_requester_to_a_ticket_without_any(
    app,
    catalog,
    team,
):
    for key in STAFF:
        public_id = staff_ticket(app, catalog, team, requesters=())

        with app.app_context():
            assert current_ids(public_id) == []

            add(public_id, team, "other", actor=key)

            assert current_ids(public_id) == [team["other"]["id"]]


@pytest.mark.parametrize("who", ["tec", "sup", "admin"])
def test_only_users_with_the_requester_role_can_be_added(
    app,
    catalog,
    team,
    who,
):
    public_id = staff_ticket(app, catalog, team)

    with app.app_context(), pytest.raises(TicketRuleError, match="rol Solicitante"):
        add(public_id, team, who)

    with app.app_context():
        assert current_ids(public_id) == [team["req"]["id"]]
        assert events(get_ticket(public_id).id, TicketEvent.SOLICITANTE_AGREGADO) == []


def test_an_inactive_or_unknown_user_cannot_be_added(app, catalog, team, make_user):
    inactive = make_user("SOLICITANTE", username="req_off", activo=False)
    public_id = staff_ticket(app, catalog, team)

    for requester_id in (inactive["id"], 999_999):
        with app.app_context(), pytest.raises(TicketRuleError, match="rol Solicitante"):
            add_requester(
                get_ticket(public_id),
                requester_id,
                actor=user(team, "sup"),
            )

    with app.app_context():
        assert current_ids(public_id) == [team["req"]["id"]]


def test_a_requester_cannot_be_added_twice(app, catalog, team):
    public_id = staff_ticket(app, catalog, team)

    with app.app_context():
        add(public_id, team, "other")

        # `req` ya lo era desde que se creó el ticket.
        for who in ("other", "req"):
            with pytest.raises(TicketRuleError, match="ya es solicitante"):
                add(public_id, team, who)

            db.session.rollback()

        assert current_ids(public_id) == [team["req"]["id"], team["other"]["id"]]
        assert len(events(get_ticket(public_id).id, TicketEvent.SOLICITANTE_AGREGADO)) == 1


def test_a_closed_ticket_cannot_have_its_requesters_changed(app, catalog, team):
    public_id = staff_ticket(app, catalog, team)

    with app.app_context():
        link_id = link_of(public_id, team, "req").id

    set_state(app, public_id, "CERRADO")

    with app.app_context():
        with pytest.raises(TicketClosedError, match="reabrir"):
            add(public_id, team, "other")

        db.session.rollback()

        with pytest.raises(TicketClosedError, match="reabrir"):
            remove(public_id, link_id, team)

        db.session.rollback()

        assert current_ids(public_id) == [team["req"]["id"]]


def test_an_inactive_actor_cannot_change_requesters(app, catalog, team, make_user):
    inactive = make_user("SUPERVISOR", username="sup_off", activo=False)
    public_id = staff_ticket(app, catalog, team)

    with app.app_context():
        actor = db.session.get(User, inactive["id"])
        ticket = get_ticket(public_id)
        link_id = link_of(public_id, team, "req").id

        with pytest.raises(TicketRuleError, match="no está activo"):
            add_requester(ticket, team["other"]["id"], actor=actor)

        with pytest.raises(TicketRuleError, match="no está activo"):
            remove_requester(ticket, link_id, actor=actor)


def test_changing_requesters_does_not_commit(app, catalog, team):
    public_id = staff_ticket(app, catalog, team)

    with app.app_context():
        link_id = link_of(public_id, team, "req").id

        add_requester(get_ticket(public_id), team["other"]["id"], actor=user(team, "sup"))
        remove_requester(get_ticket(public_id), link_id, actor=user(team, "sup"))
        db.session.rollback()

        assert current_ids(public_id) == [team["req"]["id"]]
        assert (
            events(
                get_ticket(public_id).id,
                TicketEvent.SOLICITANTE_AGREGADO,
                TicketEvent.SOLICITANTE_RETIRADO,
            )
            == []
        )


def test_adding_and_removing_in_one_transaction_respects_the_dates_constraint(
    app,
    catalog,
    team,
):
    # Las dos horas son `now()` de la misma transacción: la restricción
    # `fecha_retiro >= fecha_asociacion` debe admitir que sean iguales.
    public_id = staff_ticket(app, catalog, team)

    with app.app_context():
        actor = user(team, "sup")
        link = add_requester(get_ticket(public_id), team["other"]["id"], actor=actor)
        remove_requester(get_ticket(public_id), link.id, actor=actor)
        db.session.commit()

        row = db.session.get(TicketRequester, link.id)

        assert row.fecha_retiro >= row.fecha_asociacion


def test_changing_requesters_does_not_conflict_with_an_open_edit(app, catalog, team):
    # Como no sube la versión, quien abrió la edición antes de que se agregara
    # un solicitante puede guardar sin ver un conflicto.
    public_id = staff_ticket(app, catalog, team)

    with app.app_context():
        opened_with = get_ticket(public_id).version

        add(public_id, team, "other")
        ticket = get_ticket(public_id)

        changed = update_ticket(
            ticket,
            actor=user(team, "tec"),
            expected_version=opened_with,
            title="Otro título",
            description=ticket.descripcion,
            category_id=ticket.categoria_id,
            location_id=None,
        )

        assert changed is True


def test_addable_requesters_exclude_current_ones_and_other_roles(
    app,
    catalog,
    team,
    make_user,
):
    make_user("SOLICITANTE", username="req_off", activo=False)
    public_id = staff_ticket(app, catalog, team)

    def addable():
        return [u.username for u in list_addable_requesters(get_ticket(public_id))]

    with app.app_context():
        # Por apellido y nombre; el personal y los inactivos no aparecen.
        assert addable() == ["req2", "req3"]

        add(public_id, team, "other")

        assert addable() == ["req3"]

        remove(public_id, link_of(public_id, team, "req").id, team)

        assert addable() == ["req3", "req1"]


# --- Servicio: retirar ------------------------------------------------


def test_removing_closes_the_participation_and_keeps_it(app, catalog, team):
    public_id = staff_ticket(app, catalog, team)

    with app.app_context():
        link_id = link_of(public_id, team, "req").id

        remove(public_id, link_id, team, reason="  Ya no depende de esta persona  ")

        ticket = get_ticket(public_id)
        row = db.session.get(TicketRequester, link_id)

        assert row.fecha_retiro is not None
        assert row.retirado_por_usuario_id == team["sup"]["id"]
        assert ticket.solicitantes_vigentes == []
        # La participación se conserva como historial.
        assert [r.id for r in ticket.solicitantes] == [link_id]
        assert ticket.version == 1

        (event,) = events(ticket.id, TicketEvent.SOLICITANTE_RETIRADO)

        assert event.visibilidad == "INTERNO"
        assert event.detalle == "Solicitante retirado: Javiera Torres."
        assert event.valor_anterior == {
            "usuario_id": team["req"]["id"],
            "username": "req1",
            "nombre": "Javiera Torres",
        }
        assert event.valor_nuevo is None
        assert event.contexto == {
            "participacion_id": link_id,
            "motivo": "Ya no depende de esta persona",
        }


def test_removing_without_a_reason_records_none(app, catalog, team):
    public_id = staff_ticket(app, catalog, team)

    with app.app_context():
        link_id = link_of(public_id, team, "req").id

        remove(public_id, link_id, team, reason="   ")

        (event,) = events(get_ticket(public_id).id, TicketEvent.SOLICITANTE_RETIRADO)

        assert event.contexto == {"participacion_id": link_id}


def test_a_ticket_can_be_left_without_requesters(app, catalog, team):
    public_id = staff_ticket(app, catalog, team)

    with app.app_context():
        remove(public_id, link_of(public_id, team, "req").id, team)

        ticket = get_ticket(public_id)

        assert ticket.solicitantes_vigentes == []
        assert ticket.estado.codigo == "NUEVO"


def test_a_removed_requester_can_be_added_again_as_a_new_row(app, catalog, team):
    public_id = staff_ticket(app, catalog, team)

    with app.app_context():
        first = link_of(public_id, team, "req").id

        remove(public_id, first, team)
        again = add(public_id, team, "req")
        ticket = get_ticket(public_id)

        assert again.id != first
        assert [r.id for r in ticket.solicitantes_vigentes] == [again.id]
        assert len(ticket.solicitantes) == 2
        assert db.session.get(TicketRequester, first).fecha_retiro is not None
        assert len(events(ticket.id, TicketEvent.SOLICITANTE_AGREGADO)) == 1
        assert len(events(ticket.id, TicketEvent.SOLICITANTE_RETIRADO)) == 1


def test_remove_rejects_unknown_foreign_or_already_removed_participations(
    app,
    catalog,
    team,
):
    public_id = staff_ticket(app, catalog, team)
    other_ticket = staff_ticket(app, catalog, team, requesters=("other",))

    with app.app_context():
        mine = link_of(public_id, team, "req").id
        foreign = link_of(other_ticket, team, "other").id

        remove(public_id, mine, team)

        # Inexistente, de otro ticket y ya retirada.
        for participation_id in (999_999, foreign, mine):
            with pytest.raises(TicketRuleError, match="ya no es solicitante"):
                remove(public_id, participation_id, team)

            db.session.rollback()

        assert current_ids(other_ticket) == [team["other"]["id"]]


def test_remove_rejects_a_long_reason(app, catalog, team):
    public_id = staff_ticket(app, catalog, team)

    with app.app_context():
        link_id = link_of(public_id, team, "req").id

        with pytest.raises(TicketRuleError, match="500 caracteres"):
            remove(public_id, link_id, team, reason="x" * 501)

        db.session.rollback()

        assert current_ids(public_id) == [team["req"]["id"]]

        # Exactamente 500 es válido.
        remove(public_id, link_id, team, reason="x" * 500)

        assert current_ids(public_id) == []


# --- Concurrencia -----------------------------------------------------


def _run_in_threads(app, tasks):
    barrier = threading.Barrier(len(tasks))
    outcomes = []

    def run(task):
        with app.app_context():
            barrier.wait(timeout=10)

            try:
                task()
                db.session.commit()
                outcomes.append("ok")
            except TicketRuleError as error:
                db.session.rollback()
                outcomes.append(str(error))
            finally:
                db.session.remove()

    threads = [threading.Thread(target=run, args=(task,)) for task in tasks]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join(timeout=30)

    return outcomes


def test_two_simultaneous_additions_of_the_same_requester(app, catalog, team):
    public_id = staff_ticket(app, catalog, team)

    def attempt(actor):
        def task():
            add_requester(
                get_ticket(public_id),
                team["other"]["id"],
                actor=user(team, actor),
            )

        return task

    outcomes = _run_in_threads(app, [attempt("sup"), attempt("tec")])

    assert sorted(outcomes) == ["Esa persona ya es solicitante del ticket.", "ok"]

    with app.app_context():
        assert current_ids(public_id).count(team["other"]["id"]) == 1
        assert len(events(get_ticket(public_id).id, TicketEvent.SOLICITANTE_AGREGADO)) == 1


def test_two_simultaneous_removals_of_the_same_participation(app, catalog, team):
    public_id = staff_ticket(app, catalog, team)

    with app.app_context():
        link_id = link_of(public_id, team, "req").id

    def attempt(actor):
        def task():
            remove_requester(
                get_ticket(public_id),
                link_id,
                actor=user(team, actor),
            )

        return task

    outcomes = _run_in_threads(app, [attempt("sup"), attempt("tec")])

    assert sorted(outcomes) == ["Esa persona ya no es solicitante del ticket.", "ok"]

    with app.app_context():
        assert current_ids(public_id) == []
        assert len(events(get_ticket(public_id).id, TicketEvent.SOLICITANTE_RETIRADO)) == 1


# --- Quién ve el ticket -----------------------------------------------


def test_an_added_requester_sees_the_ticket_and_a_removed_one_does_not(
    client,
    app,
    catalog,
    team,
):
    public_id = staff_ticket(app, catalog, team)
    link = f'href="/tickets/{public_id}"'

    login(client, team["other"])

    assert client.get(f"/tickets/{public_id}").status_code == 404
    assert link not in client.get("/tickets?vista=todos").get_data(as_text=True)

    with app.app_context():
        link_id = add(public_id, team, "other").id

    page = client.get(f"/tickets/{public_id}")

    assert page.status_code == 200
    # Ve el historial público completo, también lo anterior a su incorporación.
    assert "Ticket creado" in plain_text(page)
    assert link in client.get("/tickets?vista=todos").get_data(as_text=True)

    with app.app_context():
        remove(public_id, link_id, team)

    assert client.get(f"/tickets/{public_id}").status_code == 404
    assert link not in client.get("/tickets?vista=todos").get_data(as_text=True)


def test_the_creator_keeps_access_after_being_removed_as_requester(
    client,
    app,
    catalog,
    team,
):
    public_id = own_ticket(app, catalog, team)

    with app.app_context():
        remove(public_id, link_of(public_id, team, "req").id, team)

    login(client, team["req"])

    assert client.get(f"/tickets/{public_id}").status_code == 200
    assert f'href="/tickets/{public_id}"' in client.get(
        "/tickets?vista=todos"
    ).get_data(as_text=True)

    client.post("/logout")
    login(client, team["tec"])

    assert "Sin solicitante" in plain_text(client.get(f"/tickets/{public_id}"))


def test_the_sql_visibility_matches_the_policy_after_requesters_change(
    app,
    catalog,
    team,
):
    """Agregar, retirar y volver a agregar: el listado (SQL) y el detalle
    (Python) deben decidir siempre igual."""
    own = own_ticket(app, catalog, team)
    shared = staff_ticket(app, catalog, team, requesters=("req", "other"))

    with app.app_context():
        # El creador deja de ser solicitante; otra persona se retira; una
        # tercera se agrega y la retirada vuelve.
        remove(own, link_of(own, team, "req").id, team)
        remove(shared, link_of(shared, team, "other").id, team)
        add(shared, team, "third")
        add(shared, team, "other")

        tickets = list(db.session.scalars(db.select(Ticket)))

        def listed(key):
            return {
                t.public_id
                for t in list_tickets(user(team, key), tab=TAB_ALL).items
            }

        for key in team:
            person = user(team, key)
            visible = listed(key)

            for ticket in tickets:
                assert (ticket.public_id in visible) is can_view_ticket(
                    person, ticket
                ), (key, ticket.public_id)

        # Y el resultado concreto, para que la comparación no sea vacía.
        assert listed("req") == {own, shared}
        assert listed("other") == {shared}
        assert listed("third") == {shared}
        assert listed("tec") == {own, shared}


def test_staff_search_by_requester_follows_additions_and_removals(
    app,
    catalog,
    team,
):
    public_id = staff_ticket(app, catalog, team)

    def found():
        page = list_tickets(
            user(team, "tec"),
            TicketFilters(query_text="Contreras"),
            tab=TAB_ALL,
        )

        return [t.public_id for t in page.items]

    with app.app_context():
        assert found() == []

        link_id = add(public_id, team, "other").id

        assert found() == [public_id]

        remove(public_id, link_id, team)

        assert found() == []


# --- Historial: lo ve solo el personal --------------------------------


def test_a_requester_never_sees_the_requester_events_or_other_requesters(
    client,
    app,
    catalog,
    team,
):
    public_id = staff_ticket(app, catalog, team)

    with app.app_context():
        link_id = add(public_id, team, "other").id
        remove(public_id, link_id, team, reason="Se equivocó de ticket")

    login(client, team["req"])
    page = plain_text(client.get(f"/tickets/{public_id}"))

    assert "Ticket creado" in page
    assert "Solicitante agregado" not in page
    assert "Solicitante retirado" not in page
    assert "Paula Contreras" not in page
    assert "Se equivocó de ticket" not in page

    # El filtro lo aplica la consulta, no la plantilla.
    with app.app_context():
        shown = list_ticket_history(get_ticket(public_id), user(team, "req"))

        assert {e.tipo_evento for e in shown} == {"TICKET_CREADO"}


def test_staff_sees_the_requester_events_with_their_reason(
    client,
    app,
    catalog,
    team,
):
    public_id = staff_ticket(app, catalog, team)

    with app.app_context():
        link_id = add(public_id, team, "other").id
        remove(public_id, link_id, team, reason="Se equivocó de ticket")

    login(client, team["tec"])
    page = plain_text(client.get(f"/tickets/{public_id}"))

    assert "Solicitante agregado: «Paula Contreras»" in page
    assert "Solicitante retirado: «Paula Contreras»" in page
    assert "Motivo: Se equivocó de ticket" in page


def test_the_history_lines_describe_requester_events(app, catalog, team):
    public_id = staff_ticket(app, catalog, team)

    with app.app_context():
        link_id = add(public_id, team, "other").id
        remove(public_id, link_id, team, reason="Error")

        lines = {
            e.tipo_evento: describe_history_changes(e)
            for e in events(
                get_ticket(public_id).id,
                TicketEvent.SOLICITANTE_AGREGADO,
                TicketEvent.SOLICITANTE_RETIRADO,
            )
        }

    # El motivo nunca va en las líneas: quién lo ve lo decide la ruta.
    assert lines["SOLICITANTE_AGREGADO"] == ["Solicitante agregado: «Paula Contreras»"]
    assert lines["SOLICITANTE_RETIRADO"] == ["Solicitante retirado: «Paula Contreras»"]


# --- Pantallas: acceso ------------------------------------------------


def test_a_requester_cannot_use_the_requester_screens(client, app, catalog, team):
    public_id = staff_ticket(app, catalog, team)

    with app.app_context():
        link_id = link_of(public_id, team, "req").id

    # `req` ve el ticket (es solicitante), pero no puede gestionarlos: 403.
    login(client, team["req"])
    base = f"/tickets/{public_id}/requesters"

    assert client.get(base).status_code == 403
    assert (
        client.post(
            f"{base}/add",
            data={"solicitante": team["other"]["id"]},
        ).status_code
        == 403
    )
    assert client.get(f"{base}/{link_id}/remove").status_code == 403
    assert client.post(f"{base}/{link_id}/remove", data={"motivo": "x"}).status_code == 403

    with app.app_context():
        assert current_ids(public_id) == [team["req"]["id"]]


def test_unseen_tickets_are_404_on_every_requester_route(client, app, catalog, team):
    public_id = staff_ticket(app, catalog, team)
    login(client, team["other"])
    base = f"/tickets/{public_id}/requesters"

    for method, path in (
        ("get", ""),
        ("post", "/add"),
        ("get", "/1/remove"),
        ("post", "/1/remove"),
    ):
        assert getattr(client, method)(base + path).status_code == 404, path


def test_nonexistent_tickets_are_404_on_every_requester_route(client, team):
    login(client, team["sup"])

    for public_id in ("999999", "abc"):
        for method, path in (
            ("get", ""),
            ("post", "/add"),
            ("get", "/1/remove"),
            ("post", "/1/remove"),
        ):
            url = f"/tickets/{public_id}/requesters{path}"

            assert getattr(client, method)(url).status_code == 404, url


# --- Pantallas: gestionar ---------------------------------------------


@pytest.mark.parametrize("key", STAFF)
def test_staff_open_the_requesters_screen(client, app, catalog, team, key):
    public_id = staff_ticket(app, catalog, team)
    login(client, team[key])

    page = plain_text(client.get(f"/tickets/{public_id}/requesters"))

    assert "Solicitantes actuales" in page
    assert "Javiera Torres (req1)" in page
    # El creador original se muestra y no cambia.
    assert "Diego Soto" in page
    # Quien ya es solicitante no se ofrece para agregar; las demás personas
    # con el rol Solicitante, sí; el personal, nunca.
    assert "Torres, Javiera (req1)" not in page
    assert "Contreras, Paula (req2)" in page
    assert "Fuentes, Matías (req3)" in page
    assert "Soto, Diego" not in page


def test_an_inactive_requester_is_marked_and_can_still_be_removed(
    client,
    app,
    catalog,
    team,
):
    public_id = staff_ticket(app, catalog, team)

    with app.app_context():
        link_id = link_of(public_id, team, "req").id
        user(team, "req").activo = False
        db.session.commit()

    login(client, team["sup"])
    page = plain_text(client.get(f"/tickets/{public_id}/requesters"))

    # Sigue siendo solicitante vigente y se marca; no se ofrece para agregar.
    assert "Javiera Torres (req1) (inactivo)" in page

    response = client.post(
        f"/tickets/{public_id}/requesters/{link_id}/remove",
        data={},
        follow_redirects=True,
    )

    assert "Javiera Torres dejó de ser solicitante del ticket." in plain_text(response)

    with app.app_context():
        assert current_ids(public_id) == []


def test_the_screen_says_so_when_there_are_no_requesters_or_nobody_to_add(
    client,
    app,
    catalog,
    team,
):
    empty = staff_ticket(app, catalog, team, requesters=())
    full = staff_ticket(app, catalog, team, requesters=("req", "other", "third"))
    login(client, team["sup"])

    page = plain_text(client.get(f"/tickets/{empty}/requesters"))

    assert "Este ticket no tiene solicitantes." in page

    page = plain_text(client.get(f"/tickets/{full}/requesters"))

    assert "No hay más personas con el rol Solicitante para agregar." in page
    assert "Selecciona a una persona" not in page


def test_staff_add_a_requester_from_the_screen(client, app, catalog, team):
    public_id = staff_ticket(app, catalog, team)
    login(client, team["sup"])

    response = client.post(
        f"/tickets/{public_id}/requesters/add",
        data={"solicitante": team["other"]["id"]},
        follow_redirects=True,
    )
    page = plain_text(response)

    assert "Solicitante agregado." in page
    assert "Paula Contreras (req2)" in page
    # Ya no se ofrece para agregar.
    assert "Contreras, Paula (req2)" not in page

    detail = plain_text(client.get(f"/tickets/{public_id}"))

    assert "Solicitantes Gestionar" in detail
    assert "Javiera Torres" in detail and "Paula Contreras" in detail
    assert "Solicitante agregado: «Paula Contreras»" in detail


def test_the_screen_rejects_invalid_requesters(client, app, catalog, team, make_user):
    inactive = make_user("SOLICITANTE", username="req_off", activo=False)
    public_id = staff_ticket(app, catalog, team)
    login(client, team["sup"])
    url = f"/tickets/{public_id}/requesters/add"

    cases = (
        ({}, "Elige a una persona de la lista."),
        ({"solicitante": ""}, "Elige a una persona de la lista."),
        ({"solicitante": "abc"}, "Ingresa un número entero."),
        ({"solicitante": team["tec"]["id"]}, "Elige a una persona de la lista."),
        ({"solicitante": inactive["id"]}, "Elige a una persona de la lista."),
        ({"solicitante": team["req"]["id"]}, "Elige a una persona de la lista."),
    )

    for data, message in cases:
        response = client.post(url, data=data, follow_redirects=True)

        assert message in plain_text(response), data

    with app.app_context():
        assert current_ids(public_id) == [team["req"]["id"]]


def test_removing_asks_for_confirmation_and_then_removes(client, app, catalog, team):
    public_id = staff_ticket(app, catalog, team)

    with app.app_context():
        link_id = link_of(public_id, team, "req").id

    login(client, team["sup"])
    url = f"/tickets/{public_id}/requesters/{link_id}/remove"

    page = plain_text(client.get(url))

    assert "Retirar solicitante" in page
    assert (
        "Javiera Torres dejará de ser solicitante del ticket y dejará de verlo."
        in page
    )
    assert "Opcional." in page

    # Abrir la confirmación no cambia nada.
    with app.app_context():
        assert current_ids(public_id) == [team["req"]["id"]]

    response = client.post(url, data={"motivo": "Ya no lo necesita"}, follow_redirects=True)
    content = plain_text(response)

    assert "Javiera Torres dejó de ser solicitante del ticket." in content
    assert "Este ticket no tiene solicitantes." in content

    detail = plain_text(client.get(f"/tickets/{public_id}"))

    assert "Solicitante retirado: «Javiera Torres»" in detail
    assert "Motivo: Ya no lo necesita" in detail
    assert "Sin solicitante" in detail

    with app.app_context():
        assert current_ids(public_id) == []


def test_removing_the_creator_warns_that_they_keep_access(client, app, catalog, team):
    public_id = own_ticket(app, catalog, team)

    with app.app_context():
        link_id = link_of(public_id, team, "req").id

    login(client, team["sup"])
    page = plain_text(client.get(f"/tickets/{public_id}/requesters/{link_id}/remove"))

    assert "creó este ticket, así que lo seguirá viendo" in page
    assert "dejará de verlo" not in page


def test_removing_an_unknown_participation_reports_it(client, app, catalog, team):
    public_id = staff_ticket(app, catalog, team)
    login(client, team["sup"])
    url = f"/tickets/{public_id}/requesters/99999/remove"

    for method in (client.get, client.post):
        response = method(url, follow_redirects=True)

        assert "Esa persona ya no es solicitante del ticket." in plain_text(response)


def test_the_removal_screen_rejects_a_long_reason(client, app, catalog, team):
    public_id = staff_ticket(app, catalog, team)

    with app.app_context():
        link_id = link_of(public_id, team, "req").id

    login(client, team["sup"])
    response = client.post(
        f"/tickets/{public_id}/requesters/{link_id}/remove",
        data={"motivo": "x" * 501},
    )

    assert response.status_code == 200
    assert "Máximo 500 caracteres." in plain_text(response)

    with app.app_context():
        assert current_ids(public_id) == [team["req"]["id"]]


def test_the_requester_screens_redirect_for_a_closed_ticket(
    client,
    app,
    catalog,
    team,
):
    public_id = staff_ticket(app, catalog, team)

    with app.app_context():
        link_id = link_of(public_id, team, "req").id

    set_state(app, public_id, "CERRADO")
    login(client, team["sup"])
    base = f"/tickets/{public_id}/requesters"
    message = "Un ticket cerrado no se puede modificar."

    for response in (
        client.get(base, follow_redirects=True),
        client.get(f"{base}/{link_id}/remove", follow_redirects=True),
        client.post(f"{base}/{link_id}/remove", data={}, follow_redirects=True),
        client.post(
            f"{base}/add",
            data={"solicitante": team["other"]["id"]},
            follow_redirects=True,
        ),
    ):
        assert message in plain_text(response)

    with app.app_context():
        assert current_ids(public_id) == [team["req"]["id"]]


def test_the_detail_offers_the_manage_link_only_to_staff_on_open_tickets(
    client,
    app,
    catalog,
    team,
):
    public_id = staff_ticket(app, catalog, team)
    url = f"/tickets/{public_id}/requesters"

    for key in STAFF:
        client.post("/logout")
        login(client, team[key])
        html = client.get(f"/tickets/{public_id}").get_data(as_text=True)

        assert url in html and "Gestionar" in html

    client.post("/logout")
    login(client, team["req"])

    assert "/requesters" not in client.get(f"/tickets/{public_id}").get_data(
        as_text=True
    )

    set_state(app, public_id, "CERRADO")
    client.post("/logout")
    login(client, team["tec"])

    assert "/requesters" not in client.get(f"/tickets/{public_id}").get_data(
        as_text=True
    )
