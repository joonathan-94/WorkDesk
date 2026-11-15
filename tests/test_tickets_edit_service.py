import pytest

from src.workdesk.extensions import db
from src.workdesk.models import (
    Categoria,
    Prioridad,
    Ticket,
    TicketEvent,
    TicketHistory,
    Ubicacion,
    User,
)
from src.workdesk.tickets.editing import (
    TicketClosedError,
    TicketConflictError,
    change_priority,
    describe_history_changes,
    update_ticket,
)
from src.workdesk.tickets.service import TicketRuleError
from tests.ticket_helpers import make_ticket, set_state, ticket_by_public_id


@pytest.fixture()
def staff(make_user, catalog):
    return make_user("TECNICO", username="personal")


@pytest.fixture()
def public_id(app, catalog, staff):
    return make_ticket(
        app,
        catalog,
        staff["id"],
        title="Título original",
        description="Descripción original",
    )


def edit(public_id, staff_id, catalog, **overrides):
    """Llama a `update_ticket` con los valores actuales salvo lo indicado."""
    ticket = ticket_by_public_id(public_id)
    values = {
        "expected_version": ticket.version,
        "title": ticket.titulo,
        "description": ticket.descripcion,
        "category_id": ticket.categoria_id,
        "location_id": ticket.ubicacion_id,
    }
    values.update(overrides)

    return ticket, update_ticket(
        ticket,
        actor=db.session.get(User, staff_id),
        **values,
    )


def events(ticket_id) -> list[TicketHistory]:
    return list(
        db.session.scalars(
            db.select(TicketHistory)
            .where(TicketHistory.ticket_id == ticket_id)
            .order_by(TicketHistory.id)
        )
    )


def event_types(ticket_id) -> list[str]:
    return [entry.tipo_evento for entry in events(ticket_id)]


# --- Editar datos -----------------------------------------------------


def test_updates_title_and_description_and_records_only_what_changed(
    app,
    catalog,
    staff,
    public_id,
):
    with app.app_context():
        ticket, changed = edit(
            public_id,
            staff["id"],
            catalog,
            title="  Título nuevo  ",
            description="Descripción original",
        )
        db.session.commit()

        assert changed is True
        assert ticket.titulo == "Título nuevo"
        assert ticket.descripcion == "Descripción original"

        entry = events(ticket.id)[-1]

        assert entry.tipo_evento == TicketEvent.TICKET_MODIFICADO.value
        assert entry.actor_usuario_id == staff["id"]
        # Solo se registra el campo que cambió.
        assert entry.valor_anterior == {"titulo": "Título original"}
        assert entry.valor_nuevo == {"titulo": "Título nuevo"}


def test_an_edit_raises_the_version_and_records_who_and_when(
    app,
    catalog,
    staff,
    public_id,
):
    with app.app_context():
        ticket = ticket_by_public_id(public_id)

        assert ticket.version == 1
        assert ticket.fecha_modificacion is None

        edit(public_id, staff["id"], catalog, title="Otro título")
        db.session.commit()

        ticket = ticket_by_public_id(public_id)

        assert ticket.version == 2
        assert ticket.usuario_modificacion_id == staff["id"]
        assert ticket.fecha_modificacion is not None
        assert ticket.fecha_actualizacion == ticket.fecha_modificacion


def test_a_category_change_has_its_own_event_with_names(
    app,
    catalog,
    staff,
    public_id,
):
    with app.app_context():
        ticket, changed = edit(
            public_id,
            staff["id"],
            catalog,
            category_id=catalog["networks"],
        )
        db.session.commit()

        assert changed is True
        assert ticket.categoria_id == catalog["networks"]
        assert event_types(ticket.id) == ["TICKET_CREADO", "CATEGORIA_CAMBIADA"]

        entry = events(ticket.id)[-1]

        assert entry.valor_anterior["nombre"] == "Hardware"
        assert entry.valor_nuevo["nombre"] == "Redes"
        assert "Hardware" in entry.detalle and "Redes" in entry.detalle


