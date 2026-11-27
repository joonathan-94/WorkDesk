"""Crear un respaldo (`backup-create`, RF-127, RNF-038 a RNF-040 y RNF-043).

**Una sola foto.** El volcado y la lista de adjuntos salen del mismo instante de la base:
se abre una transacción de solo lectura `REPEATABLE READ`, se exporta su foto
(`pg_export_snapshot`) y `pg_dump` vuelca exactamente esa foto (`--snapshot`). En la misma
transacción se leen las rutas de los adjuntos, así que el paquete trae justo los archivos que
el volcado referencia: ni uno subido un segundo después ni un resto de `_tmp`. Por eso no hace
falta un modo de mantenimiento: la aplicación sigue funcionando mientras se respalda.

**Lo que la copia descubre.** Cada adjunto se copia calculando su SHA-256, y la base guarda el
que tenía al subirse: si no coinciden, el archivo se dañó o se cambió en el disco, y se avisa.
Se avisa también de un adjunto activo cuyo archivo no está. El respaldo se crea igual (no
copiar el resto no arreglaría nada), con esos avisos en su manifiesto.

**Nada a medias.** Todo se escribe en una carpeta temporal dentro de la carpeta de respaldos y
el paquete solo toma su nombre final cuando está completo, con su huella al lado. Un error
borra la carpeta temporal; un proceso cortado la deja (`backup-list` la señala).

Dos respaldos a la vez de la misma instalación no tienen sentido: un bloqueo consultivo de
la transacción de la foto, sobre el esquema que se respalda, hace que el segundo se rechace
en lugar de esperar.
"""

import contextlib
import getpass
import hashlib
import os
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from flask import current_app
from sqlalchemy import func, literal, select, text
from sqlalchemy.exc import SQLAlchemyError

from ..audit import AuditAction, AuditResult, record_admin_event
from ..extensions import db
from ..models import Attachment, Ticket, User
from ..tickets.storage import absolute_path
from .package import (
    CHUNK_SIZE,
    DATABASE_MEMBER,
    FORMAT,
    MANIFEST_MEMBER,
    SIGNATURE_MEMBER,
    TEMP_PREFIX,
    backup_name,
    checksum_line,
    checksum_path,
    encode_manifest,
    file_sha256,
    manifest_warnings,
    sign,
    upload_member,
)
from .postgres import (
    BackupError,
    connection_for,
    find_tool,
    run_tool,
    tool_environment,
    tool_version,
)

# Distinto de los demás bloqueos consultivos de WorkDesk (configuración y login por IP).
_BACKUP_LOCK_PREFIX = "workdesk-respaldo:"
# Un `pg_dump` que no consigue sus bloqueos de lectura (por ejemplo, durante una migración)
# falla en lugar de quedarse esperando y, mientras espera, frenar a la aplicación.
LOCK_WAIT_TIMEOUT = "60s"
MAX_ERROR_LENGTH = 500


@dataclass(frozen=True)
class _AttachmentRow:
    path: str
    active: bool
    size: int
    sha256: str
    mime_type: str


@dataclass(frozen=True)
class _Snapshot:
    """Lo que se lee de la base en el mismo instante que vuelca `pg_dump`."""

    id: str
    database: str
    schema: str
    server_version: str
    revision: str | None
    tickets: int
    users: int
    attachments: list[_AttachmentRow]


@dataclass(frozen=True)
class BackupResult:
    path: Path
    size: int
    sha256: str
    manifest: dict
    warnings: list[str]


def _count(connection, model) -> int:
    return connection.scalar(select(func.count()).select_from(model.__table__))


def _revision(connection) -> str | None:
    """La revisión de Alembic, o `None` si la base no se creó con las migraciones."""
    if connection.scalar(text("SELECT to_regclass('alembic_version') IS NOT NULL")):
        revisions = connection.scalars(text("SELECT version_num FROM alembic_version")).all()

        return ",".join(sorted(revisions)) or None

    return None


def backup_lock_key():
    """La clave del bloqueo de los respaldos: una por esquema. Los bloqueos consultivos valen
    para toda la base, y dos instalaciones en esquemas distintos no deben estorbarse."""
    return func.hashtext(literal(_BACKUP_LOCK_PREFIX) + func.current_schema())


