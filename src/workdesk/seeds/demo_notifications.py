"""Notificaciones de demostración (solo desarrollo).

Mientras ningún evento del sistema genera avisos por sí solo (llegan con la entrega
6 de `v0.5.0`), este seed deja unas cuantas notificaciones de ejemplo para poder ver
el centro de notificaciones y la campana con contador. Son avisos sueltos con el
aspecto de los reales, escritos para cada rol: el personal recibe asignaciones,
respuestas y avisos de SLA; el Solicitante, cambios de estado, respuestas y la
revisión de la solución (el SLA es solo para el personal).

Cada aviso apunta a un ticket que esa persona puede ver (el mismo criterio que el
listado de tickets), unos están leídos y otros no, y sus fechas van de hace unos
minutos a hace unos días. Es idempotente: no repite un aviso que ya existe.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ..extensions import db
from ..models import Notificacion, NotificationEvent, Ticket, User
from ..security import STAFF_ROLES
from ..tickets.service import visible_tickets_condition
from .demo import DEMO_USERS

E = NotificationEvent

# (evento, título, mensaje, hace cuántos minutos, ¿ya leída?). En el mensaje, `{n}`
# es el número del ticket y `{title}` su título.
STAFF_SAMPLES = (
    (E.TICKET_ASIGNADO, "Ticket asignado", "Se te asignó el ticket #{n}: «{title}».", 25, False),
    (
        E.COMENTARIO_PUBLICO,
        "Respuesta del solicitante",
        "El solicitante respondió en el ticket #{n}.",
        90,
        False,
    ),
    (
        E.SLA_PROXIMO_A_VENCER,
        "SLA próximo a vencer",
        "El ticket #{n} consumió el 80 % de su tiempo de resolución.",
        180,
        False,
    ),
    (
        E.SLA_VENCIDO,
        "SLA vencido",
        "Venció el tiempo de resolución del ticket #{n}.",
        24 * 60,
        True,
    ),
    (
        E.TICKET_REABIERTO,
        "Ticket reabierto",
        "El solicitante reabrió el ticket #{n}: hay que retomar el trabajo.",
        2 * 24 * 60,
        True,
    ),
)

REQUESTER_SAMPLES = (
    (
        E.ESTADO_CAMBIADO,
        "Tu ticket cambió de estado",
        "El ticket #{n} ya lo está atendiendo el equipo de soporte.",
        30,
        False,
    ),
    (
        E.COMENTARIO_PUBLICO,
        "Nueva respuesta",
        "El equipo respondió en tu ticket #{n}.",
        120,
        False,
    ),
    (
        E.VALIDACION_PENDIENTE,
        "Revisa la solución",
        "El ticket #{n} fue resuelto: confirma si la solución te sirvió.",
        300,
        False,
    ),
    (E.TICKET_CERRADO, "Ticket cerrado", "Se cerró tu ticket #{n}.", 24 * 60, True),
    (
        E.TICKET_CREADO,
        "Ticket creado",
        "Registramos tu ticket #{n}: «{title}».",
        3 * 24 * 60,
        True,
    ),
)

# Cuánto después de crearse se marcan como leídas las que ya lo están.
READ_AFTER = timedelta(minutes=5)


class DemoNotificationsError(Exception):
    """No se pudieron cargar las notificaciones de demostración."""


@dataclass(frozen=True)
class DemoNotificationsResult:
    created: int
    # Quienes no tienen ningún ticket visible: no hay a qué apuntar un aviso.
    without_tickets: tuple[str, ...]


def seed_demo_notifications(
    usernames: list[str] | None = None,
    now: datetime | None = None,
) -> DemoNotificationsResult:
    """Crea las notificaciones de ejemplo y devuelve cuántas creó. Hace commit.

    Sin `usernames` las crea para el equipo de `seed-demo`; con ellos, para esas
    cuentas (por ejemplo, la del Administrador real, que `seed-demo` no crea). Lanza
    `DemoNotificationsError` si falta alguna cuenta.
    """
    now = now or datetime.now(UTC)
    users = _find_users(usernames)
    created = 0
    without_tickets = []

    for user in users:
        samples = STAFF_SAMPLES if _is_staff(user) else REQUESTER_SAMPLES
        tickets = _visible_tickets(user, len(samples))

        if not tickets:
            without_tickets.append(user.username)
            continue

        for index, sample in enumerate(samples):
            created += _create(user, tickets[index % len(tickets)], sample, now)

    db.session.commit()

    return DemoNotificationsResult(created, tuple(without_tickets))


def _find_users(usernames: list[str] | None) -> list[User]:
    if usernames is None:
        wanted = [demo.username for demo in DEMO_USERS]
    else:
        wanted = [name.strip().lower() for name in usernames if name.strip()]

    users = list(
        db.session.scalars(
            db.select(User)
            .where(db.func.lower(User.username).in_(wanted))
            .order_by(User.id)
        )
    )

    if usernames is None:
        if not users:
            raise DemoNotificationsError(
                "Faltan los usuarios de demostración. Ejecuta primero seed-demo."
            )

        return users

    missing = sorted(set(wanted) - {user.username.lower() for user in users})

    if missing or not users:
        raise DemoNotificationsError(
            "No existe el usuario: " + ", ".join(missing or ["(ninguno indicado)"])
        )

    return users


def _is_staff(user: User) -> bool:
    return user.rol.codigo in {role.value for role in STAFF_ROLES}


def _visible_tickets(user: User, limit: int) -> list[Ticket]:
    return list(
        db.session.scalars(
            db.select(Ticket)
            .where(visible_tickets_condition(user))
            .order_by(Ticket.id.desc())
            .limit(limit)
        )
    )


def _create(user: User, ticket: Ticket, sample: tuple, now: datetime) -> int:
    event, title, template, minutes_ago, read = sample
    message = template.format(n=ticket.public_id, title=ticket.titulo[:80])

    already = db.session.scalar(
        db.select(Notificacion.id).where(
            Notificacion.usuario_id == user.id,
            Notificacion.ticket_id == ticket.id,
            Notificacion.tipo_evento == event.value,
            Notificacion.mensaje == message,
        )
    )

    if already is not None:
        return 0

    created_at = now - timedelta(minutes=minutes_ago)
    db.session.add(
        Notificacion(
            usuario_id=user.id,
            ticket_id=ticket.id,
            tipo_evento=event.value,
            titulo=title,
            mensaje=message,
            leida=read,
            fecha_creacion=created_at,
            fecha_lectura=created_at + READ_AFTER if read else None,
        )
    )

    return 1