def test_editing_data_and_category_together_records_two_events(
    app,
    catalog,
    staff,
    public_id,
):
    with app.app_context():
        ticket, _ = edit(
            public_id,
            staff["id"],
            catalog,
            description="Descripción nueva",
            category_id=catalog["networks"],
        )
        db.session.commit()

        assert event_types(ticket.id) == [
            "TICKET_CREADO",
            "TICKET_MODIFICADO",
            "CATEGORIA_CAMBIADA",
        ]
        # Dos eventos, una sola subida de versión.
        assert ticket_by_public_id(public_id).version == 2


def test_setting_and_clearing_the_location(app, catalog, staff, public_id):
    with app.app_context():
        ticket, _ = edit(
            public_id,
            staff["id"],
            catalog,
            location_id=catalog["location"],
        )
        db.session.commit()

        added = events(ticket.id)[-1]

        assert added.valor_anterior == {"ubicacion": None}
        assert added.valor_nuevo == {"ubicacion": "Casa matriz"}

        ticket, _ = edit(public_id, staff["id"], catalog, location_id=None)
        db.session.commit()

        cleared = events(ticket.id)[-1]

        assert ticket.ubicacion_id is None
        assert cleared.valor_anterior == {"ubicacion": "Casa matriz"}
        assert cleared.valor_nuevo == {"ubicacion": None}


def test_an_edit_without_changes_does_nothing(app, catalog, staff, public_id):
    with app.app_context():
        ticket, changed = edit(
            public_id,
            staff["id"],
            catalog,
            # Mismos valores salvo espacios sobrantes.
            title="  Título original ",
            description=" Descripción original  ",
        )
        db.session.commit()

        assert changed is False
        assert ticket.version == 1
        assert ticket.fecha_modificacion is None
        assert event_types(ticket.id) == ["TICKET_CREADO"]


def test_an_edit_does_not_commit(app, catalog, staff, public_id):
    with app.app_context():
        edit(public_id, staff["id"], catalog, title="No confirmado")
        db.session.rollback()

        ticket = ticket_by_public_id(public_id)

        assert ticket.titulo == "Título original"
        assert ticket.version == 1
        assert event_types(ticket.id) == ["TICKET_CREADO"]


# --- Validaciones -----------------------------------------------------


@pytest.mark.parametrize(
    "overrides",
    [
        {"title": ""},
        {"title": "   "},
        {"title": "a" * 201},
        {"description": ""},
        {"description": "   "},
        {"description": "a" * 2001},
    ],
)
def test_the_same_rules_as_creation_apply(
    app,
    catalog,
    staff,
    public_id,
    overrides,
):
    with app.app_context():
        with pytest.raises(TicketRuleError):
            edit(public_id, staff["id"], catalog, **overrides)

        db.session.rollback()

        assert ticket_by_public_id(public_id).version == 1


def test_the_limits_are_accepted_exactly(app, catalog, staff, public_id):
    with app.app_context():
        ticket, changed = edit(
            public_id,
            staff["id"],
            catalog,
            title="t" * 200,
            description="d" * 2000,
        )

        assert changed is True
        assert len(ticket.titulo) == 200
        assert len(ticket.descripcion) == 2000


def test_a_new_category_or_location_must_be_active(
    app,
    catalog,
    staff,
    public_id,
):
    with app.app_context():
        db.session.get(Categoria, catalog["networks"]).activo = False
        db.session.get(Ubicacion, catalog["location"]).activo = False
        db.session.commit()

        with pytest.raises(TicketRuleError):
            edit(
                public_id,
                staff["id"],
                catalog,
                category_id=catalog["networks"],
            )

        db.session.rollback()

        with pytest.raises(TicketRuleError):
            edit(
                public_id,
                staff["id"],
                catalog,
                location_id=catalog["location"],
            )


def test_unknown_catalog_values_are_rejected(app, catalog, staff, public_id):
    with app.app_context():
        with pytest.raises(TicketRuleError):
            edit(public_id, staff["id"], catalog, category_id=999999)

        db.session.rollback()

        with pytest.raises(TicketRuleError):
            edit(public_id, staff["id"], catalog, location_id=999999)


