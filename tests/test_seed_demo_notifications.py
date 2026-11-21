"""Notificaciones de demostración (`seed-demo-notifications`): avisos de ejemplo para
ver el centro de notificaciones mientras ningún evento los genera solo."""

from datetime import UTC, datetime, timedelta

import pytest

from src.workdesk.extensions import db
from src.workdesk.models import (
    Categoria,
    Notificacion,
    NotificationEvent,
    Prioridad,
    Ticket,
    User,
)
from src.workdesk.notifications.service import count_unread
from src.workdesk.seeds import (
    DemoNotificationsError,
    seed_catalogs,
    seed_demo_notifications,
    seed_demo_users,
    seed_roles,
)
from src.workdesk.seeds.demo_notifications import (
    READ_AFTER,
    REQUESTER_SAMPLES,
    STAFF_SAMPLES,
)
from src.workdesk.tickets.service import create_ticket, visible_tickets_condition
from tests.ticket_helpers import login

PASSWORD = "ClaveDemoSegura2026"
NOW = datetime(2026, 11, 18, 15, 0, tzinfo=UTC)
STAFF = "diego.soto"
REQUESTER = "javiera.torres"


def prepare(app, *, tickets=True):
    """Roles, catálogos, el equipo demo y, si se pide, tickets de la técnica y del
    solicitante."""
    with app.app_context():
        seed_roles()
        seed_catalogs()
        seed_demo_users(PASSWORD)
        db.session.add(Categoria(nombre="Redes", orden=1))
        db.session.commit()

        if not tickets:
            return

        category = db.session.scalar(db.select(Categoria.id))
        priority = db.session.scalar(db.select(Prioridad.id).where(Prioridad.codigo == "MEDIA"))
        requester = user(REQUESTER)

        for number in range(7):
            create_ticket(
                actor=requester if number % 2 else user(STAFF),
                title=f"Problema {number}",
                description="Detalle del problema.",
                category_id=category,
                priority_id=priority,
                requester_ids=[requester.id] if number % 2 else [],
            )

        db.session.commit()


def user(username) -> User:
    return db.session.scalar(db.select(User).where(User.username == username))


def notifications_of(username) -> list[Notificacion]:
    return list(
        db.session.scalars(
            db.select(Notificacion)
            .where(Notificacion.usuario_id == user(username).id)
            .order_by(Notificacion.fecha_creacion)
        )
    )


def test_the_samples_follow_the_vocabulary_and_the_role(app):
    # Cada aviso usa un evento del vocabulario, y el SLA es solo del personal.
    for sample in (*STAFF_SAMPLES, *REQUESTER_SAMPLES):
        assert isinstance(sample[0], NotificationEvent)

    requester_events = {sample[0] for sample in REQUESTER_SAMPLES}

    assert NotificationEvent.SLA_VENCIDO not in requester_events
    assert NotificationEvent.SLA_PROXIMO_A_VENCER not in requester_events
    assert NotificationEvent.SLA_VENCIDO in {sample[0] for sample in STAFF_SAMPLES}


def test_it_creates_notifications_for_the_demo_team(app):
    prepare(app)

    with app.app_context():
        result = seed_demo_notifications(now=NOW)
        staff = notifications_of(STAFF)
        requester = notifications_of(REQUESTER)

        assert result.created > 0
        assert len(staff) == len(STAFF_SAMPLES)
        assert len(requester) == len(REQUESTER_SAMPLES)
        # Un aviso por cada uno de los eventos de ejemplo.
        assert {n.tipo_evento for n in staff} == {s[0].value for s in STAFF_SAMPLES}
        assert {n.tipo_evento for n in requester} == {s[0].value for s in REQUESTER_SAMPLES}


def test_each_notification_points_to_a_ticket_the_person_can_see(app):
    prepare(app)

    with app.app_context():
        seed_demo_notifications(now=NOW)

        # El solicitante solo recibe avisos de tickets suyos: creados por él o donde es
        # solicitante.
        visible = set(
            db.session.scalars(
                db.select(Ticket.id).where(visible_tickets_condition(user(REQUESTER)))
            )
        )

        assert visible
        assert {n.ticket_id for n in notifications_of(REQUESTER)} <= visible


def test_some_are_read_and_some_are_not_with_consistent_dates(app):
    prepare(app)

    with app.app_context():
        seed_demo_notifications(now=NOW)

        for username in (STAFF, REQUESTER):
            rows = notifications_of(username)

            assert any(n.leida for n in rows) and any(not n.leida for n in rows)

            for row in rows:
                assert row.fecha_creacion < NOW
                assert (row.fecha_lectura is not None) == row.leida

                if row.leida:
                    assert row.fecha_lectura == row.fecha_creacion + READ_AFTER

        # Las no leídas son las que cuenta la campana.
        unread = sum(1 for s in STAFF_SAMPLES if not s[4])

        assert count_unread(user(STAFF)) == unread