@contextlib.contextmanager
def _snapshot():
    """Abre la transacción de la foto y la mantiene abierta mientras `pg_dump` la usa."""
    with db.engine.connect() as connection:
        connection = connection.execution_options(
            isolation_level="REPEATABLE READ", postgresql_readonly=True
        )

        with connection.begin():
            if not connection.scalar(select(func.pg_try_advisory_xact_lock(backup_lock_key()))):
                raise BackupError("Ya hay un respaldo en curso de esta base de datos.")

            database, schema, server_version = connection.execute(
                text("SELECT current_database(), current_schema(), current_setting('server_version')")
            ).one()
            table = Attachment.__table__
            rows = connection.execute(
                select(
                    table.c.ruta_archivo,
                    table.c.activo,
                    table.c.tamano_bytes,
                    table.c.hash,
                    table.c.mime_type,
                )
                .order_by(table.c.id)
            ).all()

            yield _Snapshot(
                id=connection.scalar(text("SELECT pg_export_snapshot()")),
                database=database,
                schema=schema,
                server_version=server_version,
                revision=_revision(connection),
                tickets=_count(connection, Ticket),
                users=_count(connection, User),
                attachments=[_AttachmentRow(*row) for row in rows],
            )


def _dump(pg_dump: str, snapshot: _Snapshot, target: Path) -> None:
    connection = connection_for(current_app.config["SQLALCHEMY_DATABASE_URI"])

    with tool_environment(connection) as environment:
        run_tool(
            [
                pg_dump,
                f"--dbname={connection.conninfo}",
                "--format=custom",
                f"--schema={snapshot.schema}",
                f"--snapshot={snapshot.id}",
                f"--lock-wait-timeout={LOCK_WAIT_TIMEOUT}",
                "--no-password",
                f"--file={target}",
            ],
            environment,
        )


def _add_file(archive: zipfile.ZipFile, source: Path, member: str, *, compress: bool, moment) -> dict:
    """Copia un archivo al paquete calculando su huella mientras lo lee (una sola pasada)."""
    info = zipfile.ZipInfo(member, date_time=moment.timetuple()[:6])
    info.compress_type = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
    digest = hashlib.sha256()
    size = 0

    with source.open("rb") as reader, archive.open(info, "w", force_zip64=True) as writer:
        for chunk in iter(lambda: reader.read(CHUNK_SIZE), b""):
            digest.update(chunk)
            writer.write(chunk)
            size += len(chunk)

    return {"ruta": member, "bytes": size, "sha256": digest.hexdigest()}


def _copy_attachments(archive, snapshot: _Snapshot, uploads_root: Path, moment):
    """Los adjuntos de la foto: los copiados, los que faltan y los alterados."""
    files, missing, altered = [], [], []

    for row in snapshot.attachments:
        try:
            source = absolute_path(uploads_root, row.path)
        except ValueError:
            # Una ruta que saldría de la carpeta de adjuntos no es de WorkDesk: no se copia.
            source = None

        if source is None or not source.is_file():
            # Un adjunto eliminado puede no tener ya su archivo (la retención lo borra): solo
            # se avisa de los que se siguen viendo en los tickets.
            if row.active:
                missing.append(row.path)
            continue

        # Solo se comprime el texto (un registro baja al 0,3 %). Imágenes, PDF y documentos
        # de Office ya vienen comprimidos: medido, comprimirlos tarda 30 veces más y no
        # ahorra nada.
        compress = row.mime_type.startswith("text/")
        entry = _add_file(archive, source, upload_member(row.path), compress=compress, moment=moment)
        files.append(entry)

        if entry["sha256"] != row.sha256 or entry["bytes"] != row.size:
            altered.append(row.path)

    return files, missing, altered


