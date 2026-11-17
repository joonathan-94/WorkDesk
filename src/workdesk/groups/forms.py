from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, ValidationError

from ..catalogs.forms import (
    MAX_DESCRIPTION_LENGTH,
    MAX_NAME_LENGTH,
    OptionalIntegerField,
)


def _strip(value):
    return value.strip() if isinstance(value, str) else value


class GroupForm(FlaskForm):
    """Alta y edición de un grupo. Valida la forma de los datos; las reglas
    (nombre repetido, etc.) las aplica `groups.service`."""

    nombre = StringField(
        "Nombre",
        filters=[_strip],
        validators=[
            DataRequired(message="Ingresa el nombre."),
            Length(
                max=MAX_NAME_LENGTH,
                message=f"Máximo {MAX_NAME_LENGTH} caracteres.",
            ),
        ],
    )

    descripcion = TextAreaField(
        "Descripción",
        filters=[_strip],
        validators=[
            Optional(),
            Length(
                max=MAX_DESCRIPTION_LENGTH,
                message=f"Máximo {MAX_DESCRIPTION_LENGTH} caracteres.",
            ),
        ],
    )


class UserPickForm(FlaskForm):
    """Elegir a una persona de una lista (un técnico para un grupo o un
    supervisor responsable). Las opciones se pasan como atributo, sin
    `SelectField`, como en el resto de formularios del proyecto."""

    usuario = OptionalIntegerField("Persona")

    def __init__(self, *args, choices, message, **kwargs):
        super().__init__(*args, **kwargs)

        self.choices = list(choices)
        self.message = message

    def validate_usuario(self, field):
        if field.process_errors or field.data not in {
            value for value, _ in self.choices
        }:
            raise ValidationError(self.message)
