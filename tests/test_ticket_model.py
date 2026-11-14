from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from src.workdesk.extensions import db
from src.workdesk.models import (
    Estado,
    MotivoCierre,
    Ticket,
    TicketEvent,
    TicketHistory,
    TicketRequester,
    User,
)
from src.workdesk.models.ticket_history import TicketHistoryImmutableError


def _new_ticket(ids, creator_id, **overrides) -> Ticket:
    state = db.session.scalar(db.select(Estado).where(Estado.codigo == "NUEVO"))

    values = {
        "titulo": "No funciona la impresora",
        "descripcion": "Se queda atascada al imprimir.",
        "creado_por_usuario_id": creator_id,
        "categoria_id": ids["category_id"],
        "prioridad_id": ids["priority_id"],
        "estado_id": state.id,
    }
    values.update(overrides)

    ticket = Ticket(**values)
    db.session.add(ticket)
    db.session.flush()

    return ticket


@pytest.fixture()
def creator(make_user, ticket_catalog_ids):
    return make_user("SOLICITANTE")


# --- Ticket ----------------------------------------------------------------


def test_ticket_gets_defaults_from_the_database(app, creator, ticket_catalog_ids):
    with app.app_context():
        ticket = _new_ticket(ticket_catalog_ids, creator["id"])
        db.session.commit()
        db.session.refresh(ticket)

        assert ticket.version == 1
        assert ticket.activo is True
        assert ticket.cerrado_automaticamente is False
        assert ticket.fecha_creacion is not None
        assert ticket.fecha_cierre is None
        assert ticket.ubicacion_id is None


def test_public_id_is_a_consecutive_number_stored_as_text(
    app, creator, ticket_catalog_ids
):
    with app.app_context():
        first = _new_ticket(ticket_catalog_ids, creator["id"])
        second = _new_ticket(ticket_catalog_ids, creator["id"])
        db.session.commit()

        assert isinstance(first.public_id, str)
        assert int(second.public_id) == int(first.public_id) + 1


def test_public_id_is_unique(app, creator, ticket_catalog_ids):
    with app.app_context():
        first = _new_ticket(ticket_catalog_ids, creator["id"])

        with pytest.raises(IntegrityError):
            _new_ticket(
                ticket_catalog_ids,
                creator["id"],
                public_id=first.public_id,
            )


def test_ticket_requires_a_valid_category(app, creator, ticket_catalog_ids):
    with app.app_context(), pytest.raises(IntegrityError):
        _new_ticket(ticket_catalog_ids, creator["id"], categoria_id=999999)


def test_version_must_be_at_least_one(app, creator, ticket_catalog_ids):
    with app.app_context(), pytest.raises(IntegrityError):
        _new_ticket(ticket_catalog_ids, creator["id"], version=0)


def test_closing_date_and_reason_go_together(app, creator, ticket_catalog_ids):
    with app.app_context(), pytest.raises(IntegrityError):
        _new_ticket(
            ticket_catalog_ids,
            creator["id"],
            fecha_cierre=datetime.now(UTC),
        )


def test_a_ticket_with_closing_date_and_reason_is_valid(
    app, creator, ticket_catalog_ids
):
    with app.app_context():
        reason = db.session.scalar(
            db.select(MotivoCierre).where(MotivoCierre.codigo == "CANCELACION")
        )

        ticket = _new_ticket(
            ticket_catalog_ids,
            creator["id"],
            fecha_cierre=datetime.now(UTC),
            motivo_cierre_id=reason.id,
            cerrado_por_usuario_id=creator["id"],
        )

        assert ticket.id is not None


def test_an_automatic_closing_cannot_have_a_closing_user(
    app, creator, ticket_catalog_ids
):
    with app.app_context():
        reason = db.session.scalar(
            db.select(MotivoCierre).where(MotivoCierre.codigo == "INACTIVIDAD")
        )

        with pytest.raises(IntegrityError):
            _new_ticket(
                ticket_catalog_ids,
                creator["id"],
                fecha_cierre=datetime.now(UTC),
                motivo_cierre_id=reason.id,
                cerrado_automaticamente=True,
                cerrado_por_usuario_id=creator["id"],
            )


def test_a_user_who_created_a_ticket_cannot_be_deleted(
    app, creator, ticket_catalog_ids
):
    with app.app_context():
        _new_ticket(ticket_catalog_ids, creator["id"])
        db.session.commit()

        user = db.session.get(User, creator["id"])
        db.session.delete(user)

        with pytest.raises(IntegrityError):
            db.session.commit()


