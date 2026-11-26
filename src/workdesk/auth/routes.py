from datetime import UTC, datetime

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)

from .. import settings
from ..configuration import value_of
from ..extensions import db
from ..models import AuthEventType, AuthFailure
from ..responses import json_error
from ..security import (
    hash_password,
    password_needs_rehash,
    spend_verification_time,
    verify_password,
)
from . import bp
from .events import ip_is_throttled, record_auth_event
from .security import (
    find_user_for_login,
    refresh_login_lock,
    register_failed_login,
    reset_login_failures,
)
from .session import (
    EXEMPT_ENDPOINTS,
    PASSIVE_ENDPOINTS,
    PASSWORD_CHANGE_ALLOWED_ENDPOINTS,
    PASSWORD_CHANGE_ENDPOINT,
    session_has_expired,
    start_session_clock,
    touch_session,
)


@bp.before_app_request
def enforce_session_limits():
    """Aplica la inactividad y la duración máxima a toda petición."""
    if request.endpoint in EXEMPT_ENDPOINTS:
        return None

    if not current_user.is_authenticated:
        return None

    now = datetime.now(UTC)
    passive = request.endpoint in PASSIVE_ENDPOINTS

    if session_has_expired(now):
        if passive:
            # Una consulta automática no cierra la sesión ni gasta el aviso «Tu sesión
            # expiró»: solo le dice al script que pare. La siguiente acción de la persona
            # la cierra, con su mensaje.
            return json_error(
                "session_expired", "Tu sesión expiró. Inicia sesión nuevamente.", 401
            )

        current_app.logger.info(
            "Sesión expirada: usuario_id=%s",
            current_user.id,
        )

        record_auth_event(AuthEventType.SESION_EXPIRADA, user=current_user)
        db.session.commit()

        logout_user()
        session.clear()

        flash("Tu sesión expiró. Inicia sesión nuevamente.", "warning")

        return redirect(url_for("auth.login"))

    # Una consulta pasiva no es actividad de la persona (ver `PASSIVE_ENDPOINTS`).
    if not passive:
        touch_session(now)

    return None


@bp.before_app_request
def require_password_change():
    """Obliga a cambiar la contraseña temporal antes de usar el sistema.

    Se aplica en backend a cualquier ruta, no solo ocultando enlaces:
    mientras `debe_cambiar_password` sea verdadero, solo se permite la
    pantalla de cambio de contraseña, el cierre de sesión y las rutas
    técnicas. Se ejecuta después de `enforce_session_limits`.
    """
    if not current_user.is_authenticated:
        return None

    if not current_user.debe_cambiar_password:
        return None

    if request.endpoint in PASSWORD_CHANGE_ALLOWED_ENDPOINTS:
        return None

    return redirect(url_for(PASSWORD_CHANGE_ENDPOINT))


GENERIC_LOGIN_ERROR = "Usuario o contraseña incorrectos."
THROTTLED_LOGIN_ERROR = (
    "Hubo demasiados intentos fallidos desde este equipo. Espera unos minutos e "
    "inténtalo de nuevo."
)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "GET":
        return render_template("auth/login.html")

    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "")

    # Antes que la cuenta: un equipo que agotó sus intentos no prueba ninguna más. El
    # mensaje es otro, pero no dice nada de ninguna cuenta.
    if ip_is_throttled():
        return _reject_login(AuthFailure.DEMASIADOS_INTENTOS_IP, attempted=username)

    # Con la fila bloqueada: los intentos simultáneos sobre una cuenta se atienden
    # de uno en uno y el contador de fallos no pierde ninguno (ver `auth/security.py`).
    user = find_user_for_login(username)
    now = datetime.now(UTC)

    # Sin una cuenta que verificar se gasta igualmente una verificación: si no, responder
    # más rápido delataría qué usuarios existen (ver `security/passwords.py`).
    if user is None:
        spend_verification_time(password)
        return _reject_login(AuthFailure.USUARIO_DESCONOCIDO, attempted=username)

    if not user.activo:
        spend_verification_time(password)
        return _reject_login(AuthFailure.USUARIO_INACTIVO, user=user)

    if refresh_login_lock(user, now):
        spend_verification_time(password)
        return _reject_login(AuthFailure.CUENTA_BLOQUEADA, user=user)

    if not verify_password(user.password_hash, password):
        register_failed_login(
            user=user,
            max_attempts=value_of(settings.LOGIN_MAX_FAILED_ATTEMPTS),
            lock_minutes=value_of(settings.LOGIN_LOCK_MINUTES),
            now=now,
        )

        if user.bloqueado_hasta is not None:
            record_auth_event(AuthEventType.BLOQUEO_TEMPORAL, user=user)

        return _reject_login(AuthFailure.CONTRASENA_INCORRECTA, user=user)

    reset_login_failures(user)

    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)

    record_auth_event(AuthEventType.LOGIN_EXITOSO, user=user)
    db.session.commit()

    # Una sesión nueva en cada inicio de sesión: nada de lo que hubiera en la cookie
    # anterior (un token CSRF, un dato escrito por otra persona en ese navegador)
    # sobrevive a la autenticación.
    session.clear()
    login_user(user)
    start_session_clock(now)

    return redirect(url_for("main.dashboard"))


def _reject_login(failure: AuthFailure, *, user=None, attempted=None):
    """Registra el intento rechazado, confirma lo que haya que guardar (el contador de
    fallos, el bloqueo) y vuelve al formulario con el mensaje de siempre."""
    record_auth_event(
        AuthEventType.LOGIN_FALLIDO, user=user, attempted=attempted, failure=failure
    )
    db.session.commit()

    throttled = failure is AuthFailure.DEMASIADOS_INTENTOS_IP
    flash(THROTTLED_LOGIN_ERROR if throttled else GENERIC_LOGIN_ERROR, "error")

    return render_template("auth/login.html")


@bp.post("/logout")
@login_required
def logout():
    record_auth_event(AuthEventType.CIERRE_SESION, user=current_user)
    db.session.commit()

    logout_user()
    # Toda la sesión, no solo la identidad: nada de lo que guardó (el token CSRF, avisos
    # pendientes, el reloj de la sesión) debe quedar en ese navegador para quien llegue
    # después. Es lo mismo que hace el inicio de sesión al empezar.
    session.clear()

    return redirect(url_for("auth.login"))