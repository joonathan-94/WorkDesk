from flask_wtf import FlaskForm
from wtforms import IntegerField, StringField, TextAreaField
from wtforms.validators import (
    DataRequired,
    Length,
    Optional,
    ValidationError,
)

from ..models.ubicacion import LocationType

MAX_NAME_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 500
MAX_ORDER = 9999


def _strip(value):
    return value.strip() if isinstance(value, str) else value


class OptionalIntegerField(IntegerField):
    """Número entero opcional, con el mensaje de error en español.

    El `IntegerField` de WTForms informa del error en inglés y trata el
    campo vacío como un error; aquí un campo vacío es simplemente `None`.
    """

    def process_formdata(self, valuelist):
        # Sin el campo en la petición se conserva el valor actual (como en
        # un StringField); con el campo vacío, el valor pasa a ser None.
        if not valuelist:
            return

        if not valuelist[0].strip():
            self.data = None
            return

        try:
            self.data = int(valuelist[0])
        except ValueError as error:
            self.data = None

            raise ValueError("Ingresa un número entero.") from error


class _NamedItemForm(FlaskForm):
    """Nombre y descripción: lo que comparten todos los catálogos.

    Valida la forma de los datos. Las reglas de negocio (nombre repetido,
    protecciones) las aplica `catalogs.service`.
    """

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


class CategoryForm(_NamedItemForm):
    orden = OptionalIntegerField(
        "Orden",
        validators=[Optional()],
    )

    # Se valida aquí y no con NumberRange: ese validador también se queja
    # cuando el campo está vacío o no es un número, y repetiría el error que
    # ya informa OptionalIntegerField.
    def validate_orden(self, field):
        if field.data is not None and not 0 <= field.data <= MAX_ORDER:
            raise ValidationError(f"Usa un número entre 0 y {MAX_ORDER}.")


class PriorityForm(_NamedItemForm):
    """Solo nombre y descripción: el nivel y el color de las prioridades
    son fijos (docs/11, UI-019)."""


class LocationForm(_NamedItemForm):
    # Vacío significa "sin especificar". Se valida sin los campos de
    # selección de WTForms, igual que el rol en la administración de
    # usuarios: la plantilla dibuja el selector.
    tipo = StringField(
        "Tipo",
        filters=[_strip],
    )

    def validate_tipo(self, field):
        if field.data and field.data not in {t.value for t in LocationType}:
            raise ValidationError("Selecciona un tipo válido.")
