"""Quién recibe un aviso de cada cosa que ocurre en un ticket (docs/06, RN-94 a RN-96,
RN-168; docs/04, RF-068).

`notifications/service.py` solo crea avisos: no sabe a quién avisar. Esa decisión vive
aquí, en un único lugar, y la toman las operaciones de los tickets al terminar
(cambiar el estado, asignar, comentar). Estas son las reglas:

- **Nunca se avisa a quien hizo el cambio.** Ya lo sabe.
- **Un Solicitante solo recibe avisos de lo que también ve en el historial.** Una nota
  interna, un escalamiento, el grupo, el motivo de una espera o de un cierre no llegan
  nunca a un Solicitante, ni en el título ni en el mensaje.
- **Se avisa a las personas vigentes**: los solicitantes que no fueron retirados y los
  técnicos que siguen asignados.
- **Crear un ticket no avisa a nadie.** Quien lo crea ya lo está viendo y el reparto
  del trabajo es de la asignación (decisión de `v0.5.0`).
- **Todo envío pasa por `_send`**, que respeta lo que el Administrador haya apagado
  (`notifications/preferences.py`, RN-172). Un aviso nuevo debe declararse allí.

Nada de aquí hace commit: los avisos se confirman o se revierten junto con la operación
que los provoca, igual que su evento de historial.

Este módulo no importa el paquete `tickets` (que es quien lo usa): trabaja sobre el
ticket y los usuarios que recibe.
"""

from ..extensions import db
from ..models import NotificationEvent, Role, StateAction, Ticket, User
from ..security import STAFF_ROLES, RoleCode
from .preferences import Audience, is_enabled
from .service import notify_many

E = NotificationEvent

_STAFF_ROLE_CODES = {role.value for role in STAFF_ROLES}

# Un título largo no cabe en un aviso: se recorta.
_TITLE_LENGTH = 80

# Por acción de estado: el aviso para los solicitantes y el aviso para los técnicos
# asignados, cada uno (evento, título, mensaje); `{t}` es el ticket. Una acción que no
# está aquí no avisa a nadie: la asignación y la desasignación derivadas se avisan en
# su propia operación.
_Notice = tuple[NotificationEvent, str, str]

_IN_PROGRESS: _Notice = (E.ESTADO_CAMBIADO, "Ticket en progreso", "Se empezó a trabajar en el ticket {t}.")
_ON_HOLD: _Notice = (E.TICKET_EN_ESPERA, "Ticket en espera", "El ticket {t} quedó en espera.")
_RESUMED: _Notice = (E.ESTADO_CAMBIADO, "Ticket reactivado", "Se retomó el trabajo en el ticket {t}.")
_CLOSED: _Notice = (E.TICKET_CERRADO, "Ticket cerrado", "Se cerró el ticket {t}.")
_AUTO_CLOSED: _Notice = (
    E.TICKET_CERRADO,
    "Ticket cerrado automáticamente",
    "El ticket {t} se cerró solo porque nadie confirmó la solución a tiempo.",
)

STATE_NOTICES: dict[StateAction, tuple[_Notice, _Notice]] = {
    StateAction.INICIAR: (_IN_PROGRESS, _IN_PROGRESS),
    StateAction.PONER_EN_ESPERA: (_ON_HOLD, _ON_HOLD),
    StateAction.REACTIVAR: (_RESUMED, _RESUMED),
    # RN-95: el solicitante debe poder acceder al ticket y revisar la resolución.
    StateAction.RESOLVER: (
        (
            E.VALIDACION_PENDIENTE,
            "Revisa la solución",
            "El ticket {t} fue resuelto: confirma si la solución te sirvió.",
        ),
        (E.TICKET_RESUELTO, "Ticket resuelto", "El ticket {t} fue resuelto."),
    ),
    StateAction.CIERRE_DIRECTO: (_CLOSED, _CLOSED),
    StateAction.CONFIRMAR: (_CLOSED, _CLOSED),
    StateAction.CIERRE_EXCEPCIONAL: (_CLOSED, _CLOSED),
    # RN-58: lo cierra el planificador cuando nadie validó la solución a tiempo. El
    # aviso no nombra a nadie: no hay persona que lo hiciera.
    StateAction.AUTO_CIERRE: (_AUTO_CLOSED, _AUTO_CLOSED),
    StateAction.RECHAZAR: (
        (
            E.ESTADO_CAMBIADO,
            "Ticket en progreso",
            "La solución del ticket {t} fue rechazada: se retoma el trabajo.",
        ),
        (
            E.ESTADO_CAMBIADO,
            "Solución rechazada",
            "El solicitante rechazó la solución del ticket {t}: hay que retomarlo.",
        ),
    ),
    # RN-96: al reabrir, los técnicos deben saber que el trabajo se retoma.
    StateAction.REABRIR: (
        (
            E.TICKET_REABIERTO,
            "Ticket reabierto",
            "El ticket {t} se reabrió y se retoma el trabajo.",
        ),
        (
            E.TICKET_REABIERTO,
            "Ticket reabierto",
            "Se reabrió el ticket {t}: hay que retomar el trabajo.",
        ),
    ),
}


