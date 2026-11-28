"""Restaurar un respaldo (`backup-restore`, RF-128, RNF-041, RNF-042, CU-046, RN-182).

Reemplaza la base y los adjuntos por los de un respaldo. Es la operación de más impacto de
WorkDesk, así que antes de tocar nada:

1. **Comprueba el respaldo entero** (`verify_backup`): huellas, nombres, volcado y firma.
   Uno firmado con otra clave solo se acepta si se pide expresamente; uno sin firma, nunca.
2. **Comprueba que encaja con el código:** su revisión de migraciones es la que espera el
   código o una anterior (que `db upgrade` pone al día), y su esquema es el que se usa hoy.
3. **Exige que nadie más esté conectado** (el servidor web y el planificador detenidos).
4. **Guarda lo actual** en un respaldo previo, salvo que se pida no hacerlo (por ejemplo,
   porque la base está dañada y `pg_dump` ya no puede leerla).

Después:

5. **Prepara los adjuntos** en una carpeta junto a la actual y el volcado en una temporal,
   comprobando otra vez cada huella contra el manifiesto ya verificado. Si alguien cambió el
   paquete entre la comprobación y este momento, se detiene sin haber tocado nada.
6. **Restaura la base en una sola transacción.** Los borrados de lo actual, el volcado (que
   `pg_restore` convierte en SQL) y el cierre de todas las sesiones (sube `token_version`
   de cada usuario) van en un único script que `psql` ejecuta con `--single-transaction` y
   `ON_ERROR_STOP`. Si cualquier sentencia falla, PostgreSQL deshace todo y la base queda
   como estaba. `lock_timeout` evita quedarse esperando a una conexión olvidada.
7. **Cambia la carpeta de adjuntos** por la preparada. La anterior se borra si hay respaldo
   previo (está dentro de él); si no, se conserva al lado.
8. **Lo registra en la auditoría** (`RESPALDO_RESTAURADO`), también si falla: en la base
   restaurada si se llegó a restaurar, en la de antes si no.
"""

import hashlib
import re
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from flask import current_app
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..audit import AuditAction, AuditResult
from ..extensions import db
from ..system.migrations import RevisionMatch, compare_revision
from ..tickets.storage import absolute_path
from .creation import BackupResult, create_backup, record_backup_event
from .package import (
    CHUNK_SIZE,
    DATABASE_MEMBER,
    RESTORE_TEMP_PREFIX,
    UPLOADS_MEMBER,
    Signature,
    file_sha256,
)
from .postgres import BackupError, connection_for, find_tool, run_tool, tool_environment
from .verification import SIGNATURE_PROBLEMS, verify_backup

# Esperar a que otra conexión suelte una tabla, como mucho esto; después, falla y no cambia
# nada (mejor que quedarse colgado con medio WorkDesk bloqueado).
LOCK_TIMEOUT = "30s"
STAGING_PREFIX = ".restaurando-adjuntos-"
PREVIOUS_PREFIX = ".adjuntos-anteriores-"
WORKSPACE_PREFIX = RESTORE_TEMP_PREFIX
MAX_ERROR_LENGTH = 500

# Las entradas del volcado que crean el esquema mismo: el esquema ya existe y se conserva
# (con sus permisos); solo se reemplaza lo que hay dentro.
_SCHEMA_ENTRY = re.compile(r"^\d+;\s+\d+\s+\d+\s+(?:SCHEMA|COMMENT - SCHEMA)\s")

# Todo lo que hay en el esquema actual, como sentencias `DROP` (con `%I`, PostgreSQL pone las
# comillas). Primero las vistas, después las tablas y por último las secuencias y los tipos.
_DROP_RELATIONS = text(
    """
    SELECT format('DROP %s IF EXISTS %I.%I CASCADE;',
                  CASE c.relkind WHEN 'v' THEN 'VIEW' WHEN 'm' THEN 'MATERIALIZED VIEW'
                                 WHEN 'S' THEN 'SEQUENCE' WHEN 'f' THEN 'FOREIGN TABLE'
                                 WHEN 'c' THEN 'TYPE' ELSE 'TABLE' END,
                  n.nspname, c.relname)
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = current_schema() AND c.relkind IN ('v', 'm', 'r', 'p', 'f', 'S', 'c')
    ORDER BY CASE c.relkind WHEN 'v' THEN 0 WHEN 'm' THEN 0 WHEN 'S' THEN 2 WHEN 'c' THEN 3
                            ELSE 1 END, c.relname
    """
)
_DROP_TYPES = text(
    """
    SELECT format('DROP TYPE IF EXISTS %I.%I CASCADE;', n.nspname, t.typname)
    FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE n.nspname = current_schema() AND t.typtype IN ('e', 'd')
    ORDER BY t.typname
    """
)
_DROP_ROUTINES = text(
    """
    SELECT format('DROP %s IF EXISTS %I.%I(%s) CASCADE;',
                  CASE p.prokind WHEN 'p' THEN 'PROCEDURE' WHEN 'a' THEN 'AGGREGATE'
                                 ELSE 'FUNCTION' END,
                  n.nspname, p.proname, pg_get_function_identity_arguments(p.oid))
    FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = current_schema()
    ORDER BY p.proname
    """
)
_OTHER_CONNECTIONS = text(
    """
    SELECT count(*) FROM pg_stat_activity
    WHERE datname = current_database() AND pid <> pg_backend_pid()
      AND backend_type = 'client backend'
    """
)


