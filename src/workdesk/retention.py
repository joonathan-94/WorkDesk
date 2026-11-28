"""La retención: cuánto tiempo se conserva lo que no forma parte de la historia de un ticket.

RF-110 a RF-112, RF-123, RNF-044, RNF-045 y RN-105 a RN-110; la regla completa es RN-183.

**Qué se puede borrar y qué no.** Cuatro políticas, cada una con su interruptor y su plazo en
la configuración (`settings.py`, pantalla «Retención»):

- las notificaciones **leídas** de más de N días (una sin leer no se borra nunca);
- los eventos de autenticación de más de N días (al menos 30: son la evidencia de un intento
  de intrusión reciente);
- el **archivo físico** de los adjuntos eliminados hace más de N días. La fila se conserva y
  anota cuándo se borró el archivo (`fecha_purga_archivo`): el historial del ticket la sigue
  nombrando, así que no queda ninguna referencia rota (RN-110);
- los respaldos más antiguos, conservando los N más recientes.

Los tickets, su historial y la auditoría se conservan siempre (RN-141): son la historia y la
evidencia de WorkDesk. Los logs ya tienen su propio límite, la rotación (`LOG_MAX_BYTES` y
`LOG_BACKUP_COUNT`). «Archivar» queda para después del MVP.

**Nada se borra sin una decisión explícita.** Las cuatro políticas empiezan apagadas (RN-106);
encenderlas, apagarlas o cambiar un plazo se audita como cualquier parámetro (RN-109), y cada
pasada que borra algo deja `RETENCION_APLICADA` con las cantidades (RF-111).

**Cómo se aplica.** El planificador la ejecuta en cada pasada, por tandas de
`BATCH_SIZE` y cada política en su propia transacción: una que falla no frena a las demás, y
un atraso grande se pone al día en unas pocas pasadas sin bloquear nada mucho tiempo. Medido:
sin nada que borrar, la consulta más cara (las notificaciones, sin un índice propio) tarda unos
30 ms con 300 000 avisos.

Las tablas de eventos rechazan borrados desde el ORM (`before_delete`): esta es la única
excepción, explícita, y por eso borra con sentencias de SQL de Core.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from flask import current_app
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import SQLAlchemyError

from . import settings
from .audit import AuditAction, record_admin_event
from .backups.package import backup_files, checksum_path
from .configuration import value_of
from .extensions import db
from .models import Attachment, AuthEvent, Notificacion
from .settings import BoolSetting, IntSetting
from .sla.periods import current_time
from .tickets.storage import absolute_path

logger = logging.getLogger(__name__)

BATCH_SIZE = 5000


@dataclass(frozen=True)
class Policy:
    key: str
    label: str
    description: str
    enabled: BoolSetting
    period: IntSetting
    unit: str
    unit_one: str

    def period_text(self, value: int) -> str:
        return f"{value} {self.unit_one if value == 1 else self.unit}"


NOTIFICATIONS = Policy(
    "notificaciones",
    "Notificaciones leídas",
    "Las notificaciones ya leídas. Una sin leer no se borra nunca.",
    settings.RETENTION_NOTIFICATIONS_ENABLED,
    settings.RETENTION_NOTIFICATIONS_DAYS,
    "días",
    "día",
)
AUTH_EVENTS = Policy(
    "accesos",
    "Registro de accesos",
    "Los inicios de sesión, los intentos fallidos y los cierres de sesión.",
    settings.RETENTION_AUTH_EVENTS_ENABLED,
    settings.RETENTION_AUTH_EVENTS_DAYS,
    "días",
    "día",
)
DELETED_FILES = Policy(
    "archivos",
    "Archivos de adjuntos eliminados",
    "El archivo en disco de un adjunto que alguien eliminó. El ticket conserva el registro.",
    settings.RETENTION_DELETED_FILES_ENABLED,
    settings.RETENTION_DELETED_FILES_DAYS,
    "días",
    "día",
)
BACKUPS = Policy(
    "respaldos",
    "Respaldos",
    "Los respaldos más antiguos de la carpeta de respaldos.",
    settings.RETENTION_BACKUPS_ENABLED,
    settings.RETENTION_BACKUPS_KEEP,
    "respaldos",
    "respaldo",
)

POLICIES = (NOTIFICATIONS, AUTH_EVENTS, DELETED_FILES, BACKUPS)


@dataclass
class RetentionResult:
    """Lo que borró una pasada, por política."""

    notifications: int = 0
    auth_events: int = 0
    files: int = 0
    backups: int = 0
    failures: int = 0

    @property
    def removed(self) -> int:
        return self.notifications + self.auth_events + self.files + self.backups


def _cutoff(policy: Policy, now: datetime) -> datetime:
    return now - timedelta(days=value_of(policy.period))


def _backups_folder() -> Path:
    return Path(current_app.config["BACKUPS_DIR"])


# --- Lo que vencería: las mismas condiciones que borran, para contar o para borrar -----------


def _expired_notifications(cutoff):
    table = Notificacion.__table__

    return table, (table.c.leida, table.c.fecha_creacion < cutoff)


def _expired_auth_events(cutoff):
    table = AuthEvent.__table__

    return table, (table.c.fecha_hora < cutoff,)


def _expired_files(cutoff):
    table = Attachment.__table__

    return table, (
        ~table.c.activo,
        table.c.fecha_purga_archivo.is_(None),
        table.c.fecha_eliminacion < cutoff,
    )


def _surplus_backups() -> list[Path]:
    """Los respaldos que sobran: todos menos los N más recientes."""
    return sorted(backup_files(_backups_folder()), reverse=True)[value_of(BACKUPS.period):]


# --- Borrar ---------------------------------------------------------------------------


def _delete_batch(table, conditions) -> int:
    """Borra una tanda de las filas que cumplen las condiciones, sin recorrer la tabla entera
    ni bloquearla mucho tiempo."""
    batch = select(table.c.id).where(*conditions).limit(BATCH_SIZE).scalar_subquery()

    return db.session.execute(delete(table).where(table.c.id.in_(batch))).rowcount


def _purge_files(cutoff, now) -> int:
    table, conditions = _expired_files(cutoff)
    # `SKIP LOCKED`: dos planificadores a la vez se reparten las filas en lugar de esperarse.
    rows = db.session.execute(
        select(table.c.id, table.c.ruta_archivo)
        .where(*conditions)
        .limit(BATCH_SIZE)
        .with_for_update(skip_locked=True)
    ).all()
    root = Path(current_app.config["UPLOADS_DIR"])

    for row in rows:
        # Primero el archivo y después la marca: si la transacción no se confirma, la pasada
        # siguiente vuelve a encontrar la fila y la marca (el archivo ya no está).
        try:
            absolute_path(root, row.ruta_archivo).unlink(missing_ok=True)
        except ValueError:
            # Una ruta que saldría de la carpeta de adjuntos no es de WorkDesk: no se toca.
            logger.warning("Retención: ruta de adjunto fuera de la carpeta (%s).", row.id)

    if rows:
        db.session.execute(
            update(table).where(table.c.id.in_([row.id for row in rows])).values(fecha_purga_archivo=now)
        )

    return len(rows)


def _purge_backups() -> int:
    surplus = _surplus_backups()

    for path in surplus:
        path.unlink(missing_ok=True)
        checksum_path(path).unlink(missing_ok=True)

    return len(surplus)


def _apply(policy: Policy, now: datetime) -> int:
    if policy is NOTIFICATIONS:
        return _delete_batch(*_expired_notifications(_cutoff(policy, now)))

    if policy is AUTH_EVENTS:
        return _delete_batch(*_expired_auth_events(_cutoff(policy, now)))

    if policy is DELETED_FILES:
        return _purge_files(_cutoff(policy, now), now)

    return _purge_backups()


_RESULT_FIELDS = {
    NOTIFICATIONS: "notifications",
    AUTH_EVENTS: "auth_events",
    DELETED_FILES: "files",
    BACKUPS: "backups",
}


def _record(result: RetentionResult) -> None:
    try:
        record_admin_event(
            AuditAction.RETENCION_APLICADA,
            actor=None,
            detail=f"{result.removed} elementos eliminados",
            new_value={
                "notificaciones": result.notifications,
                "accesos": result.auth_events,
                "archivos": result.files,
                "respaldos": result.backups,
            },
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        logger.exception("No se pudo registrar la retención en la auditoría.")


def run_retention(now: datetime | None = None) -> RetentionResult:
    """Aplica las políticas encendidas. Cada una en su propia transacción; una que falla se
    registra en el log y no frena a las demás."""
    now = now or current_time()
    result = RetentionResult()

    for policy in POLICIES:
        try:
            if not value_of(policy.enabled):
                continue

            removed = _apply(policy, now)
            db.session.commit()
        except (SQLAlchemyError, OSError):
            db.session.rollback()
            logger.exception("Falló la retención de %s.", policy.key)
            result.failures += 1
            continue

        setattr(result, _RESULT_FIELDS[policy], removed)

    if result.removed:
        _record(result)
        logger.info("Retención: %s elementos eliminados.", result.removed)

    return result


# --- La pantalla ------------------------------------------------------------------------


@dataclass(frozen=True)
class PolicyState:
    policy: Policy
    enabled: bool
    period: int
    # Cuántos se borrarían ahora con el plazo vigente (aunque esté apagada).
    pending: int


def _count(table, conditions) -> int:
    return db.session.scalar(select(func.count()).select_from(table).where(*conditions))


def retention_overview(now: datetime | None = None) -> list[PolicyState]:
    """Cada política con su estado y lo que borraría hoy: antes de encender una, el
    Administrador ve qué va a pasar."""
    now = now or current_time()
    pending = {
        NOTIFICATIONS: _count(*_expired_notifications(_cutoff(NOTIFICATIONS, now))),
        AUTH_EVENTS: _count(*_expired_auth_events(_cutoff(AUTH_EVENTS, now))),
        DELETED_FILES: _count(*_expired_files(_cutoff(DELETED_FILES, now))),
        BACKUPS: len(_surplus_backups()),
    }

    return [
        PolicyState(policy, value_of(policy.enabled), value_of(policy.period), pending[policy])
        for policy in POLICIES
    ]
