"""Cambios de estado de un ticket (docs/08, sección 34; docs/09, 12.2).

Una transición solo es válida si existe como fila activa en
`transiciones_estados` para el estado actual del ticket. Quién puede
ejecutar cada acción lo decide la política de autorización de la acción
(`StateActionInfo.policy`): la tabla no guarda permisos.

Todas las acciones de estado pasan por `change_state`:

- **operativas:** iniciar el trabajo, poner en espera y reactivar;
- **resolución:** resolver (queda pendiente de validación), confirmar o
  rechazar la solución (las dos las ejecuta un solicitante del ticket);
- **cierre:** cierre directo, y cierre excepcional de un ticket Resuelto;
- **reapertura:** devuelve un ticket Resuelto o Cerrado a En progreso.

La asignación de técnicos tiene sus propias transiciones derivadas
(`apply_derived_transition`). El cierre automático por inactividad
(`AUTO_CIERRE`) llega con el planificador de `v0.5.0`.

**Regla del cierre.** Un ticket en estado `CERRADO` siempre tiene fecha de
cierre y motivo de cierre. La base solo puede garantizar que van juntos (el
CHECK `ck_tickets_cierre_coherente`): que existan cuando el estado es
`CERRADO` depende del código del estado, que vive en otra tabla, así que lo
aplica este módulo. Todo cierre pasa por `_closing_changes` y toda salida de
`Resuelto` o `Cerrado` por `_CLEARED_FIELDS`: no hay otro camino que escriba
esos campos.

Nada de aquí hace commit: el cambio y sus eventos de historial se confirman o
se revierten juntos, y el commit lo realiza quien llama.
"""

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import func

from ..extensions import db
from ..models import (
    Estado,
    MotivoCierre,
    MotivoEspera,
    StateAction,
    Ticket,
    TicketEvent,
    TicketHistory,
    TransicionEstado,
    User,
    Validation,
    ValidationType,
)
from ..security import (
    can_change_state,
    can_close_directly,
    can_close_exceptionally,
    can_reopen_ticket,
    can_resolve_ticket,
    can_validate_resolution,
)
from .service import CLOSED_STATE_CODE, TicketRuleError, record_ticket_event
from .versioning import (
    TicketClosedError,
    TicketConflictError,
    apply_ticket_changes,
    lock_ticket,
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

# Motivos que el personal elige al cerrar directamente. `DUPLICADO` lo fija el
# flujo de duplicados; `INACTIVIDAD`, el cierre automático.
DIRECT_CLOSE_DEFAULT_REASON = "CIERRE_DIRECTO"
DIRECT_CLOSE_REASONS = (DIRECT_CLOSE_DEFAULT_REASON, "CANCELACION")

# Lo fija el flujo de duplicados (`tickets/relations.py`), que cierra el ticket
# duplicado con el mismo mecanismo del cierre directo.
DUPLICATE_CLOSE_REASON = "DUPLICADO"


class StateTransitionError(TicketRuleError):
    """La acción no es válida desde el estado actual del ticket."""


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
    # Explicación que se muestra en la pantalla de confirmación.
    description: str
    success_message: str
    # `(usuario, ticket) -> bool`: quién puede ejecutarla.
    policy: Callable
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


STATE_ACTIONS = {
    StateAction.INICIAR: StateActionInfo(
        action=StateAction.INICIAR,
        slug="start",
        label="Iniciar trabajo",
        icon="play-circle",
        description="El ticket pasará a En progreso.",
        success_message="El ticket #{number} pasó a «{state}».",
        policy=_by_role(can_change_state),
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
        allows_wait_reason=True,
    ),
    StateAction.REACTIVAR: StateActionInfo(
        action=StateAction.REACTIVAR,
        slug="resume",
        label="Reactivar",
        icon="arrow-repeat",
        description="El ticket volverá a En progreso.",
        success_message="El ticket #{number} pasó a «{state}».",
        policy=_by_role(can_change_state),
    ),
    StateAction.RESOLVER: StateActionInfo(
        action=StateAction.RESOLVER,
        slug="resolve",
        label="Resolver",
        icon="check-circle",
        description=(
            "El ticket pasará a Resuelto y quedará pendiente de que el "
            "solicitante confirme la solución. Si no responde, el cierre "
            "automático llega en una versión posterior."
        ),
        success_message="El ticket #{number} quedó «{state}», pendiente de validación.",
        policy=_by_role(can_resolve_ticket),
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
            "Cierra el ticket sin pasar por Resuelto: no se pide la "
            "validación del solicitante. Úsalo para mantenciones, tareas "
            "rutinarias o casos validados por otro medio."
        ),
        success_message="El ticket #{number} quedó «{state}».",
        policy=_by_role(can_close_directly),
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
        text_label="Comentario (opcional)",
        text_hint="Si quieres, cuéntanos cómo quedó.",
    ),
    StateAction.RECHAZAR: StateActionInfo(
        action=StateAction.RECHAZAR,
        slug="reject",
        label="No, necesito más ayuda",
        icon="hand-thumbs-down",
        description=(
            "El ticket volverá a En progreso y el equipo lo retomará. "
            "Cuéntanos qué falta para que podamos ayudarte."
        ),
        success_message=(
            "Enviamos tu respuesta. El ticket #{number} volvió a «{state}»."
        ),
        policy=can_validate_resolution,
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
            "Cierra un ticket Resuelto sin esperar la validación del "
            "solicitante, por ejemplo cuando no responde o no tiene "
            "solicitante. Queda identificado como excepcional en el "
            "historial."
        ),
        success_message="El ticket #{number} quedó «{state}» (cierre excepcional).",
        policy=_by_role(can_close_exceptionally),
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
            "El ticket volverá a En progreso, conservando a los técnicos que "
            "participaron. Después puedes agregar un comentario público para "
            "explicar qué falta."
        ),
        success_message="El ticket #{number} se reabrió y está «{state}».",
        policy=can_reopen_ticket,
        primary=False,
    ),
}

