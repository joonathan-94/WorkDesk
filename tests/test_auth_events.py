"""Los eventos de autenticación (`eventos_autenticacion`) y el límite de intentos por equipo.

Cada intento de entrar deja exactamente un evento con su causa; la causa nunca se muestra a
quien intenta entrar; nada de lo que se escribió como contraseña queda registrado; y un
equipo que agota sus intentos fallidos no puede seguir probando cuentas.
"""

import threading
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from src.workdesk.auth.events import record_auth_event
from src.workdesk.auth.session import SESSION_ACTIVITY_KEY, SESSION_STARTED_KEY
from src.workdesk.extensions import db
from src.workdesk.models import AuthEvent, AuthEventType, AuthFailure, User
from src.workdesk.models.auth_event import AUTH_EVENT_LABELS, AUTH_FAILURE_LABELS
from tests.ticket_helpers import plain_text

WRONG = "ContraseñaIncorrecta123!"
GENERIC = "Usuario o contraseña incorrectos."
THROTTLED = "demasiados intentos fallidos desde este equipo"


def _login(client, username, password):
    return client.post("/login", data={"username": username, "password": password})


def _events(app):
    with app.app_context():
        return [
            (e.tipo_evento, e.detalle, e.usuario_id, e.identificador_intentado, e.resultado)
            for e in db.session.scalars(db.select(AuthEvent).order_by(AuthEvent.id))
        ]


def _from(app, ip):
    """Un cliente que llega desde la IP indicada."""
    client = app.test_client()
    client.environ_base["REMOTE_ADDR"] = ip

    return client


# --- Un evento por intento, con su causa --------------------------------------------------


def test_a_successful_login_leaves_who_from_where_and_with_what(app, client, admin_user):
    response = client.post(
        "/login",
        data={"username": admin_user["username"], "password": admin_user["password"]},
        headers={"User-Agent": "Navegador de prueba"},
    )

    assert response.status_code == 302

    with app.app_context():
        (event,) = db.session.scalars(db.select(AuthEvent)).all()

        assert event.tipo_evento == AuthEventType.LOGIN_EXITOSO
        assert event.resultado == "EXITOSO"
        assert event.usuario_id == admin_user["id"]
        assert event.detalle is None
        assert event.ip_origen == "127.0.0.1"
        assert event.user_agent == "Navegador de prueba"
        assert event.fecha_hora is not None


def test_a_wrong_password_is_recorded_on_the_account(app, client, admin_user):
    _login(client, admin_user["username"], WRONG)

    assert _events(app) == [
        ("LOGIN_FALLIDO", "CONTRASENA_INCORRECTA", admin_user["id"], None, "FALLIDO")
    ]


def test_an_unknown_username_keeps_what_was_typed(app, client):
    _login(client, "  Pedro.Gomez ", "lo-que-sea-123")

    assert _events(app) == [
        ("LOGIN_FALLIDO", "USUARIO_DESCONOCIDO", None, "pedro.gomez", "FALLIDO")
    ]


@pytest.mark.parametrize("typed", ["Mi Clave Secreta!", "clave#2026", "x" * 51])
def test_something_that_is_not_a_username_is_never_stored(app, client, typed):
    # Quien escribe su contraseña en el campo del usuario no debe dejarla en un registro.
    _login(client, typed, "lo-que-sea-123")

    assert _events(app) == [("LOGIN_FALLIDO", "USUARIO_DESCONOCIDO", None, None, "FALLIDO")]


def test_an_inactive_account_is_recorded_with_its_cause(app, client, admin_user):
    with app.app_context():
        db.session.get(User, admin_user["id"]).activo = False
        db.session.commit()

    response = _login(client, admin_user["username"], admin_user["password"])

    # La causa es interna: la persona lee lo de siempre.
    assert GENERIC in plain_text(response)
    assert _events(app)[0][:3] == ("LOGIN_FALLIDO", "USUARIO_INACTIVO", admin_user["id"])