class RestoreRefused(BackupError):
    """El respaldo no se puede restaurar aquí. `problems` dice por qué; nada se tocó."""

    def __init__(self, problems: list[str]):
        super().__init__(" ".join(problems))
        self.problems = problems


@dataclass(frozen=True)
class CurrentContent:
    tickets: int
    users: int
    attachments: int


@dataclass(frozen=True)
class RestorePlan:
    """Lo que se va a restaurar y sobre qué, ya comprobado."""

    path: Path
    sha256: str
    manifest: dict
    signature: Signature
    revision: RevisionMatch
    database: str
    schema: str
    current: CurrentContent | None  # `None`: la base no tiene las tablas de WorkDesk
    connections: int

    @property
    def needs_upgrade(self) -> bool:
        return self.revision is RevisionMatch.ANTERIOR


@dataclass
class RestoreResult:
    plan: RestorePlan
    safety_backup: BackupResult | None
    attachments: int
    warnings: list[str] = field(default_factory=list)


def _close_own_connections() -> None:
    """Suelta las conexiones de este proceso, para que no cuenten como «otra persona
    conectada» ni retengan una tabla que hay que borrar."""
    db.session.remove()
    db.engine.dispose()


def other_connections() -> int:
    _close_own_connections()

    with db.engine.connect() as connection:
        count = connection.scalar(_OTHER_CONNECTIONS)

    _close_own_connections()

    return count


def _target() -> tuple[str, str, CurrentContent | None]:
    with db.engine.connect() as connection:
        database, schema = connection.execute(text("SELECT current_database(), current_schema()")).one()

        if not connection.scalar(text("SELECT to_regclass('tickets') IS NOT NULL")):
            return database, schema, None

        tickets, users, attachments = connection.execute(
            text("SELECT (SELECT count(*) FROM tickets), (SELECT count(*) FROM usuarios), (SELECT count(*) FROM archivos)")
        ).one()

    return database, schema, CurrentContent(tickets, users, attachments)


def _compatibility_problems(manifest: dict, schema: str) -> tuple[RevisionMatch, list[str]]:
    database = manifest.get("base_de_datos") or {}
    revision = compare_revision(database.get("revision_migracion"))
    problems = []

    if revision is RevisionMatch.SIN_REVISION:
        problems.append(
            "El respaldo no tiene revisión de migraciones: no se puede saber si encaja con este código."
        )
    elif revision is RevisionMatch.DESCONOCIDA:
        problems.append(
            f"El respaldo es de la revisión {database.get('revision_migracion')}, que este código no "
            "conoce: viene de una versión más nueva de WorkDesk. Actualiza el código antes de restaurarlo."
        )

    if database.get("esquema") != schema:
        problems.append(
            f"El respaldo es del esquema «{database.get('esquema')}» y WorkDesk usa «{schema}»: "
            "el volcado se restauraría en otro sitio."
        )

    return revision, problems


def plan_restore(path: Path, *, accept_other_key: bool = False) -> RestorePlan:
    """Comprueba que el respaldo se puede restaurar aquí. Lanza `RestoreRefused` si no."""
    config = current_app.config
    verification = verify_backup(
        path,
        secret_key=config["SECRET_KEY"],
        pg_restore=find_tool("pg_restore", config.get("PG_BIN_DIR")),
    )
    problems = list(verification.problems)

    if accept_other_key and verification.signature is Signature.OTRA_CLAVE:
        # El contenido se comprobó igual, archivo por archivo: lo que no se puede confirmar es
        # de dónde viene, y quien restaura dice que lo sabe.
        problems.remove(SIGNATURE_PROBLEMS[Signature.OTRA_CLAVE])

    if verification.manifest is None:
        raise RestoreRefused(problems)

    database, schema, current = _target()
    revision, compatibility = _compatibility_problems(verification.manifest, schema)
    problems += compatibility

    if problems:
        raise RestoreRefused(problems)

    return RestorePlan(
        path=path,
        sha256=file_sha256(path),
        manifest=verification.manifest,
        signature=verification.signature,
        revision=revision,
        database=database,
        schema=schema,
        current=current,
        connections=other_connections(),
    )