def _write_package(target: Path, dump: Path, snapshot: _Snapshot, pg_dump_version: str, moment) -> dict:
    config = current_app.config

    with zipfile.ZipFile(target, "x", allowZip64=True) as archive:
        # El volcado ya viene comprimido: guardarlo tal cual ahorra tiempo sin perder espacio.
        database = _add_file(archive, dump, DATABASE_MEMBER, compress=False, moment=moment)
        uploads, missing, altered = _copy_attachments(
            archive, snapshot, Path(config["UPLOADS_DIR"]), moment
        )
        manifest = {
            "formato": FORMAT,
            "creado_en": moment.astimezone(UTC).isoformat(timespec="seconds"),
            "base_de_datos": {
                "nombre": snapshot.database,
                "esquema": snapshot.schema,
                "version_servidor": snapshot.server_version,
                "version_pg_dump": pg_dump_version,
                "revision_migracion": snapshot.revision,
            },
            "contenido": {
                "tickets": snapshot.tickets,
                "usuarios": snapshot.users,
                "adjuntos": len(snapshot.attachments),
                "adjuntos_copiados": len(uploads),
                "bytes_adjuntos": sum(entry["bytes"] for entry in uploads),
            },
            "avisos": {"adjuntos_faltantes": missing, "adjuntos_alterados": altered},
            "archivos": [database, *uploads],
        }
        raw = encode_manifest(manifest)
        archive.writestr(MANIFEST_MEMBER, raw, compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr(SIGNATURE_MEMBER, sign(raw, config["SECRET_KEY"]))

    return manifest


def _create(moment: datetime) -> BackupResult:
    config = current_app.config
    folder = Path(config["BACKUPS_DIR"])
    pg_dump = find_tool("pg_dump", config.get("PG_BIN_DIR"))
    target = folder / backup_name(moment)
    folder.mkdir(parents=True, exist_ok=True)

    if target.exists() or checksum_path(target).exists():
        raise BackupError(f"Ya existe un respaldo llamado {target.name}.")

    workspace = Path(tempfile.mkdtemp(prefix=TEMP_PREFIX, dir=folder))

    try:
        dump = workspace / DATABASE_MEMBER

        with _snapshot() as snapshot:
            _dump(pg_dump, snapshot, dump)

        partial = workspace / target.name
        manifest = _write_package(partial, dump, snapshot, tool_version(pg_dump), moment)
        digest = file_sha256(partial)
        os.replace(partial, target)
        checksum_path(target).write_text(checksum_line(digest, target), encoding="ascii")
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

    if os.name != "nt":
        # Un respaldo trae la base entera: solo lo lee el usuario que lo creó (en Windows, la
        # carpeta hereda los permisos de `instance`).
        target.chmod(0o600)

    return BackupResult(target, target.stat().st_size, digest, manifest, manifest_warnings(manifest))


def _system_user() -> str | None:
    """La cuenta del sistema que ejecuta el comando: es quien respalda (RNF-042)."""
    try:
        return getpass.getuser()
    except (KeyError, OSError):
        return None


def _record(result: AuditResult, detail: str, values: dict) -> bool:
    """Registra el intento en la auditoría. Devuelve si se pudo (la base puede ser
    justamente lo que falló)."""
    try:
        record_admin_event(
            AuditAction.RESPALDO_CREADO,
            actor=None,
            entity_type="respaldo",
            detail=detail,
            new_value={**values, "usuario_sistema": _system_user()},
            result=result,
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("No se pudo registrar el respaldo en la auditoría.")
        return False

    return True


def create_backup(*, now: datetime | None = None) -> BackupResult:
    """Crea un respaldo en `BACKUPS_DIR` y lo registra en la auditoría.

    Lanza `BackupError` si no se pudo; el intento fallido también queda en la auditoría.
    """
    moment = (now or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    name = backup_name(moment)

    try:
        result = _create(moment)
    except (BackupError, OSError, SQLAlchemyError) as error:
        db.session.rollback()

        if isinstance(error, BackupError):
            message = str(error)
        elif isinstance(error, OSError):
            message = f"No se pudo escribir el respaldo: {error.strerror or error}"
        else:
            current_app.logger.exception("Fallo de la base de datos al crear un respaldo.")
            message = "No se pudo leer la base de datos (el detalle está en el log)."

        _record(AuditResult.FALLIDO, name, {"archivo": name, "error": message[:MAX_ERROR_LENGTH]})
        raise BackupError(message) from error

    content = result.manifest["contenido"]
    notices = result.manifest["avisos"]
    recorded = _record(
        AuditResult.EXITOSO,
        name,
        {
            "archivo": name,
            "bytes": result.size,
            "sha256": result.sha256,
            "tickets": content["tickets"],
            "adjuntos": content["adjuntos_copiados"],
            "adjuntos_faltantes": len(notices["adjuntos_faltantes"]),
            "adjuntos_alterados": len(notices["adjuntos_alterados"]),
        },
    )
    current_app.logger.info("Respaldo creado: %s (%s bytes).", result.path, result.size)

    if not recorded:
        result.warnings.append("El respaldo se creó, pero no se pudo registrar en la auditoría.")

    return result
