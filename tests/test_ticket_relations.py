"""Relaciones entre tickets y duplicados (docs/06, RN-162; docs/09, 19).

Cubre el catálogo de tipos y la tabla de relaciones, las políticas, el servicio
(relacionar, quitar y marcar un duplicado, que cierra el ticket) y las pantallas.
La regla del cierre de un duplicado es la misma de siempre: cerrado ⇒ fecha y
motivo de cierre (ver `test_ticket_resolution.py`).
"""

import threading

import pytest
from sqlalchemy.exc import IntegrityError

from src.workdesk.extensions import db
from src.workdesk.models import (
    HistoryVisibility,
    RelationType,
    StateAction,
    Ticket,
    TicketEvent,
    TicketHistory,
    TicketRelation,
    TipoRelacionTicket,
    User,
)
from src.workdesk.models.ticket_history import (
    DEFAULT_EVENT_VISIBILITY,
    TICKET_EVENT_LABELS,
)
from src.workdesk.security import can_manage_relations
from src.workdesk.tickets.editing import describe_history_changes
from src.workdesk.tickets.lifecycle import StateTransitionError, change_state
from src.workdesk.tickets.relations import (
    KIND_DUPLICATE_OF,
    KIND_PRINCIPAL_OF,
    KIND_RELATED,
    MAX_RELATION_COMMENT_LENGTH,
    add_relation,
    duplicate_of,
    list_relations,
    mark_duplicate,
    parse_ticket_number,
    remove_relation,
)
from src.workdesk.tickets.service import TicketRuleError, list_ticket_history
from src.workdesk.tickets.versioning import (
    TicketClosedError,
    TicketConflictError,
)
from tests.ticket_helpers import login, make_ticket, plain_text, set_state, text

Action = StateAction


# --- Auxiliares -------------------------------------------------------------


def get_ticket(public_id) -> Ticket:
    return db.session.scalar(
        db.select(Ticket).where(Ticket.public_id == public_id)
    )


def person(user_id) -> User:
    return db.session.get(User, user_id)


def add(public_id, other, user_id, **kwargs):
    relation = add_relation(
        get_ticket(public_id), other, actor=person(user_id), **kwargs
    )
    db.session.commit()

    return relation


def duplicate(public_id, principal, user_id, *, version=None, **kwargs):
    ticket = get_ticket(public_id)
    relation = mark_duplicate(
        ticket,
        principal,
        actor=person(user_id),
        expected_version=ticket.version if version is None else version,
        **kwargs,
    )
    db.session.commit()

    return relation


def remove(public_id, relation_id, user_id):
    remove_relation(get_ticket(public_id), relation_id, actor=person(user_id))
    db.session.commit()


def all_relations(active=None) -> list[TicketRelation]:
    statement = db.select(TicketRelation).order_by(TicketRelation.id)

    if active is not None:
        statement = statement.where(TicketRelation.activo.is_(active))

    return list(db.session.scalars(statement))


def type_of(code) -> TipoRelacionTicket:
    return db.session.scalar(
        db.select(TipoRelacionTicket).where(TipoRelacionTicket.codigo == code)
    )


def relation_events(public_id) -> list[TicketHistory]:
    ticket = get_ticket(public_id)

    return list(
        db.session.scalars(
            db.select(TicketHistory)
            .where(
                TicketHistory.ticket_id == ticket.id,
                TicketHistory.tipo_evento.in_(
                    [
                        TicketEvent.RELACION_AGREGADA.value,
                        TicketEvent.RELACION_ELIMINADA.value,
                    ]
                ),
            )
            .order_by(TicketHistory.id)
        )
    )


def event_names(public_id) -> list[str]:
    ticket = get_ticket(public_id)

    return [
        e.tipo_evento
        for e in db.session.scalars(
            db.select(TicketHistory)
            .where(TicketHistory.ticket_id == ticket.id)
            .order_by(TicketHistory.id)
        )
    ]


@pytest.fixture()
def tech(make_user, catalog):
    return make_user("TECNICO", username="tecnico")


@pytest.fixture()
def supervisor(make_user, catalog):
    return make_user("SUPERVISOR", username="supervisor")


@pytest.fixture()
def requester(make_user, catalog):
    return make_user("SOLICITANTE", username="solicitante")


@pytest.fixture()
def pair(app, catalog, tech, requester):
    """Dos tickets abiertos: `a` y `b`."""
    return (
        make_ticket(app, catalog, tech["id"], requester_ids=[requester["id"]],
                    title="Ticket A"),
        make_ticket(app, catalog, tech["id"], title="Ticket B"),
    )


@pytest.fixture()
def trio(app, catalog, tech, pair):
    return (*pair, make_ticket(app, catalog, tech["id"], title="Ticket C"))


# --- Catálogo y configuración ------------------------------------------------


def test_the_seed_loads_both_relation_types(app, seeded_catalogs):
    with app.app_context():
        duplicate_type = type_of("DUPLICADO")
        related_type = type_of("RELACIONADO")

        assert duplicate_type.es_simetrica is False
        assert related_type.es_simetrica is True
        assert duplicate_type.activo and related_type.activo
        assert {t.value for t in RelationType} == {"DUPLICADO", "RELACIONADO"}


@pytest.mark.parametrize(
    "event",
    [TicketEvent.RELACION_AGREGADA, TicketEvent.RELACION_ELIMINADA],
)
def test_relation_events_are_internal_and_have_a_name(event):
    assert DEFAULT_EVENT_VISIBILITY[event] is HistoryVisibility.INTERNO
    assert TICKET_EVENT_LABELS[event]


