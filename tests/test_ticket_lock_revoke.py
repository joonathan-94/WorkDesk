"""Liberar a la fuerza el bloqueo de edición de otra persona (docs/06, RN-176).

Lo que fijan: solo Supervisor y Administrador, queda auditado y **la persona desalojada no
recupera el bloqueo** con el latido de su pantalla.
"""

import time

import pytest

from src.workdesk.audit import AuditAction
from src.workdesk.extensions import db
from src.workdesk.models import TicketEditLock
from src.workdesk.tickets.locking import (
    EditLockRevokedError,
    acquire_edit_lock,
    current_edit_lock,
    release_edit_lock,
    renew_edit_lock,
    revoke_edit_lock,
)
from src.workdesk.tickets.service import TicketRuleError
from tests.ticket_helpers import (
    audit_entries,
    login,
    make_ticket,
    person,
    plain_text,
    run_in_threads,
    ticket_by_public_id,
)


@pytest.fixture()
def people(make_user, catalog):
    return {
        "alicia": make_user("TECNICO", username="alicia_r", nombre="Alicia", apellido="Mora"),
        "tec": make_user("TECNICO", username="tec_r"),
        "sup": make_user("SUPERVISOR", username="sup_r", nombre="Bruno", apellido="Rey"),
        "admin": make_user("ADMINISTRADOR", username="admin_r"),
        "req": make_user("SOLICITANTE", username="req_r"),
    }


@pytest.fixture()
def number(app, catalog, people):
    return make_ticket(
        app,
        catalog,
        people["alicia"]["id"],
        requester_ids=[people["req"]["id"]],
    )


def _hold(app, number, user):
    with app.app_context():
        acquire_edit_lock(ticket_by_public_id(number), person(user["id"]))
        db.session.commit()


def _holder(app, number):
    with app.app_context():
        lock = current_edit_lock(ticket_by_public_id(number))

        return None if lock is None else lock.usuario_id


def _revoke(app, number, user, reason=None):
    with app.app_context():
        holder = revoke_edit_lock(ticket_by_public_id(number), person(user["id"]), reason)
        db.session.commit()

        return holder.id


# --- El servicio -----------------------------------------------------------------------


@pytest.mark.parametrize("who", ["sup", "admin"])
def test_a_supervisor_or_administrator_releases_it_and_it_is_audited(
    app, number, people, who
):
    _hold(app, number, people["alicia"])

    holder = _revoke(app, number, people[who], reason="  Salió de la oficina  ")

    assert holder == people["alicia"]["id"]
    assert _holder(app, number) is None

    with app.app_context():
        lock = db.session.scalar(db.select(TicketEditLock))
        entry = audit_entries()[-1]

        assert lock.liberado_por_usuario_id == people[who]["id"]
        assert lock.fecha_liberacion is not None
        assert entry.accion == AuditAction.BLOQUEO_EDICION_LIBERADO
        assert entry.entidad_tipo == "ticket"
        assert entry.detalle == f"#{number}"
        assert entry.valor_anterior["username"] == "alicia_r"
        assert entry.motivo == "Salió de la oficina"


@pytest.mark.parametrize("who", ["tec", "req", "alicia"])
def test_other_roles_cannot(app, number, people, who):
    _hold(app, number, people["alicia"])

    with pytest.raises(PermissionError):
        _revoke(app, number, people[who])

    assert _holder(app, number) == people["alicia"]["id"]


@pytest.mark.parametrize("case", ["sin bloqueo", "propio", "ya liberado", "expirado"])
def test_there_must_be_someone_elses_current_lock(app, number, people, case):
    if case == "propio":
        _hold(app, number, people["sup"])
    elif case in ("ya liberado", "expirado"):
        _hold(app, number, people["alicia"])

    if case == "ya liberado":
        with app.app_context():
            release_edit_lock(
                ticket_by_public_id(number), person(people["alicia"]["id"])
            )
            db.session.commit()
    elif case == "expirado":
        with app.app_context():
            db.session.execute(
                db.text(
                    "UPDATE bloqueos_edicion_tickets SET "
                    "fecha_inicio = now() - interval '10 minutes', "
                    "fecha_expiracion = now() - interval '5 minutes'"
                )
            )
            db.session.commit()

    with pytest.raises(TicketRuleError, match="Ya no hay un bloqueo"):
        _revoke(app, number, people["sup"])

    with app.app_context():
        assert audit_entries() == []


def test_two_people_releasing_at_once_audit_it_once(app, number, people):
    _hold(app, number, people["alicia"])

    def revoke(who, *, before=0.0, after=0.0):
        def task():
            time.sleep(before)
            revoke_edit_lock(ticket_by_public_id(number), person(people[who]["id"]))
            # Con la transacción abierta: sin bloquear el ticket, la otra persona vería
            # el bloqueo todavía sin liberar y lo anotaría una segunda vez.
            time.sleep(after)

        return task

    outcomes = run_in_threads(
        app, [revoke("sup", after=0.5), revoke("admin", before=0.2)]
    )

    assert outcomes.count("ok") == 1

    with app.app_context():
        entries = [
            e for e in audit_entries() if e.accion == AuditAction.BLOQUEO_EDICION_LIBERADO
        ]
        assert len(entries) == 1


