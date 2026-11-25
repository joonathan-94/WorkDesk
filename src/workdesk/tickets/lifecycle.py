"""Cambios de estado de un ticket (docs/08, sección 34; docs/09, 12.2).

Una transición solo es válida si existe como fila activa en
`transiciones_estados` para el estado actual del ticket. Quién puede
ejecutar cada acción lo decide la política de autorización de la acción
(`StateActionInfo.policy`, en `tickets/state_actions.py`): la tabla no guarda
permisos.

Todas las acciones de estado pasan por `change_state`:

- **operativas:** iniciar el trabajo, poner en espera y reactivar;
- **resolución:** resolver (queda pendiente de validación), confirmar o
  rechazar la solución (las dos las ejecuta un solicitante del ticket);
- **cierre:** cierre directo, y cierre excepcional de un ticket Resuelto;
- **reapertura:** devuelve un ticket Resuelto o Cerrado a En progreso.

La asignación de técnicos tiene sus propias transiciones derivadas
(`apply_derived_transition`). El cierre automático por inactividad
(`AUTO_CIERRE`, RN-58) lo ejecuta el planificador con `close_automatically`: es
el mismo cierre, pero lo hace el sistema (sin usuario) y comprueba su plazo dentro
de la transacción.

**Regla del cierre.** Un ticket en estado `CERRADO` siempre tiene fecha de
cierre y motivo de cierre. La base solo puede garantizar que van juntos (el
CHECK `ck_tickets_cierre_coherente`): que existan cuando el estado es
`CERRADO` depende del código del estado, que vive en otra tabla, así que lo
aplica este módulo. Todo cierre pasa por `_closing_changes` y toda salida de
`Resuelto` o `Cerrado` por `_CLEARED_FIELDS`: no hay otro camino que escriba
esos campos.

Nada de aquí hace commit: el cambio y sus eventos de historial (que escribe
`lifecycle_history.py`) se confirman o se revierten juntos, y el commit lo realiza
quien llama.
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func

from ..extensions import db
from ..models import (
    Estado,
    MotivoCierre,
    MotivoEspera,
    StateAction,
    Ticket,
    TransicionEstado,
    User,
)
from ..notifications.events import notify_state_change
from ..security.authorization import RESOLVED_STATE
from ..sla.periods import reconcile_sla
from .lifecycle_history import (
    record_action_events,
    record_automatic_close,
    record_derived_change,
    resolution_cycle,
)
from .service import CLOSED_STATE_CODE, TicketRuleError
from .state_actions import (
    AUTO_CLOSE_REASON,
    CLOSING_ACTIONS,
    DIRECT_CLOSE_DEFAULT_REASON,
    EXCEPTIONAL_CLOSE_REASON,
    MAX_WAIT_TEXT_LENGTH,
    REOPENING_ACTIONS,
    STATE_ACTIONS,
    VALIDATED_CLOSE_REASON,
    StateActionInfo,
)
from .versioning import (
    TicketClosedError,
    TicketConflictError,
    apply_ticket_changes,
    lock_ticket,
)


class StateTransitionError(TicketRuleError):
    """La acción no es válida desde el estado actual del ticket."""


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
    cycle = resolution_cycle(ticket)

    if action is StateAction.RESOLVER:
        # Cada entrada a Resuelto abre un nuevo ciclo de resolución.
        cycle += 1
        changes |= {"resolucion": text, "fecha_resolucion": func.now()}
    elif action in CLOSING_ACTIONS:
        changes |= _closing_changes(actor, close_reason)
    elif action in REOPENING_ACTIONS:
        changes |= _CLEARED_FIELDS

    apply_ticket_changes(ticket, actor, expected_version, changes)

    record_action_events(
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

    # El reloj del SLA sigue al estado: se pausa en espera, se detiene al
    # resolver o cerrar y se reanuda al volver al trabajo (RN-89 y RN-166).
    reconcile_sla(ticket, actor)

    # Los solicitantes y los técnicos asignados se enteran (RN-95 y RN-96).
    notify_state_change(ticket, actor, action)

    return new_state


def close_automatically(ticket: Ticket, *, resolved_before: datetime) -> bool:
    """Cierra un ticket `Resuelto` que nadie validó a tiempo (RN-58 y RN-59).

    Lo llama el planificador. Es el mismo cierre que hacen las personas
    (`AUTO_CIERRE` es una transición de la tabla y el estado, la fecha y el motivo
    los escribe `_closing_changes`), con tres diferencias: el actor es el sistema
    (sin usuario; el ticket queda con `cerrado_automaticamente`), el motivo es
    `INACTIVIDAD` y **el plazo se comprueba aquí, dentro de la transacción y con el
    ticket bloqueado**, no solo en la consulta que lo encontró: si mientras tanto
    el solicitante lo validó o lo rechazó, o el ticket se reabrió y se resolvió de
    nuevo, no se cierra.

    `resolved_before` es el límite: solo se cierra si se resolvió en ese instante o
    antes. Devuelve True si lo cerró y False si ya no correspondía. Sube la versión,
    registra `TICKET_CERRADO` y avisa a solicitantes y técnicos. No hace commit.
    """
    lock_ticket(ticket)
    # Los solicitantes y técnicos pudieron cambiar mientras esperaba el bloqueo.
    db.session.expire(ticket, ["solicitantes", "tecnicos"])

    old_state = db.session.get(Estado, ticket.estado_id)

    if (
        old_state.codigo != RESOLVED_STATE
        or ticket.fecha_resolucion is None
        or ticket.fecha_resolucion > resolved_before
    ):
        return False

    transition = db.session.scalar(
        db.select(TransicionEstado).where(
            TransicionEstado.estado_origen_id == old_state.id,
            TransicionEstado.accion == StateAction.AUTO_CIERRE.value,
            TransicionEstado.activa.is_(True),
        )
    )

    if transition is None:
        return False

    new_state = transition.estado_destino
    reason = _reason_by_code(AUTO_CLOSE_REASON)

    apply_ticket_changes(
        ticket,
        None,
        ticket.version,
        {"estado_id": new_state.id} | _closing_changes(None, reason),
    )
    record_automatic_close(ticket, old_state, new_state, reason)

    reconcile_sla(ticket, None)
    notify_state_change(ticket, None, StateAction.AUTO_CIERRE)

    return True


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
    record_derived_change(ticket, actor, action, old_state, new_state)

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


def _closing_changes(actor: User | None, reason: MotivoCierre) -> dict:
    """Los campos que fijan un cierre: fecha, motivo y quién cerró (`actor` es
    None en el cierre automático, que queda marcado como tal).

    Es el único lugar que escribe el cierre de un ticket (ver el docstring del
    módulo), de modo que un ticket `CERRADO` nunca queda sin fecha ni motivo.
    """
    return {
        "fecha_cierre": func.now(),
        "motivo_cierre_id": reason.id,
        "cerrado_por_usuario_id": None if actor is None else actor.id,
        "cerrado_automaticamente": actor is None,
    }