ACTION_BY_SLUG = {info.slug: info for info in STATE_ACTIONS.values()}

# Acciones que cierran el ticket. Toda entrada a `CERRADO` es una de ellas.
CLOSING_ACTIONS = (
    StateAction.CIERRE_DIRECTO,
    StateAction.CONFIRMAR,
    StateAction.CIERRE_EXCEPCIONAL,
)

# Acciones con las que el ticket sale de `Resuelto` o `Cerrado` hacia el
# trabajo: la resolución y el cierre vigentes dejan de serlo.
REOPENING_ACTIONS = (StateAction.RECHAZAR, StateAction.REABRIR)

# Lo que se limpia al reabrir. Los hechos anteriores no se pierden: el
# historial conserva la resolución, el cierre y quién los hizo.
_CLEARED_FIELDS = {
    "resolucion": None,
    "fecha_resolucion": None,
    "fecha_cierre": None,
    "motivo_cierre_id": None,
    "cerrado_por_usuario_id": None,
    "cerrado_automaticamente": False,
}


@dataclass(frozen=True)
class AvailableAction:
    """Una acción que el usuario puede ejecutar ahora sobre el ticket."""

    info: StateActionInfo
    destination: Estado


def available_actions(ticket: Ticket, user: User) -> list[AvailableAction]:
    """Acciones de estado que `user` puede ejecutar sobre el ticket ahora.

    Combina las tres condiciones: la acción está implementada, la transición
    está activa desde el estado actual y la política lo permite. Un ticket
    cerrado solo ofrece reabrirlo.
    """
    transitions = db.session.scalars(
        db.select(TransicionEstado).where(
            TransicionEstado.estado_origen_id == ticket.estado_id,
            TransicionEstado.activa.is_(True),
            TransicionEstado.accion.in_(
                [action.value for action in STATE_ACTIONS]
            ),
        )
    ).all()

    by_action = {StateAction(t.accion): t for t in transitions}

    return [
        AvailableAction(
            info=info,
            destination=by_action[action].estado_destino,
        )
        for action, info in STATE_ACTIONS.items()
        if action in by_action and info.policy(user, ticket)
    ]