@pytest.mark.parametrize(
    ("role", "allowed"),
    [
        ("SOLICITANTE", False),
        ("TECNICO", True),
        ("SUPERVISOR", True),
        ("ADMINISTRADOR", True),
    ],
)
def test_only_staff_manage_relations(app, make_user, catalog, role, allowed):
    someone = make_user(role, username="alguien")

    with app.app_context():
        assert can_manage_relations(person(someone["id"])) is allowed


def test_inactive_users_do_not_manage_relations(app, make_user, catalog):
    inactive = make_user("SUPERVISOR", username="inactivo", activo=False)

    with app.app_context():
        assert not can_manage_relations(person(inactive["id"]))


# --- Base de datos -----------------------------------------------------------


def _row(a, b, code, user_id, **values):
    return TicketRelation(
        ticket_origen_id=a.id,
        ticket_destino_id=b.id,
        tipo_relacion_id=type_of(code).id,
        usuario_creacion_id=user_id,
        **values,
    )


def test_the_database_rejects_a_ticket_related_to_itself(app, tech, pair):
    with app.app_context():
        a = get_ticket(pair[0])
        db.session.add(_row(a, a, "RELACIONADO", tech["id"]))

        with pytest.raises(IntegrityError):
            db.session.commit()


def test_the_database_rejects_a_repeated_pair_even_inverted(app, tech, pair):
    with app.app_context():
        a, b = get_ticket(pair[0]), get_ticket(pair[1])
        db.session.add(_row(a, b, "RELACIONADO", tech["id"]))
        db.session.commit()

        db.session.add(_row(b, a, "RELACIONADO", tech["id"]))

        with pytest.raises(IntegrityError):
            db.session.commit()

        db.session.rollback()
        db.session.add(_row(a, b, "RELACIONADO", tech["id"]))

        with pytest.raises(IntegrityError):
            db.session.commit()


def test_different_types_can_link_the_same_pair(app, tech, pair):
    with app.app_context():
        a, b = get_ticket(pair[0]), get_ticket(pair[1])
        db.session.add_all(
            [
                _row(a, b, "RELACIONADO", tech["id"]),
                _row(a, b, "DUPLICADO", tech["id"]),
            ]
        )
        db.session.commit()

        assert len(all_relations()) == 2


def test_a_deactivated_relation_allows_a_new_one(app, tech, pair):
    with app.app_context():
        a, b = get_ticket(pair[0]), get_ticket(pair[1])
        first = _row(a, b, "RELACIONADO", tech["id"])
        db.session.add(first)
        db.session.commit()

        first.activo = False
        first.fecha_desactivacion = db.func.now()
        first.usuario_desactivacion_id = tech["id"]
        db.session.commit()

        db.session.add(_row(b, a, "RELACIONADO", tech["id"]))
        db.session.commit()

        assert len(all_relations()) == 2
        assert len(all_relations(active=True)) == 1


@pytest.mark.parametrize(
    "values",
    [
        {"activo": False},  # inactiva sin fecha
        {"fecha_desactivacion": db.func.now()},  # activa con fecha
    ],
)
def test_the_database_checks_the_deactivation_is_coherent(app, tech, pair, values):
    with app.app_context():
        a, b = get_ticket(pair[0]), get_ticket(pair[1])
        db.session.add(_row(a, b, "RELACIONADO", tech["id"], **values))

        with pytest.raises(IntegrityError):
            db.session.commit()


# --- Número de ticket --------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [("12", "12"), ("#12", "12"), (" # 12 ", "12"), ("007", "7")],
)
def test_the_ticket_number_accepts_common_forms(value, expected):
    assert parse_ticket_number(value) == expected


@pytest.mark.parametrize("value", [None, "", "  ", "abc", "1.5", "-3", "12a", "#"])
def test_the_ticket_number_rejects_anything_else(value):
    with pytest.raises(TicketRuleError, match="número del ticket"):
        parse_ticket_number(value)


# --- Relacionar --------------------------------------------------------------


def test_relating_stores_the_pair_normalized_whichever_side_acts(
    app,
    tech,
    pair,
):
    a, b = pair

    with app.app_context():
        # Desde el ticket de id mayor.
        relation = add(b, a, tech["id"], comment="  Mismo cliente.  ")
        low, high = sorted((get_ticket(a).id, get_ticket(b).id))

        assert (relation.ticket_origen_id, relation.ticket_destino_id) == (low, high)
        assert relation.tipo.codigo == "RELACIONADO"
        assert relation.comentario == "Mismo cliente."
        assert relation.usuario_creacion_id == tech["id"]
        assert relation.activo and relation.fecha_creacion is not None


def test_relating_records_one_internal_event_on_the_acting_ticket(
    app,
    tech,
    pair,
):
    a, b = pair

    with app.app_context():
        relation = add(a, f"#{b}", tech["id"])
        (event,) = relation_events(a)

        assert event.tipo_evento == "RELACION_AGREGADA"
        assert event.visibilidad == "INTERNO"
        assert event.actor_usuario_id == tech["id"]
        assert event.valor_nuevo == {
            "relacion_id": relation.id,
            "tipo": "RELACIONADO",
            "ticket": b,
            "titulo": "Ticket B",
        }
        assert event.contexto == {"relacion_id": relation.id}
        # El otro ticket no recibe el evento: su tarjeta lee la relación.
        assert relation_events(b) == []


