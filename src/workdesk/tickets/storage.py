"""Almacenamiento local de adjuntos (docs/10, secciones 61 a 69).

Solo se ocupa de los archivos: valida, escribe por bloques calculando el
SHA-256 y resuelve rutas. No toca la base de datos (eso es `attachments.py`).

Reglas:

- El nombre que entrega el usuario nunca es una ruta: se depura y solo se
  guarda como metadato. El archivo físico lleva un nombre UUID impredecible.
- Solo se aceptan las extensiones de `ALLOWED_TYPES` (lista blanca) y el
  contenido debe coincidir con su tipo (firma de bytes); no se confía en el
  nombre ni en el tipo MIME que declara el cliente.
- Se escribe primero en un archivo temporal, se comprueba el tamaño mientras
  se lee y solo entonces se mueve a su ubicación final: un archivo rechazado
  no queda disponible.
- Las rutas se resuelven siempre contra la raíz configurada y se comprueba
  que no salgan de ella.
"""

import contextlib
import hashlib
import os
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

# Máximo de archivos que se aceptan en un mismo envío.
MAX_FILES_PER_REQUEST = 5

CHUNK_SIZE = 64 * 1024
MAX_NAME_LENGTH = 150
TEMP_DIR = "_tmp"

_PNG = b"\x89PNG\r\n\x1a\n"

# extensión -> (tipo MIME, comprobación del contenido). Lista blanca: todo lo
# que no esté aquí se rechaza (ejecutables, scripts, HTML, SVG, archivos
# comprimidos...). El MIME se deduce de la extensión validada.
ALLOWED_TYPES = {
    "png": ("image/png", "png"),
    "jpg": ("image/jpeg", "jpeg"),
    "jpeg": ("image/jpeg", "jpeg"),
    "gif": ("image/gif", "gif"),
    "pdf": ("application/pdf", "pdf"),
    "txt": ("text/plain", "text"),
    "log": ("text/plain", "text"),
    "csv": ("text/csv", "text"),
    "docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "zip",
    ),
    "xlsx": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "zip",
    ),
    "pptx": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "zip",
    ),
}

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


class UploadError(ValueError):
    """Un archivo no cumple las reglas. El mensaje es para el usuario."""


@dataclass(frozen=True)
class StoredFile:
    original_name: str
    internal_name: str
    relative_path: str
    mime_type: str
    size: int
    sha256: str


def allowed_extensions() -> list[str]:
    return sorted(ALLOWED_TYPES)


def clean_filename(name: str | None) -> str:
    """Nombre depurado para guardarlo como metadato: sin directorios, sin
    caracteres de control y de largo acotado. Nunca se usa como ruta."""
    name = (name or "").replace("\\", "/").split("/")[-1]
    name = _CONTROL_CHARS.sub("", name).strip().strip(".").strip()

    if len(name) > MAX_NAME_LENGTH:
        stem, dot, ext = name.rpartition(".")
        keep = MAX_NAME_LENGTH - len(ext) - 1

        name = f"{stem[:keep]}.{ext}" if dot and keep > 0 else name[:MAX_NAME_LENGTH]

    return name or "archivo"


def extension_of(name: str) -> str:
    return name.rpartition(".")[2].lower() if "." in name else ""


def store_upload(upload, root: str | Path, max_bytes: int) -> StoredFile:
    """Valida y guarda un archivo subido (`FileStorage`). Lanza `UploadError`.

    Lee por bloques: calcula el SHA-256 y cuenta los bytes sin cargar el
    archivo entero en memoria, y deja el resultado en `root/AAAA/MM/<uuid>`.
    """
    original = clean_filename(getattr(upload, "filename", None))
    extension = extension_of(original)

    if extension not in ALLOWED_TYPES:
        raise UploadError(
            f"«{original}»: el tipo de archivo no está permitido. Se aceptan: "
            f"{', '.join(allowed_extensions())}."
        )

    mime_type, kind = ALLOWED_TYPES[extension]
    root = Path(root)
    temp_dir = root / TEMP_DIR
    temp_dir.mkdir(parents=True, exist_ok=True)

    internal = uuid.uuid4().hex
    temp_path = temp_dir / internal
    digest = hashlib.sha256()
    size = 0

    try:
        with temp_path.open("wb") as target:
            while chunk := upload.stream.read(CHUNK_SIZE):
                if size == 0:
                    _check_signature(original, kind, chunk)

                size += len(chunk)

                if size > max_bytes:
                    raise UploadError(
                        f"«{original}» supera el tamaño máximo de "
                        f"{_human_size(max_bytes)}."
                    )

                if kind == "text" and b"\x00" in chunk:
                    raise UploadError(
                        f"«{original}» no parece un archivo de texto."
                    )

                digest.update(chunk)
                target.write(chunk)

        if size == 0:
            raise UploadError(f"«{original}» está vacío.")

        now = datetime.now(UTC)
        relative = f"{now:%Y}/{now:%m}/{internal}"
        final = root / relative
        final.parent.mkdir(parents=True, exist_ok=True)
        os.replace(temp_path, final)
    except BaseException:
        # Un archivo rechazado (o un fallo a medias) no queda disponible.
        temp_path.unlink(missing_ok=True)
        raise

    return StoredFile(
        original_name=original,
        internal_name=internal,
        relative_path=relative,
        mime_type=mime_type,
        size=size,
        sha256=digest.hexdigest(),
    )


def absolute_path(root: str | Path, relative: str) -> Path:
    """Ruta física de un adjunto. Lanza `ValueError` si saldría de la raíz."""
    base = Path(root).resolve()
    path = (base / relative).resolve()

    if not path.is_relative_to(base):
        raise ValueError("Ruta fuera del almacenamiento de adjuntos.")

    return path


def remove_file(root: str | Path, relative: str) -> None:
    """Elimina un archivo físico (compensación si falla la base de datos)."""
    with contextlib.suppress(ValueError, OSError):
        absolute_path(root, relative).unlink(missing_ok=True)


def _check_signature(name: str, kind: str, first_chunk: bytes) -> None:
    ok = {
        "png": first_chunk.startswith(_PNG),
        "jpeg": first_chunk.startswith(b"\xff\xd8\xff"),
        "gif": first_chunk[:6] in (b"GIF87a", b"GIF89a"),
        "pdf": first_chunk.startswith(b"%PDF-"),
        "zip": first_chunk.startswith(b"PK\x03\x04"),
        "text": True,
    }[kind]

    if not ok:
        raise UploadError(
            f"«{name}»: el contenido no coincide con su extensión."
        )


def _human_size(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.0f} MB"

    return f"{size / 1024:.0f} KB"
