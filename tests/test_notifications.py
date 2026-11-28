"""Notificaciones internas: el modelo, sus restricciones y el servicio (docs/09, 22;
docs/06, RN-93 a RN-97; docs/04, RF-084 a RF-086).

Un aviso para un usuario: su contenido no se reescribe, solo evoluciona su lectura, y
cada quien ve únicamente las suyas.
"""

import threading
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError

from src.workdesk.extensions import db
from src.workdesk.models import Notificacion, NotificationEvent, Ticket
from src.workdesk.models.notificacion import (
    NOTIFICATION_EVENT_ICONS,
    NOTIFICATION_EVENT_LABELS,
    NotificationContentImmutableError,
)
from src.workdesk.notifications.service import (
    MAX_MESSAGE_LENGTH,
    MAX_TITLE_LENGTH,
    PAGE_SIZE,
    VIEW_ALL,
    VIEW_UNREAD,
    NotificationRuleError,
    count_notifications,
    count_unread,
    get_notification,
    list_notifications,
    mark_all_as_read,
    mark_as_read,
    notify,
    notify_many,
)
from tests.ticket_helpers import make_ticket, person

EVENT = NotificationEvent.TICKET_ASIGNADO


# --- Auxiliares -------------------------------------------------------------


@pytest.fixture()
def tecnico(make_user, catalog):
    return make_user("TECNICO", username="tecnico")


@pytest.fixture()
def otro(make_user, tecnico):
    return make_user("TECNICO", username="otro")


@pytest.fixture()
def ticket_id(app, catalog, tecnico):
    return make_ticket(app, catalog, tecnico["id"])


def send(user_id, message="Hola", event=EVENT, **extra) -> Notificacion:
    notification = notify(person(user_id), event, message=message, **extra)
    db.session.commit()

    return notification


def ticket_row(public_id) -> Ticket:
    return db.session.scalar(db.select(Ticket).where(Ticket.public_id == public_id))


# --- El vocabulario ----------------------------------------------------------------


def test_every_event_has_a_label_and_an_icon():
    for code in NotificationEvent:
        assert NOTIFICATION_EVENT_LABELS[code].strip(), code
        assert NOTIFICATION_EVENT_ICONS[code].strip(), code

    assert set(NOTIFICATION_EVENT_LABELS) == set(NotificationEvent)
    assert set(NOTIFICATION_EVENT_ICONS) == set(NotificationEvent)


def test_the_events_cover_what_the_requirements_name():
    # RF-084 y la fase 5 del roadmap.
    assert {event.value for event in NotificationEvent} >= {
        "TICKET_CREADO",
        "TICKET_ASIGNADO",
        "TICKET_REASIGNADO",
        "ESTADO_CAMBIADO",
        "COMENTARIO_PUBLICO",
        "NOTA_INTERNA",
        "TICKET_EN_ESPERA",
        "TICKET_RESUELTO",
        "VALIDACION_PENDIENTE",
        "TICKET_CERRADO",
        "TICKET_REABIERTO",
        "SLA_PROXIMO_A_VENCER",
        "SLA_VENCIDO",
    }


def test_labels_are_different_so_they_can_be_told_apart():
    labels = list(NOTIFICATION_EVENT_LABELS.values())

    assert len(set(labels)) == len(labels)


def test_a_notification_names_its_event_and_falls_back_for_an_unknown_one(app, tecnico):
    with app.app_context():
        known = send(tecnico["id"], event=NotificationEvent.SLA_VENCIDO)

        assert known.etiqueta == "SLA vencido"
        assert known.icono == "exclamation-triangle"

        # Un código que el vocabulario ya no tiene sigue mostrándose.
        old = send(tecnico["id"])
        old.tipo_evento = "EVENTO_ANTIGUO"

        assert old.etiqueta == "EVENTO_ANTIGUO"
        assert old.icono == "bell"
        db.session.rollback()


# --- Base de datos ---------------------------------------------------------------------


def test_a_new_notification_is_unread_and_dated(app, tecnico):
    with app.app_context():
        notification = send(tecnico["id"])

        assert notification.leida is False
        assert notification.fecha_lectura is None
        assert notification.fecha_creacion is not None
        assert notification.ticket_id is None
        assert notification.titulo is None


def test_notify_returns_the_notification_already_flushed(app, tecnico):
    # Quien genera un aviso puede usar su id sin esperar a ninguna otra consulta.
    with app.app_context():
        notification = notify(person(tecnico["id"]), EVENT, message="Hola")

        assert notification.id is not None
        db.session.rollback()


