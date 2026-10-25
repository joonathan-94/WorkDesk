from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from ..extensions import db
from ..models import User
from ..security import (
    hash_password,
    password_needs_rehash,
    verify_password,
)
from . import bp


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

        credentials_are_valid = (
            user is not None
            and user.activo
            and verify_password(user.password_hash, password)
        )

        if not credentials_are_valid:
            flash("Usuario o contraseña incorrectos.", "error")
            return render_template("auth/login.html")

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