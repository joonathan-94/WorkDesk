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

from .. import settings
from ..auth.credentials import CurrentPasswordError, change_own_password
from ..auth.security import (
    lock_user_row,
    refresh_login_lock,
    register_failed_login,
    reset_login_failures,
)
from ..configuration import value_of
from ..extensions import db
from ..security import PasswordPolicyError, current_actor
from ..users.forms import ContactForm
from . import bp
from .forms import ChangePasswordForm
from .service import update_own_contact


@bp.route("", methods=["GET", "POST"])
@login_required
def index():
    """Mi cuenta: datos del usuario y edición de su información de contacto."""
    user = current_actor()

    # En GET rellena el formulario con los datos actuales; en POST manda
    # lo enviado.
    form = ContactForm(obj=user)

    if form.validate_on_submit():
        changed = update_own_contact(
            user,
            telefono=form.telefono.data,
            cargo=form.cargo.data,
            departamento_area=form.departamento_area.data,
        )
        db.session.commit()

        if changed:
            flash("Tus datos se actualizaron.", "success")
        else:
            flash("No había cambios que guardar.", "warning")

        return redirect(url_for("account.index"))

    return render_template("account/index.html", form=form, user=user)


@bp.route("/password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()

    if form.validate_on_submit():
        response = _handle_password_change(form)

        if response is not None:
            return response

    # Con el cambio obligatorio pendiente se muestra una pantalla aislada,
    # sin la navegación (el usuario no puede ir a ninguna otra parte).
    mandatory = current_user.debe_cambiar_password
    template = (
        "account/password_required.html"
        if mandatory
        else "account/password.html"
    )

    return render_template(template, form=form, mandatory=mandatory)


def _handle_password_change(form: ChangePasswordForm):
    """Procesa un envío válido del formulario.

    Devuelve una respuesta (redirección) si el flujo termina, o `None`
    para volver a mostrar el formulario con los errores añadidos.
    """
    # La contraseña actual se puede adivinar desde este formulario con una
    # sesión robada, así que se aplica el mismo bloqueo que en el login, con
    # la fila bloqueada para que los envíos simultáneos no se pisen el contador.
    user = lock_user_row(current_actor())
    now = datetime.now(UTC)

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
        max_attempts=value_of(settings.LOGIN_MAX_FAILED_ATTEMPTS),
        lock_minutes=value_of(settings.LOGIN_LOCK_MINUTES),
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
