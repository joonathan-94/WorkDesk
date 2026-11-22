"""Catálogo de las acciones de estado de un ticket (docs/08, sección 34).

Declara, para cada acción que provoca una transición, **cómo se presenta**
(textos, icono, ruta), **quién puede ejecutarla** y **qué pide** (motivo de
espera, motivo de cierre, un texto). El motor que las ejecuta y valida está en
`tickets/lifecycle.py`; las transiciones válidas entre estados, en la tabla
`transiciones_estados`. Se separó del motor para que la pantalla de
administración de estados y transiciones (`catalogs/flow.py`) pueda describir
el flujo sin depender de cómo se ejecuta.

Hay tres clases de acciones, y todas las del vocabulario (`StateAction`) están
en una de ellas (un test lo comprueba):

- **de una persona:** están en `STATE_ACTIONS`, con su política de autorización
  y los roles que pueden ejecutarlas;
- **automáticas:** las dispara otra operación (asignar o quitar técnicos) o el
  sistema (el cierre por inactividad); están en `AUTOMATIC_ACTIONS`;
- **esenciales:** son acciones de cualquiera de las dos clases cuya
  transición el Administrador no puede deshabilitar (`ESSENTIAL_REASONS`).

Para añadir una acción nueva: se agrega a `StateAction`, se declara aquí (en
`STATE_ACTIONS` si la ejecuta una persona o en `AUTOMATIC_ACTIONS` si no), se
maneja en `change_state` si necesita lógica propia y se carga su transición en
`seed-catalogs`.
"""

from collections.abc import Callable
from dataclasses import dataclass

from ..models import StateAction
from ..security import (
    STAFF_ROLES,
    RoleCode,
    can_change_state,
    can_close_directly,
    can_close_exceptionally,
    can_reopen_ticket,
    can_resolve_ticket,
    can_validate_resolution,
)

# Texto libre que acompaña a un motivo de espera que lo admite, a un cierre o
# a una validación.
MAX_WAIT_TEXT_LENGTH = 500
MAX_STATE_TEXT_LENGTH = 500

# La explicación de la solución que escribe quien resuelve. Como la descripción
# del ticket, admite hasta 2000 caracteres.
MAX_RESOLUTION_LENGTH = 2000

# Motivos de cierre que fija el propio flujo (el usuario no los elige). Son
# estructurales: aunque un Administrador los desactive en el catálogo, el
# flujo sigue funcionando.
VALIDATED_CLOSE_REASON = "RESOLUCION_VALIDADA"
EXCEPTIONAL_CLOSE_REASON = "CIERRE_EXCEPCIONAL"
AUTO_CLOSE_REASON = "INACTIVIDAD"

# Motivos que el personal elige al cerrar directamente. `DUPLICADO` lo fija el
# flujo de duplicados; `INACTIVIDAD`, el cierre automático.
DIRECT_CLOSE_DEFAULT_REASON = "CIERRE_DIRECTO"
DIRECT_CLOSE_REASONS = (DIRECT_CLOSE_DEFAULT_REASON, "CANCELACION")

# Lo fija el flujo de duplicados (`tickets/relations.py`), que cierra el ticket
# duplicado con el mismo mecanismo del cierre directo.
DUPLICATE_CLOSE_REASON = "DUPLICADO"


def _by_role(policy: Callable) -> Callable:
    """Adapta una política que solo mira el rol a la firma
    `(usuario, ticket)` que usan todas las acciones de estado."""
    return lambda user, ticket: policy(user)


@dataclass(frozen=True)
class StateActionInfo:
    """Cómo se presenta y se autoriza una acción de estado.

    Es información de presentación (textos, icono, ruta) más la política que
    decide quién la ejecuta. Las reglas de la transición están en la tabla y
    en `change_state`.
    """

    action: StateAction
    # Fragmento de la URL: /tickets/<n>/status/<slug>.
    slug: str
    label: str
    icon: str
    # Explicación de la pantalla de confirmación. No nombra estados escritos a
    # mano: el Administrador puede renombrarlos, así que el estado de destino
    # se indica con `{destination}` (ver `describe`).
    description: str
    success_message: str
    # `(usuario, ticket) -> bool`: quién puede ejecutarla sobre ese ticket.
    policy: Callable
    # Roles que pueden ejecutarla. Es lo que muestra la pantalla de estados y
    # transiciones; un test comprueba que coincide con `policy`.
    roles: tuple[RoleCode, ...]
    # Matiz que no cabe en la lista de roles (por ejemplo, «solo si es
    # solicitante del ticket»).
    roles_note: str = ""
    allows_wait_reason: bool = False
    # Códigos de motivo de cierre que se ofrecen al elegir (solo el cierre
    # directo). Vacío: la acción no pide motivo de cierre.
    close_reasons: tuple[str, ...] = ()
    # Campo de texto de la pantalla. `None`: la acción no lo pide.
    text_label: str | None = None
    text_hint: str = ""
    text_required: bool = False
    text_max: int = MAX_STATE_TEXT_LENGTH
    text_required_message: str = "Escribe una explicación."
    # Estilo del botón en la cabecera del detalle (principal o secundario).
    primary: bool = True

    def describe(self, destination_name: str) -> str:
        """La explicación de la acción con el nombre visible actual del estado
        de destino."""
        return self.description.format(destination=destination_name)


