import pytest

from src.workdesk.extensions import db
from src.workdesk.models import (
    Categoria,
    Prioridad,
    Ticket,
    TicketEvent,
    TicketHistory,
    TicketRequester,
    Ubicacion,
    User,
)
from src.workdesk.tickets.service import (
    TicketRuleError,
    categories_for_selection,
    create_ticket,
    get_ticket_by_public_id,
    list_requester_candidates,
    list_ticket_history,
)


@pytest.fixture()
def actor_id(make_user, ticket_catalog_ids):
    return make_user("TECNICO")["id"]


def _create(actor_id, ids, **overrides):
    values = {
        "actor": db.session.get(User, actor_id),
        "title": "VPN sin acceso",
        "description": "No puedo conectarme desde casa.",
        "category_id": ids["category_id"],
        "priority_id": ids["priority_id"],
    }
    values.update(overrides)

    return create_ticket(**values)


def _count(model) -> int:
    return db.session.scalar(db.select(db.func.count(model.id)))


# --- Creación correcta -----------------------------------------------------


def test_creates_a_new_ticket_with_the_given_data(
    app, actor_id, ticket_catalog_ids
):
    with app.app_context():
        ticket = _create(
            actor_id,
            ticket_catalog_ids,
            location_id=ticket_catalog_ids["location_id"],
        )
        db.session.commit()

        assert ticket.titulo == "VPN sin acceso"
        assert ticket.descripcion == "No puedo conectarme desde casa."
        assert ticket.estado.codigo == "NUEVO"
        assert ticket.creado_por_usuario_id == actor_id
        assert ticket.categoria_id == ticket_catalog_ids["category_id"]
        assert ticket.prioridad_id == ticket_catalog_ids["priority_id"]
        assert ticket.ubicacion.nombre == "Oficina central"
        assert ticket.public_id.isdigit()
        assert ticket.version == 1


def test_trims_title_and_description(app, actor_id, ticket_catalog_ids):
    with app.app_context():
        ticket = _create(
            actor_id,
            ticket_catalog_ids,
            title="  Con espacios  ",
            description="  Descripción  ",
        )

        assert ticket.titulo == "Con espacios"
        assert ticket.descripcion == "Descripción"


def test_location_is_optional(app, actor_id, ticket_catalog_ids):
    with app.app_context():
        ticket = _create(actor_id, ticket_catalog_ids)

        assert ticket.ubicacion_id is None


def test_the_creator_is_not_a_requester_by_default(
    app, actor_id, ticket_catalog_ids
):
    with app.app_context():
        ticket = _create(actor_id, ticket_catalog_ids)

        assert ticket.solicitantes == []
        assert _count(TicketRequester) == 0


def test_consecutive_tickets_get_consecutive_public_ids(
    app, actor_id, ticket_catalog_ids
):
    with app.app_context():
        first = _create(actor_id, ticket_catalog_ids)
        second = _create(actor_id, ticket_catalog_ids)

        assert int(second.public_id) == int(first.public_id) + 1


def test_does_not_commit(app, actor_id, ticket_catalog_ids):
    with app.app_context():
        _create(actor_id, ticket_catalog_ids)
        db.session.rollback()

        assert _count(Ticket) == 0
        assert _count(TicketHistory) == 0


# --- Historial -------------------------------------------------------------


def test_records_the_creation_event(app, actor_id, ticket_catalog_ids):
    with app.app_context():
        ticket = _create(
            actor_id,
            ticket_catalog_ids,
            location_id=ticket_catalog_ids["location_id"],
        )
        db.session.commit()

        entries = db.session.scalars(
            db.select(TicketHistory).where(
                TicketHistory.ticket_id == ticket.id
            )
        ).all()

        assert len(entries) == 1
        entry = entries[0]
        assert entry.tipo_evento == TicketEvent.TICKET_CREADO.value
        assert entry.actor_tipo == "USUARIO"
        assert entry.actor_usuario_id == actor_id
        assert entry.estado_nuevo_id == ticket.estado_id
        assert entry.estado_anterior_id is None
        assert entry.valor_nuevo["titulo"] == "VPN sin acceso"
        assert entry.valor_nuevo["categoria"] == "Sin clasificar"
        assert entry.valor_nuevo["prioridad"] == "Media"
        assert entry.valor_nuevo["ubicacion"] == "Oficina central"
        assert entry.valor_nuevo["solicitantes"] == []


