"""Reasignación masiva: pasar tickets de un técnico a otros en una sola operación
(docs/04, RF-034 y RF-035; docs/06, RN-30, RN-104 y RN-137 a RN-139; docs/07, CU-014).

Sirve cuando un técnico deja de estar disponible (vacaciones, licencia, renuncia...): su
trabajo debe poder redistribuirse sin tocar ticket por ticket. Es solo del Supervisor y del
Administrador (`can_manage_assignments`), y el servicio lo comprueba aunque la pantalla
también lo haga.

**Cada movimiento es `(ticket, técnico destino)`.** La pantalla propone un reparto
(`distribute`: por turnos, en el orden de los tickets) y el servicio ejecuta exactamente lo
que se le pide, validando cada uno de nuevo: lo que la persona vio al confirmar puede haber
cambiado.

**Cada ticket se procesa por separado** (su propio savepoint): uno cerrado, ya reasignado por
otra persona o con otro problema se *omite con su motivo* y no impide mover los demás. Antes
de cualquier cambio se bloquea cada ticket **en orden de id** (siempre el ticket primero,
como en todo WorkDesk): dos reasignaciones simultáneas con tickets en común no se bloquean
mutuamente.

**Qué queda registrado** (RF-035, RN-139): el historial de cada ticket recibe
`TECNICO_DESASIGNADO` y `TECNICO_ASIGNADO` (los mismos eventos de la asignación individual,
con el lote y el motivo en el contexto); la asignación anterior se cierra y se conserva, no se
sobrescribe; y una sola entrada de auditoría (`REASIGNACION_MASIVA`) resume la operación. No
se toca nada más del ticket: comentarios, archivos, solicitantes, SLA y versión siguen igual
(asignar es aditivo y el reloj del SLA no depende de quién atiende, RN-85).

Nada hace commit: lo confirma quien llama.
"""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import uuid4

from ..audit import AuditAction, record_admin_event
from ..extensions import db
from ..models import Role, StateAction, Ticket, TicketEvent, User
from ..notifications.events import (
    notify_bulk_reassignment,
    notify_reassignment_requesters,
)
from ..security import RoleCode, can_manage_assignments
from .assignment import add_assignment, close_assignment
from .lifecycle import apply_derived_transition
from .service import (
    TicketRuleError,
    full_name,
    person_snapshot,
    record_ticket_event,
)
from .versioning import TicketClosedError, begin_ticket_operation

MAX_REASON_LENGTH = 500


@dataclass(frozen=True)
class MovedTicket:
    number: str
    title: str
    destination: User


@dataclass(frozen=True)
class SkippedTicket:
    number: str
    reason: str


@dataclass
class ReassignmentResult:
    batch: str
    source: User
    moved: list[MovedTicket] = field(default_factory=list)
    skipped: list[SkippedTicket] = field(default_factory=list)


def distribute(ticket_ids: Sequence[int], destination_ids: Sequence[int]) -> list[tuple[int, int]]:
    """El reparto por defecto: los tickets, en orden de id, se reparten por turnos entre los
    destinos (en el orden dado). Es determinista: la pantalla lo muestra antes de confirmar
    y el servicio ejecuta lo mismo."""
    if not destination_ids:
        raise TicketRuleError("Elige al menos un técnico de destino.")

    return [
        (ticket_id, destination_ids[index % len(destination_ids)])
        for index, ticket_id in enumerate(sorted(ticket_ids))
    ]


def reassign_tickets(
    actor: User,
    *,
    source_id: int,
    moves: Sequence[tuple[int, int]],
    reason: str,
) -> ReassignmentResult:
    """Mueve los tickets de `moves` (`(id del ticket, id del técnico destino)`) del técnico
    `source_id` a sus destinos. Devuelve lo movido y lo omitido, con su motivo.

    Errores que detienen toda la operación (`TicketRuleError`, sin dejar nada hecho): actor
    sin permiso o inactivo, motivo vacío o demasiado largo, sin movimientos, técnico de
    origen inexistente, destinos que no son Técnicos activos o que son el propio origen, o un
    ticket repetido. Todo lo demás se resuelve ticket por ticket.
    """
    reason, source, destinations = _validate_request(actor, source_id, moves, reason)

    result = ReassignmentResult(batch=uuid4().hex, source=source)
    moved_tickets: dict[User, list[Ticket]] = defaultdict(list)

    # Siempre en orden de id: dos operaciones que comparten tickets los bloquean en el mismo
    # orden y no se esperan mutuamente.
    for ticket_id, destination_id in sorted(moves):
        ticket = db.session.get(Ticket, ticket_id)

        if ticket is None:
            result.skipped.append(SkippedTicket(str(ticket_id), "El ticket no existe."))
            continue

        destination = destinations[destination_id]

        try:
            with db.session.begin_nested():
                _move(ticket, source, destination, actor, reason, result.batch)
        except TicketClosedError:
            result.skipped.append(SkippedTicket(ticket.public_id, "El ticket está cerrado."))
        except TicketRuleError as error:
            result.skipped.append(SkippedTicket(ticket.public_id, str(error)))
        else:
            result.moved.append(MovedTicket(ticket.public_id, ticket.titulo, destination))
            moved_tickets[destination].append(ticket)

    if result.moved:
        _audit(actor, source, result, reason)
        notify_bulk_reassignment(actor, source, moved_tickets)

    return result