# --- Operaciones de los tickets -----------------------------------------------


def notify_state_change(
    ticket: Ticket, actor: User | None, action: StateAction
) -> None:
    """Avisa a los solicitantes y a los técnicos asignados (menos a `actor`, que es
    None cuando lo hace el sistema) de una acción de estado."""
    notices = STATE_NOTICES.get(StateAction(action))

    if notices is None:
        return

    for (audience, people), (event, title, message) in zip(
        (
            (Audience.SOLICITANTES, _requesters(ticket)),
            (Audience.TECNICOS, _technicians(ticket)),
        ),
        notices,
        strict=True,
    ):
        _send(
            audience,
            event,
            _others(people, actor),
            title=title,
            message=message.format(t=_label(ticket)),
            ticket=ticket,
        )


def notify_assignment(ticket: Ticket, actor: User, technician: User) -> None:
    """Avisa al técnico asignado y a los solicitantes (menos a `actor`)."""
    _send(
        Audience.TECNICOS,
        E.TICKET_ASIGNADO,
        _others([technician], actor),
        title="Ticket asignado",
        message=f"Se te asignó el ticket {_label(ticket)}.",
        ticket=ticket,
    )
    _send(
        Audience.SOLICITANTES,
        E.TICKET_ASIGNADO,
        _others(_requesters(ticket), actor),
        title="Tu ticket ya tiene técnico",
        message=f"El ticket {_label(ticket)} ahora lo atiende {_name(technician)}.",
        ticket=ticket,
    )


def notify_unassignment(ticket: Ticket, actor: User, technician: User) -> None:
    """Avisa al técnico al que se quitó del ticket (si no fue él mismo)."""
    _send(
        Audience.TECNICOS,
        E.TICKET_REASIGNADO,
        _others([technician], actor),
        title="Ya no estás asignado",
        message=f"Se te quitó del ticket {_label(ticket)}.",
        ticket=ticket,
    )


def notify_reassignment_requesters(ticket: Ticket, actor: User, technician: User) -> None:
    """Avisa a los solicitantes de que ahora los atiende otro técnico (una reasignación
    masiva). No dice de dónde viene el ticket ni el motivo."""
    _send(
        Audience.SOLICITANTES,
        E.TICKET_ASIGNADO,
        _others(_requesters(ticket), actor),
        title="Tu ticket cambió de técnico",
        message=f"El ticket {_label(ticket)} ahora lo atiende {_name(technician)}.",
        ticket=ticket,
    )


def notify_bulk_reassignment(
    actor: User, source: User, moved: dict[User, list[Ticket]]
) -> None:
    """Un solo aviso a cada técnico que recibe tickets y otro al técnico de origen, con
    cuántos se movieron: una reasignación masiva no inunda a nadie con un aviso por
    ticket. No incluye el motivo ni los títulos."""
    for destination, tickets in moved.items():
        _send(
            Audience.TECNICOS,
            E.TICKET_REASIGNADO,
            _others([destination], actor),
            title="Tickets reasignados a ti",
            message=(
                f"Se te reasignaron {_count(tickets)} de {_name(source)}."
            ),
            ticket=tickets[0] if len(tickets) == 1 else None,
        )

    total = [ticket for tickets in moved.values() for ticket in tickets]

    if total:
        _send(
            Audience.TECNICOS,
            E.TICKET_REASIGNADO,
            _others([source], actor),
            title="Tus tickets se reasignaron",
            message=f"{_count(total).capitalize()} tuyos se reasignaron a otros técnicos.",
            ticket=total[0] if len(total) == 1 else None,
        )


def _count(tickets: list[Ticket]) -> str:
    return "1 ticket" if len(tickets) == 1 else f"{len(tickets)} tickets"


def notify_escalation(
    ticket: Ticket, actor: User, before: list[User], after: list[User]
) -> None:
    """Avisa a los técnicos nuevos y a los que dejaron de atender el ticket.

    Un escalamiento es interno: no se avisa a los solicitantes ni se dice el motivo ni
    el grupo."""
    before_ids = {user.id for user in before}
    after_ids = {user.id for user in after}

    _send(
        Audience.TECNICOS,
        E.TICKET_REASIGNADO,
        _others([user for user in after if user.id not in before_ids], actor),
        title="Ticket escalado",
        message=f"Se te asignó el ticket {_label(ticket)} por un escalamiento.",
        ticket=ticket,
    )
    _send(
        Audience.TECNICOS,
        E.TICKET_REASIGNADO,
        _others([user for user in before if user.id not in after_ids], actor),
        title="Ya no estás asignado",
        message=f"El ticket {_label(ticket)} se escaló a otro técnico.",
        ticket=ticket,
    )