def test_reading_state_must_be_coherent(app, tecnico):
    with app.app_context():
        base = {"usuario_id": tecnico["id"], "tipo_evento": EVENT.value, "mensaje": "Hola"}

        for values in (
            {"leida": True},  # leída sin fecha de lectura
            {"leida": False, "fecha_lectura": datetime.now(UTC)},  # fecha sin leer
        ):
            db.session.add(Notificacion(**base, **values))

            with pytest.raises(IntegrityError):
                db.session.flush()

            db.session.rollback()

        # Las dos combinaciones coherentes sí.
        db.session.add(Notificacion(**base, leida=False))
        db.session.add(Notificacion(**base, leida=True, fecha_lectura=datetime.now(UTC)))
        db.session.commit()


@pytest.mark.parametrize("message", ["", "   ", "\n\t"])
def test_the_database_rejects_an_empty_message(app, tecnico, message):
    with app.app_context():
        db.session.add(
            Notificacion(usuario_id=tecnico["id"], tipo_evento=EVENT.value, mensaje=message)
        )

        with pytest.raises(IntegrityError):
            db.session.flush()

        db.session.rollback()


def test_a_notification_needs_an_existing_recipient(app, catalog):
    with app.app_context():
        db.session.add(
            Notificacion(usuario_id=999999, tipo_evento=EVENT.value, mensaje="Hola")
        )

        with pytest.raises(IntegrityError):
            db.session.flush()

        db.session.rollback()


def test_a_notification_may_exist_without_a_ticket_but_not_with_a_missing_one(
    app, tecnico
):
    with app.app_context():
        db.session.add(
            Notificacion(
                usuario_id=tecnico["id"],
                ticket_id=999999,
                tipo_evento=EVENT.value,
                mensaje="Hola",
            )
        )

        with pytest.raises(IntegrityError):
            db.session.flush()

        db.session.rollback()


def test_a_recipient_or_a_ticket_with_notifications_cannot_be_deleted(
    app, tecnico, ticket_id
):
    with app.app_context():
        send(tecnico["id"], ticket=ticket_row(ticket_id))

        for target in (person(tecnico["id"]), ticket_row(ticket_id)):
            db.session.delete(target)

            with pytest.raises(IntegrityError):
                db.session.flush()

            db.session.rollback()


def test_the_listing_index_exists(app):
    with app.app_context():
        # Solo el esquema de este proceso: el mismo índice existe en el de los demás procesos
        # y en el esquema desechable de `test_migrations`, que puede estar borrándose ahora.
        definition = db.session.scalar(
            db.text(
                "select indexdef from pg_indexes "
                "where schemaname = current_schema() "
                "and indexname = 'ix_notificaciones_usuario_leida_fecha'"
            )
        )

        assert definition is not None
        assert "(usuario_id, leida, fecha_creacion)" in definition


# --- El contenido no se reescribe ----------------------------------------------------


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("mensaje", "Otro mensaje"),
        ("titulo", "Otro título"),
        ("tipo_evento", "SLA_VENCIDO"),
        ("usuario_id", 999),
        ("ticket_id", 999),
        ("fecha_creacion", datetime(2020, 1, 1, tzinfo=UTC)),
    ],
)
def test_the_content_of_a_notification_cannot_be_rewritten(
    app, tecnico, field, value
):
    with app.app_context():
        notification = send(tecnico["id"], title="Título")
        setattr(notification, field, value)

        with pytest.raises(NotificationContentImmutableError):
            db.session.flush()

        db.session.rollback()


def test_only_the_reading_state_can_change_through_the_orm(app, tecnico):
    with app.app_context():
        notification = send(tecnico["id"])
        notification.leida = True
        notification.fecha_lectura = datetime.now(UTC)
        db.session.commit()

        assert db.session.get(Notificacion, notification.id).leida is True


# --- Crear ---------------------------------------------------------------------------


def test_notify_stores_everything_it_is_given(app, tecnico, ticket_id):
    with app.app_context():
        ticket = ticket_row(ticket_id)
        notification = notify(
            person(tecnico["id"]),
            EVENT,
            message="  Se te asignó el ticket.  ",
            title="  Ticket asignado  ",
            ticket=ticket,
        )
        db.session.commit()

        assert notification.usuario_id == tecnico["id"]
        assert notification.ticket_id == ticket.id
        assert notification.tipo_evento == "TICKET_ASIGNADO"
        assert notification.titulo == "Ticket asignado"
        assert notification.mensaje == "Se te asignó el ticket."
        assert notification.ticket is ticket


