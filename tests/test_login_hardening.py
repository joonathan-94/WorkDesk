"""Endurecimiento del inicio de sesión (revisiones previas a `v0.7.0` y `v0.8.0`).

Tres defectos que arrastraba el login desde `v0.1.0`:

- **Fuga por tiempo.** Un usuario inexistente, inactivo o bloqueado recibía el error sin que
  se calculara ningún hash, y uno que existe con la contraseña equivocada pagaba Argon2id
  (decenas de milisegundos). El mensaje era idéntico, pero la diferencia de tiempo
  delataba qué usuarios existen. Medir tiempos en un test es frágil, así que se comprueba
  la causa: en cada camino sin cuenta que verificar se gasta una verificación de relleno.
- **Sesión heredada.** `login_user` se llamaba sin vaciar la sesión anterior, de modo que
  lo que hubiera en la cookie antes de autenticarse sobrevivía al inicio de sesión. El
  logout tampoco la vaciaba entera.
- **Contador que pierde intentos.** Varios intentos simultáneos leían el mismo contador de
  fallos y cada uno escribía «uno más»: 20 intentos a la vez dejaban el contador en 2 y la
  cuenta sin bloquear, así que con ráfagas en paralelo se probaban muchas más contraseñas
  de las permitidas. Ahora se bloquea la fila del usuario (`auth/security.py`).
"""

import threading

import pytest

from src.workdesk.extensions import db
from src.workdesk.models import User
from src.workdesk.security import passwords

WRONG = "ContraseñaIncorrecta123!"
GENERIC_ERROR = "Usuario o contraseña incorrectos."
MAX_ATTEMPTS = 5  # LOGIN_MAX_FAILED_ATTEMPTS por defecto


def _login(client, username, password):
    return client.post("/login", data={"username": username, "password": password})


def _at_once(count, action):
    """Ejecuta `action(i)` en `count` hilos que arrancan a la vez."""
    barrier = threading.Barrier(count)

    def run(index):
        barrier.wait(timeout=10)
        action(index)

    threads = [threading.Thread(target=run, args=(i,)) for i in range(count)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join(timeout=60)


def _attempts_and_lock(app, user_id):
    with app.app_context():
        user = db.session.get(User, user_id)

        return user.intentos_fallidos, user.bloqueado_hasta is not None


@pytest.fixture()
def stand_in_calls(monkeypatch):
    """Cuenta las veces que el login gasta la verificación de relleno."""
    calls = []
    original = passwords.spend_verification_time

    def counting(password):
        calls.append(password)
        return original(password)

    # La ruta importa el nombre, así que se sustituye donde se usa.
    monkeypatch.setattr("src.workdesk.auth.routes.spend_verification_time", counting)

    return calls


def test_an_unknown_username_spends_a_verification(client, stand_in_calls):
    response = _login(client, "no.existe", "cualquier-cosa-123")

    assert GENERIC_ERROR in response.get_data(as_text=True)
    assert stand_in_calls == ["cualquier-cosa-123"]


def test_an_inactive_user_spends_a_verification(client, app, admin_user, stand_in_calls):
    with app.app_context():
        db.session.get(User, admin_user["id"]).activo = False
        db.session.commit()

    response = _login(client, admin_user["username"], admin_user["password"])

    assert GENERIC_ERROR in response.get_data(as_text=True)
    assert len(stand_in_calls) == 1


def test_a_locked_account_spends_a_verification(client, admin_user, stand_in_calls):
    for _ in range(5):
        _login(client, admin_user["username"], WRONG)

    stand_in_calls.clear()
    response = _login(client, admin_user["username"], admin_user["password"])

    assert GENERIC_ERROR in response.get_data(as_text=True)
    assert len(stand_in_calls) == 1


def test_a_real_account_does_not_spend_the_stand_in(client, admin_user, stand_in_calls):
    # La cuenta que existe ya paga la verificación de verdad: gastar otra duplicaría el coste.
    _login(client, admin_user["username"], WRONG)
    assert stand_in_calls == []

    response = _login(client, admin_user["username"], admin_user["password"])

    assert response.status_code == 302
    assert stand_in_calls == []


def test_the_stand_in_verification_is_a_real_argon2id_check(monkeypatch):
    # Si el relleno no usara un hash válido, `verify` fallaría al instante y no gastaría
    # el tiempo que debe imitar.
    seen = []
    monkeypatch.setattr(passwords, "verify_password", lambda stored, given: seen.append(stored))

    passwords.spend_verification_time("lo-que-escribió-la-persona")

    assert len(seen) == 1
    assert seen[0].startswith("$argon2id$")


def test_login_discards_what_the_previous_session_held(client, admin_user):
    with client.session_transaction() as session:
        session["dato_previo"] = "no debe sobrevivir"

    response = _login(client, admin_user["username"], admin_user["password"])

    assert response.status_code == 302

    with client.session_transaction() as session:
        assert "dato_previo" not in session
        assert "_user_id" in session

    # El reloj de la sesión sigue funcionando: sin él la sesión se consideraría expirada.
    assert client.get("/dashboard").status_code == 200


def test_logout_clears_everything_the_session_held(client, admin_user):
    _login(client, admin_user["username"], admin_user["password"])

    with client.session_transaction() as session:
        session["dato_de_la_sesion"] = "no debe quedar en el navegador"

    client.post("/logout")

    with client.session_transaction() as session:
        assert dict(session) == {}


# --- Intentos simultáneos ---------------------------------------------------------------


def test_simultaneous_failed_logins_never_lose_an_attempt(app, admin_user, monkeypatch):
    """Doce intentos a la vez con la contraseña equivocada: el contador llega exactamente
    al límite, la cuenta queda bloqueada y solo se verifican tantas contraseñas como
    permite el límite (el resto encuentra la cuenta ya bloqueada)."""
    verified = []
    real_verify = passwords.verify_password

    def counting(stored, given):
        verified.append(given)
        return real_verify(stored, given)

    monkeypatch.setattr("src.workdesk.auth.routes.verify_password", counting)

    _at_once(12, lambda _: _login(app.test_client(), admin_user["username"], WRONG))

    assert _attempts_and_lock(app, admin_user["id"]) == (MAX_ATTEMPTS, True)
    assert len(verified) == MAX_ATTEMPTS


def test_simultaneous_wrong_current_passwords_never_lose_an_attempt(app, admin_user):
    """El formulario de cambio de contraseña comparte el contador del login: con una sesión
    robada no se puede adivinar la contraseña actual enviando el formulario en paralelo."""
    clients = [app.test_client() for _ in range(8)]

    # Cada inicio de sesión correcto reinicia el contador, así que todos van antes.
    for client in clients:
        assert _login(client, admin_user["username"], admin_user["password"]).status_code == 302

    form = {
        "current_password": WRONG,
        "new_password": "OtraContraseñaSegura123!",
        "confirm_password": "OtraContraseñaSegura123!",
    }

    _at_once(len(clients), lambda i: clients[i].post("/account/password", data=form))

    assert _attempts_and_lock(app, admin_user["id"]) == (MAX_ATTEMPTS, True)
