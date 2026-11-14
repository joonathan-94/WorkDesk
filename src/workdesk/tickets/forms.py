from flask_wtf import FlaskForm
from wtforms import Field, StringField, TextAreaField
from wtforms.validators import DataRequired, Length, ValidationError

from ..catalogs.forms import OptionalIntegerField
from ..models.ticket import MAX_DESCRIPTION_LENGTH, MAX_TITLE_LENGTH


def _strip(value):
    return value.strip() if isinstance(value, str) else value


def _normalize_text(value):
    """Recorta y unifica los saltos de línea.

    Los navegadores envían los saltos de un textarea como CRLF: contarían
    como dos caracteres y el límite no coincidiría con el contador que ve la
    persona (que cuenta uno por salto).
    """
    if not isinstance(value, str):
        return value

    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


class IntegerListField(Field):
    """Lista de enteros enviada como varios valores con el mismo nombre
    (una casilla por valor). Sin ninguna marcada, la lista queda vacía.
    """

    def process_formdata(self, valuelist):
        try:
            self.data = [int(value) for value in valuelist if value.strip()]
        except ValueError as error:
            self.data = []

            raise ValueError("La selección no es válida.") from error


class TicketForm(FlaskForm):
    """Creación de un ticket (docs/11, UI-004).

    Valida la forma de los datos y que lo elegido esté entre las opciones
    ofrecidas, que quien construye el formulario lee de la base de datos y
    pasa como atributos (como el rol en `users/forms.py`, sin `SelectField`).
    Las reglas de negocio las aplica `tickets.service`.

    `requester_choices` es None para el Solicitante: no elige solicitantes
    (queda como su propio solicitante) y cualquier valor enviado se ignora.
    """

    titulo = StringField(
        "Título",
        filters=[_strip],
        validators=[
            DataRequired(message="Ingresa un título."),
            Length(
                max=MAX_TITLE_LENGTH,
                message=f"Máximo {MAX_TITLE_LENGTH} caracteres.",
            ),
        ],
    )

    descripcion = TextAreaField(
        "Descripción",
        filters=[_normalize_text],
        validators=[
            DataRequired(message="Describe tu solicitud."),
            Length(
                max=MAX_DESCRIPTION_LENGTH,
                message=f"Máximo {MAX_DESCRIPTION_LENGTH} caracteres.",
            ),
        ],
    )

    categoria = OptionalIntegerField("Categoría")
    prioridad = OptionalIntegerField("Prioridad")
    ubicacion = OptionalIntegerField("Ubicación")
    solicitantes = IntegerListField("Solicitantes", default=list)

    def __init__(
        self,
        *args,
        category_choices,
        priority_choices,
        location_choices,
        requester_choices=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.category_choices = list(category_choices)
        self.priority_choices = list(priority_choices)
        self.location_choices = list(location_choices)
        self.requester_choices = (
            None if requester_choices is None else list(requester_choices)
        )

    def validate_categoria(self, field):
        self._require_choice(
            field,
            self.category_choices,
            "Selecciona una categoría.",
        )

    def validate_prioridad(self, field):
        self._require_choice(
            field,
            self.priority_choices,
            "Selecciona una prioridad.",
        )

    def validate_ubicacion(self, field):
        # Opcional: solo se comprueba si se eligió algo.
        if field.process_errors or field.data is None:
            return

        self._require_choice(
            field,
            self.location_choices,
            "Selecciona una ubicación válida.",
        )

    def validate_solicitantes(self, field):
        if self.requester_choices is None:
            # El Solicitante no elige solicitantes: se ignora lo enviado.
            field.data = []
            return

        valid_ids = {value for value, _ in self.requester_choices}

        if any(value not in valid_ids for value in field.data):
            raise ValidationError("Elige solicitantes de la lista.")

    @staticmethod
    def _require_choice(field, choices, message):
        # Si el valor ni siquiera es un número, ya hay un error más preciso.
        if field.process_errors:
            return

        if field.data not in {value for value, _ in choices}:
            raise ValidationError(message)
