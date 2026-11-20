"""Limpieza de los textos que escriben las personas.

Lo comparten los formularios (que limpian lo que llega del navegador) y los
servicios (que no confían en que alguien ya lo haya hecho). Son funciones
pequeñas a propósito: tenerlas en un solo lugar evita que cada módulo escriba
su propia copia y que, con el tiempo, dejen de comportarse igual.
"""


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
