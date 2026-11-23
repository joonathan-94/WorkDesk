"""Bloqueo temporal de edición de un ticket (docs/06, RN-115 a RN-117;
docs/09, 28; docs/10, secciones 71 a 74).

Mientras alguien tiene abierta la pantalla de editar o de cambiar la prioridad,
el ticket queda reservado para esa persona. Es una mejora de la experiencia: la
versión del ticket (`tickets.version`) sigue siendo la barrera final, y eso lo
cubren `test_tickets_edit_service.py` y `test_tickets_edit_routes.py`.
"""

import threading
from datetime import timedelta

import pytest
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from src.workdesk import create_app
from src.workdesk.extensions import db
from src.workdesk.models import TicketEditLock
from src.workdesk.tickets.locking import (
    acquire_edit_lock,
    current_edit_lock,
    release_edit_lock,
)
from src.workdesk.tickets.service import TicketRuleError
from tests.ticket_helpers import (
    login,
    make_ticket,
    person,
    plain_text,
    set_state,
    text,
    ticket_by_public_id,
)

# --- Auxiliares -------------------------------------------------------------


def acquire(public_id, user_id):
    status = acquire_edit_lock(ticket_by_public_id(public_id), person(user_id))
    db.session.commit()

    return status


def release(public_id, user_id) -> bool:
    released = release_edit_lock(ticket_by_public_id(public_id), person(user_id))
    db.session.commit()

    return released


def locks_of(public_id) -> list[TicketEditLock]:
    return list(
        db.session.scalars(
            db.select(TicketEditLock)
            .where(TicketEditLock.ticket_id == ticket_by_public_id(public_id).id)
            .order_by(TicketEditLock.id)
        )
    )


def unreleased(public_id) -> list[TicketEditLock]:
    return [lock for lock in locks_of(public_id) if lock.fecha_liberacion is None]


def expire(public_id, *, minutes=10):
    """Deja el bloqueo no liberado del ticket como expirado: mueve su inicio y
    su expiración al pasado (la base exige que la expiración sea posterior al
    inicio)."""
    with_ticket = ticket_by_public_id(public_id).id
    db.session.execute(
        update(TicketEditLock.__table__)
        .where(
            TicketEditLock.__table__.c.ticket_id == with_ticket,
            TicketEditLock.__table__.c.fecha_liberacion.is_(None),
        )
        .values(
            fecha_inicio=db.func.clock_timestamp() - timedelta(minutes=minutes),
            fecha_expiracion=db.func.clock_timestamp()
            - timedelta(minutes=minutes - 5),
        )
    )
    db.session.commit()


@pytest.fixture()
def alice(make_user, catalog):
    return make_user("TECNICO", username="alicia", nombre="Alicia", apellido="Mora")


@pytest.fixture()
def bruno(make_user, catalog):
    return make_user("SUPERVISOR", username="bruno", nombre="Bruno", apellido="Rey")


@pytest.fixture()
def requester(make_user, catalog):
    return make_user("SOLICITANTE", username="solicitante")


@pytest.fixture()
def ticket_id(app, catalog, alice, requester):
    return make_ticket(app, catalog, alice["id"], requester_ids=[requester["id"]])


@pytest.fixture()
def other_ticket(app, catalog, alice):
    return make_ticket(app, catalog, alice["id"], title="Otro ticket")


# --- Configuración -----------------------------------------------------------


def test_the_default_lock_times_are_120_and_45_seconds(app):
    assert app.config["EDIT_LOCK_TTL_SECONDS"] == 120
    assert app.config["EDIT_LOCK_HEARTBEAT_SECONDS"] == 45


@pytest.mark.parametrize(
    ("ttl", "heartbeat"),
    [
        (0, 45),
        (-10, 45),
        (120, 0),
        (120, -1),
        # El latido debe ser menor que la duración: si no, el bloqueo expiraría
        # entre dos renovaciones aunque la persona siga editando.
        (45, 45),
        (30, 45),
    ],
)
def test_the_app_rejects_inconsistent_lock_times(ttl, heartbeat):
    config = {
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "EDIT_LOCK_TTL_SECONDS": ttl,
        "EDIT_LOCK_HEARTBEAT_SECONDS": heartbeat,
    }

    with pytest.raises(RuntimeError, match="EDIT_LOCK"):
        create_app(config)


# --- Base de datos -----------------------------------------------------------


