"""El formato de un respaldo: qué contiene, cómo se firma y cómo se lee sin restaurarlo.

Un respaldo es un `.zip` con este contenido (docs/10, sección 112):

    workdesk-respaldo-20261127-183522Z.zip
    ├── database.dump        el volcado de `pg_dump` (formato custom, ya comprimido)
    ├── uploads/AAAA/MM/...  los adjuntos que el volcado referencia
    ├── manifest.json        qué hay, cuánto pesa y su SHA-256, archivo por archivo
    └── manifest.sig         la firma del manifiesto

Y a su lado, `<nombre>.zip.sha256`: la huella del paquete entero, en el formato de
`sha256sum`, para comprobarlo también sin WorkDesk (`Get-FileHash` o `sha256sum`).

**Integridad y autenticidad.** Las huellas detectan un archivo dañado, pero cualquiera
puede recalcularlas después de cambiar algo. La firma (HMAC-SHA256 del manifiesto con una
clave derivada de `SECRET_KEY`) solo la puede producir esta instalación: un respaldo
alterado, o fabricado por quien pudo escribir en la carpeta de respaldos, no pasa la
comprobación. Como el manifiesto lleva la huella de cada archivo, firmarlo firma todo.
Restaurar un respaldo trae usuarios y permisos, así que importa de dónde viene.

No hay tabla de respaldos (`docs/12`, fase 8): la carpeta con sus manifiestos es la fuente
de verdad, y la auditoría registra cada creación.
"""

import hashlib
import hmac
import json
import re
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath

FORMAT = "workdesk-respaldo/1"
PREFIX = "workdesk-respaldo-"
EXTENSION = ".zip"
CHECKSUM_SUFFIX = ".sha256"
# Lo que deja un respaldo o una restauración a medias (un proceso cortado): se puede borrar.
TEMP_PREFIX = ".tmp-respaldo-"
RESTORE_TEMP_PREFIX = ".tmp-restauracion-"

DATABASE_MEMBER = "database.dump"
UPLOADS_MEMBER = "uploads"
MANIFEST_MEMBER = "manifest.json"
SIGNATURE_MEMBER = "manifest.sig"
CONTROL_MEMBERS = frozenset({MANIFEST_MEMBER, SIGNATURE_MEMBER})

CHUNK_SIZE = 1024 * 1024
# Un manifiesto lista unos cien bytes por adjunto: 64 MB son cientos de miles de archivos.
# El tope impide que un respaldo fabricado agote la memoria al leerlo.
MAX_MANIFEST_BYTES = 64 * 1024 * 1024
MAX_SIGNATURE_BYTES = 1024

# El nombre que pone `backup-create`: la hora en UTC (la «Z»), para que dos respaldos nunca
# se confundan en un cambio de horario.
NAME_PATTERN = re.compile(r"^workdesk-respaldo-\d{8}-\d{6}Z\.zip$")

_SIGNATURE_CONTEXT = b"workdesk/firma-de-respaldos/v1\x00"


class Signature(StrEnum):
    """De quién es la firma de un respaldo."""

    VALIDA = "VALIDA"  # la produjo esta instalación (la misma SECRET_KEY)
    OTRA_CLAVE = "OTRA_CLAVE"  # otra clave, o el manifiesto se modificó después
    AUSENTE = "AUSENTE"  # no tiene firma


SIGNATURE_LABELS = {
    Signature.VALIDA: "de esta instalación",
    Signature.OTRA_CLAVE: "no corresponde (otra SECRET_KEY o un manifiesto modificado)",
    Signature.AUSENTE: "no tiene",
}


def backup_name(moment: datetime) -> str:
    return f"{PREFIX}{moment.astimezone(UTC):%Y%m%d-%H%M%S}Z{EXTENSION}"


def checksum_path(package: Path) -> Path:
    return package.with_name(package.name + CHECKSUM_SUFFIX)


def signing_key(secret_key: str) -> bytes:
    """La clave de las firmas. Se deriva de `SECRET_KEY` con un contexto propio: la firma de
    un respaldo nunca sirve como firma de una cookie de sesión, ni al revés."""
    return hashlib.sha256(_SIGNATURE_CONTEXT + secret_key.encode("utf-8")).digest()


def sign(manifest: bytes, secret_key: str) -> str:
    return hmac.new(signing_key(secret_key), manifest, hashlib.sha256).hexdigest()


def signature_status(manifest: bytes, signature: bytes | None, secret_key: str) -> Signature:
    if signature is None:
        return Signature.AUSENTE

    expected = sign(manifest, secret_key).encode("ascii")

    return Signature.VALIDA if hmac.compare_digest(expected, signature.strip()) else Signature.OTRA_CLAVE


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)

    return digest.hexdigest()


def checksum_line(digest: str, package: Path) -> str:
    """Una línea como las de `sha256sum`: la huella, dos espacios y el nombre."""
    return f"{digest}  {package.name}\n"


def read_checksum(package: Path) -> str | None:
    """La huella guardada junto al paquete, o `None` si no está o no se entiende."""
    path = checksum_path(package)

    try:
        text = path.read_text(encoding="ascii")[:256]
    except (OSError, UnicodeDecodeError):
        return None

    match = re.match(r"^([0-9a-f]{64})\s", text)

    return match.group(1) if match else None


def unsafe_member_name(name: str) -> bool:
    """Si un nombre dentro del `.zip` podría escribir fuera de su carpeta al extraerlo
    («zip slip»): absoluto, con `..`, con una unidad de Windows o con barras invertidas."""
    path = PurePosixPath(name)

    return (
        not name
        or "\\" in name
        or ":" in name
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in name.split("/"))
    )


