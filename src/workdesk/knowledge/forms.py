"""Formularios de la base de conocimiento. Validan la forma de los datos; las reglas las
aplica `knowledge/service.py`."""

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField
from wtforms.validators import DataRequired, Length, ValidationError

from ..catalogs.forms import OptionalIntegerField
from ..cleaning import strip_text
from ..models.article import MAX_ARTICLE_CONTENT_LENGTH, MAX_ARTICLE_TITLE_LENGTH
from ..models.article import ArticleVisibility as Visibility

VISIBILITY_CHOICES = (
    (Visibility.PRIVADO.value, "Privado: solo el personal de soporte"),
    (Visibility.PUBLICO.value, "Público: también los solicitantes"),
)


def _normalize_newlines(value):
    # Así el límite coincide con el contador del navegador (ver el formulario de tickets).
    if not isinstance(value, str):
        return value

    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


class ArticleForm(FlaskForm):
    """Crear y editar un artículo."""

    titulo = StringField(
        "Título",
        filters=[strip_text],
        validators=[
            DataRequired(message="El título es obligatorio."),
            Length(
                max=MAX_ARTICLE_TITLE_LENGTH,
                message=f"Máximo {MAX_ARTICLE_TITLE_LENGTH} caracteres.",
            ),
        ],
    )
    contenido = TextAreaField(
        "Contenido",
        filters=[_normalize_newlines],
        validators=[
            DataRequired(message="El contenido es obligatorio."),
            Length(
                max=MAX_ARTICLE_CONTENT_LENGTH,
                message=f"Máximo {MAX_ARTICLE_CONTENT_LENGTH} caracteres.",
            ),
        ],
    )
    categoria = OptionalIntegerField("Categoría")
    visibilidad = StringField("Visibilidad")
    # Solo al editar: la versión con la que se abrió la pantalla.
    version = OptionalIntegerField("Versión")

    def __init__(self, *args, category_choices, **kwargs):
        super().__init__(*args, **kwargs)
        self.category_choices = list(category_choices)
        self.visibility_choices = list(VISIBILITY_CHOICES)

    def validate_categoria(self, field):
        if field.data not in {code for code, _label in self.category_choices}:
            raise ValidationError("Elige una categoría disponible.")

    def validate_visibilidad(self, field):
        if field.data not in {code for code, _label in self.visibility_choices}:
            raise ValidationError("Elige si el artículo es público o privado.")