# --- Solicitantes ----------------------------------------------------------


def test_associates_the_given_requesters(
    app, actor_id, make_user, ticket_catalog_ids
):
    first = make_user("SOLICITANTE", username="sol_uno")
    second = make_user("SOLICITANTE", username="sol_dos")

    with app.app_context():
        ticket = _create(
            actor_id,
            ticket_catalog_ids,
            requester_ids=[first["id"], second["id"]],
        )
        db.session.commit()

        assert [r.solicitante_id for r in ticket.solicitantes] == [
            first["id"],
            second["id"],
        ]
        assert all(r.fecha_retiro is None for r in ticket.solicitantes)
        assert all(
            r.asociado_por_usuario_id == actor_id for r in ticket.solicitantes
        )

        entry = db.session.scalar(db.select(TicketHistory))
        assert [s["username"] for s in entry.valor_nuevo["solicitantes"]] == [
            "sol_uno",
            "sol_dos",
        ]


def test_duplicate_requesters_are_associated_once(
    app, actor_id, make_user, ticket_catalog_ids
):
    requester = make_user("SOLICITANTE")

    with app.app_context():
        ticket = _create(
            actor_id,
            ticket_catalog_ids,
            requester_ids=[requester["id"], requester["id"]],
        )

        assert len(ticket.solicitantes) == 1


def test_a_requester_can_be_the_creator(app, make_user, ticket_catalog_ids):
    requester = make_user("SOLICITANTE")

    with app.app_context():
        ticket = _create(
            requester["id"],
            ticket_catalog_ids,
            requester_ids=[requester["id"]],
        )

        assert ticket.creado_por_usuario_id == requester["id"]
        assert ticket.solicitantes[0].solicitante_id == requester["id"]


def test_rejects_a_requester_that_does_not_exist(
    app, actor_id, ticket_catalog_ids
):
    with app.app_context():
        with pytest.raises(TicketRuleError):
            _create(actor_id, ticket_catalog_ids, requester_ids=[999999])

        assert _count(Ticket) == 0


def test_rejects_an_inactive_requester(
    app, actor_id, make_user, ticket_catalog_ids
):
    requester = make_user("SOLICITANTE", activo=False)

    with app.app_context(), pytest.raises(TicketRuleError):
        _create(
            actor_id, ticket_catalog_ids, requester_ids=[requester["id"]]
        )


def test_rejects_a_requester_that_is_not_a_solicitante(
    app, actor_id, make_user, ticket_catalog_ids
):
    other = make_user("SUPERVISOR")

    with app.app_context(), pytest.raises(TicketRuleError):
        _create(actor_id, ticket_catalog_ids, requester_ids=[other["id"]])


# --- Validaciones ----------------------------------------------------------


@pytest.mark.parametrize("field", ["title", "description"])
@pytest.mark.parametrize("value", ["", "   "])
def test_title_and_description_are_required(
    app, actor_id, ticket_catalog_ids, field, value
):
    with app.app_context():
        with pytest.raises(TicketRuleError):
            _create(actor_id, ticket_catalog_ids, **{field: value})

        assert _count(Ticket) == 0


def test_title_has_a_maximum_length(app, actor_id, ticket_catalog_ids):
    with app.app_context():
        assert _create(actor_id, ticket_catalog_ids, title="a" * 200)

        with pytest.raises(TicketRuleError):
            _create(actor_id, ticket_catalog_ids, title="a" * 201)


def test_rejects_an_inactive_actor(app, make_user, ticket_catalog_ids):
    inactive = make_user("TECNICO", username="tec_inactivo", activo=False)

    with app.app_context(), pytest.raises(TicketRuleError):
        _create(inactive["id"], ticket_catalog_ids)


@pytest.mark.parametrize(
    ("key", "model"),
    [
        ("category_id", Categoria),
        ("priority_id", Prioridad),
        ("location_id", Ubicacion),
    ],
)
def test_rejects_an_inactive_catalog_value(
    app, actor_id, ticket_catalog_ids, key, model
):
    ids = {**ticket_catalog_ids}

    with app.app_context():
        record = db.session.get(model, ids[key])
        record.activo = False
        db.session.commit()

        with pytest.raises(TicketRuleError):
            _create(actor_id, ids, **{key: ids[key]})

        assert _count(Ticket) == 0


