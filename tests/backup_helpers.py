"""Ayudantes de los tests de respaldos y restauración (`test_backups`, `test_restore`)."""

import hashlib
import os
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import text

from src.workdesk.backups import package, postgres
from src.workdesk.extensions import db

MOMENT = datetime(2026, 11, 27, 18, 35, 22, tzinfo=UTC)
# La `SECRET_KEY` de la aplicación de pruebas (`tests/conftest.py`).
SECRET = "test-secret-key"

try:
    PG_DUMP = postgres.find_tool("pg_dump", os.getenv("PG_BIN_DIR"))
    PG_RESTORE = postgres.find_tool("pg_restore", os.getenv("PG_BIN_DIR"))
    PSQL = postgres.find_tool("psql", os.getenv("PG_BIN_DIR"))
except postgres.BackupError:
    PG_DUMP = PG_RESTORE = PSQL = None

needs_tools = pytest.mark.skipif(PG_DUMP is None, reason="pg_dump, pg_restore y psql no están instalados")


def members(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {info.filename: archive.read(info) for info in archive.infolist()}


def rewrite(target: Path, items, *, checksum=True) -> Path:
    """Escribe un paquete con los miembros dados (pares nombre, contenido) y su `.sha256`."""
    with zipfile.ZipFile(target, "w") as archive:
        for name, data in items:
            archive.writestr(zipfile.ZipInfo(name, date_time=(2026, 11, 27, 0, 0, 0)), data)

    if checksum:
        package.checksum_path(target).write_text(
            package.checksum_line(package.file_sha256(target), target), encoding="ascii"
        )

    return target


def resigned(contents: dict[str, bytes], manifest: dict, secret=SECRET) -> dict[str, bytes]:
    """Los miembros con el manifiesto cambiado y vuelto a firmar (con esta u otra clave)."""
    raw = package.encode_manifest(manifest)

    return {**contents, package.MANIFEST_MEMBER: raw, package.SIGNATURE_MEMBER: package.sign(raw, secret).encode()}


def entry(data: bytes, name: str) -> dict:
    return {"ruta": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def install_alembic_version(app, revision: str | None):
    """Deja el esquema con la `alembic_version` que haría `db upgrade` hasta `revision` (sin
    tabla si es `None`) y devuelve cómo dejarlo como estaba.

    La suite crea el esquema desde los modelos, sin migraciones. Sin `-n` usa el `public` de
    `workdesk_test`, que puede tener ya una tabla: se aparta y se devuelve al final (salvo
    que una restauración la haya borrado, que es lo que hace con lo que no trae el respaldo).
    """
    with app.app_context():
        existed = db.session.scalar(text("SELECT to_regclass('alembic_version') IS NOT NULL"))

        if existed:
            db.session.execute(text("ALTER TABLE alembic_version RENAME TO alembic_version_apartada"))

        if revision is not None:
            db.session.execute(text("CREATE TABLE alembic_version (version_num varchar(32) PRIMARY KEY)"))
            db.session.execute(text("INSERT INTO alembic_version VALUES (:revision)"), {"revision": revision})

        db.session.commit()

    def put_back():
        with app.app_context():
            db.session.execute(text("DROP TABLE IF EXISTS alembic_version"))

            if existed and db.session.scalar(text("SELECT to_regclass('alembic_version_apartada') IS NOT NULL")):
                db.session.execute(text("ALTER TABLE alembic_version_apartada RENAME TO alembic_version"))

            db.session.commit()

    return put_back