def test_relating_does_not_touch_the_versions(app, tech, pair):
    a, b = pair

    with app.app_context():
        before = (get_ticket(a).version, get_ticket(b).version)
        add(a, b, tech["id"])

        assert (get_ticket(a).version, get_ticket(b).version) == before
        assert get_ticket(a).fecha_modificacion is None


def test_both_tickets_list_the_relation(app, tech, pair):
    a, b = pair

    with app.app_context():
        add(a, b, tech["id"])

        (from_a,) = list_relations(get_ticket(a))
        (from_b,) = list_relations(get_ticket(b))

        assert (from_a.kind, from_a.other.public_id) == (KIND_RELATED, b)
        assert (from_b.kind, from_b.other.public_id) == (KIND_RELATED, a)
        assert from_a.relation.id == from_b.relation.id
        assert from_a.removable


def test_a_ticket_cannot_be_related_to_itself(app, tech, pair):
    with app.app_context(), pytest.raises(TicketRuleError, match="consigo mismo"):
        add(pair[0], pair[0], tech["id"])


def test_relating_needs_an_existing_ticket(app, tech, pair):
    with app.app_context():
        with pytest.raises(TicketRuleError, match="No existe el ticket #99999"):
            add(pair[0], "99999", tech["id"])

        with pytest.raises(TicketRuleError, match="número del ticket"):
            add(pair[0], "abc", tech["id"])


def test_the_same_pair_cannot_be_related_twice_from_either_side(app, tech, pair):
    a, b = pair

    with app.app_context():
        add(a, b, tech["id"])

        for acting, other in ((a, b), (b, a)):
            with pytest.raises(TicketRuleError, match="ya están relacionados"):
                add(acting, other, tech["id"])

            db.session.rollback()

        assert len(all_relations(active=True)) == 1


def test_a_pair_already_linked_as_duplicate_is_not_related_again(
    app,
    tech,
    pair,
):
    a, b = pair

    with app.app_context():
        duplicate(a, b, tech["id"])

        with pytest.raises(TicketRuleError, match="vinculados como duplicado"):
            add(b, a, tech["id"])


def test_the_comment_has_a_limit(app, tech, trio):
    a, b, c = trio

    with app.app_context():
        add(a, b, tech["id"], comment="x" * MAX_RELATION_COMMENT_LENGTH)

        with pytest.raises(TicketRuleError, match="500"):
            add(a, c, tech["id"], comment="x" * (MAX_RELATION_COMMENT_LENGTH + 1))


def test_a_closed_ticket_cannot_acquire_relations_but_can_be_the_other_side(
    app,
    tech,
    trio,
):
    a, b, c = trio
    set_state(app, b, "CERRADO")
    set_state(app, c, "CERRADO")

    with app.app_context():
        # El otro ticket puede estar cerrado.
        add(a, b, tech["id"])

        assert get_ticket(b).estado.codigo == "CERRADO"

        # Pero no se actúa desde un ticket cerrado.
        with pytest.raises(TicketClosedError):
            add(c, a, tech["id"])


def test_an_inactive_actor_cannot_relate(app, make_user, pair):
    inactive = make_user("TECNICO", username="inactivo", activo=False)

    with app.app_context(), pytest.raises(TicketRuleError, match="no está activo"):
        add(pair[0], pair[1], inactive["id"])


def test_the_service_does_not_commit(app, tech, pair):
    a, b = pair

    with app.app_context():
        add_relation(get_ticket(a), b, actor=person(tech["id"]))
        db.session.rollback()

        assert all_relations() == []
        assert relation_events(a) == []


# --- Quitar ---------------------------------------------------------------------


def test_removing_a_relation_deactivates_it_and_keeps_it_as_history(
    app,
    supervisor,
    tech,
    pair,
):
    a, b = pair

    with app.app_context():
        relation = add(a, b, tech["id"])
        remove(a, relation.id, supervisor["id"])

        stored = db.session.get(TicketRelation, relation.id)

        assert stored.activo is False
        assert stored.fecha_desactivacion is not None
        assert stored.usuario_desactivacion_id == supervisor["id"]
        assert list_relations(get_ticket(a)) == []
        assert list_relations(get_ticket(b)) == []

        removal = relation_events(a)[-1]

        assert removal.tipo_evento == "RELACION_ELIMINADA"
        assert removal.visibilidad == "INTERNO"
        assert removal.valor_anterior["ticket"] == b
        assert removal.contexto == {"relacion_id": relation.id}


def test_a_removed_relation_can_be_established_again(app, tech, pair):
    a, b = pair

    with app.app_context():
        first = add(a, b, tech["id"])
        remove(a, first.id, tech["id"])
        second = add(b, a, tech["id"])

        assert second.id != first.id
        assert len(all_relations()) == 2
        assert len(all_relations(active=True)) == 1


def test_a_relation_can_be_removed_from_the_other_ticket(app, tech, pair):
    a, b = pair

    with app.app_context():
        relation = add(a, b, tech["id"])
        remove(b, relation.id, tech["id"])

        assert db.session.get(TicketRelation, relation.id).activo is False
        assert relation_events(b)[-1].tipo_evento == "RELACION_ELIMINADA"


