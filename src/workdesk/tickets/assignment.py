"""Asignación de técnicos, grupo y escalamiento de un ticket (docs/06, RN-157).

Un ticket tiene 0..N técnicos a la vez (`tickets_tecnicos`) y, opcionalmente,
un grupo (`tickets.grupo_id`). La asignación es organizativa: no es requisito
para que un técnico actúe sobre el ticket. Solo puede asignarse a un
**Técnico activo**.

Quién puede hacer cada cosa lo decide la capa de rutas con las políticas de
`security/authorization.py`; aquí viven las reglas de los datos. Nada hace
commit: el cambio y su evento de historial se confirman o se revierten
juntos.

Qué sube la versión del ticket (`tickets.version`): cambiar el grupo y
escalar (cambian la estructura del ticket) y el cambio de estado derivado de
una asignación, que va en el mismo `UPDATE`. Asignar y quitar técnicos por sí
solos no la suben: son aditivos y no pisan datos (RNF-026). Todas las
operaciones bloquean la fila del ticket antes de validar.
"""

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import (
    Grupo,
    Role,
    StateAction,
    Ticket,
    TicketEvent,
    TicketTechnician,
    User,
)
from ..notifications.events import (
    notify_assignment,
    notify_escalation,
    notify_unassignment,
)
from ..security import RoleCode
from .lifecycle import apply_derived_transition
from .service import (
    TicketRuleError,
    clean_optional_reason,
    full_name,
    person_snapshot,
    record_ticket_event,
)
from .versioning import (
    TicketConflictError,
    apply_ticket_changes,
    begin_ticket_operation,
)

_ALREADY_ASSIGNED = "Ese técnico ya está asignado al ticket."


# --- Consultas --------------------------------------------------------


def list_assignable_technicians(ticket: Ticket) -> list[User]:
    """Técnicos activos que todavía no están asignados al ticket."""
    assigned = [a.tecnico_id for a in ticket.tecnicos_vigentes]

    return _active_technicians(exclude_ids=assigned)


def list_escalation_technicians() -> list[User]:
    """Técnicos activos a los que se puede escalar un ticket."""
    return _active_technicians()


def list_groups_for_ticket(ticket: Ticket) -> list[Grupo]:
    """Grupos activos, más el grupo actual del ticket aunque se haya
    desactivado (para poder mostrarlo y conservarlo)."""
    groups = list(
        db.session.scalars(
            db.select(Grupo)
            .where(Grupo.activo.is_(True))
            .order_by(func.lower(Grupo.nombre))
        )
    )

    current = ticket.grupo

    if current is not None and all(g.id != current.id for g in groups):
        groups.append(current)

    return groups


# --- Asignar y quitar técnicos ----------------------------------------


def assign_technician(
    ticket: Ticket,
    technician_id: int,
    *,
    actor: User,
) -> TicketTechnician:
    """Asigna un técnico al ticket.

    Debe ser un Técnico activo que no esté ya asignado. Si el ticket está
    `Nuevo`, el primer técnico lo pasa a `Asignado` (transición `ASIGNAR`,
    si está activa). Registra `TECNICO_ASIGNADO` y, en su caso,
    `ESTADO_CAMBIADO`. Un ticket cerrado lanza `TicketClosedError`.

    Sirve tanto para que un Técnico se asigne a sí mismo como para que un
    Supervisor o un Administrador asignen a otra persona (la política la
    comprueba la ruta).
    """
    _begin(ticket, actor)

    technician = _get_active_technician(technician_id)

    if any(a.tecnico_id == technician.id for a in ticket.tecnicos_vigentes):
        raise TicketRuleError(_ALREADY_ASSIGNED)

    assignment = add_assignment(ticket, technician, actor)

    record_ticket_event(
        ticket,
        TicketEvent.TECNICO_ASIGNADO,
        actor=actor,
        detail=f"Técnico asignado: {full_name(technician)}.",
        new_value=person_snapshot(technician),
        context={"asignacion_id": assignment.id},
    )

    apply_derived_transition(
        ticket,
        actor=actor,
        action=StateAction.ASIGNAR,
        from_state_code="NUEVO",
    )

    notify_assignment(ticket, actor, technician)

    return assignment