def _listed(manifest: dict) -> dict[str, dict]:
    return {entry["ruta"]: entry for entry in manifest["archivos"]}


def _extract(archive: zipfile.ZipFile, entry: dict, target: Path) -> None:
    """Copia un archivo del paquete comprobando de nuevo su huella mientras lo lee."""
    digest = hashlib.sha256()
    size = 0
    target.parent.mkdir(parents=True, exist_ok=True)

    with archive.open(entry["ruta"]) as source, target.open("xb") as writer:
        while chunk := source.read(CHUNK_SIZE):
            size += len(chunk)

            if size > entry["bytes"]:
                break

            digest.update(chunk)
            writer.write(chunk)

    if size != entry["bytes"] or digest.hexdigest() != entry["sha256"]:
        raise BackupError(
            f"{entry['ruta']} cambió desde que se comprobó el respaldo. No se restauró nada."
        )


def _stage(plan: RestorePlan, workspace: Path, staging: Path) -> tuple[Path, int]:
    """El volcado en `workspace` y los adjuntos en `staging`, comprobados contra el
    manifiesto ya verificado (y firmado)."""
    entries = _listed(plan.manifest)
    dump = workspace / "volcado.dump"
    staging.mkdir()
    attachments = 0

    with zipfile.ZipFile(plan.path) as archive:
        _extract(archive, entries[DATABASE_MEMBER], dump)

        for name, entry in entries.items():
            if name.startswith(f"{UPLOADS_MEMBER}/"):
                # `absolute_path` vuelve a impedir que un nombre salga de la carpeta.
                _extract(archive, entry, absolute_path(staging, name.removeprefix(f"{UPLOADS_MEMBER}/")))
                attachments += 1

    return dump, attachments


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def post_restore_sql(schema: str) -> str:
    """Lo que se ejecuta al final, en la misma transacción: todas las sesiones de antes dejan
    de valer (`token_version`), porque los permisos y las cuentas son ahora los del respaldo."""
    return f"UPDATE {_quote(schema)}.usuarios SET token_version = token_version + 1;\n"


def _write_script(plan: RestorePlan, dump: Path, workspace: Path) -> Path:
    """Un único script: borrar lo actual, crear lo del respaldo y cerrar las sesiones."""
    pg_restore = find_tool("pg_restore", current_app.config.get("PG_BIN_DIR"))
    listing = run_tool([pg_restore, "--list", str(dump)])
    toc = workspace / "contenido.list"
    toc.write_text(
        "".join(line + "\n" for line in listing.splitlines() if not _SCHEMA_ENTRY.match(line)),
        encoding="utf-8",
    )
    generated = workspace / "volcado.sql"
    run_tool(
        [pg_restore, f"--use-list={toc}", "--no-owner", "--no-privileges", f"--file={generated}", str(dump)]
    )

    with db.engine.connect() as connection:
        drops = [*connection.scalars(_DROP_RELATIONS), *connection.scalars(_DROP_TYPES), *connection.scalars(_DROP_ROUTINES)]

    _close_own_connections()
    script = workspace / "restaurar.sql"

    with script.open("w", encoding="utf-8", newline="\n") as writer:
        writer.write(f"SET lock_timeout = '{LOCK_TIMEOUT}';\n")
        writer.writelines(statement + "\n" for statement in drops)

        with generated.open(encoding="utf-8") as reader:
            shutil.copyfileobj(reader, writer, CHUNK_SIZE)

        writer.write(post_restore_sql(plan.schema))

    return script


def _run_script(script: Path) -> None:
    psql = find_tool("psql", current_app.config.get("PG_BIN_DIR"))
    connection = connection_for(current_app.config["SQLALCHEMY_DATABASE_URI"])

    with tool_environment(connection) as environment:
        run_tool(
            [
                psql,
                "--no-psqlrc",
                "--quiet",
                "--set=ON_ERROR_STOP=1",
                "--single-transaction",
                "--no-password",
                f"--dbname={connection.conninfo}",
                f"--file={script}",
            ],
            environment,
        )