STATE_ACTIONS = {
    StateAction.INICIAR: StateActionInfo(
        action=StateAction.INICIAR,
        slug="start",
        label="Iniciar trabajo",
        icon="play-circle",
        description="El ticket pasará a «{destination}».",
        success_message="El ticket #{number} pasó a «{state}».",
        policy=_by_role(can_change_state),
        roles=STAFF_ROLES,
    ),
    StateAction.PONER_EN_ESPERA: StateActionInfo(
        action=StateAction.PONER_EN_ESPERA,
        slug="hold",
        label="Poner en espera",
        icon="pause-circle",
        description=(
            "Usa la espera cuando no se puede avanzar por una causa concreta "
            "(un dato pendiente, un tercero, una aprobación). El motivo es "
            "opcional."
        ),
        success_message="El ticket #{number} pasó a «{state}».",
        policy=_by_role(can_change_state),
        roles=STAFF_ROLES,
        allows_wait_reason=True,
    ),
    StateAction.REACTIVAR: StateActionInfo(
        action=StateAction.REACTIVAR,
        slug="resume",
        label="Reactivar",
        icon="arrow-repeat",
        description="El ticket volverá a «{destination}».",
        success_message="El ticket #{number} pasó a «{state}».",
        policy=_by_role(can_change_state),
        roles=STAFF_ROLES,
    ),
    StateAction.RESOLVER: StateActionInfo(
        action=StateAction.RESOLVER,
        slug="resolve",
        label="Resolver",
        icon="check-circle",
        description=(
            "El ticket pasará a «{destination}» y quedará pendiente de que el "
            "solicitante confirme la solución. Si no responde, un Supervisor "
            "puede cerrarlo de forma excepcional."
        ),
        success_message="El ticket #{number} quedó «{state}», pendiente de validación.",
        policy=_by_role(can_resolve_ticket),
        roles=STAFF_ROLES,
        text_label="Explicación de la solución",
        text_hint=(
            "Opcional. La ve el solicitante, que la revisa antes de "
            "confirmar."
        ),
        text_max=MAX_RESOLUTION_LENGTH,
    ),
    StateAction.CIERRE_DIRECTO: StateActionInfo(
        action=StateAction.CIERRE_DIRECTO,
        slug="close",
        label="Cerrar ticket",
        icon="x-circle",
        description=(
            "Cierra el ticket sin pasar por la validación del solicitante. "
            "Úsalo para mantenciones, tareas rutinarias o casos validados por "
            "otro medio."
        ),
        success_message="El ticket #{number} quedó «{state}».",
        policy=_by_role(can_close_directly),
        roles=STAFF_ROLES,
        close_reasons=DIRECT_CLOSE_REASONS,
        text_label="Explicación del cierre",
        text_hint="Opcional. Queda en el historial y solo la ve el personal.",
        primary=False,
    ),
    StateAction.CONFIRMAR: StateActionInfo(
        action=StateAction.CONFIRMAR,
        slug="confirm",
        label="Sí, está resuelto",
        icon="hand-thumbs-up",
        description=(
            "Al confirmar, el ticket se cierra. La confirmación de uno de "
            "los solicitantes basta para cerrarlo."
        ),
        success_message="Gracias. El ticket #{number} quedó «{state}».",
        policy=can_validate_resolution,
        roles=(RoleCode.SOLICITANTE,),
        roles_note="solo un solicitante del ticket",
        text_label="Comentario (opcional)",
        text_hint="Si quieres, cuéntanos cómo quedó.",
    ),
    StateAction.RECHAZAR: StateActionInfo(
        action=StateAction.RECHAZAR,
        slug="reject",
        label="No, necesito más ayuda",
        icon="hand-thumbs-down",
        description=(
            "El ticket volverá a «{destination}» y el equipo lo retomará. "
            "Cuéntanos qué falta para que podamos ayudarte."
        ),
        success_message=(
            "Enviamos tu respuesta. El ticket #{number} volvió a «{state}»."
        ),
        policy=can_validate_resolution,
        roles=(RoleCode.SOLICITANTE,),
        roles_note="solo un solicitante del ticket",
        text_label="¿Qué falta por resolver?",
        text_hint="Lo ve el equipo de soporte.",
        text_required=True,
        text_required_message="Cuéntanos por qué no quedó resuelto.",
    ),
    StateAction.CIERRE_EXCEPCIONAL: StateActionInfo(
        action=StateAction.CIERRE_EXCEPCIONAL,
        slug="close-exceptional",
        label="Cierre excepcional",
        icon="shield-check",
        description=(
            "Cierra un ticket pendiente de validación sin esperar al "
            "solicitante, por ejemplo cuando no responde o no tiene "
            "solicitante. Queda identificado como excepcional en el "
            "historial."
        ),
        success_message="El ticket #{number} quedó «{state}» (cierre excepcional).",
        policy=_by_role(can_close_exceptionally),
        roles=(RoleCode.SUPERVISOR, RoleCode.ADMINISTRADOR),
        text_label="Motivo del cierre excepcional",
        text_hint="Obligatorio. Queda en el historial y solo lo ve el personal.",
        text_required=True,
        text_required_message="Explica por qué se cierra de forma excepcional.",
        primary=False,
    ),
    StateAction.REABRIR: StateActionInfo(
        action=StateAction.REABRIR,
        slug="reopen",
        label="Reabrir ticket",
        icon="arrow-counterclockwise",
        description=(
            "El ticket volverá a «{destination}», conservando a los técnicos "
            "que participaron. Después puedes agregar un comentario público "
            "para explicar qué falta."
        ),
        success_message="El ticket #{number} se reabrió y está «{state}».",
        policy=can_reopen_ticket,
        roles=(*STAFF_ROLES, RoleCode.SOLICITANTE),
        roles_note=(
            "el solicitante, solo un ticket cerrado y dentro del plazo de "
            "reapertura"
        ),
        primary=False,
    ),
}

