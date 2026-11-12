from flask import (
    abort,
    current_app,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user

from ..extensions import db
from ..security import (
    PasswordPolicyError,
    RoleCode,
    generate_temporary_password,
    roles_required,
)
from . import bp
from .forms import (
    PASSWORD_MODE_CHOICES,
    PASSWORD_MODE_GENERATE,
    ChangeRoleForm,
    CreateUserForm,
    EditUserForm,
    ReasonForm,
    ResetPasswordForm,
)
from .service import (
    VALID_STATUSES,
    DuplicateUserError,
    UnknownRoleError,
    UserRuleError,
    activate_user,
    change_role,
    create_user,
    deactivate_user,
    get_user,
    list_roles,
    list_users,
    reset_user_password,
    update_profile,
)

# Todas las rutas de este módulo son exclusivas del Administrador. La
# autorización se comprueba aquí, en backend; ocultar enlaces no la sustituye.
admin_only = roles_required(RoleCode.ADMINISTRADOR)


# --- Listado ----------------------------------------------------------


@bp.get("")
@admin_only
def list_users_page():
    query_text = request.args.get("q", "").strip()
    role_code = request.args.get("rol", "")
    status = request.args.get("estado", "")
    page = max(request.args.get("page", 1, type=int), 1)

    roles = list_roles()

    # Los filtros inválidos se ignoran en lugar de producir un error.
    if role_code not in {role.codigo for role in roles}:
        role_code = ""

    if status not in VALID_STATUSES:
        status = ""

    pagination = list_users(
        query_text=query_text,
        role_code=role_code,
        status=status,
        page=page,
    )

    return render_template(
        "users/list.html",
        pagination=pagination,
        roles=roles,
        query_text=query_text,
        role_code=role_code,
        status=status,
    )


# --- Alta -------------------------------------------------------------


@bp.route("/new", methods=["GET", "POST"])
@admin_only
def new_user():
    form = CreateUserForm(role_choices=_role_choices())

    if form.validate_on_submit():
        response = _create_from_form(form)

        if response is not None:
            return response

    return render_template(
        "users/new.html",
        form=form,
        password_modes=PASSWORD_MODE_CHOICES,
    )


def _create_from_form(form: CreateUserForm):
    """Crea el usuario con los datos del formulario.

    Devuelve la respuesta de éxito, o `None` para volver a mostrar el
    formulario con los errores añadidos.
    """
    generate = form.password_mode.data == PASSWORD_MODE_GENERATE
    temporary_password = _choose_temporary_password(form)

    try:
        user = create_user(
            actor=_actor(),
            nombre=form.nombre.data,
            apellido=form.apellido.data,
            username=form.username.data,
            email=form.email.data,
            role_code=form.rol.data,
            temporary_password=temporary_password,
            telefono=form.telefono.data,
            cargo=form.cargo.data,
            departamento_area=form.departamento_area.data,
        )
        db.session.commit()
    except DuplicateUserError as error:
        db.session.rollback()
        _add_duplicate_error(form, error)
        return None
    except PasswordPolicyError as error:
        db.session.rollback()
        form.temporary_password.errors.append(str(error))
        return None
    except UnknownRoleError:
        db.session.rollback()
        form.rol.errors.append("Selecciona un rol válido.")
        return None

    return _no_store(
        render_template(
            "users/created.html",
            user=user,
            generated_password=temporary_password if generate else None,
        )
    )


def _add_duplicate_error(form, error: DuplicateUserError):
    if error.field == "email":
        form.email.errors.append("Ya existe un usuario con ese correo.")
    elif error.field == "username":
        form.username.errors.append("Ya existe un usuario con ese nombre.")
    else:
        form.username.errors.append(
            "El usuario o el correo ya están registrados."
        )


# --- Detalle y edición ------------------------------------------------


@bp.get("/<int:user_id>")
@admin_only
def detail(user_id: int):
    user = _get_or_404(user_id)

    return render_template(
        "users/detail.html",
        user=user,
        is_self=user.id == current_user.id,
    )


@bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
@admin_only
def edit_user(user_id: int):
    user = _get_or_404(user_id)

    # En GET rellena el formulario con los datos actuales; en POST manda
    # lo enviado.
    form = EditUserForm(obj=user)

    if form.validate_on_submit():
        try:
            changed = update_profile(
                user,
                actor=_actor(),
                nombre=form.nombre.data,
                apellido=form.apellido.data,
                email=form.email.data,
                telefono=form.telefono.data,
                cargo=form.cargo.data,
                departamento_area=form.departamento_area.data,
            )
            db.session.commit()
        except DuplicateUserError:
            db.session.rollback()
            form.email.errors.append("Ya existe un usuario con ese correo.")
        else:
            if changed:
                flash("Los datos del usuario se actualizaron.", "success")
            else:
                flash("No había cambios que guardar.", "warning")

            return redirect(url_for("users.detail", user_id=user_id))

    return render_template("users/edit.html", form=form, user=user)


# --- Cambio de rol ----------------------------------------------------


@bp.route("/<int:user_id>/role", methods=["GET", "POST"])
@admin_only
def change_user_role(user_id: int):
    user = _get_or_404(user_id)

    if user.id == current_user.id:
        return _blocked(user_id, "No puedes cambiar tu propio rol.")

    form = ChangeRoleForm(
        role_choices=_role_choices(),
        rol=user.rol.codigo,
    )

    if form.validate_on_submit():
        try:
            change_role(
                user,
                form.rol.data,
                actor=_actor(),
                reason=form.motivo.data,
            )
            db.session.commit()
        except UnknownRoleError:
            db.session.rollback()
            form.rol.errors.append("Selecciona un rol válido.")
        except UserRuleError as error:
            return _blocked(user_id, str(error))
        else:
            flash(
                f"El rol de {user.nombre} {user.apellido} ahora es "
                f"{user.rol.nombre}. Deberá iniciar sesión de nuevo.",
                "success",
            )

            return redirect(url_for("users.detail", user_id=user_id))

    return render_template("users/role.html", form=form, user=user)


# --- Activación y desactivación ---------------------------------------


@bp.route("/<int:user_id>/deactivate", methods=["GET", "POST"])
@admin_only
def deactivate(user_id: int):
    if user_id == current_user.id:
        return _blocked(user_id, "No puedes desactivar tu propia cuenta.")

    return _confirm_status_change(
        user_id,
        mode="deactivate",
        operation=deactivate_user,
        success_message="La cuenta de {name} fue desactivada.",
    )


@bp.route("/<int:user_id>/activate", methods=["GET", "POST"])
@admin_only
def activate(user_id: int):
    return _confirm_status_change(
        user_id,
        mode="activate",
        operation=activate_user,
        success_message="La cuenta de {name} fue reactivada.",
    )


def _confirm_status_change(user_id, *, mode, operation, success_message):
    """Pantalla de confirmación y ejecución de activar o desactivar."""
    user = _get_or_404(user_id)
    form = ReasonForm()

    if form.validate_on_submit():
        name = f"{user.nombre} {user.apellido}"

        try:
            operation(user, actor=_actor(), reason=form.motivo.data)
            db.session.commit()
        except UserRuleError as error:
            return _blocked(user_id, str(error))

        flash(success_message.format(name=name), "success")

        return redirect(url_for("users.detail", user_id=user_id))

    return render_template(
        "users/status_confirm.html",
        form=form,
        user=user,
        mode=mode,
    )


# --- Restablecimiento de contraseña -----------------------------------


@bp.route("/<int:user_id>/reset-password", methods=["GET", "POST"])
@admin_only
def reset_password_page(user_id: int):
    user = _get_or_404(user_id)

    if user.id == current_user.id:
        return _blocked(
            user_id,
            "Para cambiar tu propia contraseña usa «Cambiar contraseña».",
        )

    form = ResetPasswordForm()

    if form.validate_on_submit():
        generate = form.password_mode.data == PASSWORD_MODE_GENERATE
        temporary_password = _choose_temporary_password(form)

        try:
            reset_user_password(
                user,
                temporary_password,
                actor=_actor(),
            )
            db.session.commit()
        except PasswordPolicyError as error:
            db.session.rollback()
            form.temporary_password.errors.append(str(error))
        except UserRuleError as error:
            return _blocked(user_id, str(error))
        else:
            return _no_store(
                render_template(
                    "users/password_reset_done.html",
                    user=user,
                    generated_password=(
                        temporary_password if generate else None
                    ),
                )
            )

    return render_template(
        "users/reset_password.html",
        form=form,
        user=user,
        password_modes=PASSWORD_MODE_CHOICES,
    )


# --- Utilidades -------------------------------------------------------


def _actor():
    return current_user._get_current_object()


def _get_or_404(user_id: int):
    user = get_user(user_id)

    if user is None:
        abort(404)

    return user


def _role_choices():
    return [(role.codigo, role.nombre) for role in list_roles()]


def _choose_temporary_password(form) -> str:
    """Contraseña temporal según el modo elegido: generada o escrita."""
    if form.password_mode.data == PASSWORD_MODE_GENERATE:
        return generate_temporary_password(
            current_app.config["PASSWORD_MIN_LENGTH"]
        )

    return form.temporary_password.data


def _blocked(user_id: int, message: str):
    """Una regla de negocio impide la acción: avisa y vuelve al detalle."""
    db.session.rollback()
    flash(message, "error")

    return redirect(url_for("users.detail", user_id=user_id))


def _no_store(html: str):
    """Respuesta que muestra una contraseña generada: no se guarda en caché.

    La contraseña solo existe en esa respuesta: no se guarda en la sesión
    (cookie firmada pero legible), ni en la base de datos, ni en los
    registros. Por eso no se redirige y se impide que se cachee.
    """
    response = make_response(html)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    return response
