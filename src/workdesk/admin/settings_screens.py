"""Las pantallas de configuración del área de administración (docs/11, UI-023 y UI-025).

Cada pantalla es un grupo de parámetros de `settings.py` con los textos que ve el
Administrador. Aquí solo hay presentación: los nombres, los valores por defecto y los rangos
siguen definidos en `settings.py`, y las reglas de guardado en `configuration.py`. El
interruptor del SLA no está aquí sino en la pantalla «SLA» (UI-022).
"""

from dataclasses import dataclass

from .. import settings
from ..settings import BoolSetting, Setting


@dataclass(frozen=True)
class SettingField:
    """Un parámetro tal como se muestra en una pantalla."""

    setting: Setting
    label: str
    help: str
    # Unidad que se escribe junto al rango.
    unit: str = ""
    # Cuántas unidades guardadas equivalen a una de las que se escriben (los bytes se
    # escriben en KB).
    scale: int = 1

    @property
    def is_switch(self) -> bool:
        return isinstance(self.setting, BoolSetting)

    def to_display(self, value):
        return value if self.is_switch else value // self.scale

    def from_display(self, value):
        return value if self.is_switch else value * self.scale

    def limits(self) -> tuple[int, int]:
        """El rango válido en las unidades que se escriben en pantalla."""
        lowest = -(-self.setting.minimum // self.scale)

        return lowest, self.setting.maximum // self.scale


@dataclass(frozen=True)
class SettingsGroup:
    slug: str
    title: str
    description: str
    fields: tuple[SettingField, ...]

    @property
    def settings(self) -> tuple[Setting, ...]:
        return tuple(field.setting for field in self.fields)


GROUPS = (
    SettingsGroup(
        slug="seguridad",
        title="Seguridad y sesión",
        description="Bloqueo por intentos fallidos, contraseñas y duración de la sesión.",
        fields=(
            SettingField(
                settings.LOGIN_MAX_FAILED_ATTEMPTS,
                "Intentos fallidos antes de bloquear la cuenta",
                "Al alcanzarlos, la cuenta no puede iniciar sesión durante el tiempo de bloqueo.",
                unit="intentos",
            ),
            SettingField(
                settings.LOGIN_LOCK_MINUTES,
                "Tiempo de bloqueo",
                "Cuánto dura el bloqueo temporal de una cuenta.",
                unit="minutos",
            ),
            SettingField(
                settings.PASSWORD_MIN_LENGTH,
                "Longitud mínima de contraseña",
                "Se aplica a las contraseñas nuevas; las actuales no cambian.",
                unit="caracteres",
            ),
            SettingField(
                settings.SESSION_IDLE_MINUTES,
                "Inactividad máxima de la sesión",
                "Pasado este tiempo sin actividad hay que volver a iniciar sesión.",
                unit="minutos",
            ),
            SettingField(
                settings.SESSION_MAX_HOURS,
                "Duración máxima de la sesión",
                "Aunque haya actividad, la sesión termina al cumplirse este tiempo.",
                unit="horas",
            ),
        ),
    ),
    SettingsGroup(
        slug="cierre",
        title="Cierre y reapertura",
        description="Plazos de validación de una solución y de reapertura de un ticket.",
        fields=(
            SettingField(
                settings.AUTO_CLOSE_ENABLED,
                "Cerrar automáticamente los tickets resueltos sin validar",
                "Lo ejecuta el planificador. Apagado, un ticket resuelto espera a que "
                "alguien lo confirme, lo rechace o lo cierre.",
            ),
            SettingField(
                settings.AUTO_CLOSE_HOURS,
                "Plazo para validar una solución",
                "Horas corridas desde la resolución antes del cierre automático.",
                unit="horas",
            ),
            SettingField(
                settings.REOPEN_WINDOW_DAYS,
                "Plazo para que un solicitante reabra un ticket",
                "Días desde el cierre. El personal puede reabrir siempre.",
                unit="días",
            ),
        ),
    ),
    SettingsGroup(
        slug="archivos",
        title="Archivos",
        description="Tamaño y cantidad de los adjuntos.",
        fields=(
            SettingField(
                settings.UPLOAD_MAX_BYTES,
                "Tamaño máximo por archivo",
                "1024 KB son 1 MB.",
                unit="KB",
                scale=1024,
            ),
            SettingField(
                settings.UPLOAD_MAX_FILES_PER_TICKET,
                "Archivos activos por ticket",
                "Cuántos adjuntos puede tener un ticket como máximo.",
                unit="archivos",
            ),
        ),
    ),
    SettingsGroup(
        slug="colaboracion",
        title="Comentarios y edición",
        description="Corrección de comentarios y reserva de un ticket mientras se edita.",
        fields=(
            SettingField(
                settings.COMMENT_EDIT_WINDOW_MINUTES,
                "Tiempo para editar o eliminar un comentario propio",
                "El Supervisor y el Administrador no tienen este límite.",
                unit="minutos",
            ),
            SettingField(
                settings.EDIT_LOCK_TTL_SECONDS,
                "Duración del bloqueo de edición",
                "Cuánto se mantiene la reserva de un ticket si la pantalla deja de renovarla.",
                unit="segundos",
            ),
            SettingField(
                settings.EDIT_LOCK_HEARTBEAT_SECONDS,
                "Renovación del bloqueo",
                "Cada cuánto renueva la reserva la pantalla de edición. Debe ser menor que "
                "la duración.",
                unit="segundos",
            ),
        ),
    ),
    SettingsGroup(
        slug="duplicados",
        title="Posibles duplicados",
        description="La advertencia de tickets parecidos al crear uno. Nunca impide crearlo.",
        fields=(
            SettingField(
                settings.DUPLICATE_WINDOW_DAYS,
                "Días hacia atrás que se revisan",
                "Se comparan los tickets abiertos creados en ese plazo; 0 desactiva la "
                "advertencia.",
                unit="días",
            ),
            SettingField(
                settings.DUPLICATE_MIN_WORDS,
                "Palabras del título que deben coincidir",
                "Con menos palabras avisa más a menudo; con más, solo ante títulos muy "
                "parecidos.",
                unit="palabras",
            ),
        ),
    ),
    SettingsGroup(
        slug="operacion",
        title="Carga y planificador",
        description="Marca de carga alta y frecuencia de las tareas automáticas.",
        fields=(
            SettingField(
                settings.WORKLOAD_HIGH_ACTIVE_TICKETS,
                "Tickets activos para marcar «carga alta»",
                "Solo informa en la carga de trabajo; 0 desactiva la marca.",
                unit="tickets",
            ),
            SettingField(
                settings.SCHEDULER_INTERVAL_SECONDS,
                "Frecuencia del planificador",
                "Cada cuánto revisa avisos de SLA y cierres automáticos cuando está en marcha "
                "como proceso continuo.",
                unit="segundos",
            ),
        ),
    ),
)

GROUPS_BY_SLUG = {group.slug: group for group in GROUPS}