def _lock_row(ticket, user_id, *, start, end, release=None):
    return TicketEditLock(
        ticket_id=ticket.id,
        usuario_id=user_id,
        fecha_inicio=start,
        fecha_expiracion=end,
        fecha_liberacion=release,
    )


def test_the_database_allows_one_unreleased_lock_per_ticket(
    app,
    alice,
    bruno,
    ticket_id,
):
    with app.app_context():
        now = db.session.scalar(db.select(db.func.clock_timestamp()))
        ticket = ticket_by_public_id(ticket_id)

        db.session.add(
            _lock_row(ticket, alice["id"], start=now, end=now + timedelta(minutes=2))
        )
        db.session.commit()

        db.session.add(
            _lock_row(ticket, bruno["id"], start=now, end=now + timedelta(minutes=2))
        )

        with pytest.raises(IntegrityError):
            db.session.commit()


def test_released_locks_do_not_count_against_the_unique_index(
    app,
    alice,
    bruno,
    ticket_id,
):
    with app.app_context():
        now = db.session.scalar(db.select(db.func.clock_timestamp()))
        ticket = ticket_by_public_id(ticket_id)
        end = now + timedelta(minutes=2)

        db.session.add_all(
            [
                _lock_row(ticket, alice["id"], start=now, end=end, release=now),
                _lock_row(ticket, bruno["id"], start=now, end=end, release=now),
                _lock_row(ticket, alice["id"], start=now, end=end),
            ]
        )
        db.session.commit()

        assert len(locks_of(ticket_id)) == 3


@pytest.mark.parametrize(
    ("end_offset", "release_offset"),
    [
        (0, None),  # expira cuando empieza
        (-60, None),  # expira antes de empezar
        (120, -60),  # se libera antes de empezar
    ],
)
def test_the_database_checks_the_lock_times(
    app,
    alice,
    ticket_id,
    end_offset,
    release_offset,
):
    with app.app_context():
        now = db.session.scalar(db.select(db.func.clock_timestamp()))
        db.session.add(
            _lock_row(
                ticket_by_public_id(ticket_id),
                alice["id"],
                start=now,
                end=now + timedelta(seconds=end_offset),
                release=None
                if release_offset is None
                else now + timedelta(seconds=release_offset),
            )
        )

        with pytest.raises(IntegrityError):
            db.session.commit()


# --- Adquirir ----------------------------------------------------------------


def test_acquiring_creates_a_lock_for_the_configured_time(app, alice, ticket_id):
    with app.app_context():
        status = acquire(ticket_id, alice["id"])
        (lock,) = locks_of(ticket_id)

        assert status.mine is True
        assert status.lock.id == lock.id
        assert lock.usuario_id == alice["id"]
        assert lock.fecha_liberacion is None
        assert lock.fecha_expiracion - lock.fecha_inicio == timedelta(seconds=120)


def test_the_lock_time_comes_from_the_configuration(app, alice, ticket_id):
    app.config["EDIT_LOCK_TTL_SECONDS"] = 300

    with app.app_context():
        acquire(ticket_id, alice["id"])
        (lock,) = locks_of(ticket_id)

        assert lock.fecha_expiracion - lock.fecha_inicio == timedelta(seconds=300)


def test_acquiring_again_renews_the_same_lock(app, alice, ticket_id):
    with app.app_context():
        first = acquire(ticket_id, alice["id"]).lock
        first_id, first_expiration = first.id, first.fecha_expiracion

        second = acquire(ticket_id, alice["id"])

        assert second.mine is True
        assert second.lock.id == first_id
        assert second.lock.fecha_expiracion > first_expiration
        assert len(locks_of(ticket_id)) == 1


def test_someone_else_cannot_take_a_valid_lock(app, alice, bruno, ticket_id):
    with app.app_context():
        acquire(ticket_id, alice["id"])
        status = acquire(ticket_id, bruno["id"])

        assert status.mine is False
        assert status.lock.usuario_id == alice["id"]
        assert status.lock.usuario.nombre == "Alicia"
        assert len(locks_of(ticket_id)) == 1


