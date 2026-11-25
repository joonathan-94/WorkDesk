"""Limpieza de los textos que escriben las personas.

Lo comparten los formularios (que limpian lo que llega del navegador) y los
servicios (que no confían en que alguien ya lo haya hecho). Son funciones
pequeñas a propósito: tenerlas en un solo lugar evita que cada módulo escriba
su propia copia y que, con el tiempo, dejen de comportarse igual.
"""

# Largo máximo del motivo que acompaña a una acción (cambiar la prioridad, reasignar,
# desactivar, cambiar la configuración...).
MAX_REASON_LENGTH = 500


def blank_to_none(value: str | None) -> str | None:
    """Recorta el texto y devuelve None si no queda nada.

    Sirve para los campos opcionales: un campo vacío o de solo espacios se
    guarda como «sin valor» y no como una cadena vacía.
    """
    if value is None:
        return None

    value = value.strip()

    return value or None


def strip_text(value):
    """Filtro de WTForms: recorta los espacios de los extremos de un texto.

    Deja pasar cualquier valor que no sea texto (por ejemplo, `None` cuando el
    campo no llegó en la petición) para que lo valide el campo.
    """
    return value.strip() if isinstance(value, str) else value


def normalize_newlines(value):
    """Filtro de WTForms para textos de varias líneas: unifica los saltos y recorta.

    Los navegadores envían los saltos de un textarea como CRLF: contarían como dos
    caracteres y el límite no coincidiría con el contador que ve la persona (que
    cuenta uno por salto).
    """
    if not isinstance(value, str):
        return value

    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


def clean_optional_reason(reason: str | None, error: type[Exception]) -> str | None:
    """Recorta un motivo opcional: None si queda vacío y `error` si supera el máximo.

    `error` es la excepción de reglas del área que llama, para que cada servicio siga
    informando con la suya.
    """
    reason = (reason or "").strip()

    if len(reason) > MAX_REASON_LENGTH:
        raise error(f"El motivo no puede superar los {MAX_REASON_LENGTH} caracteres.")

    return reason or None


def clean_required_reason(reason: str | None, error: type[Exception], missing: str) -> str:
    """Como `clean_optional_reason`, pero sin motivo lanza `error` con `missing`."""
    cleaned = clean_optional_reason(reason, error)

    if cleaned is None:
        raise error(missing)

    return cleaned
