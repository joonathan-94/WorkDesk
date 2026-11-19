"""Solicitantes de un ticket ya creado (docs/06, RN-158).

Un ticket tiene 0..N solicitantes (`tickets_solicitantes`). Los iniciales se
asocian al crearlo (`create_ticket`); aquí el personal puede agregar y retirar
solicitantes después, mientras el ticket no esté cerrado. Solo puede ser
solicitante un usuario **activo con rol Solicitante**.

Quién puede hacerlo lo decide la capa de rutas con `can_manage_requesters`;
aquí viven las reglas de los datos. Nada hace commit: el cambio y su evento de
historial se confirman o se revierten juntos.

Reglas que conviene tener presentes:

- Retirar a alguien conserva su fila (con `fecha_retiro`, quién lo retiró y,
  en el historial, el motivo): la participación queda como historial. Puede
  volver a agregarse más adelante con una fila nueva.
- Retirar a un solicitante le quita el acceso al ticket, salvo que además sea
  quien lo creó: el creador original no cambia nunca (RN-13, RN-153). Lo
  decide `can_view_ticket`, que ya ignora las participaciones retiradas.
- Un ticket puede quedarse sin solicitantes (RN-12).
- Agregar y retirar solicitantes no sube la versión del ticket
  (`tickets.version`): no cambia ninguno de los datos que se editan, es
  aditivo como asignar técnicos. Sí bloquea la fila del ticket antes de
  validar, para que dos personas que actúan a la vez no se pisen.
- Los eventos del historial son internos: el Solicitante no ve quiénes más
  figuran en un ticket (docs/11, UI-005).
"""

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import Role, Ticket, TicketEvent, TicketRequester, User
from ..security import RoleCode
from .service import (
    TicketRuleError,
    clean_optional_reason,
    full_name,
    list_requester_candidates,
    person_snapshot,
    record_ticket_event,
)
from .versioning import begin_ticket_operation

_ALREADY_REQUESTER = "Esa persona ya es solicitante del ticket."


# --- Consultas --------------------------------------------------------


def list_addable_requesters(ticket: Ticket) -> list[User]:
    """Usuarios que pueden agregarse como solicitantes: activos, con rol
    Solicitante y que todavía no son solicitantes vigentes del ticket.

    Incluye a quien creó el ticket si es un Solicitante (por ejemplo, para
    volver a asociar a alguien que se retiró).
    """
    current = {r.solicitante_id for r in ticket.solicitantes_vigentes}

    return [user for user in list_requester_candidates() if user.id not in current]


# --- Agregar y retirar ------------------------------------------------


def add_requester(
    ticket: Ticket,
    requester_id: int,
    *,
    actor: User,
) -> TicketRequester:
    """Agrega un solicitante al ticket.

    Debe ser un usuario activo con rol Solicitante que no sea ya solicitante
    vigente. Si estuvo retirado antes, se crea una participación nueva (la
    anterior se conserva como historial). Registra `SOLICITANTE_AGREGADO`
    (evento interno). Un ticket cerrado lanza `TicketClosedError`.
    """
    begin_ticket_operation(ticket, actor, expire=("solicitantes",))

    requester = _get_active_requester(requester_id)

    if any(r.solicitante_id == requester.id for r in ticket.solicitantes_vigentes):
        raise TicketRuleError(_ALREADY_REQUESTER)

    link = TicketRequester(
        ticket_id=ticket.id,
        solicitante_id=requester.id,
        asociado_por_usuario_id=actor.id,
    )

    # La fila del ticket ya está bloqueada, así que dos altas simultáneas se
    # serializan; el índice único parcial es el respaldo y el savepoint
    # deshace solo este intento.
    try:
        with db.session.begin_nested():
            db.session.add(link)
            db.session.flush()
    except IntegrityError as error:
        raise TicketRuleError(_ALREADY_REQUESTER) from error

    db.session.expire(ticket, ["solicitantes"])

    record_ticket_event(
        ticket,
        TicketEvent.SOLICITANTE_AGREGADO,
        actor=actor,
        detail=f"Solicitante agregado: {full_name(requester)}.",
        new_value=person_snapshot(requester),
        context={"participacion_id": link.id},
    )

    return link


def remove_requester(
    ticket: Ticket,
    participation_id: int,
    *,
    actor: User,
    reason: str | None = None,
) -> None:
    """Retira a un solicitante del ticket: cierra su participación y la
    conserva (con quién la retiró).

    `participation_id` es el id de la fila de `tickets_solicitantes`, no el
    del usuario. El motivo es opcional (máx. 500 caracteres) y queda en el
    historial. Registra `SOLICITANTE_RETIRADO` (evento interno). Un ticket
    cerrado lanza `TicketClosedError`.
    """
    begin_ticket_operation(ticket, actor, expire=("solicitantes",))

    link = next(
        (r for r in ticket.solicitantes_vigentes if r.id == participation_id),
        None,
    )

    if link is None:
        raise TicketRuleError("Esa persona ya no es solicitante del ticket.")

    reason = clean_optional_reason(reason)
    requester = link.solicitante

    # La hora la pone la base de datos, como `fecha_asociacion`.
    link.fecha_retiro = func.now()
    link.retirado_por_usuario_id = actor.id
    db.session.flush()
    db.session.expire(ticket, ["solicitantes"])

    context = {"participacion_id": link.id}

    if reason:
        context["motivo"] = reason

    record_ticket_event(
        ticket,
        TicketEvent.SOLICITANTE_RETIRADO,
        actor=actor,
        detail=f"Solicitante retirado: {full_name(requester)}.",
        old_value=person_snapshot(requester),
        context=context,
    )


# --- Piezas comunes ---------------------------------------------------


def _get_active_requester(user_id: int) -> User:
    user = db.session.scalar(
        db.select(User)
        .join(Role, User.rol_id == Role.id)
        .where(
            User.id == user_id,
            User.activo.is_(True),
            Role.codigo == RoleCode.SOLICITANTE,
        )
    )

    if user is None:
        raise TicketRuleError(
            "Elige a una persona de la lista: debe estar activa y tener el "
            "rol Solicitante."
        )

    return user