def test_the_current_values_can_be_kept_even_if_they_were_deactivated(
    app,
    catalog,
    staff,
    make_user,
):
    # Desactivar un valor no obliga a cambiar los tickets que ya lo usan.
    public_id = make_ticket(
        app,
        catalog,
        staff["id"],
        category_id=catalog["networks"],
        location_id=catalog["location"],
    )

    with app.app_context():
        db.session.get(Categoria, catalog["networks"]).activo = False
        db.session.get(Ubicacion, catalog["location"]).activo = False
        db.session.commit()

        ticket, changed = edit(
            public_id,
            staff["id"],
            catalog,
            title="Solo cambia el título",
        )

        assert changed is True
        assert ticket.categoria_id == catalog["networks"]
        assert ticket.ubicacion_id == catalog["location"]
        # Y como no se cambió la categoría, no hay evento de categoría.
        assert "CATEGORIA_CAMBIADA" not in event_types(ticket.id)


def test_an_inactive_actor_cannot_edit(app, catalog, staff, public_id):
    with app.app_context():
        db.session.get(User, staff["id"]).activo = False
        db.session.commit()

        with pytest.raises(TicketRuleError):
            edit(public_id, staff["id"], catalog, title="X")


# --- Ticket cerrado ---------------------------------------------------


def test_a_closed_ticket_cannot_be_edited(app, catalog, staff, public_id):
    set_state(app, public_id, "CERRADO")

    with app.app_context():
        with pytest.raises(TicketClosedError):
            edit(public_id, staff["id"], catalog, title="No se puede")

        db.session.rollback()

        assert ticket_by_public_id(public_id).titulo == "Título original"


# --- Control de versión -----------------------------------------------


def test_a_stale_version_is_rejected_as_a_conflict(
    app,
    catalog,
    staff,
    public_id,
):
    with app.app_context():
        # La persona A abre el formulario con la versión 1...
        stale_version = ticket_by_public_id(public_id).version

        # ...la persona B guarda primero...
        edit(public_id, staff["id"], catalog, title="Cambio de B")
        db.session.commit()

        # ...y cuando A guarda, su versión ya no es la actual.
        with pytest.raises(TicketConflictError):
            edit(
                public_id,
                staff["id"],
                catalog,
                expected_version=stale_version,
                title="Cambio de A",
            )

        db.session.rollback()

        ticket = ticket_by_public_id(public_id)

        # El cambio de B se conserva y el de A no deja rastro.
        assert ticket.titulo == "Cambio de B"
        assert ticket.version == 2
        assert event_types(ticket.id) == ["TICKET_CREADO", "TICKET_MODIFICADO"]


def test_each_successful_edit_raises_the_version_by_one(
    app,
    catalog,
    staff,
    public_id,
):
    with app.app_context():
        for expected, title in ((1, "Uno"), (2, "Dos"), (3, "Tres")):
            ticket, _ = edit(
                public_id,
                staff["id"],
                catalog,
                expected_version=expected,
                title=title,
            )
            db.session.commit()

            assert ticket.version == expected + 1


# --- Cambio de prioridad ----------------------------------------------


def priority_change(public_id, staff_id, priority_id, reason, **overrides):
    ticket = ticket_by_public_id(public_id)
    values = {"expected_version": ticket.version}
    values.update(overrides)

    return ticket, change_priority(
        ticket,
        actor=db.session.get(User, staff_id),
        priority_id=priority_id,
        reason=reason,
        **values,
    )


def test_changing_the_priority_records_the_reason(
    app,
    catalog,
    staff,
    public_id,
):
    with app.app_context():
        ticket, changed = priority_change(
            public_id,
            staff["id"],
            catalog["high"],
            "  El cliente no puede trabajar  ",
        )
        db.session.commit()

        assert changed is True
        assert ticket.prioridad_id == catalog["high"]
        assert ticket.version == 2
        assert ticket.usuario_modificacion_id == staff["id"]

        entry = events(ticket.id)[-1]

        assert entry.tipo_evento == TicketEvent.PRIORIDAD_CAMBIADA.value
        assert entry.actor_usuario_id == staff["id"]
        assert entry.valor_anterior["codigo"] == "MEDIA"
        assert entry.valor_anterior["nombre"] == "Media"
        assert entry.valor_nuevo["codigo"] == "ALTA"
        assert entry.valor_nuevo["nombre"] == "Alta"
        # El motivo va en el contexto del evento, recortado.
        assert entry.contexto == {"motivo": "El cliente no puede trabajar"}
        assert "Media" in entry.detalle and "Alta" in entry.detalle


