from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import event

from src.workdesk.extensions import db
from src.workdesk.models import (
    Estado,
    Prioridad,
    Ticket,
    User,
)
from src.workdesk.security import can_view_ticket
from src.workdesk.tickets.queries import (
    DEFAULT_SORT,
    PAGE_SIZE,
    SORT_OLDEST,
    SORT_PRIORITY,
    SORT_RECENT,
    SORT_UPDATED,
    TAB_ALL,
    TAB_CLOSED,
    TAB_OPEN,
    TicketFilters,
    count_tickets_by_tab,
    list_states,
    list_tickets,
    visible_tickets_condition,
)
from tests.ticket_helpers import (
    make_ticket,
    retire,
    set_created,
    set_state,
    ticket_by_public_id,
)


def get_user(user_id):
    return db.session.get(User, user_id)


def public_ids(app, user_id, filters=None, **kwargs):
    with app.app_context():
        page = list_tickets(get_user(user_id), filters, **kwargs)

        return [ticket.public_id for ticket in page.items]


@pytest.fixture()
def staff(make_user, catalog):
    return make_user("TECNICO", username="personal")


# --- Visibilidad ------------------------------------------------------


def test_staff_sees_every_ticket(app, make_user, catalog, staff):
    owner = make_user("SOLICITANTE", username="dueno")
    first = make_ticket(app, catalog, owner["id"])
    second = make_ticket(app, catalog, staff["id"])

    assert sorted(public_ids(app, staff["id"], tab=TAB_ALL)) == sorted(
        [first, second]
    )


def test_a_solicitante_sees_only_what_is_theirs(
    app,
    make_user,
    catalog,
    staff,
):
    mine = make_user("SOLICITANTE", username="mio")
    other = make_user("SOLICITANTE", username="otro")
    created = make_ticket(app, catalog, mine["id"])
    as_requester = make_ticket(
        app,
        catalog,
        staff["id"],
        requester_ids=[mine["id"]],
    )
    make_ticket(app, catalog, other["id"])
    make_ticket(app, catalog, staff["id"], requester_ids=[other["id"]])

    assert sorted(public_ids(app, mine["id"], tab=TAB_ALL)) == sorted(
        [created, as_requester]
    )


def test_a_removed_requester_no_longer_sees_the_ticket(
    app,
    make_user,
    catalog,
    staff,
):
    requester = make_user("SOLICITANTE", username="retirado")
    public_id = make_ticket(
        app,
        catalog,
        staff["id"],
        requester_ids=[requester["id"]],
    )

    assert public_ids(app, requester["id"], tab=TAB_ALL) == [public_id]

    retire(app, public_id, requester["id"])

    assert public_ids(app, requester["id"], tab=TAB_ALL) == []


def test_an_inactive_user_sees_nothing(app, make_user, catalog, staff):
    inactive = make_user("SOLICITANTE", username="inactivo")
    make_ticket(app, catalog, inactive["id"])

    with app.app_context():
        get_user(inactive["id"]).activo = False
        db.session.commit()

    assert public_ids(app, inactive["id"], tab=TAB_ALL) == []


def test_the_sql_visibility_matches_the_python_policy(
    app,
    make_user,
    catalog,
):
    """El listado (SQL) y el detalle (Python) deben decidir siempre igual."""
    users = {
        "tecnico": make_user("TECNICO", username="tecnico"),
        "supervisor": make_user("SUPERVISOR", username="supervisor"),
        "admin": make_user("ADMINISTRADOR", username="admin"),
        "creador": make_user("SOLICITANTE", username="creador"),
        "vigente": make_user("SOLICITANTE", username="vigente"),
        "retirado": make_user("SOLICITANTE", username="retirado"),
        "ajeno": make_user("SOLICITANTE", username="ajeno"),
        "inactivo": make_user("SOLICITANTE", username="inactivo"),
    }
    make_ticket(app, catalog, users["creador"]["id"])
    shared = make_ticket(
        app,
        catalog,
        users["tecnico"]["id"],
        requester_ids=[users["vigente"]["id"], users["retirado"]["id"]],
    )
    make_ticket(app, catalog, users["inactivo"]["id"])
    retire(app, shared, users["retirado"]["id"])

    with app.app_context():
        get_user(users["inactivo"]["id"]).activo = False
        db.session.commit()

    with app.app_context():
        all_tickets = list(db.session.scalars(db.select(Ticket)))

        for data in users.values():
            user = get_user(data["id"])
            listed = {
                t.id for t in list_tickets(user, tab=TAB_ALL).items
            }

            for ticket in all_tickets:
                assert (ticket.id in listed) is can_view_ticket(
                    user, ticket
                ), (data["username"], ticket.public_id)