@pytest.mark.parametrize(
    "key", ["category_id", "priority_id", "location_id"]
)
def test_rejects_a_catalog_value_that_does_not_exist(
    app, actor_id, ticket_catalog_ids, key
):
    with app.app_context(), pytest.raises(TicketRuleError):
        _create(actor_id, ticket_catalog_ids, **{key: 999999})


def test_requires_the_initial_state_to_exist(app, make_user):
    # Sin seed-catalogs no hay estado Nuevo.
    user = make_user("TECNICO")

    with app.app_context():
        category = Categoria(nombre="Prueba")
        priority = Prioridad(nombre="Prueba", nivel=1)
        db.session.add_all([category, priority])
        db.session.commit()

        with pytest.raises(TicketRuleError, match="seed-catalogs"):
            create_ticket(
                actor=db.session.get(User, user["id"]),
                title="Título",
                description="Descripción",
                category_id=category.id,
                priority_id=priority.id,
            )


# --- Límite de la descripción ----------------------------------------------


def test_description_has_a_maximum_length(app, actor_id, ticket_catalog_ids):
    with app.app_context():
        assert _create(actor_id, ticket_catalog_ids, description="a" * 2000)

        with pytest.raises(TicketRuleError, match="2000"):
            _create(actor_id, ticket_catalog_ids, description="a" * 2001)


# --- Candidatos a solicitante ----------------------------------------------


def test_requester_candidates_are_active_solicitantes_by_last_name(
    app,
    make_user,
    ticket_catalog_ids,
):
    make_user("SOLICITANTE", username="zeta", apellido="Zapata")
    make_user("SOLICITANTE", username="alfa", apellido="acosta")
    make_user("SOLICITANTE", username="baja", apellido="Bajas", activo=False)
    make_user("TECNICO", username="tec")
    make_user("SUPERVISOR", username="sup")

    with app.app_context():
        usernames = [user.username for user in list_requester_candidates()]

    # Por apellido sin distinguir mayúsculas; sin inactivos ni otros roles.
    assert usernames == ["alfa", "zeta"]


# --- Categorías para el formulario -----------------------------------------


def test_categories_for_selection_put_the_fallback_last(
    app,
    ticket_catalog_ids,
):
    with app.app_context():
        db.session.add_all(
            [
                Categoria(nombre="Zeta", orden=2),
                Categoria(nombre="Alfa", orden=1),
                Categoria(nombre="Sin orden"),
            ]
        )
        db.session.commit()

        names = [category.nombre for category in categories_for_selection()]

    # "Sin clasificar" (orden 0) sería la primera por orden: va al final.
    assert names == ["Alfa", "Zeta", "Sin orden", "Sin clasificar"]


def test_categories_for_selection_exclude_inactive_ones(
    app,
    ticket_catalog_ids,
):
    with app.app_context():
        db.session.add(Categoria(nombre="Antigua", activo=False))
        db.session.commit()

        names = [category.nombre for category in categories_for_selection()]

    assert "Antigua" not in names


# --- Consulta de un ticket -------------------------------------------------


def test_a_ticket_is_found_by_its_public_id(app, actor_id, ticket_catalog_ids):
    with app.app_context():
        ticket = _create(actor_id, ticket_catalog_ids)
        db.session.commit()

        found = get_ticket_by_public_id(ticket.public_id)

        assert found.id == ticket.id
        assert found.estado.codigo == "NUEVO"


def test_an_unknown_public_id_returns_none(app, ticket_catalog_ids):
    with app.app_context():
        assert get_ticket_by_public_id("999999") is None


def test_the_history_is_listed_oldest_first_with_its_actor(
    app,
    actor_id,
    ticket_catalog_ids,
):
    with app.app_context():
        ticket = _create(actor_id, ticket_catalog_ids)
        db.session.commit()

        (entry,) = list_ticket_history(ticket)

        assert entry.tipo_evento == TicketEvent.TICKET_CREADO.value
        assert entry.evento_nombre == "Ticket creado"
        assert entry.actor.id == actor_id


def test_an_unknown_event_type_is_shown_as_is(app):
    with app.app_context():
        entry = TicketHistory(tipo_evento="EVENTO_FUTURO")

        assert entry.evento_nombre == "EVENTO_FUTURO"
