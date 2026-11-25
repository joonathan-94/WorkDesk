"""Lo que un cambio de estado deja escrito: eventos del historial y validaciones.

Lo usa `lifecycle.py`, que es quien decide si el cambio es válido y quién escribe el
estado; aquí solo se anota lo ocurrido. Cada acción deja un evento propio con el estado
anterior y el nuevo (docs/09, 12.2). Ninguna función hace commit.
"""

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
    User,
    Validation,
    ValidationType,
)
from .service import record_ticket_event
from .state_actions import CLOSING_ACTIONS, REOPENING_ACTIONS, StateActionInfo


def resolution_cycle(ticket: Ticket) -> int:
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


def record_action_events(
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


def record_automatic_close(
    ticket: Ticket, old_state: Estado, new_state: Estado, reason: MotivoCierre
) -> None:
    """El cierre por inactividad: lo hace el sistema, así que no hay actor."""
    record_ticket_event(
        ticket,
        TicketEvent.TICKET_CERRADO,
        actor=None,
        detail=_state_detail(old_state, new_state),
        old_state=old_state,
        new_state=new_state,
        old_value=_state_snapshot(old_state),
        new_value=_state_snapshot(new_state)
        | {"motivo_cierre": {"codigo": reason.codigo, "nombre": reason.nombre}},
        context={
            "accion": StateAction.AUTO_CIERRE.value,
            "motivo_cierre": reason.codigo,
        },
    )


def record_derived_change(
    ticket: Ticket,
    actor: User,
    action: StateAction,
    old_state: Estado,
    new_state: Estado,
) -> None:
    """El cambio de estado que es consecuencia de otra operación (la asignación)."""
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
