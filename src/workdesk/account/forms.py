from flask_wtf import FlaskForm
from wtforms import PasswordField
from wtforms.validators import DataRequired, EqualTo


class ChangePasswordForm(FlaskForm):
    """Formulario de cambio de contraseña propio.

    Solo valida la forma (campos presentes y confirmación coincidente).
    Las reglas de la contraseña viven en la política de contraseñas
    (security/password_policy.py) para que exista una única fuente.
    """

    current_password = PasswordField(
        "Contraseña actual",
        validators=[DataRequired(message="Ingresa tu contraseña actual.")],
    )

    new_password = PasswordField(
        "Nueva contraseña",
        validators=[DataRequired(message="Ingresa la nueva contraseña.")],
    )

    confirm_password = PasswordField(
        "Confirmar nueva contraseña",
        validators=[
            DataRequired(message="Confirma la nueva contraseña."),
            EqualTo(
                "new_password",
                message="Las contraseñas no coinciden.",
            ),
        ],
    )