def list_close_reasons(info: StateActionInfo) -> list[MotivoCierre]:
    """Motivos de cierre activos que se ofrecen en la pantalla de la acción
    (el cierre directo), en el orden del catálogo."""
    if not info.close_reasons:
        return []

    return list(
        db.session.scalars(
            db.select(MotivoCierre)
            .where(
                MotivoCierre.codigo.in_(info.close_reasons),
                MotivoCierre.activo.is_(True),
            )
            .order_by(MotivoCierre.orden.asc().nulls_last(), MotivoCierre.id)
        )
    )


def change_state(
    ticket: Ticket,
    *,
    actor: User,
    action: StateAction,
    expected_version: int,
    wait_reason_id: int | None = None,
    text: str | None = None,
    close_reason_id: int | None = None,
    close_reason_code: str | None = None,
    extra_context: dict | None = None,
) -> Estado:
    """Ejecuta la acción de estado y devuelve el estado nuevo del ticket.

    - Bloquea la fila del ticket (`SELECT ... FOR UPDATE`) y la vuelve a
      leer, de modo que la transición se valida contra el estado real: si
      dos personas actúan a la vez, la segunda espera y ve el resultado de
      la primera.
    - `expected_version` es la versión que tenía quien abrió la pantalla; si
      otra persona modificó el ticket, lanza `TicketConflictError`.
    - Un ticket cerrado solo admite `REABRIR` (el resto lanza
      `TicketClosedError`). Una acción que no existe como transición activa
      desde el estado actual, o que el actor no puede ejecutar sobre este
      ticket, lanza `StateTransitionError`.
    - `wait_reason_id` solo se admite al poner en espera, `close_reason_id`
      solo al cerrar directamente y `text` según la acción (ver
      `StateActionInfo.text_label`).
    - `close_reason_code` y `extra_context` no los usa ninguna pantalla: los
      usa el flujo de duplicados para cerrar con el motivo `DUPLICADO` (solo
      el cierre directo lo admite) y dejar en el evento de cierre el ticket
      principal.

    Sube la versión del ticket y registra los eventos de la acción con el
    estado anterior y el nuevo.
    """
    action = StateAction(action)
    info = STATE_ACTIONS.get(action)

    if info is None:
        raise StateTransitionError("Esta acción todavía no está disponible.")

    if not actor.is_active:
        raise TicketRuleError("El usuario no está activo.")

    lock_ticket(ticket)
    # Los solicitantes pudieron cambiar mientras esperaba el bloqueo.
    db.session.expire(ticket, ["solicitantes"])

    old_state = db.session.get(Estado, ticket.estado_id)

    if old_state.codigo == CLOSED_STATE_CODE and action is not StateAction.REABRIR:
        raise TicketClosedError(
            "Un ticket cerrado no se puede modificar. Primero debe reabrirse."
        )

    if ticket.version != expected_version:
        raise TicketConflictError(
            "Otra persona modificó este ticket mientras decidías. Revisa su "
            "estado actual e inténtalo de nuevo."
        )

    if not info.policy(actor, ticket):
        raise StateTransitionError(
            "No puedes realizar esta acción sobre este ticket."
        )

    transition = db.session.scalar(
        db.select(TransicionEstado).where(
            TransicionEstado.estado_origen_id == old_state.id,
            TransicionEstado.accion == action.value,
            TransicionEstado.activa.is_(True),
        )
    )

    if transition is None:
        raise StateTransitionError(
            "Esta acción no está disponible para el estado actual del ticket."
        )

    wait_reason, close_reason, text = _clean_inputs(
        info, wait_reason_id, close_reason_id, text, close_reason_code
    )
    new_state = transition.estado_destino

    changes: dict = {"estado_id": new_state.id}
    cycle = _resolution_cycle(ticket)

    if action is StateAction.RESOLVER:
        # Cada entrada a Resuelto abre un nuevo ciclo de resolución.
        cycle += 1
        changes |= {"resolucion": text, "fecha_resolucion": func.now()}
    elif action in CLOSING_ACTIONS:
        changes |= _closing_changes(actor, close_reason)
    elif action in REOPENING_ACTIONS:
        changes |= _CLEARED_FIELDS

    apply_ticket_changes(ticket, actor, expected_version, changes)

    _record_action_events(
        ticket,
        info,
        actor=actor,
        old_state=old_state,
        new_state=new_state,
        text=text,
        wait_reason=wait_reason,
        close_reason=close_reason,
        cycle=max(cycle, 1),
        extra_context=extra_context,
    )

    return new_state