ACTION_BY_SLUG = {info.slug: info for info in STATE_ACTIONS.values()}

# Acciones que no ejecuta una persona desde una pantalla de estado: las
# dispara otra operación o el sistema. El texto dice cuándo ocurren.
AUTOMATIC_ACTIONS = {
    StateAction.ASIGNAR: "Automática: al asignar al primer técnico del ticket.",
    StateAction.DESASIGNACION: (
        "Automática: al quitar al último técnico del ticket."
    ),
    StateAction.AUTO_CIERRE: (
        "El sistema, cuando nadie valida la solución en el plazo "
        "configurado (lo ejecuta el planificador)."
    ),
}

# Acciones esenciales: su transición no se puede deshabilitar desde la
# configuración, porque el flujo dejaría de ser coherente (RF-118: la
# configuración no puede «impedir las operaciones esenciales de WorkDesk»).
# Cada una lleva la razón que se muestra al Administrador. Las razones no
# nombran estados escritos a mano, porque el Administrador puede renombrarlos.
ESSENTIAL_REASONS = {
    StateAction.ASIGNAR: (
        "Mantiene la coherencia entre tener técnicos asignados y el estado "
        "del ticket (RN-37)."
    ),
    StateAction.DESASIGNACION: (
        "Sin ella, un ticket sin técnicos seguiría marcado como asignado "
        "(RN-37)."
    ),
    StateAction.CONFIRMAR: (
        "Es la validación del solicitante: sin ella no podría cerrar su "
        "ticket (RN-53 y RN-54)."
    ),
    StateAction.RECHAZAR: (
        "Es el derecho del solicitante a rechazar una solución que no le "
        "sirvió (RN-55)."
    ),
    StateAction.CIERRE_EXCEPCIONAL: (
        "Es la salida del Supervisor para cerrar un ticket pendiente de "
        "validación cuando el solicitante no responde o no existe (RF-054)."
    ),
    StateAction.AUTO_CIERRE: (
        "La usa el cierre automático por inactividad (RN-58); su plazo es "
        "AUTO_CLOSE_HOURS."
    ),
    StateAction.REABRIR: (
        "Sin ella, un ticket cerrado, o resuelto por error, no podría volver "
        "a trabajarse (RN-66 y RN-69)."
    ),
}

ESSENTIAL_ACTIONS = frozenset(ESSENTIAL_REASONS)

# Acciones que cierran el ticket. Toda entrada a `CERRADO` es una de ellas.
CLOSING_ACTIONS = (
    StateAction.CIERRE_DIRECTO,
    StateAction.CONFIRMAR,
    StateAction.CIERRE_EXCEPCIONAL,
)

# Acciones con las que el ticket sale de `Resuelto` o `Cerrado` hacia el
# trabajo: la resolución y el cierre vigentes dejan de serlo.
REOPENING_ACTIONS = (StateAction.RECHAZAR, StateAction.REABRIR)

# Acciones que devuelven un ticket a un estado anterior del flujo. No cuentan
# para saber si un estado es alcanzable *avanzando* (`catalogs/flow.py`): si
# se deshabilitaran las dos formas de iniciar el trabajo, un ticket solo
# llegaría a «En progreso» resolviéndolo y reabriéndolo, y eso no es un flujo.
RETURN_ACTIONS = frozenset(
    {StateAction.RECHAZAR, StateAction.REABRIR, StateAction.DESASIGNACION}
)