def test_the_visibility_condition_hides_everything_from_anonymous(
    app,
    make_user,
    catalog,
    staff,
):
    from flask_login import AnonymousUserMixin

    make_ticket(app, catalog, staff["id"])

    with app.app_context():
        found = db.session.scalars(
            db.select(Ticket).where(
                visible_tickets_condition(AnonymousUserMixin())
            )
        ).all()

    assert found == []


# --- Búsqueda ---------------------------------------------------------


def test_search_by_number_with_or_without_hash(app, catalog, staff):
    first = make_ticket(app, catalog, staff["id"], title="Alfa")
    second = make_ticket(app, catalog, staff["id"], title="Beta")

    for query in (second, f"#{second}", f" #{second} "):
        assert public_ids(
            app,
            staff["id"],
            TicketFilters(query_text=query),
            tab=TAB_ALL,
        ) == [second]

    assert first != second


def test_a_number_search_is_exact_not_a_prefix(app, catalog, staff):
    # Con más de 9 tickets, "1" no debe traer el 10 ni el 11.
    ids = [
        make_ticket(app, catalog, staff["id"], title=f"Ticket {chr(97 + i)}")
        for i in range(11)
    ]

    assert public_ids(
        app,
        staff["id"],
        TicketFilters(query_text=ids[0]),
        tab=TAB_ALL,
    ) == [ids[0]]


def test_search_matches_title_and_description_ignoring_case(
    app,
    catalog,
    staff,
):
    by_title = make_ticket(app, catalog, staff["id"], title="Falla de VPN")
    by_description = make_ticket(
        app,
        catalog,
        staff["id"],
        title="Otro",
        description="Se cae la vpn al conectar",
    )
    make_ticket(app, catalog, staff["id"], title="Impresora")

    assert sorted(
        public_ids(
            app,
            staff["id"],
            TicketFilters(query_text="vPn"),
            tab=TAB_ALL,
        )
    ) == sorted([by_title, by_description])


def test_search_treats_wildcards_literally(app, catalog, staff):
    percent = make_ticket(app, catalog, staff["id"], title="Avance 100% listo")
    underscore = make_ticket(app, catalog, staff["id"], title="archivo_final")
    make_ticket(app, catalog, staff["id"], title="Avance 1000 listo")
    make_ticket(app, catalog, staff["id"], title="archivo final")

    assert public_ids(
        app,
        staff["id"],
        TicketFilters(query_text="100%"),
        tab=TAB_ALL,
    ) == [percent]
    assert public_ids(
        app,
        staff["id"],
        TicketFilters(query_text="o_f"),
        tab=TAB_ALL,
    ) == [underscore]


def test_an_overlong_search_is_truncated_without_failing(
    app,
    catalog,
    staff,
):
    make_ticket(app, catalog, staff["id"])

    assert (
        public_ids(
            app,
            staff["id"],
            TicketFilters(query_text="x" * 500),
            tab=TAB_ALL,
        )
        == []
    )


def test_staff_can_search_by_requester_name(app, make_user, catalog, staff):
    requester = make_user(
        "SOLICITANTE",
        username="zapata",
        nombre="Zoe",
        apellido="Zapata",
    )
    found = make_ticket(
        app,
        catalog,
        staff["id"],
        title="Sin nombre",
        requester_ids=[requester["id"]],
    )
    make_ticket(app, catalog, staff["id"], title="Otro ticket")

    for query in ("Zapata", "zoe zapata", "zapata"):
        assert public_ids(
            app,
            staff["id"],
            TicketFilters(query_text=query),
            tab=TAB_ALL,
        ) == [found]