def test_notify_accepts_the_event_code_as_text(app, tecnico):
    with app.app_context():
        notification = send(tecnico["id"], event="SLA_VENCIDO")

        assert notification.tipo_evento == "SLA_VENCIDO"


def test_notify_does_not_commit(app, tecnico):
    with app.app_context():
        notify(person(tecnico["id"]), EVENT, message="Hola")
        db.session.rollback()

        assert db.session.scalar(db.select(db.func.count(Notificacion.id))) == 0


@pytest.mark.parametrize("event", ["NO_EXISTE", "", "ticket_asignado", None])
def test_an_unknown_event_is_rejected(app, tecnico, event):
    with app.app_context(), pytest.raises(NotificationRuleError, match="evento"):
        notify(person(tecnico["id"]), event, message="Hola")


@pytest.mark.parametrize("message", ["", "   ", None])
def test_a_message_is_required(app, tecnico, message):
    with app.app_context(), pytest.raises(NotificationRuleError, match="mensaje"):
        notify(person(tecnico["id"]), EVENT, message=message)


def test_message_and_title_limits_are_exact(app, tecnico):
    with app.app_context():
        send(tecnico["id"], message="x" * MAX_MESSAGE_LENGTH, title="t" * MAX_TITLE_LENGTH)

        with pytest.raises(NotificationRuleError, match="mensaje"):
            notify(person(tecnico["id"]), EVENT, message="x" * (MAX_MESSAGE_LENGTH + 1))

        with pytest.raises(NotificationRuleError, match="título"):
            notify(
                person(tecnico["id"]),
                EVENT,
                message="Hola",
                title="t" * (MAX_TITLE_LENGTH + 1),
            )

        db.session.rollback()


def test_a_blank_title_is_stored_as_none(app, tecnico):
    with app.app_context():
        assert send(tecnico["id"], title="   ").titulo is None


def test_a_rejected_notification_leaves_nothing_behind(app, tecnico):
    with app.app_context():
        with pytest.raises(NotificationRuleError):
            notify(person(tecnico["id"]), EVENT, message="")

        db.session.commit()
        assert db.session.scalar(db.select(db.func.count(Notificacion.id))) == 0


def test_an_inactive_recipient_receives_nothing(app, make_user, catalog):
    inactive = make_user("TECNICO", username="inactivo", activo=False)

    with app.app_context():
        assert notify(person(inactive["id"]), EVENT, message="Hola") is None
        db.session.commit()

        assert db.session.scalar(db.select(db.func.count(Notificacion.id))) == 0


def test_notify_many_notifies_each_person_once_and_skips_the_inactive(
    app, tecnico, otro, make_user
):
    inactive = make_user("TECNICO", username="inactivo", activo=False)

    with app.app_context():
        people = [
            person(tecnico["id"]),
            person(otro["id"]),
            person(tecnico["id"]),  # repetido
            person(inactive["id"]),
        ]
        created = notify_many(people, EVENT, message="Aviso para todos")
        db.session.commit()

        assert sorted(n.usuario_id for n in created) == sorted([tecnico["id"], otro["id"]])
        assert db.session.scalar(db.select(db.func.count(Notificacion.id))) == 2


# --- Consultar ----------------------------------------------------------------------


def test_the_counts_are_per_user(app, tecnico, otro):
    with app.app_context():
        first = send(tecnico["id"])
        send(tecnico["id"])
        send(tecnico["id"])
        send(otro["id"])
        mark_as_read(person(tecnico["id"]), first.id)
        db.session.commit()

        assert count_unread(person(tecnico["id"])) == 2
        assert count_unread(person(otro["id"])) == 1

        counts = count_notifications(person(tecnico["id"]))

        assert (counts.total, counts.unread) == (3, 2)


def test_a_user_without_notifications_has_zero(app, tecnico):
    with app.app_context():
        counts = count_notifications(person(tecnico["id"]))

        assert (counts.total, counts.unread) == (0, 0)
        assert count_unread(person(tecnico["id"])) == 0


def test_the_listing_shows_only_my_notifications_newest_first(app, tecnico, otro):
    with app.app_context():
        for number in range(3):
            send(tecnico["id"], message=f"Mensaje {number}")

        send(otro["id"], message="Del otro")

        items = list_notifications(person(tecnico["id"])).items

        # Cada una se creó en su propia transacción: la más nueva va primero.
        assert [n.mensaje for n in items] == ["Mensaje 2", "Mensaje 1", "Mensaje 0"]