def test_removing_rejects_unknown_foreign_or_removed_relations(
    app,
    tech,
    trio,
):
    a, b, c = trio

    with app.app_context():
        between_b_and_c = add(b, c, tech["id"])

        for relation_id in (999999, between_b_and_c.id):
            with pytest.raises(TicketRuleError, match="ya no existe"):
                remove(a, relation_id, tech["id"])

            db.session.rollback()

        remove(b, between_b_and_c.id, tech["id"])

        with pytest.raises(TicketRuleError, match="ya no existe"):
            remove(b, between_b_and_c.id, tech["id"])


def test_a_closed_ticket_cannot_remove_relations(app, tech, pair):
    a, b = pair

    with app.app_context():
        relation_id = add(a, b, tech["id"]).id

    set_state(app, a, "CERRADO")

    with app.app_context(), pytest.raises(TicketClosedError):
        remove(a, relation_id, tech["id"])


def test_two_people_removing_the_same_relation_at_once_remove_it_once(
    app,
    make_user,
    tech,
    pair,
):
    other = make_user("SUPERVISOR", username="otro")
    a, b = pair

    with app.app_context():
        relation_id = add(a, b, tech["id"]).id

    barrier = threading.Barrier(2)
    outcomes = []

    def attempt(public_id, user_id):
        with app.app_context():
            ticket = get_ticket(public_id)
            actor = person(user_id)
            barrier.wait(timeout=10)

            try:
                remove_relation(ticket, relation_id, actor=actor)
                db.session.commit()
                outcomes.append("ok")
            except TicketRuleError as error:
                db.session.rollback()
                outcomes.append(str(error))
            finally:
                db.session.remove()

    threads = [
        threading.Thread(target=attempt, args=(a, tech["id"])),
        threading.Thread(target=attempt, args=(b, other["id"])),
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join(timeout=30)

    assert sorted(outcomes) == ["Esa relación ya no existe.", "ok"]

    with app.app_context():
        removals = [
            e for e in relation_events(a) + relation_events(b)
            if e.tipo_evento == "RELACION_ELIMINADA"
        ]

        assert len(removals) == 1


# --- Marcar un duplicado ------------------------------------------------------------


def test_marking_a_duplicate_links_it_and_closes_it(app, tech, pair):
    dup, principal = pair

    with app.app_context():
        relation = duplicate(dup, principal, tech["id"], comment="Mismo problema.")
        ticket = get_ticket(dup)

        assert relation.tipo.codigo == "DUPLICADO"
        # Del duplicado al principal.
        assert relation.ticket_origen_id == ticket.id
        assert relation.ticket_destino_id == get_ticket(principal).id
        assert relation.comentario == "Mismo problema."

        # Cerrado como cualquier otro cierre: fecha, motivo y quién.
        assert ticket.estado.codigo == "CERRADO"
        assert ticket.fecha_cierre is not None
        assert ticket.motivo_cierre.codigo == "DUPLICADO"
        assert ticket.cerrado_por_usuario_id == tech["id"]
        assert ticket.cerrado_automaticamente is False
        assert ticket.version == 2


def test_marking_a_duplicate_leaves_the_principal_untouched(app, tech, pair):
    dup, principal = pair

    with app.app_context():
        before = (
            get_ticket(principal).version,
            get_ticket(principal).estado.codigo,
            event_names(principal),
        )
        duplicate(dup, principal, tech["id"])

        after = get_ticket(principal)

        assert (after.version, after.estado.codigo, event_names(principal)) == before
        assert after.fecha_modificacion is None


def test_marking_a_duplicate_records_the_relation_then_the_closing(
    app,
    tech,
    pair,
):
    dup, principal = pair

    with app.app_context():
        relation = duplicate(dup, principal, tech["id"])
        history = event_names(dup)

        assert history[-2:] == ["RELACION_AGREGADA", "TICKET_CERRADO"]

        added = relation_events(dup)[0]
        closing = db.session.scalar(
            db.select(TicketHistory).where(
                TicketHistory.ticket_id == get_ticket(dup).id,
                TicketHistory.tipo_evento == "TICKET_CERRADO",
            )
        )

        assert added.visibilidad == "INTERNO"
        assert added.valor_nuevo["tipo"] == "DUPLICADO"
        assert added.valor_nuevo["ticket"] == principal
        # El cierre es público y lleva el motivo; el principal va solo en el
        # contexto (la consulta del Solicitante no lo muestra: ver pantallas).
        assert closing.visibilidad == "PUBLICO"
        assert closing.valor_nuevo["motivo_cierre"]["codigo"] == "DUPLICADO"
        assert closing.contexto == {
            "accion": "CIERRE_DIRECTO",
            "duplicado_de": principal,
            "relacion_id": relation.id,
            "motivo_cierre": "DUPLICADO",
        }


@pytest.mark.parametrize("origin", ["NUEVO", "ASIGNADO", "EN_PROGRESO", "EN_ESPERA"])
def test_a_duplicate_can_be_closed_from_every_open_state(
    app,
    tech,
    pair,
    origin,
):
    dup, principal = pair
    set_state(app, dup, origin)

    with app.app_context():
        duplicate(dup, principal, tech["id"])

        assert get_ticket(dup).estado.codigo == "CERRADO"


def test_a_resolved_ticket_cannot_be_marked_as_duplicate(app, tech, pair):
    dup, principal = pair
    set_state(app, dup, "RESUELTO")

    with app.app_context():
        with pytest.raises(StateTransitionError):
            duplicate(dup, principal, tech["id"])

        db.session.rollback()

        assert all_relations() == []
        assert get_ticket(dup).estado.codigo == "RESUELTO"


def test_a_closed_ticket_cannot_be_marked_as_duplicate(app, tech, pair):
    dup, principal = pair
    set_state(app, dup, "CERRADO")

    with app.app_context(), pytest.raises(TicketClosedError):
        duplicate(dup, principal, tech["id"])


def test_the_principal_may_be_in_any_state_including_closed(app, tech, pair):
    dup, principal = pair
    set_state(app, principal, "CERRADO")

    with app.app_context():
        duplicate(dup, principal, tech["id"])

        assert get_ticket(principal).estado.codigo == "CERRADO"
        assert get_ticket(dup).estado.codigo == "CERRADO"


def test_a_ticket_cannot_be_its_own_duplicate_nor_of_a_missing_one(
    app,
    tech,
    pair,
):
    with app.app_context():
        with pytest.raises(TicketRuleError, match="sí mismo"):
            duplicate(pair[0], pair[0], tech["id"])

        with pytest.raises(TicketRuleError, match="No existe el ticket"):
            duplicate(pair[0], "99999", tech["id"])

        assert all_relations() == []


def test_the_principal_cannot_itself_be_a_duplicate(app, tech, trio):
    a, b, c = trio

    with app.app_context():
        duplicate(b, c, tech["id"])  # B es duplicado de C

        with pytest.raises(TicketRuleError, match="ya es un duplicado de otro"):
            duplicate(a, b, tech["id"])  # A de B: B ya es un duplicado


def test_a_principal_cannot_become_a_duplicate(app, tech, trio):
    a, b, c = trio

    with app.app_context():
        duplicate(a, b, tech["id"])  # A es duplicado de B

        with pytest.raises(TicketRuleError, match="duplicados de este"):
            duplicate(b, c, tech["id"])  # B ya es principal de A


def test_there_are_no_duplicate_cycles(app, tech, pair):
    a, b = pair

    with app.app_context():
        duplicate(a, b, tech["id"])

        # B de A: A ya es duplicado de B (y además está cerrado).
        with pytest.raises(TicketRuleError):
            duplicate(b, a, tech["id"])


def test_a_ticket_marked_as_duplicate_cannot_be_marked_again(app, tech, trio):
    a, b, c = trio

    with app.app_context():
        duplicate(a, b, tech["id"])

        ticket = get_ticket(a)
        change_state(
            ticket,
            actor=person(tech["id"]),
            action=Action.REABRIR,
            expected_version=ticket.version,
        )
        db.session.commit()

        with pytest.raises(TicketRuleError, match="ya figura como duplicado"):
            duplicate(a, c, tech["id"])


def test_the_duplicate_relation_is_listed_from_both_sides(app, tech, pair):
    dup, principal = pair

    with app.app_context():
        duplicate(dup, principal, tech["id"])

        (from_dup,) = list_relations(get_ticket(dup))
        (from_principal,) = list_relations(get_ticket(principal))

        assert (from_dup.kind, from_dup.other.public_id) == (KIND_DUPLICATE_OF, principal)
        assert (from_principal.kind, from_principal.other.public_id) == (
            KIND_PRINCIPAL_OF,
            dup,
        )
        assert duplicate_of(get_ticket(dup)).id == from_dup.relation.id
        assert duplicate_of(get_ticket(principal)) is None


def test_the_principal_can_have_several_duplicates(app, tech, trio):
    a, b, c = trio

    with app.app_context():
        duplicate(a, c, tech["id"])
        duplicate(b, c, tech["id"])

        views = list_relations(get_ticket(c))

        assert [v.kind for v in views] == [KIND_PRINCIPAL_OF, KIND_PRINCIPAL_OF]
        assert {v.other.public_id for v in views} == {a, b}


def test_marking_a_duplicate_transfers_nothing(app, tech, requester, pair):
    dup, principal = pair

    with app.app_context():
        before = [r.solicitante_id for r in get_ticket(principal).solicitantes_vigentes]
        duplicate(dup, principal, tech["id"])

        assert [
            r.solicitante_id for r in get_ticket(principal).solicitantes_vigentes
        ] == before == []
        # El duplicado conserva a su solicitante.
        assert [
            r.solicitante_id for r in get_ticket(dup).solicitantes_vigentes
        ] == [requester["id"]]


def test_marking_a_duplicate_with_a_stale_version_is_a_conflict(app, tech, pair):
    dup, principal = pair

    with app.app_context():
        with pytest.raises(TicketConflictError):
            duplicate(dup, principal, tech["id"], version=99)

        db.session.rollback()

        assert all_relations() == []
        assert get_ticket(dup).estado.codigo == "NUEVO"


def test_an_inactive_actor_cannot_mark_a_duplicate(app, make_user, pair):
    inactive = make_user("TECNICO", username="inactivo", activo=False)

    with app.app_context(), pytest.raises(TicketRuleError, match="no está activo"):
        duplicate(pair[0], pair[1], inactive["id"])


def test_a_failed_duplicate_leaves_nothing_behind(app, tech, pair):
    dup, principal = pair
    set_state(app, dup, "RESUELTO")

    with app.app_context():
        ticket = get_ticket(dup)

        with pytest.raises(StateTransitionError):
            mark_duplicate(
                ticket,
                principal,
                actor=person(tech["id"]),
                expected_version=ticket.version,
            )

        db.session.rollback()

        assert all_relations() == []
        assert relation_events(dup) == []


def test_two_people_marking_opposite_duplicates_at_once_create_no_cycle(
    app,
    make_user,
    tech,
    pair,
):
    """A de B y B de A a la vez: se bloquean las dos filas en orden de id, así
    que no hay interbloqueo y solo una prospera."""
    other = make_user("SUPERVISOR", username="otro")
    a, b = pair
    barrier = threading.Barrier(2)
    outcomes = []

    def attempt(duplicate_id, principal_id, user_id):
        with app.app_context():
            ticket = get_ticket(duplicate_id)
            actor = person(user_id)
            barrier.wait(timeout=10)

            try:
                mark_duplicate(
                    ticket,
                    principal_id,
                    actor=actor,
                    expected_version=1,
                )
                db.session.commit()
                outcomes.append("ok")
            except TicketRuleError as error:
                db.session.rollback()
                outcomes.append(type(error).__name__)
            finally:
                db.session.remove()

    threads = [
        threading.Thread(target=attempt, args=(a, b, tech["id"])),
        threading.Thread(target=attempt, args=(b, a, other["id"])),
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join(timeout=30)

    assert outcomes.count("ok") == 1
    assert len(outcomes) == 2

    with app.app_context():
        assert len(all_relations(active=True)) == 1


def test_a_duplicate_relation_cannot_be_removed_while_it_stays_closed(
    app,
    tech,
    trio,
):
    dup, principal, _ = trio

    with app.app_context():
        relation = duplicate(dup, principal, tech["id"])
        (view,) = list_relations(get_ticket(principal))

        assert view.removable is False

        # Desde el principal (abierto), el duplicado sigue cerrado.
        with pytest.raises(TicketRuleError, match="sigue cerrado"):
            remove(principal, relation.id, tech["id"])


def test_a_reopened_duplicate_can_have_its_relation_removed(app, tech, pair):
    dup, principal = pair

    with app.app_context():
        relation = duplicate(dup, principal, tech["id"])
        ticket = get_ticket(dup)
        change_state(
            ticket,
            actor=person(tech["id"]),
            action=Action.REABRIR,
            expected_version=ticket.version,
        )
        db.session.commit()

        # Reabierto: ya no es el rastro de un cierre.
        assert all(v.removable for v in list_relations(get_ticket(dup)))

        remove(dup, relation.id, tech["id"])

        assert list_relations(get_ticket(dup)) == []
        assert relation_events(dup)[-1].tipo_evento == "RELACION_ELIMINADA"
        # Reabrir conserva el cierre anterior en el historial, no la relación.
        assert duplicate_of(get_ticket(dup)) is None


def test_reopening_a_duplicate_keeps_the_relation_until_removed(app, tech, pair):
    dup, principal = pair

    with app.app_context():
        duplicate(dup, principal, tech["id"])
        ticket = get_ticket(dup)
        change_state(
            ticket,
            actor=person(tech["id"]),
            action=Action.REABRIR,
            expected_version=ticket.version,
        )
        db.session.commit()

        ticket = get_ticket(dup)

        assert ticket.estado.codigo == "EN_PROGRESO"
        assert ticket.motivo_cierre_id is None
        assert duplicate_of(ticket) is not None


# --- Historial: lo que ve cada rol --------------------------------------------------


def test_the_requester_never_receives_the_relation_events(
    app,
    tech,
    requester,
    pair,
):
    dup, principal = pair

    with app.app_context():
        add(dup, principal, tech["id"])
        history = list_ticket_history(get_ticket(dup), person(requester["id"]))

        assert "RELACION_AGREGADA" not in [h.tipo_evento for h in history]

        staff = list_ticket_history(get_ticket(dup), person(tech["id"]))

        assert "RELACION_AGREGADA" in [h.tipo_evento for h in staff]


def test_history_lines_describe_the_relation_events(app, tech, trio):
    a, b, c = trio

    with app.app_context():
        add(a, b, tech["id"])
        duplicate(c, b, tech["id"])
        removal = add(a, c, tech["id"])
        remove(a, removal.id, tech["id"])

        lines = [
            describe_history_changes(event)
            for event in relation_events(a) + relation_events(c)
        ]

        assert [f"Relacionado con #{b}"] in lines
        assert [f"Duplicado de #{b}"] in lines
        assert [f"Relación con #{c} eliminada"] in lines


# --- Pantallas -------------------------------------------------------------------------


def base(public_id):
    return f"/tickets/{public_id}"


def version_of(app, public_id):
    with app.app_context():
        return get_ticket(public_id).version


def state_of(app, public_id):
    with app.app_context():
        return get_ticket(public_id).estado.codigo


def relation_count(app):
    with app.app_context():
        return len(all_relations(active=True))


def test_the_requester_cannot_use_any_relation_screen(
    client,
    app,
    requester,
    pair,
):
    a, b = pair
    login(client, requester)

    for url in (
        f"{base(a)}/relations",
        f"{base(a)}/duplicate",
        f"{base(a)}/relations/1/remove",
    ):
        assert client.get(url).status_code == 403

    for url, data in (
        (f"{base(a)}/relations/add", {"ticket": b}),
        (f"{base(a)}/duplicate", {"ticket": b, "version": 1}),
        (f"{base(a)}/relations/1/remove", {}),
    ):
        assert client.post(url, data=data).status_code == 403

    assert relation_count(app) == 0
    assert state_of(app, a) == "NUEVO"


def test_a_ticket_the_user_cannot_see_is_a_404_on_every_relation_screen(
    client,
    app,
    make_user,
    pair,
):
    stranger = make_user("SOLICITANTE", username="ajeno")
    a, b = pair
    login(client, stranger)

    for url in (f"{base(a)}/relations", f"{base(a)}/duplicate"):
        assert client.get(url).status_code == 404

    assert (
        client.post(f"{base(a)}/relations/add", data={"ticket": b}).status_code == 404
    )
    assert client.get(f"{base(999999)}/relations").status_code == 404


def test_the_requester_does_not_see_the_relations_card(
    client,
    app,
    tech,
    requester,
    pair,
):
    a, b = pair

    with app.app_context():
        add(a, b, tech["id"])

    login(client, requester)
    page = plain_text(client.get(base(a)))

    assert "Relaciones" not in page
    assert "Ticket B" not in page
    assert f"/tickets/{a}/relations" not in client.get(base(a)).get_data(as_text=True)


def test_the_detail_shows_the_relations_card_to_staff(client, app, tech, pair):
    a, b = pair

    with app.app_context():
        add(a, b, tech["id"])

    login(client, tech)
    page = plain_text(client.get(base(a)))

    assert "Relaciones (1)" in page
    assert "Relacionado con" in page
    assert f"#{b}" in page and "Ticket B" in page
    assert f"/tickets/{a}/relations" in client.get(base(a)).get_data(as_text=True)


def test_the_relations_page_for_staff(client, app, tech, pair):
    a, b = pair

    with app.app_context():
        add(a, b, tech["id"], comment="Mismo cliente.")

    login(client, tech)
    response = client.get(f"{base(a)}/relations")
    page = plain_text(response)

    assert response.status_code == 200
    assert "Relaciones vigentes" in page
    assert "Relacionado con" in page and "Ticket B" in page
    assert "Mismo cliente." in page
    assert "Relacionar con otro ticket" in page
    assert "Marcar como duplicado" in page
    assert "Quitar" in page


def test_relating_through_the_screen(client, app, tech, pair):
    a, b = pair
    login(client, tech)

    response = client.post(
        f"{base(a)}/relations/add",
        data={"ticket": f"#{b}", "comentario": "Mismo cliente."},
        follow_redirects=True,
    )

    assert f"El ticket #{a} quedó relacionado con el #{b}." in plain_text(response)
    assert relation_count(app) == 1


@pytest.mark.parametrize(
    ("number", "message"),
    [
        ("", "Escribe el número del ticket."),
        ("abc", "Escribe el número del ticket, por ejemplo 12."),
        ("99999", "No existe el ticket #99999."),
    ],
)
def test_relating_through_the_screen_reports_bad_numbers(
    client,
    app,
    tech,
    pair,
    number,
    message,
):
    login(client, tech)
    response = client.post(
        f"{base(pair[0])}/relations/add",
        data={"ticket": number},
        follow_redirects=True,
    )

    assert message in plain_text(response)
    assert relation_count(app) == 0


def test_relating_with_itself_or_twice_is_reported(client, app, tech, pair):
    a, b = pair
    login(client, tech)

    own = client.post(
        f"{base(a)}/relations/add", data={"ticket": a}, follow_redirects=True
    )

    assert "consigo mismo" in plain_text(own)

    client.post(f"{base(a)}/relations/add", data={"ticket": b})
    twice = client.post(
        f"{base(b)}/relations/add", data={"ticket": a}, follow_redirects=True
    )

    assert "ya están relacionados" in plain_text(twice)
    assert relation_count(app) == 1


def test_a_long_comment_is_rejected_in_the_screen(client, app, tech, pair):
    a, b = pair
    login(client, tech)
    response = client.post(
        f"{base(a)}/relations/add",
        data={"ticket": b, "comentario": "x" * (MAX_RELATION_COMMENT_LENGTH + 1)},
        follow_redirects=True,
    )

    assert f"Máximo {MAX_RELATION_COMMENT_LENGTH} caracteres." in plain_text(response)
    assert relation_count(app) == 0


def test_removing_through_the_screen_asks_for_confirmation(
    client,
    app,
    tech,
    pair,
):
    a, b = pair

    with app.app_context():
        relation_id = add(a, b, tech["id"]).id

    login(client, tech)
    url = f"{base(a)}/relations/{relation_id}/remove"
    screen = client.get(url)

    assert screen.status_code == 200
    assert "Se quitará la relación" in text(screen)
    assert relation_count(app) == 1

    response = client.post(url, follow_redirects=True)

    assert f"Se quitó la relación con el ticket #{b}." in plain_text(response)
    assert relation_count(app) == 0


def test_removing_an_unknown_relation_in_the_screen_is_reported(
    client,
    tech,
    pair,
):
    login(client, tech)
    response = client.get(
        f"{base(pair[0])}/relations/999999/remove", follow_redirects=True
    )

    assert "Esa relación ya no existe o no se puede quitar." in plain_text(response)


def test_the_duplicate_screen_explains_what_will_happen(client, tech, pair):
    a, _ = pair
    login(client, tech)
    screen = client.get(f"{base(a)}/duplicate")
    page = plain_text(screen)

    assert screen.status_code == 200
    assert f"El ticket #{a} se cerrará con el motivo «Duplicado»" in page
    assert "Número del ticket" in page
    assert "Marcar como duplicado y cerrar" in page


def test_marking_a_duplicate_through_the_screen(client, app, tech, pair):
    a, b = pair
    login(client, tech)

    response = client.post(
        f"{base(a)}/duplicate",
        data={"ticket": b, "version": version_of(app, a), "comentario": "Igual."},
        follow_redirects=True,
    )
    page = plain_text(response)

    assert f"El ticket #{a} quedó cerrado como duplicado del #{b}." in page
    assert state_of(app, a) == "CERRADO"
    # El detalle del duplicado cerrado muestra el motivo y su relación.
    assert "Duplicado" in page
    assert "Duplicado de" in page and "Ticket B" in page

    with app.app_context():
        assert get_ticket(a).motivo_cierre.codigo == "DUPLICADO"


def test_the_principal_shows_its_duplicate(client, app, tech, pair):
    a, b = pair

    with app.app_context():
        duplicate(a, b, tech["id"])

    login(client, tech)
    page = plain_text(client.get(base(b)))

    assert "Su duplicado" in page and "Ticket A" in page


def test_the_duplicate_screen_keeps_what_was_typed_on_errors(
    client,
    app,
    tech,
    pair,
):
    a, _ = pair
    login(client, tech)
    response = client.post(
        f"{base(a)}/duplicate",
        data={"ticket": "99999", "version": version_of(app, a), "comentario": "Texto."},
    )

    assert response.status_code == 200
    assert "No existe el ticket #99999." in text(response)
    assert 'value="99999"' in response.get_data(as_text=True)
    assert "Texto." in response.get_data(as_text=True)
    assert state_of(app, a) == "NUEVO"


def test_the_duplicate_screen_needs_the_version(client, app, tech, pair):
    a, b = pair
    login(client, tech)
    response = client.post(f"{base(a)}/duplicate", data={"ticket": b})

    assert response.status_code == 200
    assert "No se pudo comprobar la versión del ticket" in text(response)
    assert state_of(app, a) == "NUEVO"


def test_a_stale_version_in_the_duplicate_screen_is_a_conflict(
    client,
    app,
    tech,
    pair,
):
    a, b = pair
    login(client, tech)
    response = client.post(
        f"{base(a)}/duplicate",
        data={"ticket": b, "version": 99},
        follow_redirects=True,
    )

    assert "Otra persona modificó este ticket" in plain_text(response)
    assert state_of(app, a) == "NUEVO"
    assert relation_count(app) == 0


def test_the_closed_summary_tells_the_requester_it_is_a_duplicate_but_not_of_what(
    client,
    app,
    tech,
    requester,
    pair,
):
    a, b = pair

    with app.app_context():
        duplicate(a, b, tech["id"], comment="Nota del equipo.")

    login(client, requester)
    page = plain_text(client.get(base(a)))

    assert "Duplicado" in page  # el motivo del cierre es público
    assert "Ticket B" not in page
    assert "Nota del equipo." not in page
    assert "Relación agregada" not in page


def test_closed_tickets_refuse_the_relation_screens_that_change_things(
    client,
    app,
    tech,
    pair,
):
    a, b = pair

    with app.app_context():
        relation_id = add(a, b, tech["id"]).id

    set_state(app, a, "CERRADO")
    login(client, tech)

    # Se puede ver la pantalla (las relaciones siguen visibles) pero no
    # cambiarlas.
    assert client.get(f"{base(a)}/relations").status_code == 200

    for url in (f"{base(a)}/duplicate", f"{base(a)}/relations/{relation_id}/remove"):
        response = client.get(url, follow_redirects=True)

        assert "Un ticket cerrado no se puede modificar." in plain_text(response)

    response = client.post(
        f"{base(a)}/relations/add", data={"ticket": b}, follow_redirects=True
    )

    assert "Un ticket cerrado no se puede modificar." in plain_text(response)


def test_the_duplicate_screen_is_not_offered_for_a_resolved_ticket(
    client,
    app,
    tech,
    pair,
):
    a, _ = pair
    set_state(app, a, "RESUELTO")
    login(client, tech)
    response = client.get(f"{base(a)}/duplicate", follow_redirects=True)

    assert "no se puede cerrar como duplicado" in plain_text(response)


def test_the_relation_screens_belong_to_the_tickets_menu(client, tech, pair):
    a, _ = pair
    login(client, tech)

    for url in (f"{base(a)}/relations", f"{base(a)}/duplicate"):
        html = client.get(url).get_data(as_text=True)

        assert 'aria-current="page"' in html
        assert "Tickets" in html


def test_relations_are_loaded_without_a_query_per_row(app, tech, trio):
    a, b, c = trio

    with app.app_context():
        add(a, b, tech["id"])
        add(a, c, tech["id"])

        ticket = get_ticket(a)
        statements = []

        def count(conn, cursor, statement, *args):
            statements.append(statement)

        from sqlalchemy import event

        event.listen(db.engine, "before_cursor_execute", count)

        try:
            views = list_relations(ticket)
            # Tocar el otro ticket, su estado y quién la creó no consulta más.
            for view in views:
                _ = (
                    view.other.estado.codigo,
                    view.relation.creada_por.nombre,
                    view.relation.tipo.codigo,
                )
        finally:
            event.remove(db.engine, "before_cursor_execute", count)

        assert len(views) == 2
        assert len(statements) == 1