def apply_derived_transition(
    ticket: Ticket,
    *,
    actor: User,
    action: StateAction,
    from_state_code: str,
) -> Estado | None:
    """Aplica la transición de estado que es consecuencia de otra operación.

    La usa la asignación: asignar al primer técnico de un ticket `Nuevo` lo
    pasa a `Asignado` (`ASIGNAR`) y quitar al último técnico de un ticket
    `Asignado` lo devuelve a `Nuevo` (`DESASIGNACION`). Solo actúa si el
    ticket está en `from_state_code` y la transición existe y está activa
    (si el Administrador la deshabilitó, el estado no cambia). Quien llama
    ya bloqueó el ticket. Sube la versión y registra `ESTADO_CAMBIADO`.
    Devuelve el estado nuevo o None si no hubo cambio.
    """
    old_state = db.session.get(Estado, ticket.estado_id)

    if old_state.codigo != from_state_code:
        return None

    transition = db.session.scalar(
        db.select(TransicionEstado).where(
            TransicionEstado.estado_origen_id == old_state.id,
            TransicionEstado.accion == action.value,
            TransicionEstado.activa.is_(True),
        )
    )

    if transition is None:
        return None

    new_state = transition.estado_destino

    apply_ticket_changes(
        ticket,
        actor,
        ticket.version,
        {"estado_id": new_state.id},
    )
    record_ticket_event(
        ticket,
        TicketEvent.ESTADO_CAMBIADO,
        actor=actor,
        detail=_state_detail(old_state, new_state),
        old_state=old_state,
        new_state=new_state,
        old_value=_state_snapshot(old_state),
        new_value=_state_snapshot(new_state),
        context={"accion": action.value, "derivado": True},
    )

    return new_state


def _clean_inputs(
    info: StateActionInfo,
    wait_reason_id: int | None,
    close_reason_id: int | None,
    text: str | None,
    close_reason_code: str | None = None,
) -> tuple[MotivoEspera | None, MotivoCierre | None, str | None]:
    """Valida lo que acompaña a la acción y devuelve el motivo de espera, el
    motivo de cierre y el texto ya limpios."""
    text = (text or "").strip() or None

    if info.allows_wait_reason:
        reason, text = _clean_wait_reason(wait_reason_id, text)

        if close_reason_id is not None:
            raise TicketRuleError("Esta acción no admite un motivo de cierre.")

        return reason, None, text

    if wait_reason_id is not None or (text and info.text_label is None):
        raise TicketRuleError("Esta acción no admite un motivo de espera.")

    close_reason = _resolve_close_reason(info, close_reason_id, close_reason_code)

    if info.text_label is None:
        return None, close_reason, None

    if info.text_required and not text:
        raise TicketRuleError(info.text_required_message)

    if text and len(text) > info.text_max:
        raise TicketRuleError(
            f"El texto no puede superar los {info.text_max} caracteres."
        )

    return None, close_reason, text