def test_an_expired_lock_is_released_and_replaced(app, alice, bruno, ticket_id):
    with app.app_context():
        acquire(ticket_id, alice["id"])
        expire(ticket_id)

        status = acquire(ticket_id, bruno["id"])
        old, new = locks_of(ticket_id)

        assert status.mine is True
        assert old.usuario_id == alice["id"]
        # El expirado se libera de forma lógica y se conserva como historial.
        assert old.fecha_liberacion is not None
        assert new.usuario_id == bruno["id"] and new.fecha_liberacion is None
        assert unreleased(ticket_id) == [new]


def test_an_expired_own_lock_that_nobody_took_is_renewed(app, alice, ticket_id):
    with app.app_context():
        acquire(ticket_id, alice["id"])
        expire(ticket_id)
        status = acquire(ticket_id, alice["id"])

        assert status.mine is True
        assert len(locks_of(ticket_id)) == 1
        assert current_edit_lock(ticket_by_public_id(ticket_id)) is not None


def test_a_lock_is_per_ticket(app, alice, bruno, ticket_id, other_ticket):
    with app.app_context():
        acquire(ticket_id, alice["id"])

        assert acquire(other_ticket, bruno["id"]).mine is True


def test_an_inactive_user_cannot_acquire(app, make_user, ticket_id):
    inactive = make_user("TECNICO", username="inactivo", activo=False)

    with app.app_context():
        with pytest.raises(TicketRuleError, match="no está activo"):
            acquire(ticket_id, inactive["id"])

        db.session.rollback()

        assert locks_of(ticket_id) == []


def test_the_service_does_not_commit(app, alice, ticket_id):
    with app.app_context():
        acquire_edit_lock(ticket_by_public_id(ticket_id), person(alice["id"]))
        db.session.rollback()

        assert locks_of(ticket_id) == []


# --- Liberar -----------------------------------------------------------------


def test_releasing_frees_the_ticket_for_someone_else(app, alice, bruno, ticket_id):
    with app.app_context():
        acquire(ticket_id, alice["id"])

        assert release(ticket_id, alice["id"]) is True

        (lock,) = locks_of(ticket_id)

        assert lock.fecha_liberacion is not None
        assert current_edit_lock(ticket_by_public_id(ticket_id)) is None
        assert acquire(ticket_id, bruno["id"]).mine is True


def test_releasing_never_touches_someone_elses_lock(app, alice, bruno, ticket_id):
    with app.app_context():
        acquire(ticket_id, alice["id"])

        assert release(ticket_id, bruno["id"]) is False
        assert unreleased(ticket_id)[0].usuario_id == alice["id"]


def test_releasing_without_a_lock_is_not_an_error(app, alice, ticket_id):
    with app.app_context():
        assert release(ticket_id, alice["id"]) is False
        assert locks_of(ticket_id) == []


# --- Consultar ---------------------------------------------------------------


def test_the_current_lock_is_only_the_valid_one(app, alice, ticket_id):
    with app.app_context():
        ticket = ticket_by_public_id(ticket_id)

        assert current_edit_lock(ticket) is None

        acquire(ticket_id, alice["id"])

        assert current_edit_lock(ticket_by_public_id(ticket_id)).usuario.nombre == "Alicia"

        expire(ticket_id)

        # Expirado: ya no es vigente, aunque nadie lo haya liberado.
        assert current_edit_lock(ticket_by_public_id(ticket_id)) is None

        acquire(ticket_id, alice["id"])
        release(ticket_id, alice["id"])

        assert current_edit_lock(ticket_by_public_id(ticket_id)) is None


def test_consulting_the_lock_changes_nothing(app, alice, ticket_id):
    with app.app_context():
        acquire(ticket_id, alice["id"])
        expire(ticket_id)
        before = [(lock.id, lock.fecha_liberacion) for lock in locks_of(ticket_id)]

        current_edit_lock(ticket_by_public_id(ticket_id))
        db.session.commit()

        assert [
            (lock.id, lock.fecha_liberacion) for lock in locks_of(ticket_id)
        ] == before


# --- Concurrencia -------------------------------------------------------------