def test_the_same_priority_changes_nothing_and_records_nothing(
    app,
    catalog,
    staff,
    public_id,
):
    with app.app_context():
        # Aunque no se indique motivo: no hay nada que justificar.
        ticket, changed = priority_change(
            public_id,
            staff["id"],
            catalog["medium"],
            "",
        )
        db.session.commit()

        assert changed is False
        assert ticket.version == 1
        assert event_types(ticket.id) == ["TICKET_CREADO"]


@pytest.mark.parametrize("reason", [None, "", "   ", "x" * 501])
def test_the_reason_is_required_and_limited(
    app,
    catalog,
    staff,
    public_id,
    reason,
):
    with app.app_context():
        with pytest.raises(TicketRuleError):
            priority_change(public_id, staff["id"], catalog["high"], reason)

        db.session.rollback()

        ticket = ticket_by_public_id(public_id)

        assert ticket.prioridad_id == catalog["medium"]
        assert ticket.version == 1


def test_a_reason_of_exactly_the_maximum_is_accepted(
    app,
    catalog,
    staff,
    public_id,
):
    with app.app_context():
        _, changed = priority_change(
            public_id,
            staff["id"],
            catalog["high"],
            "x" * 500,
        )

        assert changed is True


def test_the_new_priority_must_exist_and_be_active(
    app,
    catalog,
    staff,
    public_id,
):
    with app.app_context():
        db.session.get(Prioridad, catalog["high"]).activo = False
        db.session.commit()

        for priority_id in (catalog["high"], 999999):
            with pytest.raises(TicketRuleError):
                priority_change(
                    public_id,
                    staff["id"],
                    priority_id,
                    "Motivo",
                )

            db.session.rollback()


def test_the_priority_of_a_closed_ticket_cannot_change(
    app,
    catalog,
    staff,
    public_id,
):
    set_state(app, public_id, "CERRADO")

    with app.app_context(), pytest.raises(TicketClosedError):
        priority_change(public_id, staff["id"], catalog["high"], "Motivo")


def test_a_priority_change_with_a_stale_version_is_a_conflict(
    app,
    catalog,
    staff,
    public_id,
):
    with app.app_context():
        edit(public_id, staff["id"], catalog, title="Otro cambio")
        db.session.commit()

        with pytest.raises(TicketConflictError):
            priority_change(
                public_id,
                staff["id"],
                catalog["high"],
                "Motivo",
                expected_version=1,
            )

        db.session.rollback()

        assert ticket_by_public_id(public_id).prioridad_id == catalog["medium"]


# --- Lectura del historial --------------------------------------------


def test_the_history_is_described_without_the_reason(
    app,
    catalog,
    staff,
    public_id,
):
    with app.app_context():
        edit(
            public_id,
            staff["id"],
            catalog,
            title="Nuevo",
            description="Otra descripción",
            category_id=catalog["networks"],
            location_id=catalog["location"],
        )
        priority_change(
            public_id,
            staff["id"],
            catalog["high"],
            "Motivo interno secreto",
        )
        db.session.commit()

        ticket = ticket_by_public_id(public_id)
        creation, modified, category, priority = events(ticket.id)

        assert describe_history_changes(creation) == []
        assert describe_history_changes(modified) == [
            "Título: «Título original» → «Nuevo»",
            "Descripción modificada.",
            "Ubicación: — → «Casa matriz»",
        ]
        assert describe_history_changes(category) == [
            "Categoría: «Hardware» → «Redes»"
        ]
        assert describe_history_changes(priority) == [
            "Prioridad: «Media» → «Alta»"
        ]

        for entry in (creation, modified, category, priority):
            assert "secreto" not in " ".join(describe_history_changes(entry))


def test_the_full_description_is_not_repeated_in_the_history(
    app,
    catalog,
    staff,
    public_id,
):
    with app.app_context():
        edit(
            public_id,
            staff["id"],
            catalog,
            description="Texto largo " * 50,
        )
        db.session.commit()

        modified = events(ticket_by_public_id(public_id).id)[-1]

        assert describe_history_changes(modified) == ["Descripción modificada."]


def test_an_unknown_event_has_no_description():
    entry = TicketHistory(tipo_evento="EVENTO_FUTURO")

    assert describe_history_changes(entry) == []


def test_ticket_model_version_defaults_to_one(app, catalog, staff, public_id):
    with app.app_context():
        assert db.session.scalar(db.select(Ticket.version)) == 1
