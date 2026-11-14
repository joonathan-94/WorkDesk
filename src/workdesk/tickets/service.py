from collections.abc import Iterable

from ..extensions import db
from ..models import (
    Categoria,
    Estado,
    Prioridad,
    Role,
    Ticket,
    TicketEvent,
    TicketHistory,
    TicketRequester,
    Ubicacion,
    User,
)
from ..models.admin_audit_log import ActorType
from ..models.ticket import MAX_TITLE_LENGTH
from ..security import RoleCode

INITIAL_STATE_CODE = "NUEVO"


class TicketRuleError(ValueError):
    """Un dato del ticket incumple una regla de negocio.

    El mensaje está pensado para mostrarse al usuario.
    """


def create_ticket(
    *,
    actor: User,
    title: str,
    description: str,
    category_id: int,
    priority_id: int,
    location_id: int | None = None,
    requester_ids: Iterable[int] = (),
) -> Ticket:
    """Crea un ticket en estado Nuevo y registra su evento de creación.

    - La categoría, la prioridad y la ubicación deben estar activas
      (un valor desactivado ya no puede elegirse en tickets nuevos).
    - Los solicitantes son opcionales (0..N): deben ser usuarios activos con
      rol Solicitante. El creador no se convierte en solicitante por sí
      mismo; quien llama decide quiénes lo son.
    - `creado_por_usuario_id` queda fijado con el actor y no cambia nunca.

    Lanza `TicketRuleError` sin dejar nada pendiente en la sesión. No hace
    commit: el ticket y su historial se confirman juntos, quien llama
    confirma la transacción.

    Quién puede crear tickets a nombre de otras personas lo decide la capa de
    rutas; este servicio solo asocia a los solicitantes que recibe.
    """
    title = title.strip()
    description = description.strip()

    if not title:
        raise TicketRuleError("El título es obligatorio.")

    if len(title) > MAX_TITLE_LENGTH:
        raise TicketRuleError(
            f"El título no puede superar los {MAX_TITLE_LENGTH} caracteres."
        )

    if not description:
        raise TicketRuleError("La descripción es obligatoria.")

    if not actor.is_active:
        raise TicketRuleError("El usuario no está activo.")

    category = _get_active(Categoria, category_id, "La categoría")
    priority = _get_active(Prioridad, priority_id, "La prioridad")
    location = (
        None
        if location_id is None
        else _get_active(Ubicacion, location_id, "La ubicación")
    )
    requesters = _load_requesters(requester_ids)
    state = _initial_state()

    ticket = Ticket(
        titulo=title,
        descripcion=description,
        creado_por_usuario_id=actor.id,
        categoria_id=category.id,
        prioridad_id=priority.id,
        estado_id=state.id,
        ubicacion_id=None if location is None else location.id,
    )
    db.session.add(ticket)
    db.session.flush()

    for requester in requesters:
        db.session.add(
            TicketRequester(
                ticket_id=ticket.id,
                solicitante_id=requester.id,
                asociado_por_usuario_id=actor.id,
            )
        )

    record_ticket_event(
        ticket,
        TicketEvent.TICKET_CREADO,
        actor=actor,
        detail="Ticket creado.",
        new_state=state,
        new_value={
            "titulo": ticket.titulo,
            "categoria": category.nombre,
            "prioridad": priority.nombre,
            "ubicacion": None if location is None else location.nombre,
            "solicitantes": [
                {"id": r.id, "username": r.username} for r in requesters
            ],
        },
    )

    db.session.refresh(ticket)

    return ticket


def record_ticket_event(
    ticket: Ticket,
    event: TicketEvent,
    *,
    actor: User | None,
    detail: str | None = None,
    old_state: Estado | None = None,
    new_state: Estado | None = None,
    old_value: dict | None = None,
    new_value: dict | None = None,
    context: dict | None = None,
) -> TicketHistory:
    """Añade un evento al historial del ticket en la sesión actual.

    No hace commit: el evento se confirma o se revierte junto con la
    operación que lo origina. `actor=None` identifica una acción del sistema.
    """
    entry = TicketHistory(
        ticket_id=ticket.id,
        actor_usuario_id=None if actor is None else actor.id,
        actor_tipo=(
            ActorType.SISTEMA if actor is None else ActorType.USUARIO
        ).value,
        tipo_evento=TicketEvent(event).value,
        estado_anterior_id=None if old_state is None else old_state.id,
        estado_nuevo_id=None if new_state is None else new_state.id,
        detalle=detail,
        valor_anterior=old_value,
        valor_nuevo=new_value,
        contexto=context,
    )

    db.session.add(entry)
    db.session.flush()

    return entry


def _get_active(model, record_id: int, label: str):
    record = db.session.get(model, record_id)

    if record is None or not record.activo:
        raise TicketRuleError(f"{label} seleccionada no está disponible.")

    return record


def _load_requesters(requester_ids: Iterable[int]) -> list[User]:
    # Sin duplicados y en el orden recibido.
    unique_ids = list(dict.fromkeys(requester_ids))

    if not unique_ids:
        return []

    users = db.session.scalars(
        db.select(User)
        .join(Role, User.rol_id == Role.id)
        .where(
            User.id.in_(unique_ids),
            User.activo.is_(True),
            Role.codigo == RoleCode.SOLICITANTE,
        )
    ).all()

    if len(users) != len(unique_ids):
        raise TicketRuleError(
            "Alguno de los solicitantes no existe, no está activo o no "
            "tiene el rol Solicitante."
        )

    by_id = {user.id: user for user in users}

    return [by_id[user_id] for user_id in unique_ids]


def _initial_state() -> Estado:
    state = db.session.scalar(
        db.select(Estado).where(Estado.codigo == INITIAL_STATE_CODE)
    )

    if state is None:
        raise TicketRuleError(
            "No existe el estado inicial. Ejecuta el comando seed-catalogs."
        )

    return state