def unassign_technician(
    ticket: Ticket,
    assignment_id: int,
    *,
    actor: User,
    reason: str | None = None,
) -> None:
    """Quita a un técnico del ticket: cierra su asignación y la conserva.

    Si era el último técnico de un ticket `Asignado`, el ticket vuelve a
    `Nuevo` (transición `DESASIGNACION`, si está activa). Registra
    `TECNICO_DESASIGNADO` y, en su caso, `ESTADO_CAMBIADO`.
    """
    _begin(ticket, actor)

    assignment = next(
        (a for a in ticket.tecnicos_vigentes if a.id == assignment_id),
        None,
    )

    if assignment is None:
        raise TicketRuleError("Ese técnico ya no está asignado al ticket.")

    reason = clean_optional_reason(reason)
    technician = assignment.tecnico

    close_assignment(assignment, actor, reason)
    db.session.flush()
    db.session.expire(ticket, ["tecnicos"])

    context = {"asignacion_id": assignment.id}

    if reason:
        context["motivo"] = reason

    record_ticket_event(
        ticket,
        TicketEvent.TECNICO_DESASIGNADO,
        actor=actor,
        detail=f"Técnico desasignado: {full_name(technician)}.",
        old_value=person_snapshot(technician),
        context=context,
    )

    if not ticket.tecnicos_vigentes:
        apply_derived_transition(
            ticket,
            actor=actor,
            action=StateAction.DESASIGNACION,
            from_state_code="ASIGNADO",
        )

    notify_unassignment(ticket, actor, technician)


# --- Grupo ------------------------------------------------------------


def set_group(
    ticket: Ticket,
    group_id: int | None,
    *,
    actor: User,
    expected_version: int,
) -> bool:
    """Fija el grupo del ticket (o lo quita con `None`).

    El grupo nuevo debe estar activo; el actual puede conservarse aunque se
    haya desactivado. Cambiar el grupo no cambia el estado. Devuelve False,
    sin tocar nada, si el grupo es el mismo. Sube la versión y registra
    `GRUPO_CAMBIADO` (evento interno).
    """
    _begin(ticket, actor)
    _check_version(ticket, expected_version)

    group = _get_group(ticket, group_id)
    old_group = ticket.grupo

    if _same_group(old_group, group):
        return False

    apply_ticket_changes(
        ticket,
        actor,
        expected_version,
        {"grupo_id": None if group is None else group.id},
    )

    record_ticket_event(
        ticket,
        TicketEvent.GRUPO_CAMBIADO,
        actor=actor,
        detail=(
            f"Grupo cambiado de {_group_label(old_group)} "
            f"a {_group_label(group)}."
        ),
        old_value=_group_snapshot(old_group),
        new_value=_group_snapshot(group),
    )

    return True


# --- Escalamiento -----------------------------------------------------


def escalate_ticket(
    ticket: Ticket,
    *,
    actor: User,
    expected_version: int,
    group_id: int | None,
    technician_id: int | None,
    reason: str,
) -> None:
    """Escala el ticket manualmente a otro grupo y/o a otro técnico (RF-039).

    - `group_id`: el grupo al que se escala. Debe ser distinto del actual.
    - `technician_id`: el técnico que pasa a atender el ticket. Reemplaza a
      los técnicos actuales (las asignaciones anteriores se cierran y se
      conservan). Debe ser un Técnico activo que no sea el único ya asignado.
    - Hay que cambiar al menos una de las dos cosas y el motivo es
      obligatorio (máx. 500 caracteres).

    Es una acción manual: no cambia la prioridad ni se dispara por reglas de
    SLA. Sube la versión y registra un único evento interno `TICKET_ESCALADO`
    con el grupo y los técnicos anteriores y nuevos y el motivo. Si el ticket
    está `Nuevo`, el técnico nuevo lo pasa a `Asignado`.
    """
    _begin(ticket, actor)
    _check_version(ticket, expected_version)

    reason = _clean_required_reason(reason)
    old_group = ticket.grupo
    new_group = old_group if group_id is None else _get_group(ticket, group_id)
    group_changes = group_id is not None and not _same_group(old_group, new_group)

    current = ticket.tecnicos_vigentes
    technician = None if technician_id is None else _get_active_technician(
        technician_id
    )
    technician_changes = technician is not None and [
        a.tecnico_id for a in current
    ] != [technician.id]

    if not group_changes and not technician_changes:
        raise TicketRuleError(
            "Elige otro grupo u otro técnico: así no habría ningún cambio."
        )

    before = _escalation_snapshot(old_group, current)
    previous_technicians = [a.tecnico for a in current]

    changes = {"grupo_id": new_group.id} if group_changes else {}
    apply_ticket_changes(ticket, actor, expected_version, changes)

    if technician_changes:
        for assignment in current:
            close_assignment(assignment, actor, "Escalamiento.")

        db.session.flush()
        add_assignment(ticket, technician, actor)

    db.session.expire(ticket, ["tecnicos"])
    after = _escalation_snapshot(
        new_group if group_changes else old_group,
        ticket.tecnicos_vigentes,
    )

    record_ticket_event(
        ticket,
        TicketEvent.TICKET_ESCALADO,
        actor=actor,
        detail="Ticket escalado.",
        old_value=before,
        new_value=after,
        context={"motivo": reason},
    )

    if technician_changes:
        apply_derived_transition(
            ticket,
            actor=actor,
            action=StateAction.ASIGNAR,
            from_state_code="NUEVO",
        )

        notify_escalation(
            ticket,
            actor,
            previous_technicians,
            [a.tecnico for a in ticket.tecnicos_vigentes],
        )