def test_a_removed_requester_is_not_searchable(
    app,
    make_user,
    catalog,
    staff,
):
    requester = make_user("SOLICITANTE", username="zapata", apellido="Zapata")
    public_id = make_ticket(
        app,
        catalog,
        staff["id"],
        requester_ids=[requester["id"]],
    )
    retire(app, public_id, requester["id"])

    assert (
        public_ids(
            app,
            staff["id"],
            TicketFilters(query_text="Zapata"),
            tab=TAB_ALL,
        )
        == []
    )


def test_a_solicitante_cannot_search_other_requesters(
    app,
    make_user,
    catalog,
    staff,
):
    mine = make_user("SOLICITANTE", username="mio", apellido="Mio")
    other = make_user("SOLICITANTE", username="otro", apellido="Zapata")
    shared = make_ticket(
        app,
        catalog,
        staff["id"],
        title="Compartido",
        requester_ids=[mine["id"], other["id"]],
    )
    filters = TicketFilters(query_text="Zapata")

    # El personal sí lo encuentra por el nombre del otro solicitante; el
    # Solicitante no: no puede averiguar quién más figura en un ticket.
    assert public_ids(app, staff["id"], filters, tab=TAB_ALL) == [shared]
    assert public_ids(app, mine["id"], filters, tab=TAB_ALL) == []


# --- Pestañas y contadores --------------------------------------------


def test_tabs_split_open_and_closed_tickets(app, catalog, staff):
    new = make_ticket(app, catalog, staff["id"], title="Nuevo")
    resolved = make_ticket(app, catalog, staff["id"], title="Resuelto")
    closed = make_ticket(app, catalog, staff["id"], title="Cerrado")
    set_state(app, resolved, "RESUELTO")
    set_state(app, closed, "CERRADO")

    # Un ticket Resuelto sigue abierto: espera la validación.
    assert sorted(public_ids(app, staff["id"], tab=TAB_OPEN)) == sorted(
        [new, resolved]
    )
    assert public_ids(app, staff["id"], tab=TAB_CLOSED) == [closed]
    assert len(public_ids(app, staff["id"], tab=TAB_ALL)) == 3


def test_the_default_tab_is_open(app, catalog, staff):
    open_ticket = make_ticket(app, catalog, staff["id"])
    closed = make_ticket(app, catalog, staff["id"])
    set_state(app, closed, "CERRADO")

    assert public_ids(app, staff["id"]) == [open_ticket]


def test_the_counters_follow_visibility_and_filters(
    app,
    make_user,
    catalog,
    staff,
):
    mine = make_user("SOLICITANTE", username="mio")
    make_ticket(app, catalog, mine["id"], title="Mi abierto")
    mine_closed = make_ticket(app, catalog, mine["id"], title="Mi cerrado")
    set_state(app, mine_closed, "CERRADO")
    make_ticket(app, catalog, staff["id"], title="Ajeno")

    with app.app_context():
        assert count_tickets_by_tab(get_user(staff["id"])) == {
            TAB_ALL: 3,
            TAB_OPEN: 2,
            TAB_CLOSED: 1,
        }
        assert count_tickets_by_tab(get_user(mine["id"])) == {
            TAB_ALL: 2,
            TAB_OPEN: 1,
            TAB_CLOSED: 1,
        }
        # Con búsqueda, los contadores cuentan solo lo que coincide.
        assert count_tickets_by_tab(
            get_user(staff["id"]),
            TicketFilters(query_text="cerrado"),
        ) == {TAB_ALL: 1, TAB_OPEN: 0, TAB_CLOSED: 1}


def test_the_counters_of_an_empty_system_are_zero(app, catalog, staff):
    with app.app_context():
        assert count_tickets_by_tab(get_user(staff["id"])) == {
            TAB_ALL: 0,
            TAB_OPEN: 0,
            TAB_CLOSED: 0,
        }


# --- Filtros ----------------------------------------------------------


