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

from ..extensions import db
from ..models import User
from ..security import (
    hash_password,
    password_needs_rehash,
    verify_password,
)
from . import bp
from .security import (
    refresh_login_lock,
    register_failed_login,
    reset_login_failures,
)
from .session import (
    EXEMPT_ENDPOINTS,
    PASSWORD_CHANGE_ALLOWED_ENDPOINTS,
    PASSWORD_CHANGE_ENDPOINT,
    clear_session_clock,
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

    if session_has_expired(now):
        current_app.logger.info(
            "Sesión expirada: usuario_id=%s",
            current_user.id,
        )

        logout_user()
        session.clear()

        flash("Tu sesión expiró. Inicia sesión nuevamente.", "warning")

        return redirect(url_for("auth.login"))

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


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")

        user = db.session.scalar(
            db.select(User).where(User.username == username)
        )

        if user is None or not user.activo:
            flash("Usuario o contraseña incorrectos.", "error")
            return render_template("auth/login.html")

        now = datetime.now(UTC)

        if refresh_login_lock(user, now):
            flash("Usuario o contraseña incorrectos.", "error")
            return render_template("auth/login.html")

        if not verify_password(user.password_hash, password):
            register_failed_login(
                user=user,
                max_attempts=current_app.config[
                    "LOGIN_MAX_FAILED_ATTEMPTS"
                ],
                lock_minutes=current_app.config["LOGIN_LOCK_MINUTES"],
                now=now,
            )

            db.session.commit()

            flash("Usuario o contraseña incorrectos.", "error")
            return render_template("auth/login.html")

        reset_login_failures(user)

        if password_needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)

        db.session.commit()

        login_user(user)
        start_session_clock(now)

        return redirect(url_for("main.dashboard"))

    return render_template("auth/login.html")


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    clear_session_clock()

    return redirect(url_for("auth.login"))