def notify_priority_lowered(
    ticket: Ticket, actor: User, old_priority, new_priority, sla_label: str
) -> None:
    """Avisa a los Supervisores de que se bajó la prioridad con el SLA en riesgo
    (RN-88): los responsables del grupo del ticket y, si no tiene grupo o ninguno
    está activo, todos los Supervisores activos. `sla_label` es «próximo a vencer»
    o «vencido». No se copia el motivo: se lee en el historial."""
    _send(
        Audience.SUPERVISORES,
        E.SLA_PRIORIDAD_BAJADA,
        _others(_supervisors_of(ticket), actor),
        title="Prioridad bajada con el SLA en riesgo",
        message=(
            f"{_name(actor)} bajó la prioridad del ticket {_label(ticket)} de "
            f"{old_priority.nombre} a {new_priority.nombre} con el SLA {sla_label}."
        ),
        ticket=ticket,
    )


def notify_sla_warning(ticket: Ticket) -> None:
    """Avisa de que el ticket está próximo a vencer su SLA (RN-91): a los técnicos
    asignados y, si no tiene ninguno, a los Supervisores responsables del grupo (o a
    todos). El SLA es interno: los solicitantes nunca lo reciben."""
    technicians = _technicians(ticket)
    # Los Supervisores reciben el aviso solo de un ticket sin técnico: apagar el de los
    # técnicos no lo desvía a ellos.
    audience, people = (
        (Audience.TECNICOS, technicians)
        if technicians
        else (Audience.SUPERVISORES, _supervisors_of(ticket))
    )
    _send(
        audience,
        E.SLA_PROXIMO_A_VENCER,
        people,
        title="SLA próximo a vencer",
        message=f"El ticket {_label(ticket)} está próximo a vencer su SLA.",
        ticket=ticket,
    )


def notify_sla_breach(ticket: Ticket) -> None:
    """Avisa de que el ticket venció su SLA (RN-91): a los técnicos asignados y a los
    Supervisores responsables del grupo (o a todos si no hay ninguno)."""
    for audience, people in (
        (Audience.TECNICOS, _technicians(ticket)),
        (Audience.SUPERVISORES, _supervisors_of(ticket)),
    ):
        _send(
            audience,
            E.SLA_VENCIDO,
            people,
            title="SLA vencido",
            message=f"El SLA del ticket {_label(ticket)} venció.",
            ticket=ticket,
        )


def notify_comment(ticket: Ticket, actor: User, *, internal: bool) -> None:
    """Avisa de un comentario nuevo (RF-068), sin copiar su texto.

    - Nota interna: solo a los técnicos asignados.
    - Comentario público del personal: a los solicitantes.
    - Comentario público de un solicitante: a los técnicos asignados.
    """
    label = _label(ticket)

    if internal:
        _send(
            Audience.TECNICOS,
            E.NOTA_INTERNA,
            _others(_technicians(ticket), actor),
            title="Nota interna",
            message=f"{_name(actor)} escribió una nota interna en el ticket {label}.",
            ticket=ticket,
        )
    elif _is_staff(actor):
        _send(
            Audience.SOLICITANTES,
            E.COMENTARIO_PUBLICO,
            _others(_requesters(ticket), actor),
            title="Nueva respuesta",
            message=f"{_name(actor)} respondió en el ticket {label}.",
            ticket=ticket,
        )
    else:
        _send(
            Audience.TECNICOS,
            E.COMENTARIO_PUBLICO,
            _others(_technicians(ticket), actor),
            title="Respuesta del solicitante",
            message=f"{_name(actor)} comentó en el ticket {label}.",
            ticket=ticket,
        )


# --- Piezas comunes -----------------------------------------------------------


def _send(
    audience: Audience,
    event: NotificationEvent,
    people: list[User],
    **notice,
) -> None:
    """El único camino de envío: respeta lo que el Administrador haya apagado."""
    if is_enabled(event, audience):
        notify_many(people, event, **notice)


def _requesters(ticket: Ticket) -> list[User]:
    return [participation.solicitante for participation in ticket.solicitantes_vigentes]


def _technicians(ticket: Ticket) -> list[User]:
    return [assignment.tecnico for assignment in ticket.tecnicos_vigentes]


def _supervisors_of(ticket: Ticket) -> list[User]:
    """Los Supervisores responsables del grupo del ticket que están activos; si no hay
    ninguno (o el ticket no tiene grupo), todos los Supervisores activos."""
    if ticket.grupo is not None:
        responsible = [
            designation.supervisor
            for designation in ticket.grupo.supervisores_vigentes
            if designation.supervisor.is_active
        ]

        if responsible:
            return responsible

    return list(
        db.session.scalars(
            db.select(User)
            .join(Role, Role.id == User.rol_id)
            .where(Role.codigo == RoleCode.SUPERVISOR.value, User.activo.is_(True))
            .order_by(User.id)
        )
    )


def _others(people: list[User], actor: User | None) -> list[User]:
    """Las personas menos quien hizo el cambio (`actor` es None si fue el sistema:
    entonces nadie se excluye)."""
    return [person for person in people if actor is None or person.id != actor.id]


def _is_staff(user: User) -> bool:
    return user.rol.codigo in _STAFF_ROLE_CODES


def _name(user: User) -> str:
    return f"{user.nombre} {user.apellido}".strip()


def _label(ticket: Ticket) -> str:
    title = ticket.titulo

    if len(title) > _TITLE_LENGTH:
        title = title[: _TITLE_LENGTH - 1].rstrip() + "…"

    return f"#{ticket.public_id} «{title}»"