def _clean_wait_reason(
    wait_reason_id: int | None,
    text: str | None,
) -> tuple[MotivoEspera | None, str | None]:
    reason = None

    if wait_reason_id is not None:
        reason = db.session.get(MotivoEspera, wait_reason_id)

        if reason is None or not reason.activo:
            raise TicketRuleError(
                "El motivo de espera seleccionado no está disponible."
            )

    if text:
        if reason is None or not reason.permite_texto_otro:
            raise TicketRuleError(
                "Elige un motivo que admita texto libre para escribir una "
                "explicación."
            )

        if len(text) > MAX_WAIT_TEXT_LENGTH:
            raise TicketRuleError(
                f"La explicación no puede superar los {MAX_WAIT_TEXT_LENGTH} "
                "caracteres."
            )

    return reason, text


def _resolve_close_reason(
    info: StateActionInfo,
    close_reason_id: int | None,
    close_reason_code: str | None = None,
) -> MotivoCierre | None:
    """Motivo de cierre de la acción.

    En el cierre directo el personal elige entre los motivos que la acción
    ofrece (el de por defecto si no elige) y deben estar activos. En la
    confirmación y el cierre excepcional el motivo lo fija el flujo y no se
    puede elegir. Las demás acciones no cierran.

    `close_reason_code` es el motivo que fija otro flujo (duplicados): solo lo
    admite el cierre directo y es estructural, como los demás que fija el flujo.
    """
    if close_reason_code is not None:
        if info.action is not StateAction.CIERRE_DIRECTO or close_reason_id is not None:
            raise TicketRuleError("Esta acción no admite un motivo de cierre.")

        return _reason_by_code(close_reason_code)

    if info.close_reasons:
        if close_reason_id is None:
            return _reason_by_code(DIRECT_CLOSE_DEFAULT_REASON, active_only=True)

        reason = db.session.get(MotivoCierre, close_reason_id)

        if (
            reason is None
            or not reason.activo
            or reason.codigo not in info.close_reasons
        ):
            raise TicketRuleError(
                "El motivo de cierre seleccionado no está disponible."
            )

        return reason

    if close_reason_id is not None:
        raise TicketRuleError("Esta acción no admite un motivo de cierre.")

    fixed = {
        StateAction.CONFIRMAR: VALIDATED_CLOSE_REASON,
        StateAction.CIERRE_EXCEPCIONAL: EXCEPTIONAL_CLOSE_REASON,
    }.get(info.action)

    return None if fixed is None else _reason_by_code(fixed)


def _reason_by_code(code: str, *, active_only: bool = False) -> MotivoCierre:
    reason = db.session.scalar(
        db.select(MotivoCierre).where(MotivoCierre.codigo == code)
    )

    if reason is None or (active_only and not reason.activo):
        raise TicketRuleError(
            f"El motivo de cierre «{code}» no está disponible. Pide al "
            "Administrador que revise el catálogo de motivos de cierre."
        )

    return reason


def _closing_changes(actor: User, reason: MotivoCierre) -> dict:
    """Los campos que fijan un cierre: fecha, motivo y quién cerró.

    Es el único lugar que escribe el cierre de un ticket (ver el docstring del
    módulo), de modo que un ticket `CERRADO` nunca queda sin fecha ni motivo.
    """
    return {
        "fecha_cierre": func.now(),
        "motivo_cierre_id": reason.id,
        "cerrado_por_usuario_id": actor.id,
        "cerrado_automaticamente": False,
    }


def _resolution_cycle(ticket: Ticket) -> int:
    """Cuántas veces ha sido resuelto el ticket (los eventos
    `TICKET_RESUELTO`). El ciclo en curso de una validación es este número."""
    return (
        db.session.scalar(
            db.select(func.count())
            .select_from(TicketHistory)
            .where(
                TicketHistory.ticket_id == ticket.id,
                TicketHistory.tipo_evento == TicketEvent.TICKET_RESUELTO.value,
            )
        )
        or 0
    )