def test_notifications_created_at_the_same_instant_keep_a_stable_order(app, tecnico):
    with app.app_context():
        moment = datetime(2026, 11, 16, 10, 0, tzinfo=UTC)

        for number in range(3):
            db.session.add(
                Notificacion(
                    usuario_id=tecnico["id"],
                    tipo_evento=EVENT.value,
                    mensaje=f"Mensaje {number}",
                    fecha_creacion=moment,
                )
            )

        db.session.commit()
        items = list_notifications(person(tecnico["id"])).items

        assert [n.mensaje for n in items] == ["Mensaje 2", "Mensaje 1", "Mensaje 0"]


def test_many_notifications_at_the_same_instant_are_listed_newest_id_first(app, tecnico):
    # Todas las de una misma transacción comparten la fecha: sin un desempate por id,
    # el orden (y con él la paginación) quedaría a merced de la base de datos.
    with app.app_context():
        moment = datetime(2026, 11, 16, 10, 0, tzinfo=UTC)

        for number in range(PAGE_SIZE + 10):
            db.session.add(
                Notificacion(
                    usuario_id=tecnico["id"],
                    tipo_evento=EVENT.value,
                    mensaje=f"Mensaje {number}",
                    fecha_creacion=moment,
                )
            )

        db.session.commit()
        user = person(tecnico["id"])
        everything = sorted(
            db.session.scalars(
                db.select(Notificacion.id).where(Notificacion.usuario_id == user.id)
            ),
            reverse=True,
        )

        # Marcar las más antiguas como leídas reescribe sus filas, que PostgreSQL deja
        # al final de la tabla: así el orden físico no coincide con el de los ids y
        # un orden sin desempate no podría acertar por casualidad.
        for oldest in everything[-5:]:
            mark_as_read(user, oldest)

        db.session.commit()
        first = [n.id for n in list_notifications(user, page=1).items]
        second = [n.id for n in list_notifications(user, page=2).items]

        assert first + second == everything


def test_a_page_holds_twenty_notifications(app, tecnico):
    # El tamaño documentado (docs/11, UI-008): la 21.ª pasa a la página siguiente.
    assert PAGE_SIZE == 20

    with app.app_context():
        for number in range(21):
            db.session.add(
                Notificacion(
                    usuario_id=tecnico["id"],
                    tipo_evento=EVENT.value,
                    mensaje=f"Mensaje {number}",
                    fecha_creacion=datetime(2026, 11, 16, tzinfo=UTC) + timedelta(minutes=number),
                )
            )

        db.session.commit()
        user = person(tecnico["id"])

        assert len(list_notifications(user, page=1).items) == 20
        assert len(list_notifications(user, page=2).items) == 1


def test_the_unread_view_hides_the_read_ones(app, tecnico):
    with app.app_context():
        first = send(tecnico["id"], message="Primera")
        send(tecnico["id"], message="Segunda")
        mark_as_read(person(tecnico["id"]), first.id)
        db.session.commit()

        everything = list_notifications(person(tecnico["id"]), view=VIEW_ALL).items
        unread = list_notifications(person(tecnico["id"]), view=VIEW_UNREAD).items

        assert [n.mensaje for n in everything] == ["Segunda", "Primera"]
        assert [n.mensaje for n in unread] == ["Segunda"]

        # Un filtro desconocido es «todas».
        assert len(list_notifications(person(tecnico["id"]), view="otra-cosa").items) == 2


def test_the_listing_is_paginated(app, tecnico):
    with app.app_context():
        for number in range(PAGE_SIZE * 2 + 5):
            db.session.add(
                Notificacion(
                    usuario_id=tecnico["id"],
                    tipo_evento=EVENT.value,
                    mensaje=f"Mensaje {number}",
                    fecha_creacion=datetime(2026, 11, 16, tzinfo=UTC) + timedelta(minutes=number),
                )
            )

        db.session.commit()
        user = person(tecnico["id"])
        first = list_notifications(user, page=1)
        third = list_notifications(user, page=3)
        beyond = list_notifications(user, page=99)

        assert first.total == PAGE_SIZE * 2 + 5
        assert first.pages == 3
        assert len(first.items) == PAGE_SIZE
        assert first.items[0].mensaje == f"Mensaje {PAGE_SIZE * 2 + 4}"
        assert len(third.items) == 5
        assert beyond.items == []


def test_showing_the_listing_with_tickets_costs_a_fixed_number_of_queries(
    app, tecnico, ticket_id
):
    with app.app_context():
        ticket = ticket_row(ticket_id)

        for _ in range(10):
            send(tecnico["id"], ticket=ticket)

        user = person(tecnico["id"])
        queries = []

        def count(conn, cursor, statement, *args):
            queries.append(statement)

        event.listen(db.engine, "before_cursor_execute", count)

        try:
            page = list_notifications(user)
            shown = [n.ticket.public_id for n in page.items]
        finally:
            event.remove(db.engine, "before_cursor_execute", count)

        assert len(shown) == 10
        # La página y el total: el ticket viene en la misma consulta.
        assert len(queries) <= 2


