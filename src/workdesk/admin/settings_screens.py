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
                settings.LOGIN_MAX_FAILED_PER_IP,
                "Intentos fallidos desde un mismo equipo",
                "Al alcanzarlos dentro del tiempo de bloqueo, en cualquier cuenta, ese equipo "
                "no puede intentarlo de nuevo hasta que pase ese tiempo. Frena a quien prueba "
                "pocas contraseñas en muchas cuentas. 0 lo desactiva: hazlo si todas las "
                "personas llegan a WorkDesk a través de un mismo proxy.",
                unit="intentos",
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
        slug="creacion",
        title="Creación de tickets",
        description="Qué se exige al crear un ticket y la advertencia de tickets parecidos.",
        fields=(
            SettingField(
                settings.LOCATION_REQUIRED,
                "Exigir la ubicación al crear un ticket",
                "Solo se exige mientras haya alguna ubicación activa. Los tickets que ya "
                "existen sin ubicación se pueden seguir editando sin ella.",
            ),
            SettingField(
                settings.DUPLICATE_WINDOW_DAYS,
                "Días hacia atrás que se revisan",
                "Posibles duplicados: se comparan los tickets abiertos creados en ese "
                "plazo; 0 desactiva la advertencia, que nunca impide crear.",
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
                settings.INACTIVE_TICKET_DAYS,
                "Días sin actividad para marcar un ticket",
                "Un ticket en trabajo en el que nadie del equipo hizo nada en estos días se cuenta "
                "como «sin actividad reciente» en la carga de trabajo. Los comentarios del "
                "solicitante no cuentan como actividad. Solo informa; 0 lo desactiva.",
                unit="días",
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

    SettingsGroup(
        slug="retencion",
        title="Retención",
        description=(
            "Cuánto se conserva de lo que no forma parte de la historia de un ticket. Cada "
            "política está apagada hasta que la enciendas, y el planificador la aplica en cada "
            "pasada."
        ),
        fields=(
            SettingField(
                settings.RETENTION_NOTIFICATIONS_ENABLED,
                "Eliminar las notificaciones leídas antiguas",
                "Una notificación sin leer no se elimina nunca.",
            ),
            SettingField(
                settings.RETENTION_NOTIFICATIONS_DAYS,
                "Conservar las notificaciones leídas",
                "Contados desde que se creó la notificación.",
                unit="días",
            ),
            SettingField(
                settings.RETENTION_AUTH_EVENTS_ENABLED,
                "Eliminar el registro de accesos antiguo",
                "Los inicios de sesión, los intentos fallidos y los cierres de sesión.",
            ),
            SettingField(
                settings.RETENTION_AUTH_EVENTS_DAYS,
                "Conservar el registro de accesos",
                "Al menos 30 días: es la evidencia de un intento de intrusión reciente.",
                unit="días",
            ),
            SettingField(
                settings.RETENTION_DELETED_FILES_ENABLED,
                "Borrar del disco los archivos de adjuntos eliminados",
                "Solo el archivo: el ticket conserva el registro de que existió y quién lo "
                "eliminó.",
            ),
            SettingField(
                settings.RETENTION_DELETED_FILES_DAYS,
                "Conservar el archivo de un adjunto eliminado",
                "Contados desde que se eliminó. Mientras tanto sigue en los respaldos.",
                unit="días",
            ),
            SettingField(
                settings.RETENTION_BACKUPS_ENABLED,
                "Eliminar los respaldos más antiguos",
                "Los de la carpeta de respaldos del servidor; las copias que guardes en otro "
                "lugar no se tocan.",
            ),
            SettingField(
                settings.RETENTION_BACKUPS_KEEP,
                "Respaldos que se conservan",
                "Los más recientes. Siempre queda al menos uno.",
                unit="respaldos",
            ),
        ),
    ),
)

GROUPS_BY_SLUG = {group.slug: group for group in GROUPS}