def test_the_lock_is_recorded_once_and_then_every_attempt_meets_it(app, client, admin_user):
    for _ in range(6):
        response = _login(client, admin_user["username"], WRONG)

    assert GENERIC in plain_text(response)
    kinds = [(kind, cause) for kind, cause, *_ in _events(app)]

    assert kinds == [
        *[("LOGIN_FALLIDO", "CONTRASENA_INCORRECTA")] * 4,
        ("BLOQUEO_TEMPORAL", None),
        ("LOGIN_FALLIDO", "CONTRASENA_INCORRECTA"),
        ("LOGIN_FALLIDO", "CUENTA_BLOQUEADA"),
    ]


def test_logging_out_is_recorded(app, client, admin_user):
    _login(client, admin_user["username"], admin_user["password"])
    client.post("/logout")

    assert [kind for kind, *_ in _events(app)] == ["LOGIN_EXITOSO", "CIERRE_SESION"]


def test_an_expired_session_is_recorded_when_it_closes(app, client, admin_user):
    _login(client, admin_user["username"], admin_user["password"])

    with client.session_transaction() as session:
        long_ago = (datetime.now(UTC) - timedelta(days=1)).timestamp()
        session[SESSION_STARTED_KEY] = long_ago
        session[SESSION_ACTIVITY_KEY] = long_ago

    client.get("/dashboard")

    assert [kind for kind, *_ in _events(app)] == ["LOGIN_EXITOSO", "SESION_EXPIRADA"]


def test_a_wrong_current_password_when_changing_it_is_recorded(app, client, admin_user):
    _login(client, admin_user["username"], admin_user["password"])
    client.post(
        "/account/password",
        data={
            "current_password": WRONG,
            "new_password": "OtraContraseñaSegura123!",
            "confirm_password": "OtraContraseñaSegura123!",
        },
    )

    assert _events(app)[-1][:3] == (
        "VERIFICACION_FALLIDA",
        "CONTRASENA_INCORRECTA",
        admin_user["id"],
    )


def test_no_password_ever_reaches_the_events(app, client, admin_user):
    secret = "ContraseñaQueNoDebeQuedar99!"
    _login(client, admin_user["username"], secret)
    _login(client, "no.existe", secret)
    _login(client, secret, secret)

    with app.app_context():
        for event in db.session.scalars(db.select(AuthEvent)):
            values = [getattr(event, c.key) for c in AuthEvent.__table__.columns]

            assert all(secret.lower() not in str(v).lower() for v in values)


# --- El límite por equipo -----------------------------------------------------------------


def test_an_ip_that_exhausts_its_attempts_cannot_try_more_accounts(app, admin_user):
    app.config["LOGIN_MAX_FAILED_PER_IP"] = 3
    attacker = _from(app, "10.0.0.66")

    for name in ("ana.uno", "bea.dos", "carla.tres"):
        _login(attacker, name, WRONG)

    # Ni siquiera con la contraseña correcta de una cuenta real, y sin tocar esa cuenta.
    response = _login(attacker, admin_user["username"], admin_user["password"])

    assert response.status_code == 200
    assert THROTTLED in plain_text(response).lower()
    # Se rechaza antes de mirar la cuenta: queda lo que se escribió (qué cuenta probaban).
    assert _events(app)[-1][:4] == (
        "LOGIN_FALLIDO",
        "DEMASIADOS_INTENTOS_IP",
        None,
        admin_user["username"],
    )

    with app.app_context():
        assert db.session.get(User, admin_user["id"]).intentos_fallidos == 0

    # Otro equipo entra con normalidad.
    other = _login(_from(app, "10.0.0.7"), admin_user["username"], admin_user["password"])
    assert other.status_code == 302