def test_someone_elses_notification_does_not_exist_for_me(app, tecnico, otro):
    with app.app_context():
        mine = send(tecnico["id"])
        theirs = send(otro["id"])

        assert get_notification(person(tecnico["id"]), mine.id).id == mine.id
        assert get_notification(person(tecnico["id"]), theirs.id) is None
        assert get_notification(person(tecnico["id"]), 999999) is None


# --- Estado de lectura (RF-086) ------------------------------------------------------


def test_marking_as_read_sets_the_first_reading_date(app, tecnico):
    with app.app_context():
        notification = send(tecnico["id"])

        result = mark_as_read(person(tecnico["id"]), notification.id)
        db.session.commit()

        assert result.leida is True
        assert result.fecha_lectura is not None
        assert count_unread(person(tecnico["id"])) == 0


def test_marking_again_does_not_change_the_first_reading_date(app, tecnico):
    with app.app_context():
        notification = send(tecnico["id"])
        user = person(tecnico["id"])

        first = mark_as_read(user, notification.id).fecha_lectura
        db.session.commit()

        # La fecha de lectura es la de la primera vez, aunque pase el tiempo.
        db.session.execute(db.text("select pg_sleep(0.05)"))
        again = mark_as_read(user, notification.id).fecha_lectura
        db.session.commit()

        assert again == first


def test_the_content_survives_being_read(app, tecnico, ticket_id):
    with app.app_context():
        notification = send(
            tecnico["id"], message="Mensaje", title="Título", ticket=ticket_row(ticket_id)
        )
        before = (notification.mensaje, notification.titulo, notification.ticket_id)

        mark_as_read(person(tecnico["id"]), notification.id)
        db.session.commit()
        db.session.refresh(notification)

        assert (notification.mensaje, notification.titulo, notification.ticket_id) == before
        # Leer no la elimina.
        assert db.session.scalar(db.select(db.func.count(Notificacion.id))) == 1


def test_nobody_can_mark_someone_elses_notification(app, tecnico, otro):
    with app.app_context():
        theirs = send(otro["id"])

        assert mark_as_read(person(tecnico["id"]), theirs.id) is None
        db.session.commit()

        assert db.session.get(Notificacion, theirs.id).leida is False


def test_marking_an_unknown_notification_is_none(app, tecnico):
    with app.app_context():
        assert mark_as_read(person(tecnico["id"]), 999999) is None


def test_marking_all_reads_only_my_unread_ones(app, tecnico, otro):
    with app.app_context():
        read_before = send(tecnico["id"], message="Ya leída")
        user = person(tecnico["id"])
        mark_as_read(user, read_before.id)
        db.session.commit()
        original_date = db.session.get(Notificacion, read_before.id).fecha_lectura

        send(tecnico["id"], message="Nueva 1")
        send(tecnico["id"], message="Nueva 2")
        send(otro["id"], message="Del otro")

        changed = mark_all_as_read(user)
        db.session.commit()

        assert changed == 2
        assert count_unread(user) == 0
        assert count_unread(person(otro["id"])) == 1
        # La que ya estaba leída conserva su fecha.
        assert db.session.get(Notificacion, read_before.id).fecha_lectura == original_date
        # Y repetirlo no cambia nada.
        assert mark_all_as_read(user) == 0


def test_two_tabs_marking_the_same_notification_read_leave_one_reading_date(
    app, tecnico
):
    with app.app_context():
        notification_id = send(tecnico["id"]).id

    barrier = threading.Barrier(2)
    results = []

    def run():
        with app.app_context():
            barrier.wait(timeout=10)

            try:
                result = mark_as_read(person(tecnico["id"]), notification_id)
                db.session.commit()
                results.append((result.leida, result.fecha_lectura))
            finally:
                db.session.remove()

    threads = [threading.Thread(target=run) for _ in range(2)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join(timeout=30)

    assert len(results) == 2
    assert all(leida for leida, _ in results)

    with app.app_context():
        stored = db.session.get(Notificacion, notification_id)

        # Gana la primera: la segunda no la vuelve a fechar.
        assert stored.leida is True
        assert stored.fecha_lectura in {date for _, date in results}
        assert count_unread(person(tecnico["id"])) == 0