def _validate_request(actor, source_id, moves, reason):
    """Todo lo que puede detener la operación completa, antes de tocar ningún ticket.
    Devuelve el motivo limpio, el técnico de origen y los destinos por id."""
    if not can_manage_assignments(actor):
        raise PermissionError("Solo el Supervisor y el Administrador pueden reasignar.")

    if not actor.is_active:
        raise TicketRuleError("El usuario no está activo.")

    reason = _clean_reason(reason)
    source = _get_source(source_id)

    if not moves:
        raise TicketRuleError("Elige al menos un ticket para reasignar.")

    ticket_ids = [ticket_id for ticket_id, _ in moves]

    if len(set(ticket_ids)) != len(ticket_ids):
        raise TicketRuleError("Un ticket no puede aparecer dos veces en la reasignación.")

    destinations = {
        destination_id: _get_destination(destination_id, source)
        for destination_id in {destination for _, destination in moves}
    }

    return reason, source, destinations


# --- Un ticket ----------------------------------------------------------------------


def _move(
    ticket: Ticket,
    source: User,
    destination: User,
    actor: User,
    reason: str,
    batch: str,
) -> None:
    begin_ticket_operation(ticket, actor, expire=("tecnicos",))

    current = ticket.tecnicos_vigentes
    old = next((a for a in current if a.tecnico_id == source.id), None)

    if old is None:
        raise TicketRuleError(
            f"El ticket ya no está asignado a {full_name(source)}."
        )

    context = {"lote": batch, "motivo": reason, "reasignacion_masiva": True}

    # Si el destino ya atendía el ticket, solo se quita al técnico de origen.
    already_there = any(a.tecnico_id == destination.id for a in current)
    new = None if already_there else add_assignment(ticket, destination, actor)

    close_assignment(old, actor, f"Reasignación masiva: {reason}")
    db.session.flush()
    db.session.expire(ticket, ["tecnicos"])

    record_ticket_event(
        ticket,
        TicketEvent.TECNICO_DESASIGNADO,
        actor=actor,
        detail=f"Técnico desasignado: {full_name(source)}.",
        old_value=person_snapshot(source),
        context={**context, "asignacion_id": old.id},
    )

    if new is not None:
        record_ticket_event(
            ticket,
            TicketEvent.TECNICO_ASIGNADO,
            actor=actor,
            detail=f"Técnico asignado: {full_name(destination)}.",
            new_value=person_snapshot(destination),
            context={**context, "asignacion_id": new.id},
        )

    apply_derived_transition(
        ticket,
        actor=actor,
        action=StateAction.ASIGNAR,
        from_state_code="NUEVO",
    )

    notify_reassignment_requesters(ticket, actor, destination)


# --- Piezas ---------------------------------------------------------------------------


def _clean_reason(reason: str | None) -> str:
    reason = " ".join((reason or "").split())

    if not reason:
        raise TicketRuleError("Indica el motivo de la reasignación (por ejemplo, vacaciones).")

    if len(reason) > MAX_REASON_LENGTH:
        raise TicketRuleError(
            f"El motivo no puede superar los {MAX_REASON_LENGTH} caracteres."
        )

    return reason


def _get_source(user_id: int) -> User:
    """El técnico de origen: cualquier usuario que aún conserve tickets asignados. Puede estar
    desactivado, o ya no ser Técnico (cambió de rol): su trabajo debe poder redistribuirse
    igual (RN-104 y RN-137)."""
    user = db.session.get(User, user_id)

    if user is None:
        raise TicketRuleError("El técnico de origen no existe.")

    return user


def _get_destination(user_id: int, source: User) -> User:
    if user_id == source.id:
        raise TicketRuleError("El técnico de destino no puede ser el mismo de origen.")

    user = db.session.scalar(
        db.select(User)
        .join(Role, User.rol_id == Role.id)
        .where(
            User.id == user_id,
            User.activo.is_(True),
            Role.codigo == RoleCode.TECNICO,
        )
    )

    if user is None:
        raise TicketRuleError("Elige técnicos de destino activos de la lista.")

    return user


def _audit(actor: User, source: User, result: ReassignmentResult, reason: str) -> None:
    by_destination: dict[str, list[str]] = defaultdict(list)

    for moved in result.moved:
        by_destination[moved.destination.username].append(moved.number)

    record_admin_event(
        AuditAction.REASIGNACION_MASIVA,
        actor=actor,
        entity_type="tecnico",
        entity_id=source.id,
        detail=(
            f"{len(result.moved)} tickets de {full_name(source)}"
            f" ({len(result.skipped)} omitidos)."
        ),
        old_value={
            "tecnico": person_snapshot(source),
            "tickets": [moved.number for moved in result.moved],
        },
        new_value={
            "lote": result.batch,
            "destinos": dict(by_destination),
            "omitidos": {skipped.number: skipped.reason for skipped in result.skipped},
        },
        reason=reason,
    )


__all__ = [
    "MAX_REASON_LENGTH",
    "MovedTicket",
    "ReassignmentResult",
    "SkippedTicket",
    "distribute",
    "reassign_tickets",
]
