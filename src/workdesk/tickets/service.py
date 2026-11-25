from collections.abc import Iterable

from sqlalchemy import false, true
from sqlalchemy.orm import joinedload, selectinload

from ..catalogs.service import list_categories
from ..extensions import db
from ..models import (
    Categoria,
    Estado,
    HistoryVisibility,
    MotivoEspera,
    Prioridad,
    Role,
    Ticket,
    TicketEvent,
    TicketHistory,
    TicketRequester,
    TicketTechnician,
    Ubicacion,
    User,
)
from ..models.admin_audit_log import ActorType
from ..models.categoria import FALLBACK_CATEGORY_CODE
from ..models.ticket import MAX_DESCRIPTION_LENGTH, MAX_TITLE_LENGTH
from ..models.ticket_history import DEFAULT_EVENT_VISIBILITY
from ..security import (
    RoleCode,
    can_view_internal_activity,
    has_any_role,
)
from ..sla.periods import reconcile_sla

INITIAL_STATE_CODE = "NUEVO"
CLOSED_STATE_CODE = "CERRADO"

# Máximo de caracteres de un motivo (cambio de prioridad, asignación,
# solicitantes...).


class TicketRuleError(ValueError):
    """Un dato del ticket incumple una regla de negocio.

    El mensaje está pensado para mostrarse al usuario.
    """


def clean_title_and_description(title: str, description: str) -> tuple[str, str]:
    """Recorta y valida el título y la descripción de un ticket.

    Son las mismas reglas al crear y al editar: ambos obligatorios y con su
    longitud máxima. Lanza `TicketRuleError` con un mensaje para el usuario.
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

    if len(description) > MAX_DESCRIPTION_LENGTH:
        raise TicketRuleError(
            "La descripción no puede superar los "
            f"{MAX_DESCRIPTION_LENGTH} caracteres."
        )

    return title, description


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
    title, description = clean_title_and_description(title, description)

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

    # Abre el primer período de SLA con la política de la prioridad (si la tiene).
    # Sin usuario de cambio: ese campo es de quien cambia algo después de crearlo.
    reconcile_sla(ticket, None)

    return ticket


def get_ticket_by_public_id(public_id: str) -> Ticket | None:
    """Busca un ticket por su identificador público.

    Carga de una vez lo que muestra el detalle (estado, prioridad, categoría,
    ubicación, creador y solicitantes) para no hacer una consulta por cada uno.
    No comprueba permisos: quien llama debe aplicar `can_view_ticket`.
    """
    return db.session.scalar(
        db.select(Ticket)
        .where(Ticket.public_id == public_id)
        .options(
            joinedload(Ticket.estado),
            joinedload(Ticket.prioridad),
            joinedload(Ticket.categoria),
            joinedload(Ticket.ubicacion),
            joinedload(Ticket.creado_por),
            joinedload(Ticket.grupo),
            selectinload(Ticket.solicitantes).joinedload(
                TicketRequester.solicitante
            ),
            selectinload(Ticket.tecnicos).joinedload(
                TicketTechnician.tecnico
            ),
        )
    )


def visible_history_condition(user):
    """Condición SQL con los eventos del historial que `user` puede ver.

    - El personal ve todos, internos incluidos.
    - El Solicitante ve solo los eventos públicos.
    - Cualquier otro caso (anónimo, inactivo, sin rol): ninguno.

    Es la única fuente de esta regla: el detalle, el historial y cualquier
    conteo deben salir de una consulta que la use, nunca ocultar el evento
    en la plantilla. Igual que `visible_tickets_condition`, no comprueba el
    acceso al ticket: quien llama debe haber aplicado antes `can_view_ticket`.
    """
    if can_view_internal_activity(user):
        return true()

    if has_any_role(user, RoleCode.SOLICITANTE):
        return TicketHistory.visibilidad == HistoryVisibility.PUBLICO.value

    return false()


def list_ticket_history(ticket: Ticket, viewer: User) -> list[TicketHistory]:
    """Eventos del ticket que `viewer` puede ver, del más antiguo al más reciente.

    `viewer` es obligatorio a propósito: así ninguna pantalla puede listar el
    historial completo sin decidir para quién.
    """
    return list(
        db.session.scalars(
            db.select(TicketHistory)
            .where(
                TicketHistory.ticket_id == ticket.id,
                visible_history_condition(viewer),
            )
            .options(
                joinedload(TicketHistory.actor),
                joinedload(TicketHistory.motivo_espera),
            )
            .order_by(TicketHistory.fecha_hora, TicketHistory.id)
        )
    )


def list_requester_candidates() -> list[User]:
    """Usuarios que pueden figurar como solicitantes: activos y con rol
    Solicitante, ordenados por apellido y nombre.
    """
    return list(
        db.session.scalars(
            db.select(User)
            .join(Role, User.rol_id == Role.id)
            .where(
                User.activo.is_(True),
                Role.codigo == RoleCode.SOLICITANTE,
            )
            .order_by(db.func.lower(User.apellido), db.func.lower(User.nombre))
        )
    )


def categories_for_selection() -> list[Categoria]:
    """Categorías activas para el desplegable del formulario.

    Van por orden y nombre, pero la categoría de respaldo `Sin clasificar`
    siempre queda al final: es la salida para quien no sabe cuál elegir, no
    la opción por defecto.
    """
    categories = list_categories("activo")

    return [
        category
        for category in categories
        if category.codigo != FALLBACK_CATEGORY_CODE
    ] + [
        category
        for category in categories
        if category.codigo == FALLBACK_CATEGORY_CODE
    ]


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
    visibility: HistoryVisibility | None = None,
    wait_reason: MotivoEspera | None = None,
) -> TicketHistory:
    """Añade un evento al historial del ticket en la sesión actual.

    No hace commit: el evento se confirma o se revierte junto con la
    operación que lo origina. `actor=None` identifica una acción del sistema.

    `event` debe pertenecer a `TicketEvent`; cualquier otro valor lanza
    `ValueError` (el vocabulario lo controla la aplicación, no la base de
    datos). `visibility` indica quién puede ver el evento; si se omite se usa
    la que el vocabulario define para ese evento (`DEFAULT_EVENT_VISIBILITY`).
    `wait_reason` es el motivo del catálogo cuando el evento es la entrada a
    `En espera`.
    """
    event = TicketEvent(event)
    visibility = HistoryVisibility(
        DEFAULT_EVENT_VISIBILITY[event] if visibility is None else visibility
    )

    entry = TicketHistory(
        ticket_id=ticket.id,
        actor_usuario_id=None if actor is None else actor.id,
        actor_tipo=(
            ActorType.SISTEMA if actor is None else ActorType.USUARIO
        ).value,
        tipo_evento=event.value,
        visibilidad=visibility.value,
        motivo_espera_id=None if wait_reason is None else wait_reason.id,
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


def full_name(user: User) -> str:
    """Nombre y apellido de una persona, como se muestran en el historial."""
    return f"{user.nombre} {user.apellido}"


def person_snapshot(user: User) -> dict:
    """Datos de una persona para guardar en `valor_anterior` o `valor_nuevo`
    de un evento (así el historial se lee aunque la persona cambie después)."""
    return {
        "usuario_id": user.id,
        "username": user.username,
        "nombre": full_name(user),
    }


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