def test_the_dates_go_from_minutes_to_days_ago(app):
    prepare(app)

    with app.app_context():
        seed_demo_notifications(now=NOW)
        rows = notifications_of(STAFF)

        assert rows[0].fecha_creacion == NOW - timedelta(minutes=max(s[3] for s in STAFF_SAMPLES))
        assert rows[-1].fecha_creacion == NOW - timedelta(minutes=min(s[3] for s in STAFF_SAMPLES))


def test_running_it_again_creates_nothing(app):
    prepare(app)

    with app.app_context():
        first = seed_demo_notifications(now=NOW)
        total = db.session.scalar(db.select(db.func.count(Notificacion.id)))
        second = seed_demo_notifications(now=NOW)

        assert first.created == total
        assert second.created == 0
        assert db.session.scalar(db.select(db.func.count(Notificacion.id))) == total


def test_it_can_target_a_specific_account_case_insensitively(app):
    prepare(app)

    with app.app_context():
        result = seed_demo_notifications([STAFF.upper()], now=NOW)

        assert result.created == len(STAFF_SAMPLES)
        assert notifications_of(REQUESTER) == []


def test_account_names_are_trimmed_and_blank_ones_ignored(app):
    prepare(app)

    with app.app_context():
        # Lo que llega de la línea de comandos puede traer espacios o un valor vacío.
        result = seed_demo_notifications([f"  {STAFF}  ", "", "   "], now=NOW)

        assert result.created == len(STAFF_SAMPLES)
        assert notifications_of(REQUESTER) == []


def test_it_can_target_an_account_the_demo_team_does_not_include(app, make_user):
    prepare(app)
    admin = make_user("ADMINISTRADOR", username="admin")

    with app.app_context():
        result = seed_demo_notifications(["admin"], now=NOW)
        rows = notifications_of("admin")

        # El Administrador ve todos los tickets: recibe los avisos del personal.
        assert result.created == len(STAFF_SAMPLES)
        assert len(rows) == len(STAFF_SAMPLES)
        assert rows[0].usuario_id == admin["id"]


def test_someone_without_visible_tickets_is_reported_and_gets_nothing(app):
    prepare(app, tickets=False)

    with app.app_context():
        result = seed_demo_notifications([STAFF, REQUESTER], now=NOW)

        assert result.created == 0
        assert set(result.without_tickets) == {STAFF, REQUESTER}
        assert db.session.scalar(db.select(db.func.count(Notificacion.id))) == 0


def test_a_missing_account_is_an_error_and_creates_nothing(app):
    prepare(app)

    with app.app_context():
        with pytest.raises(DemoNotificationsError, match="No existe"):
            seed_demo_notifications([STAFF, "nadie"], now=NOW)

        assert db.session.scalar(db.select(db.func.count(Notificacion.id))) == 0


def test_without_the_demo_team_it_asks_for_seed_demo(app):
    with app.app_context():
        seed_roles()

        with pytest.raises(DemoNotificationsError, match="seed-demo"):
            seed_demo_notifications(now=NOW)


def test_the_notifications_show_up_in_the_center_of_that_person(app, client):
    prepare(app)

    with app.app_context():
        seed_demo_notifications(now=datetime.now(UTC))

    # La cuenta demo entra con la contraseña del seed y ve sus avisos y la campana.
    login(client, {"username": STAFF, "password": PASSWORD})
    response = client.get("/notifications")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Ticket asignado" in html
    assert html.count("notification--unread") == sum(1 for s in STAFF_SAMPLES if not s[4])


# --- El comando ---------------------------------------------------------------------


def test_the_command_reports_what_it_created(app):
    prepare(app)
    runner = app.test_cli_runner()

    first = runner.invoke(args=["seed-demo-notifications"])
    second = runner.invoke(args=["seed-demo-notifications"])

    assert first.exit_code == 0, first.output
    assert "Notificaciones demo creadas:" in first.output
    assert "creadas: 0." not in first.output
    assert "Notificaciones demo creadas: 0." in second.output


def test_the_command_accepts_several_accounts(app):
    prepare(app)
    result = app.test_cli_runner().invoke(
        args=["seed-demo-notifications", "--username", STAFF, "--username", REQUESTER]
    )

    expected = len(STAFF_SAMPLES) + len(REQUESTER_SAMPLES)

    assert f"Notificaciones demo creadas: {expected}." in result.output


def test_the_command_mentions_who_has_no_tickets(app):
    prepare(app, tickets=False)
    result = app.test_cli_runner().invoke(args=["seed-demo-notifications"])

    assert result.exit_code == 0
    assert "Notificaciones demo creadas: 0." in result.output
    assert f"Aviso: {STAFF} no ve ningún ticket" in result.output


def test_the_command_fails_for_a_missing_account(app):
    prepare(app)
    result = app.test_cli_runner().invoke(
        args=["seed-demo-notifications", "--username", "nadie"]
    )

    assert result.exit_code != 0
    assert "No existe el usuario: nadie" in result.output


def test_the_command_is_refused_in_production(app):
    prepare(app)
    app.config["APP_ENV"] = "production"
    result = app.test_cli_runner().invoke(args=["seed-demo-notifications"])

    assert result.exit_code != 0
    assert "no se cargan en producción" in result.output

    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(Notificacion.id))) == 0
