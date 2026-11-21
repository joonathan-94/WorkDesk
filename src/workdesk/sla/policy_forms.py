"""Formulario de los objetivos de SLA de una prioridad (docs/11, UI-022).

Valida la *forma* de lo que escribe el Administrador y la convierte en datos. Los
dos objetivos son duraciones escritas como las diría una persona («30 min»,
«4 h» o «1 h 30 min»): un texto es más cómodo que dos casillas de horas y
minutos por objetivo y funciona sin JavaScript. Los tiempos son **horas
laborales**, así que no hay días: un «día» dura distinto según el calendario.

Qué valores son aceptables (mayor que cero, tope, primera respuesta dentro de la
resolución, umbral entre 1 y 100) lo decide `policy_problems`, en el servicio:
aquí solo se señala cada error junto a su campo, todos a la vez.
"""

import re

from wtforms import BooleanField, StringField
from wtforms.validators import DataRequired, Length, Optional, ValidationError

from ..catalogs.forms import OptionalIntegerField
from ..cleaning import strip_text
from ..formatting import format_duration
from ..models import PoliticaSla
from ..users.forms import ReasonForm
from .policies import policy_problems, policy_token

MAX_DURATION_TEXT_LENGTH = 40

# Con qué porcentaje se propone el aviso al definir una política nueva (el valor
# de ejemplo de docs/11, UI-022).
DEFAULT_WARNING_PERCENT = 80

_DURATION = re.compile(
    r"(?:(?P<hours>[0-9]+)\s*(?:horas?|hrs?|h))?"
    r"\s*"
    r"(?:(?P<minutes>[0-9]+)\s*(?P<unit>minutos?|mins?|m)?)?",
    re.IGNORECASE,
)

_DURATION_EXAMPLES = "«30 min», «4 h» o «1 h 30 min»"


# --- Las duraciones: de texto a minutos y de minutos a texto ----------------------


def parse_duration(text: str | None) -> int | None:
    """Los minutos de una duración escrita como «30 min», «4 h» o «1 h 30 min».

    Acepta horas (`h`, `hr`, `hrs`, `hora`, `horas`) y minutos (`m`, `min`, `mins`,
    `minuto`, `minutos`), con o sin espacios, y los minutos pueden ir tras las
    horas sin unidad («1h30»). Un texto vacío es «sin objetivo» y devuelve `None`.
    Lanza `ValueError` con el mensaje para mostrar si algo está mal escrito.
    """
    text = (text or "").strip()

    if not text:
        return None

    if re.search(r"[0-9][.,][0-9]", text):
        raise ValueError(
            "Usa horas y minutos enteros, por ejemplo «1 h 30 min», en lugar "
            "de decimales."
        )

    match = _DURATION.fullmatch(text)

    if match is None or (match["hours"] is None and match["minutes"] is None):
        raise ValueError(
            f"«{text}» no es una duración válida. Escribe, por ejemplo, "
            f"{_DURATION_EXAMPLES}."
        )

    # Un número suelto es ambiguo (¿minutos u horas?), salvo tras las horas.
    if match["hours"] is None and match["unit"] is None:
        raise ValueError(
            f"A «{text}» le falta la unidad: escribe «{text} min» o «{text} h»."
        )

    return int(match["hours"] or 0) * 60 + int(match["minutes"] or 0)


def duration_text(minutes: int | None) -> str:
    """Los minutos como se escriben en el formulario; vacío si no hay objetivo."""
    return "" if minutes is None else format_duration(minutes)


# --- El formulario ------------------------------------------------------------------


class PolicyForm(ReasonForm):
    """Los objetivos de una prioridad: primera respuesta, resolución, umbral de
    aviso y pausa en espera.

    Hereda el motivo opcional de `ReasonForm`. Tras validar, `response_minutes` y
    `resolution_minutes` tienen las duraciones ya convertidas.
    """

    primera_respuesta = StringField(
        "Primera respuesta",
        filters=[strip_text],
        validators=[
            Optional(),
            Length(
                max=MAX_DURATION_TEXT_LENGTH,
                message=f"Máximo {MAX_DURATION_TEXT_LENGTH} caracteres.",
            ),
        ],
    )

    resolucion = StringField(
        "Resolución",
        filters=[strip_text],
        validators=[
            DataRequired(message="Ingresa el objetivo de resolución."),
            Length(
                max=MAX_DURATION_TEXT_LENGTH,
                message=f"Máximo {MAX_DURATION_TEXT_LENGTH} caracteres.",
            ),
        ],
    )

    umbral_aviso = OptionalIntegerField(
        "Umbral de aviso (%)",
        validators=[Optional()],
    )

    # Una casilla sin marcar no viaja en la petición: el valor es False, que es
    # lo correcto. La plantilla pone la etiqueta con el nombre vigente del estado.
    pausa_en_espera = BooleanField("Pausar el SLA mientras el ticket esté en espera")

    # La marca de la política tal como estaba al abrir la pantalla: sin ella no se
    # puede comprobar que nadie más la haya cambiado mientras tanto.
    base = StringField("Marca")

    def validate_base(self, field):
        if not field.data:
            raise ValidationError(
                "No se pudo comprobar el estado de la política. Recarga la página."
            )

    def _parse(self, field: StringField) -> int | None:
        """Los minutos del campo, o `None` si está vacío o mal escrito (en cuyo
        caso el error queda junto al campo)."""
        # Un campo que ya falló (demasiado largo, vacío siendo obligatorio) no se
        # vuelve a señalar.
        if field.errors:
            return None

        try:
            return parse_duration(field.data)
        except ValueError as error:
            field.errors = [*field.errors, str(error)]

            return None

    def validate(self, extra_validators=None):
        valid = super().validate(extra_validators)

        self.response_minutes = self._parse(self.primera_respuesta)
        self.resolution_minutes = self._parse(self.resolucion)

        problems = policy_problems(
            response_minutes=self.response_minutes,
            resolution_minutes=self.resolution_minutes,
            warning_percent=self.umbral_aviso.data,
        )

        for name, message in problems.items():
            field = getattr(self, name)

            # Si el campo ya tiene su error (por ejemplo, el de una duración mal
            # escrita) no se repite.
            if not field.errors:
                field.errors = [message]

        return valid and not any(
            field.errors
            for field in (
                self.primera_respuesta,
                self.resolucion,
                self.umbral_aviso,
            )
        )


def policy_form_data(policy: PoliticaSla | None) -> dict:
    """Los valores con los que se rellena el formulario al abrirlo.

    Con una política existente, los suyos; sin ella, un formulario en blanco con
    el aviso propuesto y la pausa en espera activada.
    """
    if policy is None:
        return {
            "primera_respuesta": "",
            "resolucion": "",
            "umbral_aviso": DEFAULT_WARNING_PERCENT,
            "pausa_en_espera": True,
            "base": policy_token(None),
        }

    return {
        "primera_respuesta": duration_text(policy.tiempo_objetivo_respuesta_minutos),
        "resolucion": duration_text(policy.tiempo_objetivo_resolucion_minutos),
        "umbral_aviso": policy.umbral_aviso_consumo_porcentaje,
        "pausa_en_espera": policy.pausa_en_espera,
        "base": policy_token(policy),
    }
