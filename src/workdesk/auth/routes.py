from datetime import UTC, datetime

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_user, logout_user

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

        return redirect(url_for("main.dashboard"))

    return render_template("auth/login.html")


@bp.post("/logout")
def logout():
    logout_user()

    return redirect(url_for("auth.login"))