def _swap_uploads(staging: Path, uploads: Path, previous: Path, *, keep_previous: bool) -> None:
    if uploads.exists():
        uploads.rename(previous)

    staging.rename(uploads)

    # Una carpeta vacía (una instalación nueva) no tiene nada que conservar.
    if not keep_previous or (previous.is_dir() and not any(previous.iterdir())):
        shutil.rmtree(previous, ignore_errors=True)


def _audit_values(plan: RestorePlan, safety: BackupResult | None, **extra) -> dict:
    content = plan.manifest.get("contenido") or {}

    return {
        "archivo": plan.path.name,
        "sha256": plan.sha256,
        "firma": plan.signature.value,
        "revision_migracion": (plan.manifest.get("base_de_datos") or {}).get("revision_migracion"),
        "respaldo_previo": None if safety is None else safety.path.name,
        "tickets": content.get("tickets"),
        "adjuntos": content.get("adjuntos_copiados"),
        **extra,
    }


def _safety_backup(plan: RestorePlan, make_it: bool, moment: datetime) -> BackupResult | None:
    if not make_it or plan.current is None:
        return None

    try:
        return create_backup(now=moment)
    except BackupError as error:
        raise BackupError(
            f"No se pudo crear el respaldo de lo actual, así que no se restauró nada ({error}). "
            "Si la base está dañada y no se puede respaldar, usa --skip-safety-backup."
        ) from error


def restore_backup(
    plan: RestorePlan,
    *,
    safety_backup: bool = True,
    ignore_connections: bool = False,
    now: datetime | None = None,
) -> RestoreResult:
    """Restaura un respaldo ya comprobado (`plan_restore`). Lanza `BackupError` si no se pudo;
    hasta que la transacción de la base se confirma, no queda nada cambiado."""
    config = current_app.config
    moment = (now or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    stamp = f"{moment:%Y%m%d-%H%M%S}Z"

    if not ignore_connections and (connections := other_connections()):
        raise RestoreRefused(
            [
                (
                    f"Hay {connections} conexiones más a la base de datos. Detén el servidor web y "
                    "el planificador antes de restaurar (o usa --ignore-connections si sabes de qué son)."
                )
            ]
        )

    safety = _safety_backup(plan, safety_backup, moment)
    uploads = Path(config["UPLOADS_DIR"]).resolve()
    staging = uploads.with_name(f"{STAGING_PREFIX}{stamp}")
    workspace = Path(tempfile.mkdtemp(prefix=WORKSPACE_PREFIX, dir=config["BACKUPS_DIR"]))

    try:
        dump, attachments = _stage(plan, workspace, staging)
        _run_script(_write_script(plan, dump, workspace))
    except (BackupError, OSError, SQLAlchemyError) as error:
        shutil.rmtree(staging, ignore_errors=True)
        message = str(error) if isinstance(error, BackupError) else f"No se pudo preparar la restauración: {error}"
        record_backup_event(
            AuditAction.RESPALDO_RESTAURADO,
            AuditResult.FALLIDO,
            plan.path.name,
            _audit_values(plan, safety, error=message[:MAX_ERROR_LENGTH]),
        )
        raise BackupError(f"No se restauró nada: la base y los adjuntos siguen como estaban. {message}") from error
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

    result = RestoreResult(plan=plan, safety_backup=safety, attachments=attachments)
    previous = uploads.with_name(f"{PREVIOUS_PREFIX}{stamp}")
    swapped = True

    try:
        _swap_uploads(staging, uploads, previous, keep_previous=safety is None)
    except OSError as error:
        swapped = False
        result.warnings.append(
            f"La base se restauró, pero no se pudo cambiar la carpeta de adjuntos ({error.strerror or error}). "
            f"Los adjuntos del respaldo están en {staging}: detén lo que use {uploads} y renómbrala."
        )

    if swapped and safety is None and previous.exists():
        result.warnings.append(f"No se creó un respaldo previo: los adjuntos que había quedaron en {previous}.")

    recorded = record_backup_event(
        AuditAction.RESPALDO_RESTAURADO,
        AuditResult.EXITOSO if swapped else AuditResult.FALLIDO,
        plan.path.name,
        _audit_values(
            plan,
            safety,
            adjuntos_restaurados=attachments if swapped else 0,
            actualizar_migraciones=plan.needs_upgrade,
        ),
    )
    current_app.logger.warning("Respaldo restaurado: %s.", plan.path)

    if not recorded:
        result.warnings.append("La restauración se hizo, pero no se pudo registrar en la auditoría.")

    return result