def test_only_failures_inside_the_window_count(app, admin_user):
    app.config["LOGIN_MAX_FAILED_PER_IP"] = 3
    app.config["LOGIN_LOCK_MINUTES"] = 15

    with app.app_context():
        long_ago = datetime.now(UTC) - timedelta(minutes=16)

        for _ in range(5):
            db.session.add(
                AuthEvent(
                    fecha_hora=long_ago,
                    tipo_evento="LOGIN_FALLIDO",
                    resultado="FALLIDO",
                    detalle="USUARIO_DESCONOCIDO",
                    ip_origen="10.0.0.66",
                )
            )

        db.session.commit()

    response = _login(_from(app, "10.0.0.66"), admin_user["username"], admin_user["password"])

    assert response.status_code == 302


def test_zero_turns_the_ip_limit_off(app, admin_user):
    app.config["LOGIN_MAX_FAILED_PER_IP"] = 0
    client = _from(app, "10.0.0.66")

    for index in range(30):
        _login(client, f"nadie.{index}", WRONG)

    assert _login(client, admin_user["username"], admin_user["password"]).status_code == 302


def test_simultaneous_attempts_from_one_ip_are_counted_one_by_one(app):
    """Doce intentos a la vez desde un equipo con un límite de 3: exactamente tres llegan a
    mirar una cuenta; el resto se rechaza por el límite."""
    app.config["LOGIN_MAX_FAILED_PER_IP"] = 3
    barrier = threading.Barrier(12)

    def attempt(index):
        client = _from(app, "10.0.0.66")
        barrier.wait(timeout=10)
        _login(client, f"nadie.{index}", WRONG)

    threads = [threading.Thread(target=attempt, args=(i,)) for i in range(12)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join(timeout=60)

    causes = [cause for _kind, cause, *_ in _events(app)]

    assert causes.count("USUARIO_DESCONOCIDO") == 3
    assert causes.count("DEMASIADOS_INTENTOS_IP") == 9


# --- Integridad del registro ---------------------------------------------------------------


def test_every_event_and_cause_has_a_label():
    assert set(AUTH_EVENT_LABELS) == set(AuthEventType)
    assert set(AUTH_FAILURE_LABELS) == set(AuthFailure)


def test_a_failure_must_say_why_and_a_success_must_not(app):
    with app.app_context(), pytest.raises(ValueError):
        record_auth_event(AuthEventType.LOGIN_FALLIDO)

    with app.app_context(), pytest.raises(ValueError):
        record_auth_event(AuthEventType.CIERRE_SESION, failure=AuthFailure.CUENTA_BLOQUEADA)


@pytest.mark.parametrize(
    "values",
    [
        # Un inicio de sesión correcto sin cuenta.
        {"tipo_evento": "LOGIN_EXITOSO", "resultado": "EXITOSO"},
        # Un rechazo sin causa.
        {"tipo_evento": "LOGIN_FALLIDO", "resultado": "FALLIDO"},
        # Un resultado inventado.
        {"tipo_evento": "CIERRE_SESION", "resultado": "QUIZAS"},
    ],
    ids=["exito-sin-usuario", "fallo-sin-causa", "resultado-desconocido"],
)
def test_the_database_refuses_an_incoherent_event(app, values):
    with app.app_context():
        db.session.add(AuthEvent(**values))

        with pytest.raises(IntegrityError):
            db.session.flush()


# --- «Mi cuenta» ----------------------------------------------------------------------------


def test_my_account_shows_my_recent_access_and_nobody_else(app, client, make_user):
    me = make_user("SOLICITANTE", username="yo.mismo")
    other = make_user("SOLICITANTE", username="otra.persona")

    _login(_from(app, "10.0.0.9"), other["username"], other["password"])
    _login(client, me["username"], WRONG)
    _login(client, me["username"], me["password"])

    page = plain_text(client.get("/account"))

    assert "Actividad reciente de tu cuenta" in page
    assert "Intento de inicio de sesión fallido" in page
    assert "Inicio de sesión" in page
    assert "10.0.0.9" not in page