# --- Solicitantes ----------------------------------------------------------


def test_a_ticket_can_have_no_requesters(app, creator, ticket_catalog_ids):
    with app.app_context():
        ticket = _new_ticket(ticket_catalog_ids, creator["id"])
        db.session.commit()

        assert ticket.solicitantes == []


def test_a_requester_cannot_be_current_twice_in_the_same_ticket(
    app, creator, ticket_catalog_ids
):
    with app.app_context():
        ticket = _new_ticket(ticket_catalog_ids, creator["id"])
        db.session.add(
            TicketRequester(ticket_id=ticket.id, solicitante_id=creator["id"])
        )
        db.session.flush()

        db.session.add(
            TicketRequester(ticket_id=ticket.id, solicitante_id=creator["id"])
        )

        with pytest.raises(IntegrityError):
            db.session.flush()


def test_a_removed_requester_can_be_associated_again(
    app, creator, ticket_catalog_ids
):
    with app.app_context():
        ticket = _new_ticket(ticket_catalog_ids, creator["id"])
        now = datetime.now(UTC)
        db.session.add(
            TicketRequester(
                ticket_id=ticket.id,
                solicitante_id=creator["id"],
                fecha_asociacion=now - timedelta(days=1),
                fecha_retiro=now,
            )
        )
        db.session.add(
            TicketRequester(ticket_id=ticket.id, solicitante_id=creator["id"])
        )
        db.session.commit()

        assert len(ticket.solicitantes) == 2


def test_withdrawal_cannot_precede_association(app, creator, ticket_catalog_ids):
    with app.app_context():
        ticket = _new_ticket(ticket_catalog_ids, creator["id"])
        now = datetime.now(UTC)
        db.session.add(
            TicketRequester(
                ticket_id=ticket.id,
                solicitante_id=creator["id"],
                fecha_asociacion=now,
                fecha_retiro=now - timedelta(days=1),
            )
        )

        with pytest.raises(IntegrityError):
            db.session.flush()


# --- Historial -------------------------------------------------------------


def _history_entry(ticket_id, **overrides) -> TicketHistory:
    values = {
        "ticket_id": ticket_id,
        "actor_tipo": "SISTEMA",
        "tipo_evento": TicketEvent.TICKET_CREADO.value,
    }
    values.update(overrides)

    return TicketHistory(**values)


def test_history_can_record_a_system_event(app, creator, ticket_catalog_ids):
    with app.app_context():
        ticket = _new_ticket(ticket_catalog_ids, creator["id"])
        entry = _history_entry(ticket.id, contexto={"motivo": "prueba"})
        db.session.add(entry)
        db.session.commit()

        assert entry.actor_usuario_id is None
        assert entry.fecha_hora is not None
        assert entry.contexto == {"motivo": "prueba"}


def test_history_actor_must_match_the_actor_type(app, creator, ticket_catalog_ids):
    with app.app_context():
        ticket = _new_ticket(ticket_catalog_ids, creator["id"])

        db.session.add(_history_entry(ticket.id, actor_tipo="USUARIO"))

        with pytest.raises(IntegrityError):
            db.session.flush()


def test_history_rejects_an_unknown_event_type(app, creator, ticket_catalog_ids):
    with app.app_context():
        ticket = _new_ticket(ticket_catalog_ids, creator["id"])

        db.session.add(_history_entry(ticket.id, tipo_evento="INVENTADO"))

        with pytest.raises(IntegrityError):
            db.session.flush()


def test_history_events_cannot_be_modified(app, creator, ticket_catalog_ids):
    with app.app_context():
        ticket = _new_ticket(ticket_catalog_ids, creator["id"])
        entry = _history_entry(ticket.id)
        db.session.add(entry)
        db.session.commit()

        entry.detalle = "alterado"

        with pytest.raises(TicketHistoryImmutableError):
            db.session.commit()


def test_history_events_cannot_be_deleted(app, creator, ticket_catalog_ids):
    with app.app_context():
        ticket = _new_ticket(ticket_catalog_ids, creator["id"])
        entry = _history_entry(ticket.id)
        db.session.add(entry)
        db.session.commit()

        db.session.delete(entry)

        with pytest.raises(TicketHistoryImmutableError):
            db.session.commit()
