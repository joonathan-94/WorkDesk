"""Notificaciones internas (docs/09, 22; docs/06, RN-93 a RN-97; docs/04, RF-084 a RF-086).

Un aviso para un usuario sobre algo que pasó en el sistema. Estas son las reglas:

- **Son siempre internas.** WorkDesk no envía correo ni mensajes externos: el
  usuario las ve en el centro de notificaciones y en el contador de la barra
  superior.
- **El contenido no se reescribe.** Solo evoluciona su lectura: marcarla como leída
  fija la *primera* lectura y no la cambia si se vuelve a marcar. Leer no elimina.
- **Cada quien ve solo las suyas.** Todas las consultas filtran por el usuario; las
  de otra persona no existen para quien las pide.
- **Quien genera un aviso decide a quién.** `notify` no comprueba si el destinatario
  puede ver el ticket ni si el evento es interno: esa decisión es de quien la
  genera (entregas 6 y 8), con las mismas reglas de visibilidad del historial. Lo
  único que impone es que el destinatario esté activo.

`notify` y `notify_many` no hacen commit: el aviso se confirma o se revierte junto
con la operación que lo provoca, y el commit lo realiza quien llama.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import func, update
from sqlalchemy.orm import joinedload

from ..cleaning import blank_to_none
from ..extensions import db
from ..models import Notificacion, NotificationEvent, Ticket, User

PAGE_SIZE = 20

MAX_TITLE_LENGTH = 150
MAX_MESSAGE_LENGTH = 1000

VIEW_ALL = "todas"
VIEW_UNREAD = "no-leidas"
VALID_VIEWS = frozenset({VIEW_ALL, VIEW_UNREAD})


class NotificationRuleError(ValueError):
    """Una regla impide crear la notificación. El mensaje es para quien programa."""


@dataclass(frozen=True)
class NotificationCounts:
    """Cuántas notificaciones tiene un usuario y cuántas sin leer."""

    total: int
    unread: int


# --- Crear ---------------------------------------------------------------------


def notify(
    recipient: User,
    event: NotificationEvent | str,
    *,
    message: str,
    title: str | None = None,
    ticket: Ticket | None = None,
) -> Notificacion | None:
    """Crea una notificación para `recipient`, o devuelve None si está inactivo.

    `event` debe pertenecer al vocabulario (`NotificationEvent`). El mensaje es
    obligatorio (hasta `MAX_MESSAGE_LENGTH` caracteres); el título y el ticket,
    opcionales (sin ticket es un aviso general). Lanza `NotificationRuleError` si
    algo no es válido, sin dejar nada pendiente.
    """
    try:
        event = NotificationEvent(event)
    except ValueError as error:
        raise NotificationRuleError(
            f"«{event}» no es un evento de notificación."
        ) from error

    message = (message or "").strip()
    title = blank_to_none(title)

    if not message:
        raise NotificationRuleError("La notificación necesita un mensaje.")

    if len(message) > MAX_MESSAGE_LENGTH:
        raise NotificationRuleError(
            f"El mensaje no puede superar los {MAX_MESSAGE_LENGTH} caracteres."
        )

    if title is not None and len(title) > MAX_TITLE_LENGTH:
        raise NotificationRuleError(
            f"El título no puede superar los {MAX_TITLE_LENGTH} caracteres."
        )

    # Un usuario desactivado ya no puede entrar a leerla.
    if not recipient.is_active:
        return None

    notification = Notificacion(
        usuario_id=recipient.id,
        ticket_id=None if ticket is None else ticket.id,
        tipo_evento=event.value,
        titulo=title,
        mensaje=message,
    )
    db.session.add(notification)
    db.session.flush()

    return notification


def notify_many(
    recipients: Iterable[User],
    event: NotificationEvent | str,
    *,
    message: str,
    title: str | None = None,
    ticket: Ticket | None = None,
) -> list[Notificacion]:
    """Notifica a varias personas, una sola vez a cada una (sin repetidos) y sin
    contar a los inactivos. Devuelve las notificaciones creadas."""
    created = []
    seen: set[int] = set()

    for recipient in recipients:
        if recipient.id in seen:
            continue

        seen.add(recipient.id)
        notification = notify(
            recipient, event, message=message, title=title, ticket=ticket
        )

        if notification is not None:
            created.append(notification)

    return created


# --- Consultar -----------------------------------------------------------------


def count_unread(user: User) -> int:
    """Cuántas notificaciones sin leer tiene el usuario (el contador de la campana)."""
    return db.session.scalar(
        db.select(func.count(Notificacion.id)).where(
            Notificacion.usuario_id == user.id,
            Notificacion.leida.is_(False),
        )
    )


def count_notifications(user: User) -> NotificationCounts:
    """El total y las no leídas del usuario, en una sola consulta."""
    total, unread = db.session.execute(
        db.select(
            func.count(Notificacion.id),
            func.count(Notificacion.id).filter(Notificacion.leida.is_(False)),
        ).where(Notificacion.usuario_id == user.id)
    ).one()

    return NotificationCounts(total=total, unread=unread)


def list_notifications(
    user: User, *, view: str = VIEW_ALL, page: int = 1, per_page: int = PAGE_SIZE
):
    """Una página de las notificaciones del usuario, de la más reciente a la más antigua.

    `view` es `VIEW_ALL` o `VIEW_UNREAD` (cualquier otro valor se trata como todas).
    El ticket se carga con la misma consulta: mostrar una fila no lanza más.
    """
    statement = (
        db.select(Notificacion)
        .options(joinedload(Notificacion.ticket))
        .where(Notificacion.usuario_id == user.id)
        .order_by(Notificacion.fecha_creacion.desc(), Notificacion.id.desc())
    )

    if view == VIEW_UNREAD:
        statement = statement.where(Notificacion.leida.is_(False))

    return db.paginate(
        statement,
        page=page,
        per_page=per_page,
        max_per_page=per_page,
        error_out=False,
    )


def get_notification(user: User, notification_id: int) -> Notificacion | None:
    """La notificación, solo si es del usuario: la de otra persona no existe."""
    return db.session.scalar(
        db.select(Notificacion)
        .where(
            Notificacion.id == notification_id,
            Notificacion.usuario_id == user.id,
        )
        .execution_options(populate_existing=True)
    )


# --- Estado de lectura -------------------------------------------------------------


def mark_as_read(user: User, notification_id: int) -> Notificacion | None:
    """Marca la notificación como leída y la devuelve; None si no es del usuario.

    Es idempotente y se hace en un solo `UPDATE`: si ya estaba leída no cambia nada
    (la fecha de lectura sigue siendo la de la primera vez) y, si dos pestañas la
    marcan a la vez, una sola lo hace.
    """
    db.session.execute(
        update(Notificacion)
        .where(
            Notificacion.id == notification_id,
            Notificacion.usuario_id == user.id,
            Notificacion.leida.is_(False),
        )
        .values(leida=True, fecha_lectura=func.now())
        .execution_options(synchronize_session=False)
    )

    return get_notification(user, notification_id)


def mark_all_as_read(user: User) -> int:
    """Marca como leídas todas las no leídas del usuario. Devuelve cuántas."""
    result = db.session.execute(
        update(Notificacion)
        .where(
            Notificacion.usuario_id == user.id,
            Notificacion.leida.is_(False),
        )
        .values(leida=True, fecha_lectura=func.now())
        .execution_options(synchronize_session=False)
    )

    return result.rowcount
