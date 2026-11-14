"""Utilidades compartidas por las búsquedas de los listados."""


def escape_like(text: str) -> str:
    """Escapa `%`, `_` y `\\` para que se busquen literalmente en un `ILIKE`.

    Se usa junto con `escape="\\\\"` en la comparación.
    """
    return (
        text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )
