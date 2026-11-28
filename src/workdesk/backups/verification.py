"""Comprobar un respaldo sin restaurarlo (`backup-verify`, RNF-040).

Responde a una pregunta: **¿se puede restaurar este respaldo aquí con confianza?** Por eso
no necesita la base de datos (sirve justo cuando se cayó) y revisa, en este orden:

1. **El paquete entero** contra su `.sha256`. Si falta se avisa, pero no basta para
   rechazarlo: lo que sigue comprueba el contenido archivo por archivo.
2. **La firma del manifiesto.** Sin ella, o con la de otra clave, el respaldo no se puede
   atribuir a esta instalación: es un problema, aunque las huellas cuadren (quien altera un
   respaldo también puede recalcularlas).
3. **Los nombres de dentro del `.zip`:** ninguno absoluto, con `..`, repetido, enlace
   simbólico o cifrado. Uno así podría escribir fuera de su carpeta al extraerlo.
4. **Que no sobre ni falte nada** respecto del manifiesto, y que **cada archivo** tenga el
   tamaño y el SHA-256 anotados. Se lee con un tope: un archivo fabricado no puede
   descomprimirse sin fin.
5. **Que `pg_restore` pueda leer el volcado** (`--list`, que lee su índice sin tocar ninguna
   base) y que traiga la tabla de tickets.

Nunca extrae nada con el nombre que trae el `.zip`: el volcado se copia a un archivo
temporal con un nombre propio, y solo después de comprobar su huella.
"""

import hashlib
import re
import shutil
import stat
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from .package import (
    CHUNK_SIZE,
    CONTROL_MEMBERS,
    DATABASE_MEMBER,
    UPLOADS_MEMBER,
    Signature,
    file_sha256,
    manifest_warnings,
    read_checksum,
    read_manifest,
    unsafe_member_name,
)
from .postgres import BackupError, run_tool

RESTORE_LIST_TIMEOUT_SECONDS = 300
_TOC_ENTRY = re.compile(r"^\d+;\s", re.MULTILINE)
_TICKETS_TABLE = re.compile(r"^\d+;\s+\d+\s+\d+\s+TABLE\s+\S+\s+tickets\s", re.MULTILINE)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class Checksum:
    CORRECTA = "correcta"
    AUSENTE = "no está (se comprobó cada archivo igualmente)"
    NO_COINCIDE = "no coincide"


@dataclass
class Verification:
    path: Path
    checksum: str | None = None
    signature: Signature = Signature.AUSENTE
    manifest: dict | None = None
    files_total: int = 0
    files_ok: int = 0
    dump_entries: int | None = None
    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


SIGNATURE_PROBLEMS = {
    Signature.AUSENTE: "No tiene firma: no se puede saber si lo creó WorkDesk.",
    Signature.OTRA_CLAVE: (
        "La firma no corresponde a esta instalación: el manifiesto se modificó después de "
        "crearlo o el respaldo se hizo con otra SECRET_KEY. No lo restaures sin saber de "
        "dónde viene."
    ),
}


def _member_problems(infos: list[zipfile.ZipInfo]) -> list[str]:
    problems = []
    names = [info.filename for info in infos]

    for name in sorted({name for name in names if names.count(name) > 1}):
        problems.append(f"El archivo {name} aparece repetido dentro del paquete.")

    for info in infos:
        if unsafe_member_name(info.filename):
            problems.append(f"El nombre {info.filename!r} podría escribir fuera de su carpeta.")
        elif stat.S_ISLNK(info.external_attr >> 16):
            problems.append(f"{info.filename} es un enlace simbólico.")
        elif info.flag_bits & 0x1:
            problems.append(f"{info.filename} está cifrado.")

    return problems


def _listed_files(manifest: dict) -> tuple[dict[str, dict], list[str]]:
    """Los archivos del manifiesto por ruta, y lo que el manifiesto tiene mal."""
    entries = manifest.get("archivos")

    if not isinstance(entries, list):
        return {}, ["El manifiesto no lista sus archivos."]

    listed, problems = {}, []

    for entry in entries:
        valid = (
            isinstance(entry, dict)
            and isinstance(entry.get("ruta"), str)
            and isinstance(entry.get("bytes"), int)
            and entry["bytes"] >= 0
            and isinstance(entry.get("sha256"), str)
            and _SHA256.match(entry["sha256"])
            and not unsafe_member_name(entry["ruta"])
            and (entry["ruta"] == DATABASE_MEMBER or entry["ruta"].startswith(f"{UPLOADS_MEMBER}/"))
        )

        if not valid:
            problems.append(f"El manifiesto tiene una entrada que no se entiende: {entry!r}"[:300])
        elif entry["ruta"] in listed:
            problems.append(f"El manifiesto lista dos veces {entry['ruta']}.")
        else:
            listed[entry["ruta"]] = entry

    if DATABASE_MEMBER not in listed:
        problems.append("El manifiesto no incluye el volcado de la base de datos.")

    return listed, problems


def _matches(archive: zipfile.ZipFile, info: zipfile.ZipInfo, entry: dict) -> str | None:
    """`None` si el archivo tiene el tamaño y la huella anotados; si no, el problema."""
    if info.file_size != entry["bytes"]:
        return f"{info.filename}: el tamaño no es el del manifiesto."

    digest = hashlib.sha256()
    read = 0

    try:
        with archive.open(info) as handle:
            while chunk := handle.read(CHUNK_SIZE):
                read += len(chunk)

                if read > entry["bytes"]:
                    return f"{info.filename}: trae más datos de los que declara."

                digest.update(chunk)
    except (zipfile.BadZipFile, OSError, EOFError) as error:
        return f"{info.filename}: no se puede leer ({error})."

    if read != entry["bytes"] or digest.hexdigest() != entry["sha256"]:
        return f"{info.filename}: su contenido no coincide con la huella del manifiesto."

    return None


def _check_dump(archive: zipfile.ZipFile, pg_restore: str, result: Verification) -> None:
    workspace = Path(tempfile.mkdtemp(prefix="workdesk-verificar-"))

    try:
        dump = workspace / "volcado.dump"

        with archive.open(DATABASE_MEMBER) as source, dump.open("wb") as target:
            shutil.copyfileobj(source, target, CHUNK_SIZE)

        try:
            listing = run_tool(
                [pg_restore, "--list", str(dump)], timeout=RESTORE_LIST_TIMEOUT_SECONDS
            )
        except BackupError as error:
            result.problems.append(f"El volcado de la base no se puede leer: {error}")
            return

        result.dump_entries = len(_TOC_ENTRY.findall(listing))

        if not _TICKETS_TABLE.search(listing):
            result.problems.append("El volcado no contiene la tabla de tickets de WorkDesk.")
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def _check_contents(archive: zipfile.ZipFile, listed: dict, result: Verification) -> bool:
    """Compara el paquete con el manifiesto. Devuelve si el volcado es el anotado."""
    infos = archive.infolist()
    result.problems += _member_problems(infos)
    present = {info.filename: info for info in infos if info.filename not in CONTROL_MEMBERS}

    for name in sorted(present.keys() - listed.keys()):
        result.problems.append(f"{name} está en el paquete pero no en el manifiesto.")

    for name in sorted(listed.keys() - present.keys()):
        result.problems.append(f"Falta {name}, que el manifiesto lista.")

    result.files_total = len(listed)
    dump_ok = False

    for name in sorted(listed.keys() & present.keys()):
        problem = _matches(archive, present[name], listed[name])

        if problem is None:
            result.files_ok += 1
            dump_ok = dump_ok or name == DATABASE_MEMBER
        else:
            result.problems.append(problem)

    return dump_ok


def verify_backup(path: Path, *, secret_key: str, pg_restore: str) -> Verification:
    """Comprueba un respaldo. `Verification.ok` dice si se puede restaurar con confianza."""
    result = Verification(path=path)
    expected = read_checksum(path)

    if expected is None:
        result.checksum = Checksum.AUSENTE
        result.warnings.append("No está el archivo .sha256 junto al paquete.")
    elif file_sha256(path) == expected:
        result.checksum = Checksum.CORRECTA
    else:
        result.checksum = Checksum.NO_COINCIDE
        result.problems.append("La huella del paquete no coincide con su archivo .sha256.")

    try:
        archive = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError):
        result.problems.append("No es un archivo .zip válido.")
        return result

    with archive:
        read = read_manifest(archive, secret_key)
        result.signature = read.signature

        if read.manifest is None:
            result.problems.append(read.problem)
            return result

        result.manifest = read.manifest

        if read.signature is not Signature.VALIDA:
            result.problems.append(SIGNATURE_PROBLEMS[read.signature])

        listed, manifest_problems = _listed_files(read.manifest)
        result.problems += manifest_problems
        result.warnings += manifest_warnings(read.manifest)

        if _check_contents(archive, listed, result):
            _check_dump(archive, pg_restore, result)

    return result
