from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import (
    DataRequired,
    Length,
    Optional,
    Regexp,
    ValidationError,
)

from ..cleaning import MAX_REASON_LENGTH, strip_text

# Las reglas de forma viven en `rules.py` (las comparte el servicio y `create-admin`).
from .rules import (
    EMAIL_FORMAT_MESSAGE,
    EMAIL_MAX_LENGTH,
    EMAIL_PATTERN,
    NAME_MAX_LENGTH,
    USERNAME_FORMAT_MESSAGE,
    USERNAME_LENGTH_MESSAGE,
    USERNAME_MAX_LENGTH,
    USERNAME_MIN_LENGTH,
    USERNAME_PATTERN,
)

PASSWORD_MODE_GENERATE = "generate"
PASSWORD_MODE_MANUAL = "manual"

PASSWORD_MODE_CHOICES = (
    (PASSWORD_MODE_GENERATE, "Generar automáticamente"),
    (PASSWORD_MODE_MANUAL, "Escribirla yo"),
)


def _normalize(value):
    return value.strip().lower() if isinstance(value, str) else value


class ContactForm(FlaskForm):
    """Datos de contacto y de organización de un usuario.

    Son los datos que el propio usuario puede editar en "Mi cuenta" y que
    el Administrador también edita desde la administración de usuarios.
    """

    telefono = StringField(
        "Teléfono",
        filters=[strip_text],
        validators=[
            Optional(),
            Length(max=30, message="Máximo 30 caracteres."),
        ],
    )

    cargo = StringField(
        "Cargo",
        filters=[strip_text],
        validators=[
            Optional(),
            Length(max=100, message="Máximo 100 caracteres."),
        ],
    )

    departamento_area = StringField(
        "Departamento o área",
        filters=[strip_text],
        validators=[
            Optional(),
            Length(max=100, message="Máximo 100 caracteres."),
        ],
    )


class ProfileForm(ContactForm):
    """Datos personales de un usuario (comunes al alta y a la edición).

    Valida la forma de los datos. Las reglas de negocio (unicidad, rol
    existente, política de contraseñas) las aplica `users.service`.
    """

    nombre = StringField(
        "Nombre",
        filters=[strip_text],
        validators=[
            DataRequired(message="Ingresa el nombre."),
            Length(max=NAME_MAX_LENGTH, message=f"Máximo {NAME_MAX_LENGTH} caracteres."),
        ],
    )

    apellido = StringField(
        "Apellido",
        filters=[strip_text],
        validators=[
            DataRequired(message="Ingresa el apellido."),
            Length(max=NAME_MAX_LENGTH, message=f"Máximo {NAME_MAX_LENGTH} caracteres."),
        ],
    )

    email = StringField(
        "Correo electrónico",
        filters=[_normalize],
        validators=[
            DataRequired(message="Ingresa el correo electrónico."),
            Length(max=EMAIL_MAX_LENGTH, message=f"Máximo {EMAIL_MAX_LENGTH} caracteres."),
            Regexp(EMAIL_PATTERN, message=EMAIL_FORMAT_MESSAGE),
        ],
    )


class TemporaryPasswordForm(FlaskForm):
    """Elección de la contraseña temporal: generada o escrita.

    Común al alta de usuarios y al restablecimiento de contraseña.
    """

    password_mode = StringField(
        "Contraseña temporal",
        default=PASSWORD_MODE_GENERATE,
    )

    # Sin validadores de campo: debe llegar vacío en modo "generar" y se
    # exige en modo "manual" en `validate_temporary_password`.
    temporary_password = PasswordField("Contraseña temporal")

    def validate_password_mode(self, field):
        valid_modes = {code for code, _ in PASSWORD_MODE_CHOICES}

        if field.data not in valid_modes:
            raise ValidationError("Elige cómo definir la contraseña.")

    def validate_temporary_password(self, field):
        if self.password_mode.data == PASSWORD_MODE_MANUAL and not field.data:
            raise ValidationError("Ingresa la contraseña temporal.")


class _RoleChoicesMixin:
    """Guarda las opciones de rol y valida que el rol elegido exista.

    `role_choices` son los pares (código, nombre) de los roles disponibles,
    leídos de la base de datos por quien construye el formulario. Se validan
    aquí, sin los campos de selección de WTForms: la plantilla dibuja el
    selector y los mensajes quedan en español.
    """

    def __init__(self, *args, role_choices, **kwargs):
        super().__init__(*args, **kwargs)

        self.role_choices = list(role_choices)

    def validate_rol(self, field):
        valid_codes = {code for code, _ in self.role_choices}

        if field.data not in valid_codes:
            raise ValidationError("Selecciona un rol válido.")


class CreateUserForm(_RoleChoicesMixin, ProfileForm, TemporaryPasswordForm):
    """Alta de usuario por el Administrador."""

    username = StringField(
        "Usuario",
        filters=[_normalize],
        validators=[
            DataRequired(message="Ingresa el nombre de usuario."),
            Length(
                min=USERNAME_MIN_LENGTH,
                max=USERNAME_MAX_LENGTH,
                message=USERNAME_LENGTH_MESSAGE,
            ),
            Regexp(USERNAME_PATTERN, message=USERNAME_FORMAT_MESSAGE),
        ],
    )

    rol = StringField(
        "Rol",
        validators=[DataRequired(message="Selecciona un rol.")],
    )


class EditUserForm(ProfileForm):
    """Edición de los datos personales (el username no se puede cambiar)."""


class ChangeRoleForm(_RoleChoicesMixin, FlaskForm):
    """Cambio de rol, con un motivo opcional para la auditoría."""

    rol = StringField(
        "Rol",
        validators=[DataRequired(message="Selecciona un rol.")],
    )

    motivo = StringField(
        "Motivo",
        filters=[strip_text],
        validators=[
            Optional(),
            Length(
                max=MAX_REASON_LENGTH,
                message=f"Máximo {MAX_REASON_LENGTH} caracteres.",
            ),
        ],
    )


class ReasonForm(FlaskForm):
    """Confirmación de una acción (activar o desactivar) con motivo opcional."""

    motivo = StringField(
        "Motivo",
        filters=[strip_text],
        validators=[
            Optional(),
            Length(
                max=MAX_REASON_LENGTH,
                message=f"Máximo {MAX_REASON_LENGTH} caracteres.",
            ),
        ],
    )


class ResetPasswordForm(TemporaryPasswordForm):
    """Restablecimiento de contraseña por el Administrador."""