def test_two_people_acquiring_at_once_get_one_lock(
    app,
    alice,
    bruno,
    ticket_id,
):
    """Los dos abren la pantalla a la vez: la fila del ticket se bloquea, así
    que la segunda espera a la primera y ve su bloqueo. Solo uno es dueño."""
    barrier = threading.Barrier(2)
    outcomes = {}

    def attempt(user_id):
        with app.app_context():
            ticket = ticket_by_public_id(ticket_id)
            actor = person(user_id)
            barrier.wait(timeout=10)

            try:
                status = acquire_edit_lock(ticket, actor)
                db.session.commit()
                outcomes[user_id] = status.mine
            finally:
                db.session.remove()

    threads = [
        threading.Thread(target=attempt, args=(person_data["id"],))
        for person_data in (alice, bruno)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join(timeout=30)

    assert sorted(outcomes.values()) == [False, True]

    with app.app_context():
        assert len(unreleased(ticket_id)) == 1
        assert len(locks_of(ticket_id)) == 1


def test_two_people_taking_over_an_expired_lock_get_one_lock(
    app,
    make_user,
    alice,
    bruno,
    ticket_id,
):
    third = make_user("TECNICO", username="tercero")

    with app.app_context():
        acquire(ticket_id, alice["id"])
        expire(ticket_id)

    barrier = threading.Barrier(2)
    outcomes = []

    def attempt(user_id):
        with app.app_context():
            ticket = ticket_by_public_id(ticket_id)
            actor = person(user_id)
            barrier.wait(timeout=10)

            try:
                outcomes.append(acquire_edit_lock(ticket, actor).mine)
                db.session.commit()
            finally:
                db.session.remove()

    threads = [
        threading.Thread(target=attempt, args=(data["id"],))
        for data in (bruno, third)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join(timeout=30)

    assert sorted(outcomes) == [False, True]

    with app.app_context():
        assert len(unreleased(ticket_id)) == 1
        # El de Alicia se liberó (conservado) y hay uno nuevo.
        assert len(locks_of(ticket_id)) == 2


# --- Pantallas ---------------------------------------------------------------


def edit_url(public_id):
    return f"/tickets/{public_id}/edit"


def priority_url(public_id):
    return f"/tickets/{public_id}/priority"


def edit_form(catalog, version=1, **values):
    data = {
        "titulo": "Título nuevo",
        "descripcion": "Descripción nueva",
        "categoria": catalog["hardware"],
        "ubicacion": "",
        "version": version,
    }
    data.update(values)

    return data


def priority_form(catalog, version=1, **values):
    data = {
        "prioridad": catalog["high"],
        "motivo": "El cliente no puede trabajar.",
        "version": version,
    }
    data.update(values)

    return data


def title_of(app, public_id):
    with app.app_context():
        return ticket_by_public_id(public_id).titulo


def lock_state(app, public_id):
    """(usuario_id o None, cuántos bloqueos hay) del ticket."""
    with app.app_context():
        current = unreleased(public_id)

        return (current[0].usuario_id if current else None), len(locks_of(public_id))


def test_opening_the_edit_screen_locks_the_ticket(client, app, alice, ticket_id):
    login(client, alice)
    response = client.get(edit_url(ticket_id))

    assert response.status_code == 200
    assert lock_state(app, ticket_id) == (alice["id"], 1)

    # La pantalla trae lo que necesita el script de renovación y avisa.
    html = response.get_data(as_text=True)

    assert "data-edit-lock" in html
    assert f'data-lock-renew-url="/tickets/{ticket_id}/lock/renew"' in html
    assert f'data-lock-release-url="/tickets/{ticket_id}/lock/release"' in html
    assert 'data-lock-heartbeat="45"' in html
    assert "data-lock-csrf=" in html
    assert "js/tickets/edit-lock.js" in html
    assert "nadie más puede editar este ticket" in text(response)
    assert "unos 2 minutos" in text(response)


def test_reopening_the_screen_renews_the_same_lock(client, app, alice, ticket_id):
    login(client, alice)
    client.get(edit_url(ticket_id))
    client.get(edit_url(ticket_id))

    assert lock_state(app, ticket_id) == (alice["id"], 1)


def test_someone_else_sees_who_is_editing_and_cannot_edit(
    client,
    app,
    alice,
    bruno,
    ticket_id,
):
    with app.app_context():
        acquire(ticket_id, alice["id"])

    login(client, bruno)
    response = client.get(edit_url(ticket_id))
    page = plain_text(response)

    assert response.status_code == 200
    assert "Alicia Mora está editando este ticket." in page
    assert "Puedes consultarlo, pero no editarlo hasta que termine" in page
    assert "Datos actuales del ticket" in page
    # Es de solo lectura: ni formulario de edición ni script de renovación.
    html = response.get_data(as_text=True)

    assert 'name="titulo"' not in html
    assert "data-edit-lock" not in html
    assert f'href="{edit_url(ticket_id)}"' in html  # «Volver a intentar»
    # Sigue siendo de Alicia y no se creó otro.
    assert lock_state(app, ticket_id) == (alice["id"], 1)


def test_saving_while_someone_else_edits_changes_nothing(
    client,
    app,
    catalog,
    alice,
    bruno,
    ticket_id,
):
    with app.app_context():
        acquire(ticket_id, alice["id"])

    login(client, bruno)
    response = client.post(edit_url(ticket_id), data=edit_form(catalog))

    assert "No se guardó nada: otra persona está editando este ticket." in text(
        response
    )
    assert title_of(app, ticket_id) == "Problema con el correo"

    with app.app_context():
        assert ticket_by_public_id(ticket_id).version == 1


def test_saving_releases_the_lock_for_everyone(
    client,
    app,
    catalog,
    alice,
    bruno,
    ticket_id,
):
    login(client, alice)
    client.get(edit_url(ticket_id))
    client.post(edit_url(ticket_id), data=edit_form(catalog))

    assert title_of(app, ticket_id) == "Título nuevo"
    assert lock_state(app, ticket_id)[0] is None

    client.post("/logout")
    login(client, bruno)

    assert client.get(edit_url(ticket_id)).status_code == 200
    assert lock_state(app, ticket_id)[0] == bruno["id"]


def test_saving_without_having_a_lock_acquires_it_if_free(
    client,
    app,
    catalog,
    alice,
    ticket_id,
):
    # Se abrió la pantalla, el bloqueo expiró y nadie lo tomó: puede guardar.
    login(client, alice)
    client.get(edit_url(ticket_id))

    with app.app_context():
        expire(ticket_id)

    client.post(edit_url(ticket_id), data=edit_form(catalog))

    assert title_of(app, ticket_id) == "Título nuevo"
    assert lock_state(app, ticket_id)[0] is None


def test_saving_after_someone_took_over_an_expired_lock_is_refused(
    client,
    app,
    catalog,
    alice,
    bruno,
    ticket_id,
):
    login(client, alice)
    client.get(edit_url(ticket_id))

    with app.app_context():
        expire(ticket_id)
        acquire(ticket_id, bruno["id"])

    response = client.post(edit_url(ticket_id), data=edit_form(catalog))

    assert "Bruno Rey está editando este ticket." in plain_text(response)
    assert title_of(app, ticket_id) == "Problema con el correo"


def test_an_expired_lock_does_not_block_anyone(client, app, alice, bruno, ticket_id):
    with app.app_context():
        acquire(ticket_id, alice["id"])
        expire(ticket_id)

    login(client, bruno)
    response = client.get(edit_url(ticket_id))

    assert 'name="titulo"' in response.get_data(as_text=True)
    assert lock_state(app, ticket_id) == (bruno["id"], 2)


def test_a_version_conflict_keeps_the_lock(client, app, catalog, alice, ticket_id):
    login(client, alice)
    client.get(edit_url(ticket_id))
    response = client.post(
        edit_url(ticket_id),
        data=edit_form(catalog, version=99),
        follow_redirects=True,
    )

    assert "Otra persona modificó este ticket" in plain_text(response)
    # Sigue editando: el bloqueo no se libera.
    assert lock_state(app, ticket_id)[0] == alice["id"]


def test_a_validation_error_keeps_the_lock(client, app, catalog, alice, ticket_id):
    login(client, alice)
    client.get(edit_url(ticket_id))
    response = client.post(
        edit_url(ticket_id),
        data=edit_form(catalog, titulo=""),
    )

    assert response.status_code == 200
    assert lock_state(app, ticket_id)[0] == alice["id"]


def test_the_priority_screen_shares_the_same_lock(
    client,
    app,
    catalog,
    alice,
    bruno,
    ticket_id,
):
    login(client, alice)
    client.get(edit_url(ticket_id))
    client.post("/logout")

    login(client, bruno)
    screen = client.get(priority_url(ticket_id))

    assert "Alicia Mora está editando este ticket." in plain_text(screen)
    assert "Cambiar prioridad" in text(screen)

    attempt = client.post(priority_url(ticket_id), data=priority_form(catalog))

    assert "No se guardó nada" in text(attempt)

    with app.app_context():
        assert ticket_by_public_id(ticket_id).prioridad_id == catalog["medium"]


def test_changing_the_priority_locks_and_then_releases(
    client,
    app,
    catalog,
    alice,
    bruno,
    ticket_id,
):
    login(client, alice)
    client.get(priority_url(ticket_id))

    assert lock_state(app, ticket_id)[0] == alice["id"]

    client.post(priority_url(ticket_id), data=priority_form(catalog))

    with app.app_context():
        assert ticket_by_public_id(ticket_id).prioridad_id == catalog["high"]

    assert lock_state(app, ticket_id)[0] is None


def test_other_actions_are_not_blocked_by_the_edit_lock(
    client,
    app,
    alice,
    bruno,
    ticket_id,
):
    """El bloqueo cubre solo editar y cambiar la prioridad: un cambio de estado
    o un comentario son acciones puntuales que confían en la versión."""
    with app.app_context():
        acquire(ticket_id, alice["id"])

    login(client, bruno)
    started = client.post(
        f"/tickets/{ticket_id}/status/start",
        data={"version": 1},
        follow_redirects=True,
    )
    commented = client.post(
        f"/tickets/{ticket_id}/comments",
        data={"contenido": "Reviso esto.", "tipo": "PUBLICO"},
        follow_redirects=True,
    )

    assert "pasó a «En progreso»" in plain_text(started)
    assert "Reviso esto." in plain_text(commented)


def test_a_closed_ticket_is_not_locked(client, app, alice, ticket_id):
    set_state(app, ticket_id, "CERRADO")
    login(client, alice)
    response = client.get(edit_url(ticket_id), follow_redirects=True)

    assert "Un ticket cerrado no se puede editar." in plain_text(response)
    assert lock_state(app, ticket_id) == (None, 0)


def test_the_requester_cannot_lock_anything(client, app, requester, ticket_id):
    login(client, requester)

    assert client.get(edit_url(ticket_id)).status_code == 403
    assert client.get(priority_url(ticket_id)).status_code == 403
    assert lock_state(app, ticket_id) == (None, 0)


def test_the_screens_that_lock_are_404_for_tickets_the_user_cannot_see(
    client,
    app,
    make_user,
    ticket_id,
):
    stranger = make_user("SOLICITANTE", username="ajeno")
    login(client, stranger)

    assert client.get(edit_url(ticket_id)).status_code == 404
    assert lock_state(app, ticket_id) == (None, 0)


# --- Latido y liberación (JSON) --------------------------------------------------


def renew_url(public_id):
    return f"/tickets/{public_id}/lock/renew"


def release_url(public_id):
    return f"/tickets/{public_id}/lock/release"


def test_renewing_extends_the_lock_of_the_holder(client, app, alice, ticket_id):
    login(client, alice)
    client.get(edit_url(ticket_id))

    with app.app_context():
        before = unreleased(ticket_id)[0].fecha_expiracion

    response = client.post(renew_url(ticket_id))

    assert response.status_code == 200
    assert response.get_json() == {"ok": True}

    with app.app_context():
        assert unreleased(ticket_id)[0].fecha_expiracion > before


def test_renewing_while_someone_else_holds_it_is_a_conflict(
    client,
    app,
    alice,
    bruno,
    ticket_id,
):
    with app.app_context():
        acquire(ticket_id, alice["id"])

    login(client, bruno)
    response = client.post(renew_url(ticket_id))

    assert response.status_code == 409
    assert response.get_json() == {
        "ok": False,
        "error": "lock_held",
        "message": "Alicia Mora está editando este ticket.",
    }
    assert lock_state(app, ticket_id) == (alice["id"], 1)


def test_renewing_after_an_expiry_nobody_used_takes_the_lock_again(
    client,
    app,
    alice,
    bruno,
    ticket_id,
):
    with app.app_context():
        acquire(ticket_id, alice["id"])
        expire(ticket_id)

    login(client, bruno)

    assert client.post(renew_url(ticket_id)).get_json() == {"ok": True}
    assert lock_state(app, ticket_id)[0] == bruno["id"]


def test_renewing_a_closed_ticket_is_a_conflict(client, app, alice, ticket_id):
    set_state(app, ticket_id, "CERRADO")
    login(client, alice)
    response = client.post(renew_url(ticket_id))

    assert response.status_code == 409
    assert response.get_json() == {
        "ok": False,
        "error": "ticket_closed",
        "message": "El ticket está cerrado.",
    }
    assert lock_state(app, ticket_id) == (None, 0)


def test_the_requester_cannot_renew_or_release(client, app, requester, ticket_id):
    login(client, requester)

    assert client.post(renew_url(ticket_id)).status_code == 403
    assert client.post(release_url(ticket_id)).status_code == 403


def test_a_ticket_the_user_cannot_see_is_a_404_for_the_lock_endpoints(
    client,
    make_user,
    ticket_id,
):
    stranger = make_user("SOLICITANTE", username="ajeno")
    login(client, stranger)

    assert client.post(renew_url(ticket_id)).status_code == 404
    assert client.post(release_url(ticket_id)).status_code == 404


def test_releasing_through_the_endpoint(client, app, alice, bruno, ticket_id):
    login(client, alice)
    client.get(edit_url(ticket_id))

    assert client.post(release_url(ticket_id)).get_json() == {
        "ok": True,
        "released": True,
    }
    assert lock_state(app, ticket_id)[0] is None

    # Liberar sin tener bloqueo no es un error.
    assert client.post(release_url(ticket_id)).get_json() == {
        "ok": True,
        "released": False,
    }


def test_the_release_endpoint_never_frees_someone_elses_lock(
    client,
    app,
    alice,
    bruno,
    ticket_id,
):
    with app.app_context():
        acquire(ticket_id, alice["id"])

    login(client, bruno)

    assert client.post(release_url(ticket_id)).get_json() == {
        "ok": True,
        "released": False,
    }
    assert lock_state(app, ticket_id)[0] == alice["id"]


def test_the_lock_endpoints_only_accept_post(client, alice, ticket_id):
    login(client, alice)

    assert client.get(renew_url(ticket_id)).status_code == 405
    assert client.get(release_url(ticket_id)).status_code == 405


# --- Detalle: quién está editando -----------------------------------------------


def test_the_detail_tells_staff_who_is_editing(client, app, alice, bruno, ticket_id):
    with app.app_context():
        acquire(ticket_id, alice["id"])

    login(client, bruno)
    page = plain_text(client.get(f"/tickets/{ticket_id}"))

    assert "Alicia Mora está editando este ticket." in page
    assert "Puedes consultarlo, pero no editarlo hasta que termine." in page


def test_the_holder_does_not_get_the_banner(client, app, alice, ticket_id):
    login(client, alice)
    client.get(edit_url(ticket_id))

    assert "está editando este ticket" not in plain_text(
        client.get(f"/tickets/{ticket_id}")
    )


def test_the_requester_never_sees_who_is_editing(
    client,
    app,
    alice,
    requester,
    ticket_id,
):
    with app.app_context():
        acquire(ticket_id, alice["id"])

    login(client, requester)
    page = plain_text(client.get(f"/tickets/{ticket_id}"))

    # (Alicia creó el ticket y sale en el historial: lo que no debe salir es
    # que está editando.)
    assert "está editando" not in page
    assert "Alicia Mora está" not in page


def test_the_banner_disappears_when_the_lock_expires_or_is_released(
    client,
    app,
    alice,
    bruno,
    ticket_id,
):
    with app.app_context():
        acquire(ticket_id, alice["id"])

    login(client, bruno)

    assert "está editando" in plain_text(client.get(f"/tickets/{ticket_id}"))

    with app.app_context():
        expire(ticket_id)

    assert "está editando" not in plain_text(client.get(f"/tickets/{ticket_id}"))


def test_a_closed_ticket_shows_no_editing_banner(client, app, alice, bruno, ticket_id):
    with app.app_context():
        acquire(ticket_id, alice["id"])

    set_state(app, ticket_id, "CERRADO")
    login(client, bruno)

    assert "está editando" not in plain_text(client.get(f"/tickets/{ticket_id}"))


# --- Script --------------------------------------------------------------------


def test_the_renewal_script_is_served_and_only_talks_to_its_own_endpoints(client):
    response = client.get("/static/js/tickets/edit-lock.js")
    source = response.get_data(as_text=True)

    assert response.status_code == 200
    # Renueva con el latido, libera al salir y no depende de servicios
    # externos (la aplicación es 100 % local).
    assert "sendBeacon" in source
    assert "X-CSRFToken" in source
    assert "data-lock-heartbeat" in source
    assert "http://" not in source and "https://" not in source
