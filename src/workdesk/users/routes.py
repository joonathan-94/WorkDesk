from flask import current_app, make_response, render_template, request
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
    CreateUserForm,
)
from .service import (
    VALID_STATUSES,
    DuplicateUserError,
    UnknownRoleError,
    create_user,
    list_roles,
    list_users,
)


@bp.get("")
@roles_required(RoleCode.ADMINISTRADOR)
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


@bp.route("/new", methods=["GET", "POST"])
@roles_required(RoleCode.ADMINISTRADOR)
def new_user():
    form = CreateUserForm(
        role_choices=[(role.codigo, role.nombre) for role in list_roles()]
    )

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

    if generate:
        temporary_password = generate_temporary_password(
            current_app.config["PASSWORD_MIN_LENGTH"]
        )
    else:
        temporary_password = form.temporary_password.data

    try:
        user = create_user(
            actor=current_user._get_current_object(),
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

    # La contraseña generada solo existe en esta respuesta: no se guarda en
    # la sesión (cookie firmada pero legible), ni en la base de datos, ni en
    # los registros. Por eso no se redirige y se impide que se cachee.
    response = make_response(
        render_template(
            "users/created.html",
            user=user,
            generated_password=temporary_password if generate else None,
        )
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    return response


def _add_duplicate_error(form: CreateUserForm, error: DuplicateUserError):
    if error.field == "email":
        form.email.errors.append("Ya existe un usuario con ese correo.")
    elif error.field == "username":
        form.username.errors.append("Ya existe un usuario con ese nombre.")
    else:
        form.username.errors.append(
            "El usuario o el correo ya están registrados."
        )