def test_filters_by_state_priority_category_and_location(
    app,
    catalog,
    staff,
):
    base = make_ticket(app, catalog, staff["id"], title="Base")
    other = make_ticket(
        app,
        catalog,
        staff["id"],
        title="Otro",
        category_id=catalog["networks"],
        priority_id=catalog["high"],
        location_id=catalog["location"],
    )
    set_state(app, other, "EN_PROGRESO")

    with app.app_context():
        in_progress = db.session.scalar(
            db.select(Estado.id).where(Estado.codigo == "EN_PROGRESO")
        )

    def found(**kwargs):
        return public_ids(
            app,
            staff["id"],
            TicketFilters(**kwargs),
            tab=TAB_ALL,
        )

    assert found(state_id=in_progress) == [other]
    assert found(priority_id=catalog["high"]) == [other]
    assert found(category_id=catalog["networks"]) == [other]
    assert found(location_id=catalog["location"]) == [other]
    assert found(category_id=catalog["hardware"]) == [base]


def test_filters_combine_with_each_other_and_with_the_search(
    app,
    catalog,
    staff,
):
    match = make_ticket(
        app,
        catalog,
        staff["id"],
        title="VPN caída",
        priority_id=catalog["high"],
    )
    make_ticket(app, catalog, staff["id"], title="VPN lenta")
    make_ticket(
        app,
        catalog,
        staff["id"],
        title="Impresora",
        priority_id=catalog["high"],
    )

    assert public_ids(
        app,
        staff["id"],
        TicketFilters(query_text="vpn", priority_id=catalog["high"]),
        tab=TAB_ALL,
    ) == [match]


def test_date_filters_use_whole_days_in_the_local_timezone(
    app,
    catalog,
    staff,
):
    app.config["APP_TIMEZONE"] = "America/Santiago"
    # En marzo Chile está en UTC-3: 23:30 locales del día 5 son las 02:30 UTC
    # del día 6, y 00:30 locales del día 6 son las 03:30 UTC.
    late_on_the_5th = make_ticket(app, catalog, staff["id"], title="Tarde 5")
    early_on_the_6th = make_ticket(app, catalog, staff["id"], title="Temprano 6")
    on_the_4th = make_ticket(app, catalog, staff["id"], title="Día 4")
    set_created(app, late_on_the_5th, datetime(2026, 3, 6, 2, 30, tzinfo=UTC))
    set_created(app, early_on_the_6th, datetime(2026, 3, 6, 3, 30, tzinfo=UTC))
    set_created(app, on_the_4th, datetime(2026, 3, 4, 15, 0, tzinfo=UTC))

    def found(**kwargs):
        return sorted(
            public_ids(
                app,
                staff["id"],
                TicketFilters(**kwargs),
                tab=TAB_ALL,
            )
        )

    only_the_5th = {
        "created_from": date(2026, 3, 5),
        "created_to": date(2026, 3, 5),
    }

    assert found(**only_the_5th) == [late_on_the_5th]
    assert found(created_from=date(2026, 3, 5)) == sorted(
        [late_on_the_5th, early_on_the_6th]
    )
    # "Hasta" incluye el día completo.
    assert found(created_to=date(2026, 3, 5)) == sorted(
        [on_the_4th, late_on_the_5th]
    )
    assert found(created_from=date(2026, 3, 9)) == []


# --- Orden ------------------------------------------------------------


def test_default_order_is_newest_first(app, catalog, staff):
    first = make_ticket(app, catalog, staff["id"])
    second = make_ticket(app, catalog, staff["id"])
    third = make_ticket(app, catalog, staff["id"])

    assert public_ids(app, staff["id"], tab=TAB_ALL) == [third, second, first]
    assert DEFAULT_SORT == SORT_RECENT


def test_oldest_first(app, catalog, staff):
    first = make_ticket(app, catalog, staff["id"])
    second = make_ticket(app, catalog, staff["id"])

    assert public_ids(
        app,
        staff["id"],
        tab=TAB_ALL,
        sort=SORT_OLDEST,
    ) == [first, second]