def upload_member(relative_path: str) -> str:
    return f"{UPLOADS_MEMBER}/{PurePosixPath(relative_path).as_posix()}"


def encode_manifest(manifest: dict) -> bytes:
    return json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")


def manifest_warnings(manifest: dict) -> list[str]:
    """Los avisos que dejó la creación en el manifiesto, como los lee una persona."""
    notices = manifest.get("avisos") or {}
    lines = [
        f"El adjunto {path} estaba activo pero su archivo no estaba en el disco."
        for path in notices.get("adjuntos_faltantes") or []
    ]
    lines += [
        f"El archivo del adjunto {path} no coincidía con la huella que se guardó al subirlo "
        "(se dañó o se modificó en el disco)."
        for path in notices.get("adjuntos_alterados") or []
    ]

    if (manifest.get("base_de_datos") or {}).get("revision_migracion") is None:
        lines.append(
            "La base no tiene revisión de migraciones (alembic_version): no se creó con "
            "«db upgrade», así que al restaurarla no se podrá comprobar que coincide con el código."
        )

    return lines


def _read_capped(archive: zipfile.ZipFile, name: str, limit: int) -> bytes | None:
    """El contenido de un miembro pequeño, o `None` si no está o pasa del tope."""
    try:
        info = archive.getinfo(name)
    except KeyError:
        return None

    if info.file_size > limit:
        return None

    with archive.open(info) as handle:
        data = handle.read(limit + 1)

    return None if len(data) > limit else data


@dataclass(frozen=True)
class ManifestRead:
    """Lo que se lee de un respaldo sin comprobar sus archivos: rápido, para listarlos."""

    manifest: dict | None
    raw: bytes | None
    signature: Signature
    problem: str | None


def read_manifest(archive: zipfile.ZipFile, secret_key: str) -> ManifestRead:
    raw = _read_capped(archive, MANIFEST_MEMBER, MAX_MANIFEST_BYTES)

    if raw is None:
        return ManifestRead(None, None, Signature.AUSENTE, "No tiene manifiesto, o es demasiado grande.")

    signature = signature_status(
        raw, _read_capped(archive, SIGNATURE_MEMBER, MAX_SIGNATURE_BYTES), secret_key
    )

    try:
        manifest = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return ManifestRead(None, raw, signature, "El manifiesto no se puede leer.")

    if not isinstance(manifest, dict) or manifest.get("formato") != FORMAT:
        return ManifestRead(None, raw, signature, "El manifiesto no es de un respaldo de WorkDesk.")

    return ManifestRead(manifest, raw, signature, None)


def parse_moment(text) -> datetime | None:
    try:
        moment = datetime.fromisoformat(text)
    except (TypeError, ValueError):
        return None

    return moment if moment.tzinfo is not None else None


@dataclass(frozen=True)
class BackupInfo:
    """Un respaldo de la carpeta, tal como lo muestra `backup-list`."""

    path: Path
    size: int
    created_at: datetime | None
    signature: Signature
    has_checksum: bool
    manifest: dict | None
    problem: str | None

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def content(self) -> dict:
        return (self.manifest or {}).get("contenido", {})

    @property
    def revision(self) -> str | None:
        return (self.manifest or {}).get("base_de_datos", {}).get("revision_migracion")


def describe(path: Path, secret_key: str) -> BackupInfo:
    size = path.stat().st_size

    try:
        with zipfile.ZipFile(path) as archive:
            read = read_manifest(archive, secret_key)
    except (zipfile.BadZipFile, OSError):
        return BackupInfo(path, size, None, Signature.AUSENTE, False, None, "No es un .zip válido.")

    created_at = parse_moment((read.manifest or {}).get("creado_en"))

    return BackupInfo(
        path=path,
        size=size,
        created_at=created_at,
        signature=read.signature,
        has_checksum=checksum_path(path).is_file(),
        manifest=read.manifest,
        problem=read.problem,
    )


def backup_files(folder: Path) -> Iterator[Path]:
    if folder.is_dir():
        yield from (
            path for path in folder.iterdir() if path.is_file() and NAME_PATTERN.match(path.name)
        )


def list_backups(folder: Path, secret_key: str) -> list[BackupInfo]:
    """Los respaldos de la carpeta, del más reciente al más antiguo.

    Solo lee los manifiestos (no las huellas de cada archivo, que es `backup-verify`): con
    respaldos de varios gigas, listarlos sigue siendo inmediato. El orden es el del nombre,
    que lleva la hora de creación en UTC.
    """
    return [describe(path, secret_key) for path in sorted(backup_files(folder), reverse=True)]


def leftover_temporaries(folder: Path) -> list[Path]:
    """Lo que dejaron respaldos o restauraciones interrumpidos (el proceso se cortó a la mitad)."""
    if not folder.is_dir():
        return []

    return sorted(path for path in folder.iterdir() if path.name.startswith((TEMP_PREFIX, RESTORE_TEMP_PREFIX)))


def resolve_backup(folder: Path, name: str | None) -> Path:
    """El respaldo que pide un comando: por nombre (dentro de la carpeta) o por ruta, o el
    más reciente si no se indica ninguno. `FileNotFoundError` si no existe."""
    if name is None:
        found = sorted(backup_files(folder), reverse=True)

        if not found:
            raise FileNotFoundError(f"No hay respaldos en {folder}.")

        return found[0]

    candidate = Path(name)

    if not candidate.is_absolute() and len(candidate.parts) == 1:
        candidate = folder / candidate

    if not candidate.is_file():
        raise FileNotFoundError(f"No existe el respaldo {name}.")

    return candidate