# --- Piezas comunes ---------------------------------------------------


def _begin(ticket: Ticket, actor: User) -> None:
    """Prepara una operación: usuario activo, ticket bloqueado y no cerrado.

    Las asignaciones y el grupo pudieron cambiar desde que se cargó el ticket
    (mientras esperaba el bloqueo), así que se vuelven a leer.
    """
    begin_ticket_operation(ticket, actor, expire=("tecnicos", "grupo"))


def _check_version(ticket: Ticket, expected_version: int) -> None:
    if ticket.version != expected_version:
        raise TicketConflictError(
            "Otra persona modificó este ticket mientras decidías. Revisa su "
            "estado actual e inténtalo de nuevo."
        )


def add_assignment(
    ticket: Ticket,
    technician: User,
    actor: User,
) -> TicketTechnician:
    assignment = TicketTechnician(
        ticket_id=ticket.id,
        tecnico_id=technician.id,
        asignado_por_usuario_id=actor.id,
    )

    # Dos asignaciones simultáneas del mismo técnico: la fila del ticket ya
    # está bloqueada, pero el índice único parcial es el respaldo y el
    # savepoint deshace solo este intento.
    try:
        with db.session.begin_nested():
            db.session.add(assignment)
            db.session.flush()
    except IntegrityError as error:
        raise TicketRuleError(_ALREADY_ASSIGNED) from error

    db.session.expire(ticket, ["tecnicos"])

    return assignment


def close_assignment(
    assignment: TicketTechnician,
    actor: User,
    reason: str | None,
) -> None:
    # La hora la pone la base de datos, como `fecha_asignacion`.
    assignment.fecha_desasignacion = func.now()
    assignment.desasignado_por_usuario_id = actor.id
    assignment.motivo_desasignacion = reason


def _get_active_technician(user_id: int) -> User:
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
        raise TicketRuleError("Elige un técnico activo de la lista.")

    return user


def _active_technicians(*, exclude_ids=()) -> list[User]:
    statement = (
        db.select(User)
        .join(Role, User.rol_id == Role.id)
        .where(User.activo.is_(True), Role.codigo == RoleCode.TECNICO)
        .order_by(func.lower(User.apellido), func.lower(User.nombre))
    )

    if exclude_ids:
        statement = statement.where(User.id.not_in(exclude_ids))

    return list(db.session.scalars(statement))


def _get_group(ticket: Ticket, group_id: int | None) -> Grupo | None:
    if group_id is None:
        return None

    group = db.session.get(Grupo, group_id)

    if group is None or (not group.activo and group.id != ticket.grupo_id):
        raise TicketRuleError("El grupo seleccionado no está disponible.")

    return group


def _same_group(first: Grupo | None, second: Grupo | None) -> bool:
    return (first.id if first else None) == (second.id if second else None)


def _group_label(group: Grupo | None) -> str:
    return "«Sin grupo»" if group is None else f"«{group.nombre}»"


def _group_snapshot(group: Grupo | None) -> dict:
    return {
        "grupo_id": None if group is None else group.id,
        "nombre": None if group is None else group.nombre,
    }


def _escalation_snapshot(group: Grupo | None, assignments) -> dict:
    return {
        "grupo": _group_snapshot(group),
        "tecnicos": [person_snapshot(a.tecnico) for a in assignments],
    }


def _clean_required_reason(reason: str | None) -> str:
    reason = (reason or "").strip()

    if not reason:
        raise TicketRuleError("Indica el motivo del escalamiento.")

    return clean_optional_reason(reason)