def test_highest_priority_first(app, catalog, staff):
    with app.app_context():
        low = db.session.scalar(
            db.select(Prioridad.id).where(Prioridad.codigo == "BAJA")
        )

    low_ticket = make_ticket(app, catalog, staff["id"], priority_id=low)
    high_ticket = make_ticket(
        app,
        catalog,
        staff["id"],
        priority_id=catalog["high"],
    )
    medium_ticket = make_ticket(app, catalog, staff["id"])

    assert public_ids(
        app,
        staff["id"],
        tab=TAB_ALL,
        sort=SORT_PRIORITY,
    ) == [high_ticket, medium_ticket, low_ticket]


def test_recently_updated_first(app, catalog, staff):
    first = make_ticket(app, catalog, staff["id"])
    second = make_ticket(app, catalog, staff["id"])

    with app.app_context():
        # El primero se modificó después de que se creara el segundo.
        ticket_by_public_id(first).fecha_modificacion = datetime.now(UTC) + (
            timedelta(minutes=5)
        )
        db.session.commit()

    assert public_ids(
        app,
        staff["id"],
        tab=TAB_ALL,
        sort=SORT_UPDATED,
    ) == [first, second]


def test_an_unknown_sort_falls_back_to_the_default(app, catalog, staff):
    first = make_ticket(app, catalog, staff["id"])
    second = make_ticket(app, catalog, staff["id"])

    assert public_ids(
        app,
        staff["id"],
        tab=TAB_ALL,
        sort="inventado",
    ) == [second, first]


def test_the_update_date_falls_back_to_the_creation_date(app, catalog, staff):
    public_id = make_ticket(app, catalog, staff["id"])

    with app.app_context():
        ticket = ticket_by_public_id(public_id)

        assert ticket.fecha_modificacion is None
        assert ticket.fecha_actualizacion == ticket.fecha_creacion

        moment = datetime.now(UTC)
        ticket.fecha_modificacion = moment

        assert ticket.fecha_actualizacion == moment


# --- Paginación y consultas -------------------------------------------


def test_the_list_is_paginated_in_the_database(app, catalog, staff):
    for index in range(PAGE_SIZE + 5):
        make_ticket(app, catalog, staff["id"], title=f"Ticket {index}")

    with app.app_context():
        user = get_user(staff["id"])
        first = list_tickets(user, tab=TAB_ALL, page=1)
        second = list_tickets(user, tab=TAB_ALL, page=2)
        beyond = list_tickets(user, tab=TAB_ALL, page=99)

        assert len(first.items) == PAGE_SIZE
        assert len(second.items) == 5
        assert first.total == PAGE_SIZE + 5
        assert first.pages == 2
        assert beyond.items == []


def test_the_list_loads_its_relations_without_one_query_per_row(
    app,
    make_user,
    catalog,
    staff,
):
    requesters = [
        make_user("SOLICITANTE", username=f"sol{index}") for index in range(3)
    ]

    for index in range(10):
        make_ticket(
            app,
            catalog,
            staff["id"],
            title=f"Ticket {index}",
            requester_ids=[requesters[index % 3]["id"]],
        )

    with app.app_context():
        user = get_user(staff["id"])
        # El rol del usuario se carga una vez por petición (el layout ya lo
        # hace): no es una consulta por fila, así que no se mide aquí.
        assert user.rol.codigo == "TECNICO"
        statements = []

        def count_statement(conn, cursor, statement, *args):
            statements.append(statement)

        event.listen(db.engine, "before_cursor_execute", count_statement)

        try:
            page = list_tickets(user, tab=TAB_ALL)

            # Mostrar cada fila no debe lanzar consultas adicionales.
            rows = [
                (
                    ticket.estado.nombre_visible,
                    ticket.prioridad.nombre,
                    ticket.categoria.nombre,
                    [r.solicitante.nombre for r in ticket.solicitantes],
                    ticket.fecha_actualizacion,
                )
                for ticket in page.items
            ]
        finally:
            event.remove(db.engine, "before_cursor_execute", count_statement)

        assert len(rows) == 10
        # La página, el total y los solicitantes por lote.
        assert len(statements) <= 3


def test_the_states_are_listed_in_visual_order(app, catalog):
    with app.app_context():
        assert [state.codigo for state in list_states()] == [
            "NUEVO",
            "ASIGNADO",
            "EN_PROGRESO",
            "EN_ESPERA",
            "RESUELTO",
            "CERRADO",
        ]
