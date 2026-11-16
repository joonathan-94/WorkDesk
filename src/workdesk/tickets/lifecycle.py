"""Cambios de estado de un ticket (docs/08, sección 34; docs/09, 12.2).

Una transición solo es válida si existe como fila activa en
`transiciones_estados` para el estado actual del ticket. Quién puede
ejecutar cada acción lo decide la política de autorización de la ruta
(`can_change_state`): la tabla no guarda permisos.

Hoy están implementadas las acciones operativas: **iniciar** el trabajo,
**poner en espera** y **reactivar**. Las demás acciones de la tabla
(asignar, resolver, cerrar, reabrir...) se añaden en `STATE_ACTIONS` cuando
llega su funcionalidad: hasta entonces `change_state` las rechaza.

Nada de aquí hace commit: el cambio y su evento de historial se confirman o
se revierten juntos, y el commit lo realiza quien llama.
"""

from collections.abc import Callable
from dataclasses import dataclass

from ..extensions import db
from ..models import (
    Estado,
    MotivoEspera,
    StateAction,
    Ticket,
    TicketEvent,
    TransicionEstado,
    User,
)
from ..security import can_change_state
from .service import CLOSED_STATE_CODE, TicketRuleError, record_ticket_event
from .versioning import (
    TicketClosedError,
    TicketConflictError,
    apply_ticket_changes,
)

# Texto libre que acompaña a un motivo de espera que lo admite.
MAX_WAIT_TEXT_LENGTH = 500


class StateTransitionError(TicketRuleError):
    """La acción no es válida desde el estado actual del ticket."""


@dataclass(frozen=True)
class StateActionInfo:
    """Cómo se presenta y se autoriza una acción de estado.

    Es información de presentación (textos, icono, ruta) más la política que
    decide qué roles la ejecutan. Las reglas de la transición están en la
    tabla y en `change_state`.
    """

    action: StateAction
    # Fragmento de la URL: /tickets/<n>/status/<slug>.
    slug: str
    label: str
    icon: str
    # Explicación que se muestra en la pantalla de confirmación.
    description: str
    success_message: str
    policy: Callable
    allows_wait_reason: bool = False


STATE_ACTIONS = {
    StateAction.INICIAR: StateActionInfo(
        action=StateAction.INICIAR,
        slug="start",
        label="Iniciar trabajo",
        icon="play-circle",
        description="El ticket pasará a En progreso.",
        success_message="El ticket #{number} pasó a «{state}».",
        policy=can_change_state,
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
        policy=can_change_state,
        allows_wait_reason=True,
    ),
    StateAction.REACTIVAR: StateActionInfo(
        action=StateAction.REACTIVAR,
        slug="resume",
        label="Reactivar",
        icon="arrow-repeat",
        description="El ticket volverá a En progreso.",
        success_message="El ticket #{number} pasó a «{state}».",
        policy=can_change_state,
    ),
}

ACTION_BY_SLUG = {info.slug: info for info in STATE_ACTIONS.values()}


@dataclass(frozen=True)
class AvailableAction:
    """Una acción que el usuario puede ejecutar ahora sobre el ticket."""

    info: StateActionInfo
    destination: Estado


def available_actions(ticket: Ticket, user: User) -> list[AvailableAction]:
    """Acciones de estado que `user` puede ejecutar sobre el ticket ahora.

    Combina las tres condiciones: la acción está implementada, la transición
    está activa desde el estado actual y la política de rol lo permite. Un
    ticket cerrado no ofrece ninguna (reabrir llega con el cierre).
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
        if action in by_action and info.policy(user)
    ]


def change_state(
    ticket: Ticket,
    *,
    actor: User,
    action: StateAction,
    expected_version: int,
    wait_reason_id: int | None = None,
    text: str | None = None,
) -> Estado:
    """Ejecuta la acción de estado y devuelve el estado nuevo del ticket.

    - Bloquea la fila del ticket (`SELECT ... FOR UPDATE`) y la vuelve a
      leer, de modo que la transición se valida contra el estado real: si
      dos personas actúan a la vez, la segunda espera y ve el resultado de
      la primera.
    - `expected_version` es la versión que tenía quien abrió la pantalla; si
      otra persona modificó el ticket, lanza `TicketConflictError`.
    - Un ticket cerrado lanza `TicketClosedError`; una acción que no existe
      como transición activa desde el estado actual, `StateTransitionError`.
    - `wait_reason_id` y `text` solo se admiten al poner en espera: el motivo
      debe estar activo y el texto libre exige un motivo que lo permita.

    Sube la versión del ticket y registra `ESTADO_CAMBIADO` con el estado
    anterior y el nuevo.
    """
    action = StateAction(action)
    info = STATE_ACTIONS.get(action)

    if info is None:
        raise StateTransitionError("Esta acción todavía no está disponible.")

    if not actor.is_active:
        raise TicketRuleError("El usuario no está activo.")

    _lock_and_reload(ticket)

    old_state = db.session.get(Estado, ticket.estado_id)

    if old_state.codigo == CLOSED_STATE_CODE:
        raise TicketClosedError(
            "Un ticket cerrado no se puede modificar. Primero debe reabrirse."
        )

    if ticket.version != expected_version:
        raise TicketConflictError(
            "Otra persona modificó este ticket mientras decidías. Revisa su "
            "estado actual e inténtalo de nuevo."
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

    wait_reason, text = _clean_wait_reason(info, wait_reason_id, text)
    new_state = transition.estado_destino

    apply_ticket_changes(
        ticket,
        actor,
        expected_version,
        {"estado_id": new_state.id},
    )

    context = {"accion": action.value}

    if text:
        context["motivo"] = text

    record_ticket_event(
        ticket,
        TicketEvent.ESTADO_CAMBIADO,
        actor=actor,
        detail=(
            f"Estado cambiado de «{old_state.nombre_visible}» "
            f"a «{new_state.nombre_visible}»."
        ),
        old_state=old_state,
        new_state=new_state,
        old_value=_state_snapshot(old_state),
        new_value=_state_snapshot(new_state),
        context=context,
        wait_reason=wait_reason,
    )

    return new_state


def _lock_and_reload(ticket: Ticket) -> None:
    db.session.execute(
        db.select(Ticket.id).where(Ticket.id == ticket.id).with_for_update()
    )
    db.session.refresh(ticket)


def _clean_wait_reason(
    info: StateActionInfo,
    wait_reason_id: int | None,
    text: str | None,
) -> tuple[MotivoEspera | None, str | None]:
    text = (text or "").strip() or None

    if not info.allows_wait_reason:
        if wait_reason_id is not None or text:
            raise TicketRuleError("Esta acción no admite un motivo de espera.")

        return None, None

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


def _state_snapshot(state: Estado) -> dict:
    return {
        "estado_id": state.id,
        "codigo": state.codigo,
        "nombre": state.nombre_visible,
    }
