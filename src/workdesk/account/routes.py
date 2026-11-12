from datetime import UTC, datetime

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from ..auth.credentials import CurrentPasswordError, change_own_password
from ..auth.security import (
    refresh_login_lock,
    register_failed_login,
    reset_login_failures,
)
from ..extensions import db
from ..security import PasswordPolicyError
from . import bp
from .forms import ChangePasswordForm


@bp.route("/password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()

    if form.validate_on_submit():
        response = _handle_password_change(form)

        if response is not None:
            return response

    return render_template(
        "account/change_password.html",
        form=form,
        mandatory=current_user.debe_cambiar_password,
    )


def _handle_password_change(form: ChangePasswordForm):
    """Procesa un envío válido del formulario.

    Devuelve una respuesta (redirección) si el flujo termina, o `None`
    para volver a mostrar el formulario con los errores añadidos.
    """
    user = current_user._get_current_object()
    now = datetime.now(UTC)

    # La contraseña actual se puede adivinar desde este formulario con una
    # sesión robada, así que se aplica el mismo bloqueo que en el login.
    if refresh_login_lock(user, now):
        form.current_password.errors.append(
            "La cuenta está bloqueada temporalmente. "
            "Inténtalo de nuevo más tarde."
        )
        return None

    try:
        change_own_password(
            user,
            form.current_password.data,
            form.new_password.data,
        )
    except CurrentPasswordError as error:
        return _register_wrong_current_password(user, form, error, now)
    except PasswordPolicyError as error:
        form.new_password.errors.append(str(error))
        return None

    reset_login_failures(user)
    db.session.commit()

    # El cambio sube token_version e invalida todas las sesiones, también
    # la actual. Se vuelve a iniciar para no desconectar al usuario; el
    # reloj de la sesión no se reinicia, así la duración máxima no se
    # puede extender cambiando la contraseña.
    login_user(user)

    flash("Tu contraseña se actualizó correctamente.", "success")

    return redirect(url_for("main.dashboard"))


def _register_wrong_current_password(user, form, error, now):
    register_failed_login(
        user=user,
        max_attempts=current_app.config["LOGIN_MAX_FAILED_ATTEMPTS"],
        lock_minutes=current_app.config["LOGIN_LOCK_MINUTES"],
        now=now,
    )
    db.session.commit()

    current_app.logger.warning(
        "Contraseña actual incorrecta al cambiar la contraseña: "
        "usuario_id=%s",
        user.id,
    )

    if user.bloqueado_hasta is not None and user.bloqueado_hasta > now:
        logout_user()
        session.clear()

        flash(
            "Se superó el número de intentos permitidos. "
            "Inténtalo de nuevo más tarde.",
            "warning",
        )

        return redirect(url_for("auth.login"))

    form.current_password.errors.append(str(error))

    return None
