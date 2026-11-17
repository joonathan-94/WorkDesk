from flask_wtf import FlaskForm
from wtforms import Field, StringField, TextAreaField
from wtforms.validators import DataRequired, Length, ValidationError

from ..catalogs.forms import OptionalIntegerField
from ..models.ticket import MAX_DESCRIPTION_LENGTH, MAX_TITLE_LENGTH
from .editing import MAX_REASON_LENGTH
from .lifecycle import MAX_WAIT_TEXT_LENGTH


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


def _require_choice(field, choices, message):
    # Si el valor ni siquiera es un número, ya hay un error más preciso.
    if field.process_errors:
        return

    if field.data not in {value for value, _ in choices}:
        raise ValidationError(message)


def _require_version(field):
    """La versión viaja en un campo oculto: sin ella no se puede comprobar
    que nadie más haya modificado el ticket."""
    if field.data is None or field.data < 1:
        raise ValidationError(
            "No se pudo comprobar la versión del ticket. Recarga la página."
        )


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


class _TicketFieldsForm(FlaskForm):
    """Datos del ticket comunes a la creación y a la edición.

    Valida la forma de los datos y que lo elegido esté entre las opciones
    ofrecidas, que quien construye el formulario lee de la base de datos y
    pasa como atributos (como el rol en `users/forms.py`, sin `SelectField`).
    Las reglas de negocio las aplica `tickets.service` y `tickets.editing`.
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
    ubicacion = OptionalIntegerField("Ubicación")

    def __init__(self, *args, category_choices, location_choices, **kwargs):
        super().__init__(*args, **kwargs)

        self.category_choices = list(category_choices)
        self.location_choices = list(location_choices)

    def validate_categoria(self, field):
        _require_choice(
            field,
            self.category_choices,
            "Selecciona una categoría.",
        )

    def validate_ubicacion(self, field):
        # Opcional: solo se comprueba si se eligió algo.
        if field.process_errors or field.data is None:
            return

        _require_choice(
            field,
            self.location_choices,
            "Selecciona una ubicación válida.",
        )


class TicketForm(_TicketFieldsForm):
    """Creación de un ticket (docs/11, UI-004).

    `requester_choices` es None para el Solicitante: no elige solicitantes
    (queda como su propio solicitante) y cualquier valor enviado se ignora.
    """

    prioridad = OptionalIntegerField("Prioridad")
    solicitantes = IntegerListField("Solicitantes", default=list)

    def __init__(
        self,
        *args,
        priority_choices,
        requester_choices=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.priority_choices = list(priority_choices)
        self.requester_choices = (
            None if requester_choices is None else list(requester_choices)
        )

    def validate_prioridad(self, field):
        _require_choice(
            field,
            self.priority_choices,
            "Selecciona una prioridad.",
        )

    def validate_solicitantes(self, field):
        if self.requester_choices is None:
            # El Solicitante no elige solicitantes: se ignora lo enviado.
            field.data = []
            return

        valid_ids = {value for value, _ in self.requester_choices}

        if any(value not in valid_ids for value in field.data):
            raise ValidationError("Elige solicitantes de la lista.")


class TicketEditForm(_TicketFieldsForm):
    """Edición de título, descripción, categoría y ubicación.

    Lleva la versión del ticket con la que se abrió el formulario, para que
    el servidor detecte si otra persona lo modificó mientras tanto.
    """

    version = OptionalIntegerField("Versión")

    def validate_version(self, field):
        _require_version(field)


class PriorityChangeForm(FlaskForm):
    """Cambio de prioridad de un ticket, con un motivo obligatorio."""

    prioridad = OptionalIntegerField("Nueva prioridad")

    motivo = TextAreaField(
        "Motivo del cambio",
        filters=[_normalize_text],
        validators=[
            DataRequired(message="Indica el motivo del cambio."),
            Length(
                max=MAX_REASON_LENGTH,
                message=f"Máximo {MAX_REASON_LENGTH} caracteres.",
            ),
        ],
    )

    version = OptionalIntegerField("Versión")

    def __init__(self, *args, priority_choices, **kwargs):
        super().__init__(*args, **kwargs)

        self.priority_choices = list(priority_choices)

    def validate_prioridad(self, field):
        _require_choice(
            field,
            self.priority_choices,
            "Selecciona una prioridad.",
        )

    def validate_version(self, field):
        _require_version(field)


class StateChangeForm(FlaskForm):
    """Cambio de estado operativo de un ticket.

    Lleva la versión con la que se abrió la pantalla. El motivo de espera y su
    texto solo se piden al poner un ticket en espera y son opcionales; el
    servicio decide si la acción los admite.
    """

    version = OptionalIntegerField("Versión")
    motivo_espera = OptionalIntegerField("Motivo de espera")

    texto = TextAreaField(
        "Explicación",
        filters=[_normalize_text],
        validators=[
            Length(
                max=MAX_WAIT_TEXT_LENGTH,
                message=f"Máximo {MAX_WAIT_TEXT_LENGTH} caracteres.",
            ),
        ],
    )

    def __init__(self, *args, wait_reason_choices=(), **kwargs):
        super().__init__(*args, **kwargs)

        self.wait_reason_choices = list(wait_reason_choices)

    def validate_version(self, field):
        _require_version(field)

    def validate_motivo_espera(self, field):
        # Opcional: solo se comprueba si se eligió algo.
        if field.process_errors or field.data is None:
            return

        _require_choice(
            field,
            self.wait_reason_choices,
            "Selecciona un motivo de la lista.",
        )


class TechnicianPickForm(FlaskForm):
    """Elegir al técnico que se asigna a un ticket. Las opciones se pasan
    como atributo (sin `SelectField`, como el resto de formularios)."""

    tecnico = OptionalIntegerField("Técnico")

    def __init__(self, *args, choices, **kwargs):
        super().__init__(*args, **kwargs)

        self.choices = list(choices)

    def validate_tecnico(self, field):
        _require_choice(
            field,
            self.choices,
            "Elige un técnico de la lista.",
        )


class GroupChangeForm(FlaskForm):
    """Fijar el grupo de un ticket. Un valor vacío lo deja sin grupo."""

    version = OptionalIntegerField("Versión")
    grupo = OptionalIntegerField("Grupo")

    def __init__(self, *args, choices, **kwargs):
        super().__init__(*args, **kwargs)

        self.choices = list(choices)

    def validate_version(self, field):
        _require_version(field)

    def validate_grupo(self, field):
        # Vacío significa "sin grupo": solo se comprueba si se eligió algo.
        if field.process_errors or field.data is None:
            return

        _require_choice(field, self.choices, "Selecciona un grupo válido.")


class EscalationForm(FlaskForm):
    """Escalar un ticket a otro grupo y/o a otro técnico, con un motivo
    obligatorio. Hay que elegir al menos uno de los dos (lo comprueba el
    servicio, que conoce el valor actual)."""

    version = OptionalIntegerField("Versión")
    grupo = OptionalIntegerField("Grupo")
    tecnico = OptionalIntegerField("Técnico")

    motivo = TextAreaField(
        "Motivo del escalamiento",
        filters=[_normalize_text],
        validators=[
            DataRequired(message="Indica el motivo del escalamiento."),
            Length(
                max=MAX_REASON_LENGTH,
                message=f"Máximo {MAX_REASON_LENGTH} caracteres.",
            ),
        ],
    )

    def __init__(self, *args, group_choices, technician_choices, **kwargs):
        super().__init__(*args, **kwargs)

        self.group_choices = list(group_choices)
        self.technician_choices = list(technician_choices)

    def validate_version(self, field):
        _require_version(field)

    def validate_grupo(self, field):
        if field.process_errors or field.data is None:
            return

        _require_choice(field, self.group_choices, "Selecciona un grupo válido.")

    def validate_tecnico(self, field):
        if field.process_errors or field.data is None:
            return

        _require_choice(
            field,
            self.technician_choices,
            "Elige un técnico de la lista.",
        )