def test_the_heartbeat_of_the_removed_person_cannot_take_it_back(app, number, people):
    _hold(app, number, people["alicia"])
    _revoke(app, number, people["sup"])

    with app.app_context(), pytest.raises(EditLockRevokedError, match="Bruno Rey"):
        renew_edit_lock(ticket_by_public_id(number), person(people["alicia"]["id"]))

    assert _holder(app, number) is None


def test_opening_the_screen_again_takes_a_new_lock_and_renews_it(app, number, people):
    _hold(app, number, people["alicia"])
    _revoke(app, number, people["sup"])
    _hold(app, number, people["alicia"])

    with app.app_context():
        status = renew_edit_lock(
            ticket_by_public_id(number), person(people["alicia"]["id"])
        )
        assert status.mine
        db.session.commit()


def test_after_releasing_it_the_supervisor_can_edit(app, number, people):
    _hold(app, number, people["alicia"])
    _revoke(app, number, people["sup"])

    with app.app_context():
        status = acquire_edit_lock(
            ticket_by_public_id(number), person(people["sup"]["id"])
        )
        assert status.mine
        db.session.commit()


def test_a_normal_release_does_not_block_the_heartbeat(app, number, people):
    # Salir de la pantalla y volver (caché del navegador) debe seguir funcionando.
    _hold(app, number, people["alicia"])

    with app.app_context():
        release_edit_lock(ticket_by_public_id(number), person(people["alicia"]["id"]))
        db.session.commit()
        status = renew_edit_lock(
            ticket_by_public_id(number), person(people["alicia"]["id"])
        )
        assert status.mine


# --- Las rutas ---------------------------------------------------------------------------


def _url(number):
    return f"/tickets/{number}/lock/revoke"


@pytest.mark.parametrize(
    ("who", "offered"),
    [("sup", True), ("admin", True), ("tec", False)],
)
def test_only_those_who_can_release_it_see_the_link(
    app, client, number, people, who, offered
):
    _hold(app, number, people["alicia"])
    login(client, people[who])

    detail = client.get(f"/tickets/{number}").get_data(as_text=True)
    locked = client.get(f"/tickets/{number}/edit").get_data(as_text=True)

    assert (_url(number) in detail) is offered
    assert (_url(number) in locked) is offered


def test_the_confirmation_releases_it(app, client, number, people):
    _hold(app, number, people["alicia"])
    login(client, people["sup"])
    opened = client.get(_url(number))

    assert opened.status_code == 200
    assert "Alicia Mora" in plain_text(opened)
    assert _holder(app, number) == people["alicia"]["id"]

    response = client.post(_url(number), data={"motivo": "Urgente"})

    assert "Se liberó el bloqueo de Alicia Mora" in plain_text(
        client.get(response.headers["Location"])
    )
    assert _holder(app, number) is None


def test_asking_without_a_lock_goes_back_with_a_notice(client, number, people):
    login(client, people["sup"])

    response = client.get(_url(number))

    assert response.status_code == 302
    assert "Ya no hay un bloqueo" in plain_text(client.get(response.headers["Location"]))


@pytest.mark.parametrize(("who", "status"), [("tec", 403), ("req", 403)])
def test_the_route_is_forbidden_to_others(app, client, number, people, who, status):
    _hold(app, number, people["alicia"])
    login(client, people[who])

    assert client.get(_url(number)).status_code == status
    assert client.post(_url(number)).status_code == status
    assert _holder(app, number) == people["alicia"]["id"]


def test_the_route_requires_the_csrf_token(app, client, number, people):
    _hold(app, number, people["alicia"])
    login(client, people["sup"])
    app.config["WTF_CSRF_ENABLED"] = True

    assert client.post(_url(number)).status_code == 400
    assert _holder(app, number) == people["alicia"]["id"]


def test_the_heartbeat_route_tells_the_removed_person(app, client, number, people):
    login(client, people["alicia"])
    assert client.get(f"/tickets/{number}/edit").status_code == 200
    _revoke(app, number, people["sup"])

    response = client.post(f"/tickets/{number}/lock/renew")

    assert response.status_code == 409
    assert response.get_json() == {
        "ok": False,
        "error": "lock_revoked",
        "message": "Bruno Rey liberó tu reserva de este ticket.",
    }
    assert _holder(app, number) is None


def test_the_removed_person_can_still_save_if_nobody_else_changed_it(
    app, client, number, people
):
    # La liberación no borra su trabajo: la barrera de integridad sigue siendo la versión.
    login(client, people["alicia"])
    client.get(f"/tickets/{number}/edit")
    _revoke(app, number, people["sup"])

    with app.app_context():
        ticket = ticket_by_public_id(number)
        data = {
            "titulo": "Guardado después",
            "descripcion": ticket.descripcion,
            "categoria": ticket.categoria_id,
            "ubicacion": ticket.ubicacion_id or "",
            "version": ticket.version,
        }

    response = client.post(f"/tickets/{number}/edit", data=data)

    assert response.status_code == 302

    with app.app_context():
        assert ticket_by_public_id(number).titulo == "Guardado después"
