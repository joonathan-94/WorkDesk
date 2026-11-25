"""Anotar quién y cuándo modificó un registro por última vez."""

from datetime import UTC, datetime


class ModificationMixin:
    """Para los modelos con las columnas `fecha_modificacion` y
    `usuario_modificacion_id` (cada uno las declara con su propia clave foránea)."""

    def mark_modified(self, actor) -> None:
        self.fecha_modificacion = datetime.now(UTC)
        self.usuario_modificacion_id = actor.id