def _record_action_events(
    ticket: Ticket,
    info: StateActionInfo,
    *,
    actor: User,
    old_state: Estado,
    new_state: Estado,
    text: str | None,
    wait_reason: MotivoEspera | None,
    close_reason: MotivoCierre | None,
    cycle: int,
    extra_context: dict | None = None,
) -> None:
    """Registra el historial de la acción.

    Cada acción deja un evento propio que lleva el estado anterior y el nuevo.
    Confirmar y rechazar dejan además el de la validación (primero la
    respuesta del solicitante y después lo que provoca).
    """
    action = info.action
    old_value = _state_snapshot(old_state)
    new_value = _state_snapshot(new_state)
    context: dict = {"accion": action.value} | (extra_context or {})
    states = {
        "old_state": old_state,
        "new_state": new_state,
        "old_value": old_value,
    }

    if action is StateAction.RESOLVER:
        record_ticket_event(
            ticket,
            TicketEvent.TICKET_RESUELTO,
            actor=actor,
            detail=_state_detail(old_state, new_state),
            new_value=new_value | {"resolucion": text, "ciclo": cycle},
            context=context | {"ciclo": cycle},
            **states,
        )

        return

    if action in CLOSING_ACTIONS:
        if action is StateAction.CONFIRMAR:
            validation = _record_validation(
                ticket,
                actor,
                ValidationType.ACEPTADA,
                cycle,
                comment=text,
            )
            record_ticket_event(
                ticket,
                TicketEvent.VALIDACION_ACEPTADA,
                actor=actor,
                detail="El solicitante confirmó la solución.",
                context=context
                | {"validacion_id": validation.id, "ciclo": cycle},
            )

        elif text:
            # El motivo del cierre directo o excepcional es del personal.
            context["motivo"] = text

        record_ticket_event(
            ticket,
            TicketEvent.TICKET_CERRADO,
            actor=actor,
            detail=_state_detail(old_state, new_state),
            new_value=new_value
            | {
                "motivo_cierre": {
                    "codigo": close_reason.codigo,
                    "nombre": close_reason.nombre,
                }
            },
            context=context | {"motivo_cierre": close_reason.codigo},
            **states,
        )

        return

    if action is StateAction.RECHAZAR:
        validation = _record_validation(
            ticket,
            actor,
            ValidationType.RECHAZADA,
            cycle,
            reason=text,
        )
        record_ticket_event(
            ticket,
            TicketEvent.VALIDACION_RECHAZADA,
            actor=actor,
            detail="El solicitante rechazó la solución.",
            context=context
            | {
                "validacion_id": validation.id,
                "ciclo": cycle,
                # El motivo del rechazo es del propio solicitante: lo ve
                # quien ve el ticket (a diferencia de `motivo`).
                "motivo_rechazo": text,
            },
        )

    if action in REOPENING_ACTIONS:
        record_ticket_event(
            ticket,
            TicketEvent.TICKET_REABIERTO,
            actor=actor,
            detail=_state_detail(old_state, new_state),
            new_value=new_value,
            context=context | {"desde": old_state.codigo},
            **states,
        )

        return

    if text:
        context["motivo"] = text

    record_ticket_event(
        ticket,
        TicketEvent.ESTADO_CAMBIADO,
        actor=actor,
        detail=_state_detail(old_state, new_state),
        new_value=new_value,
        context=context,
        wait_reason=wait_reason,
        **states,
    )


def _record_validation(
    ticket: Ticket,
    actor: User,
    kind: ValidationType,
    cycle: int,
    *,
    comment: str | None = None,
    reason: str | None = None,
) -> Validation:
    """Guarda la respuesta del solicitante a la resolución en curso."""
    validation = Validation(
        ticket_id=ticket.id,
        solicitante_id=actor.id,
        ciclo_resolucion=cycle,
        tipo_validacion=kind.value,
        motivo_rechazo=reason,
        comentario_adicional=comment,
    )

    db.session.add(validation)
    db.session.flush()

    return validation


def _state_detail(old_state: Estado, new_state: Estado) -> str:
    return (
        f"Estado cambiado de «{old_state.nombre_visible}» "
        f"a «{new_state.nombre_visible}»."
    )


def _state_snapshot(state: Estado) -> dict:
    return {
        "estado_id": state.id,
        "codigo": state.codigo,
        "nombre": state.nombre_visible,
    }
