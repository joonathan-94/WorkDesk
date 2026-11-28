"""Respaldos: crear, comprobar y listar (`backups/`, RF-127, RNF-038 a RNF-043, RN-181).

Los tests de integración usan el `pg_dump` y el `pg_restore` reales contra la base de
pruebas (el esquema del proceso): un respaldo de prueba que no ejecutara la herramienta no
demostraría nada. Si las herramientas no están instaladas, esos tests se saltan.
"""

import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url

from src.workdesk import create_app
from src.workdesk.audit import AuditAction, AuditResult
from src.workdesk.backups import (
    BackupError,
    create_backup,
    creation,
    list_backups,
    package,
    postgres,
    verify_backup,
)
from src.workdesk.backups.package import Signature
from src.workdesk.extensions import db
from src.workdesk.models import AdminAuditLog, Attachment, Ticket, User
from src.workdesk.security.startup import storage_problems
from tests.backup_helpers import (
    MOMENT,
    PG_RESTORE,
    SECRET,
    install_alembic_version,
    needs_tools,
)
from tests.backup_helpers import entry as _entry
from tests.backup_helpers import members as _members
from tests.backup_helpers import resigned as _resigned
from tests.backup_helpers import rewrite as _rewrite
from tests.database import checked_database_url

# --- Ayudantes ------------------------------------------------------------------------


def _create(app, moment=MOMENT):
    with app.app_context():
        return create_backup(now=moment)


def _audit_rows(app):
    with app.app_context():
        return db.session.scalars(
            select(AdminAuditLog)
            .where(AdminAuditLog.accion == AuditAction.RESPALDO_CREADO)
            .order_by(AdminAuditLog.id)
        ).all()


def _manifest(path: Path) -> dict:
    return json.loads(_members(path)[package.MANIFEST_MEMBER])


def _verify(path: Path, secret=SECRET):
    return verify_backup(path, secret_key=secret, pg_restore=PG_RESTORE)


def _dump_rows(dump: bytes, table: str, tmp_path: Path) -> int:
    """Cuántas filas de una tabla trae un volcado (sin restaurarlo en ninguna base)."""
    path = tmp_path / "leido.dump"
    path.write_bytes(dump)
    output = subprocess.run(
        [PG_RESTORE, "--data-only", f"--table={table}", "--file=-", str(path)],
        capture_output=True, text=True, encoding="utf-8", check=True,
    ).stdout
    lines = output.split("FROM stdin;\n", 1)[1].splitlines()

    return lines.index("\\.")


@pytest.fixture()
def migrated(app):
    """Una tabla `alembic_version` como la que deja `db upgrade`, con una revisión de prueba."""
    put_back = install_alembic_version(app, "abc123def456")
    yield
    put_back()


@pytest.fixture()
def unmigrated(app):
    """Un esquema sin `alembic_version`, como uno creado sin las migraciones."""
    put_back = install_alembic_version(app, None)
    yield
    put_back()


_GOLDEN: dict[str, Path] = {}


@pytest.fixture()
def golden(app, seeded, migrated, tmp_path, tmp_path_factory):
    """Un respaldo real de los tickets de demostración, copiado para cada test: se crea una
    vez por proceso (el contenido no cambia) y cada test puede alterar su copia."""
    if "path" not in _GOLDEN:
        original = _create(app).path
        keep = tmp_path_factory.mktemp("golden") / original.name
        shutil.copy2(original, keep)
        shutil.copy2(package.checksum_path(original), package.checksum_path(keep))
        _GOLDEN["path"] = keep

    copy = tmp_path / "copia" / _GOLDEN["path"].name
    copy.parent.mkdir()
    shutil.copy2(_GOLDEN["path"], copy)
    shutil.copy2(package.checksum_path(_GOLDEN["path"]), package.checksum_path(copy))

    return copy


# --- La conexión con las herramientas ---------------------------------------------------


def test_the_passfile_escapes_what_libpq_treats_as_separators():
    assert postgres._passfile_line("a:b\\c") == "*:*:*:*:a\\:b\\\\c\n"


def test_the_password_never_goes_in_the_connection_string():
    connection = postgres.connection_for(
        "postgresql+psycopg://app:p%40ss%3Aw'rd@db.local:5433/workdesk?sslmode=require"
    )

    assert connection.password == "p@ss:w'rd"
    assert "p@ss" not in connection.conninfo
    assert "host='db.local'" in connection.conninfo
    assert "port='5433'" in connection.conninfo
    assert "dbname='workdesk'" in connection.conninfo
    assert "sslmode='require'" in connection.conninfo


def test_a_value_with_quotes_cannot_add_connection_options():
    conninfo = postgres.connection_for("postgresql://app@localhost/work' host='evil").conninfo

    assert "dbname='work\\' host=\\'evil'" in conninfo


def test_only_postgresql_can_be_backed_up():
    with pytest.raises(BackupError, match="PostgreSQL"):
        postgres.connection_for("sqlite:///workdesk.db")


def test_the_password_file_is_private_and_disappears(monkeypatch):
    monkeypatch.setenv("PGPASSWORD", "la-del-entorno")
    # `python-dotenv` deja el `.env` en el entorno del proceso: nada de eso llega al hijo.
    monkeypatch.setenv("DATABASE_URL", "postgresql://app:secreta@localhost/workdesk")
    monkeypatch.setenv("SECRET_KEY", "la-clave-de-las-cookies")
    monkeypatch.setenv("OTRA_COPIA", "contiene secreta dentro")
    connection = postgres.Connection(conninfo="dbname='x'", password="secreta")

    with postgres.tool_environment(connection) as environment:
        passfile = Path(environment["PGPASSFILE"])
        assert passfile.read_text(encoding="utf-8") == "*:*:*:*:secreta\n"
        assert not {"PGPASSWORD", "DATABASE_URL", "SECRET_KEY", "OTRA_COPIA"} & environment.keys()
        assert "PATH" in environment
        assert "secreta" not in json.dumps({k: v for k, v in environment.items() if k != "PGPASSFILE"})

        if os.name != "nt":
            assert passfile.stat().st_mode & 0o077 == 0

    assert not passfile.exists()


def test_a_missing_tool_explains_how_to_point_to_it(tmp_path):
    with pytest.raises(BackupError, match="PG_BIN_DIR"):
        postgres.find_tool("pg_dump", str(tmp_path))


def test_a_failing_tool_reports_its_last_words(tmp_path):
    script = tmp_path / "falla.py"
    script.write_text("import sys; sys.stderr.write('uno\\ndos\\n'); sys.exit(3)", encoding="utf-8")

    with pytest.raises(BackupError, match="falló: uno\ndos"):
        postgres.run_tool([sys.executable, str(script)])


# --- El formato -------------------------------------------------------------------------


def test_the_name_carries_the_utc_time():
    local = datetime(2026, 11, 27, 15, 35, 22, tzinfo=UTC) - timedelta(hours=3)

    assert package.backup_name(local) == "workdesk-respaldo-20261127-123522Z.zip"
    assert package.NAME_PATTERN.match(package.backup_name(MOMENT))


def test_the_signature_key_is_derived_from_the_secret_and_not_the_secret_itself():
    manifest = b'{"formato": "workdesk-respaldo/1"}'
    signature = package.sign(manifest, SECRET).encode()

    assert signature != hmac.new(SECRET.encode(), manifest, "sha256").hexdigest().encode()
    assert package.signature_status(manifest, signature, SECRET) is Signature.VALIDA
    assert package.signature_status(manifest, signature, "otra-clave") is Signature.OTRA_CLAVE
    assert package.signature_status(manifest + b" ", signature, SECRET) is Signature.OTRA_CLAVE
    assert package.signature_status(manifest, None, SECRET) is Signature.AUSENTE


@pytest.mark.parametrize(
    "name",
    ["../x", "uploads/../../x", "/etc/passwd", "C:/Windows/x", "uploads\\2026\\x", "", "uploads//x", "./x", "uploads/."],
)
def test_names_that_could_escape_their_folder_are_unsafe(name):
    assert package.unsafe_member_name(name)


@pytest.mark.parametrize("name", ["database.dump", "manifest.json", "uploads/2026/11/0f9c2b6e"])
def test_the_names_of_a_backup_are_safe(name):
    assert not package.unsafe_member_name(name)


# --- Dónde se guardan -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("uploads", "backups", "problem"),
    [
        ("datos/uploads", "datos/backups", None),
        ("static/uploads", "datos/backups", "UPLOADS_DIR"),
        ("datos/uploads", "static/respaldos", "BACKUPS_DIR"),
        ("datos/uploads", ".", "BACKUPS_DIR"),
        ("datos", "datos/backups", "separadas"),
        ("datos/backups/uploads", "datos/backups", "separadas"),
    ],
)
def test_nothing_is_stored_where_the_web_serves_it_or_inside_each_other(tmp_path, uploads, backups, problem):
    problems = storage_problems(
        uploads_dir=tmp_path / uploads, backups_dir=tmp_path / backups, static_dir=tmp_path / "static"
    )

    if problem is None:
        assert problems == []
    else:
        assert any(problem in line for line in problems), problems


def test_the_application_refuses_to_start_with_backups_inside_static(tmp_path):
    static = Path(__file__).resolve().parent.parent / "src" / "workdesk" / "static"

    with pytest.raises(RuntimeError, match="BACKUPS_DIR"):
        create_app(
            {
                "TESTING": True,
                "SECRET_KEY": SECRET,
                "SQLALCHEMY_DATABASE_URI": checked_database_url(),
                "UPLOADS_DIR": str(tmp_path / "uploads"),
                "BACKUPS_DIR": str(static / "respaldos"),
            }
        )


def test_by_default_backups_live_apart_from_the_uploads(tmp_path):
    app = create_app(
        {"TESTING": True, "SECRET_KEY": SECRET, "SQLALCHEMY_DATABASE_URI": checked_database_url(), "BACKUPS_DIR": None}
    )

    assert Path(app.config["BACKUPS_DIR"]) == Path(app.instance_path) / "backups"


# --- Crear ------------------------------------------------------------------------------


@needs_tools
def test_a_backup_holds_the_dump_every_attachment_and_a_manifest_that_describes_them(
    app, seeded, migrated, tmp_path
):
    result = _create(app)
    members = _members(result.path)
    manifest = json.loads(members[package.MANIFEST_MEMBER])

    with app.app_context():
        tickets = db.session.scalar(select(func.count()).select_from(Ticket))
        users = db.session.scalar(select(func.count()).select_from(User))
        attachments = db.session.execute(select(Attachment.ruta_archivo, Attachment.hash)).all()

    assert result.path.name == "workdesk-respaldo-20261127-183522Z.zip"
    assert attachments, "los tickets de demostración traen adjuntos"
    assert manifest["formato"] == package.FORMAT
    assert manifest["creado_en"] == "2026-11-27T18:35:22+00:00"
    assert manifest["base_de_datos"]["revision_migracion"] == "abc123def456"
    assert manifest["contenido"]["tickets"] == tickets
    assert manifest["contenido"]["usuarios"] == users
    assert manifest["contenido"]["adjuntos"] == manifest["contenido"]["adjuntos_copiados"] == len(attachments)
    assert manifest["avisos"] == {"adjuntos_faltantes": [], "adjuntos_alterados": []}
    assert result.warnings == []

    # Cada archivo del manifiesto está en el paquete con su huella; nada más, salvo el
    # manifiesto y su firma. Los adjuntos llevan la misma huella que guardó la base.
    listed = {entry["ruta"]: entry for entry in manifest["archivos"]}
    assert set(members) == set(listed) | {package.MANIFEST_MEMBER, package.SIGNATURE_MEMBER}

    for name, entry in listed.items():
        assert hashlib.sha256(members[name]).hexdigest() == entry["sha256"]
        assert len(members[name]) == entry["bytes"]

    assert {(name.removeprefix("uploads/"), entry["sha256"]) for name, entry in listed.items() if name != "database.dump"} == {
        (path, digest) for path, digest in attachments
    }

    # El volcado trae los mismos tickets que cuenta el manifiesto, y el paquete, su huella.
    assert _dump_rows(members["database.dump"], "tickets", tmp_path) == tickets
    assert package.read_checksum(result.path) == hashlib.sha256(result.path.read_bytes()).hexdigest() == result.sha256
    assert package.signature_status(
        members[package.MANIFEST_MEMBER], members[package.SIGNATURE_MEMBER], SECRET
    ) is Signature.VALIDA

    # No queda nada a medias.
    assert sorted(path.name for path in result.path.parent.iterdir()) == [result.path.name, f"{result.path.name}.sha256"]


@needs_tools
def test_the_schema_dumped_is_the_one_the_application_uses(app, migrated):
    result = _create(app)

    with app.app_context():
        schema = db.session.scalar(text("SELECT current_schema()"))

    assert result.manifest["base_de_datos"]["esquema"] == schema


@needs_tools
def test_the_dump_and_the_attachments_come_from_the_same_instant(app, seeded, migrated, make_user, monkeypatch, tmp_path):
    """Lo que cambia mientras `pg_dump` trabaja no entra en el respaldo, ni en el volcado
    ni en la lista de adjuntos: los dos salen de la misma foto."""
    uploads = Path(app.config["UPLOADS_DIR"])

    with app.app_context():
        users_before = db.session.scalar(select(func.count()).select_from(User))

    real = creation.run_tool

    def change_while_dumping(arguments, environment=None, **options):
        if Path(arguments[0]).stem == "pg_dump":
            make_user("SOLICITANTE", "llega_durante_el_respaldo")
            (uploads / "2026").mkdir(parents=True, exist_ok=True)
            (uploads / "2026" / "subido-durante").write_bytes(b"llega tarde")

        return real(arguments, environment, **options)

    monkeypatch.setattr(creation, "run_tool", change_while_dumping)
    result = _create(app)
    members = _members(result.path)

    assert result.manifest["contenido"]["usuarios"] == users_before
    assert _dump_rows(members["database.dump"], "usuarios", tmp_path) == users_before
    assert not any("subido-durante" in name for name in members)

    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(User)) == users_before + 1


@needs_tools
def test_only_text_is_compressed_because_the_rest_already_comes_compressed(app, seeded, migrated):
    with app.app_context():
        text_file, image = db.session.scalars(select(Attachment).order_by(Attachment.id).limit(2)).all()
        image.mime_type = "image/png"
        db.session.commit()
        names = {upload: f"uploads/{row.ruta_archivo}" for upload, row in (("texto", text_file), ("imagen", image))}

    with zipfile.ZipFile(_create(app).path) as archive:
        assert archive.getinfo(names["texto"]).compress_type == zipfile.ZIP_DEFLATED
        assert archive.getinfo(names["imagen"]).compress_type == zipfile.ZIP_STORED
        assert archive.getinfo("database.dump").compress_type == zipfile.ZIP_STORED


@needs_tools
def test_leftovers_on_disk_are_not_backed_up(app, seeded, migrated):
    uploads = Path(app.config["UPLOADS_DIR"])
    (uploads / "_tmp").mkdir(parents=True, exist_ok=True)
    (uploads / "_tmp" / "subida-cortada").write_bytes(b"resto")
    (uploads / "suelto.txt").write_bytes(b"sin ticket")

    names = set(_members(_create(app).path))

    assert not any("_tmp" in name or "suelto" in name for name in names)


@needs_tools
def test_a_missing_or_altered_attachment_is_reported_and_the_rest_is_saved(app, seeded, migrated):
    uploads = Path(app.config["UPLOADS_DIR"])

    with app.app_context():
        first, second, third = db.session.scalars(select(Attachment).order_by(Attachment.id).limit(3)).all()
        actor = db.session.scalar(select(User.id).limit(1))
        # Un adjunto eliminado cuyo archivo ya no está (la retención lo borra): no es un aviso.
        third.activo = False
        third.fecha_eliminacion = datetime.now(UTC)
        third.usuario_eliminacion_id = actor
        db.session.commit()
        paths = [first.ruta_archivo, second.ruta_archivo, third.ruta_archivo]
        total = db.session.scalar(select(func.count()).select_from(Attachment))

    (uploads / paths[0]).unlink()
    # El mismo tamaño y un byte distinto: solo la huella guardada al subirlo lo descubre.
    data = (uploads / paths[1]).read_bytes()
    (uploads / paths[1]).write_bytes(data[:-1] + bytes([data[-1] ^ 1]))
    (uploads / paths[2]).unlink()

    result = _create(app)

    assert result.manifest["avisos"] == {"adjuntos_faltantes": [paths[0]], "adjuntos_alterados": [paths[1]]}
    assert result.manifest["contenido"]["adjuntos_copiados"] == total - 2
    assert any(paths[0] in line and "no estaba en el disco" in line for line in result.warnings)
    assert any(paths[1] in line and "no coincidía" in line for line in result.warnings)
    assert len(result.warnings) == 2

    audit = _audit_rows(app)[-1]
    assert audit.valor_nuevo["adjuntos_faltantes"] == 1
    assert audit.valor_nuevo["adjuntos_alterados"] == 1


@needs_tools
def test_without_migrations_the_backup_says_it_cannot_be_matched_to_the_code(app, unmigrated):
    result = _create(app)

    assert result.manifest["base_de_datos"]["revision_migracion"] is None
    assert any("alembic_version" in line for line in result.warnings)


@needs_tools
def test_each_backup_is_audited_as_a_system_action(app, migrated):
    result = _create(app)
    (audit,) = _audit_rows(app)

    assert audit.actor_usuario_id is None
    assert audit.resultado == AuditResult.EXITOSO
    assert audit.entidad_tipo == "respaldo"
    assert audit.detalle == result.path.name
    assert audit.valor_nuevo["sha256"] == result.sha256
    assert audit.valor_nuevo["bytes"] == result.size
    assert "usuario_sistema" in audit.valor_nuevo


@needs_tools
def test_the_password_never_reaches_the_command_line_or_the_environment(app, migrated, monkeypatch):
    password = make_url(app.config["SQLALCHEMY_DATABASE_URI"]).password
    assert password, "la base de pruebas usa contraseña"
    seen = []
    real = creation.run_tool

    def spy(arguments, environment=None, **options):
        seen.append((list(arguments), dict(environment or {})))
        return real(arguments, environment, **options)

    monkeypatch.setattr(creation, "run_tool", spy)
    _create(app)
    ((arguments, environment),) = [call for call in seen if Path(call[0][0]).stem == "pg_dump"]

    assert not any(password in argument for argument in arguments)
    assert not any(password in value for value in environment.values())
    assert not {"PGPASSWORD", "SECRET_KEY", "DATABASE_URL", "TEST_DATABASE_URL"} & environment.keys()
    assert not Path(environment["PGPASSFILE"]).exists()
    assert any(argument.startswith("--snapshot=") for argument in arguments)


@needs_tools
def test_a_failed_backup_leaves_nothing_behind_and_is_audited(app, migrated, monkeypatch):
    real = creation.run_tool

    def fail_dump(arguments, environment=None, **options):
        if Path(arguments[0]).stem == "pg_dump":
            raise BackupError("pg_dump falló: disco lleno")
        return real(arguments, environment, **options)

    monkeypatch.setattr(creation, "run_tool", fail_dump)

    with pytest.raises(BackupError, match="disco lleno"):
        _create(app)

    folder = Path(app.config["BACKUPS_DIR"])
    (audit,) = _audit_rows(app)

    assert list(folder.iterdir()) == []
    assert audit.resultado == AuditResult.FALLIDO
    assert audit.valor_nuevo["error"] == "pg_dump falló: disco lleno"


@needs_tools
def test_two_backups_of_the_same_database_cannot_run_at_once(app, migrated):
    with app.app_context(), db.engine.connect() as other, other.begin():
        other.execute(select(func.pg_advisory_xact_lock(creation.backup_lock_key())))

        with pytest.raises(BackupError, match="en curso"):
            create_backup(now=MOMENT)

    assert list(Path(app.config["BACKUPS_DIR"]).iterdir()) == []
    assert [row.resultado for row in _audit_rows(app)] == [AuditResult.FALLIDO]


@needs_tools
def test_an_existing_backup_is_never_overwritten(app, migrated):
    first = _create(app)
    before = first.path.read_bytes()

    with pytest.raises(BackupError, match="Ya existe"):
        _create(app)

    assert first.path.read_bytes() == before


@pytest.mark.skipif(os.name == "nt", reason="Windows no usa los permisos de POSIX")
@needs_tools
def test_only_its_owner_can_read_a_backup(app, migrated):
    assert _create(app).path.stat().st_mode & 0o077 == 0


# --- Comprobar --------------------------------------------------------------------------


@needs_tools
def test_a_fresh_backup_verifies(golden):
    result = _verify(golden)

    assert result.ok, result.problems
    assert result.problems == result.warnings == []
    assert result.signature is Signature.VALIDA
    assert result.files_ok == result.files_total > 1
    assert result.dump_entries > 10


@needs_tools
def test_verifying_needs_neither_the_application_nor_the_database(golden):
    # Fuera de cualquier contexto de Flask: sirve aunque la base se haya caído.
    assert _verify(golden).ok


def _upload_name(members):
    return next(name for name in members if name.startswith("uploads/"))


def _tamper_attachment_content(members, manifest):
    """El mismo tamaño, un byte distinto: solo la huella lo descubre."""
    name = _upload_name(members)
    data = members[name]
    return {**members, name: data[:-1] + bytes([data[-1] ^ 1])}


def _tamper_extra_member(members, manifest):
    return {**members, "uploads/2026/11/intruso": b"no listado"}


def _tamper_missing_member(members, manifest):
    members = dict(members)
    del members[_upload_name(members)]
    return members


def _tamper_manifest_without_signing(members, manifest):
    manifest["contenido"]["tickets"] += 1
    return {**members, package.MANIFEST_MEMBER: package.encode_manifest(manifest)}


def _tamper_signed_with_another_key(members, manifest):
    manifest["contenido"]["tickets"] += 1
    return _resigned(members, manifest, secret="la-clave-de-otro")


def _tamper_signature_removed(members, manifest):
    members = dict(members)
    del members[package.SIGNATURE_MEMBER]
    return members


def _tamper_path_traversal(members, manifest):
    payload = b"fuera de su carpeta"
    manifest["archivos"].append(_entry(payload, "uploads/../../evil.txt"))
    return _resigned({**members, "uploads/../../evil.txt": payload}, manifest)


def _tamper_size_understated(members, manifest):
    name = _upload_name(members)
    entry = next(entry for entry in manifest["archivos"] if entry["ruta"] == name)
    entry["bytes"] -= 1
    return _resigned(members, manifest)


def _tamper_unreadable_dump(members, manifest):
    """Huellas y firma correctas, pero un volcado que no es un volcado: lo que dejaría un
    `pg_dump` roto. Solo `pg_restore --list` lo descubre."""
    garbage = b"PGDMP" + os.urandom(64)
    entry = next(entry for entry in manifest["archivos"] if entry["ruta"] == "database.dump")
    entry.update(_entry(garbage, "database.dump"))
    return _resigned({**members, "database.dump": garbage}, manifest)


@needs_tools
@pytest.mark.parametrize(
    ("tamper", "expected"),
    [
        (_tamper_attachment_content, "no coincide con la huella"),
        (_tamper_extra_member, "no en el manifiesto"),
        (_tamper_missing_member, "Falta"),
        (_tamper_manifest_without_signing, "firma no corresponde"),
        (_tamper_signed_with_another_key, "firma no corresponde"),
        (_tamper_signature_removed, "No tiene firma"),
        (_tamper_path_traversal, "no se entiende"),
        (_tamper_size_understated, "tamaño"),
        (_tamper_unreadable_dump, "no se puede leer"),
    ],
)
def test_an_altered_backup_does_not_verify(golden, tmp_path, tamper, expected):
    members = _members(golden)
    manifest = json.loads(members[package.MANIFEST_MEMBER])
    altered = _rewrite(tmp_path / golden.name, list(tamper(members, manifest).items()))

    result = _verify(altered)

    assert not result.ok
    assert any(expected in problem for problem in result.problems), result.problems


@needs_tools
def test_a_name_that_climbs_out_is_caught_inside_the_zip_even_if_the_manifest_does_not_list_it(golden, tmp_path):
    """Las dos defensas por separado: los nombres del `.zip` se revisan aunque el manifiesto
    no los mencione (una entrada así sobra, y además podría escribir fuera)."""
    members = {**_members(golden), "../../fuera.txt": b"intruso"}
    altered = _rewrite(tmp_path / golden.name, list(members.items()))

    problems = _verify(altered).problems

    assert any("podría escribir fuera de su carpeta" in problem for problem in problems), problems


@needs_tools
def test_a_duplicated_name_inside_the_zip_does_not_verify(golden, tmp_path):
    members = _members(golden)
    name = _upload_name(members)
    items = [*members.items(), (name, b"otra version")]

    with pytest.warns(UserWarning, match="Duplicate name"):
        altered = _rewrite(tmp_path / golden.name, items)

    assert any("repetido" in problem for problem in _verify(altered).problems)


@needs_tools
def test_a_package_that_differs_from_its_checksum_does_not_verify(golden):
    package.checksum_path(golden).write_text(package.checksum_line("0" * 64, golden), encoding="ascii")

    result = _verify(golden)

    assert not result.ok
    assert result.problems == ["La huella del paquete no coincide con su archivo .sha256."]


@needs_tools
def test_without_its_checksum_file_the_contents_are_still_checked(golden):
    package.checksum_path(golden).unlink()

    result = _verify(golden)

    assert result.ok
    assert result.warnings == ["No está el archivo .sha256 junto al paquete."]


@needs_tools
def test_a_file_that_is_not_a_zip_does_not_verify(tmp_path):
    path = tmp_path / "workdesk-respaldo-20261127-183522Z.zip"
    path.write_bytes(b"no soy un zip")

    result = _verify(path)

    assert result.problems == ["No es un archivo .zip válido."]
    assert result.warnings == ["No está el archivo .sha256 junto al paquete."]


@needs_tools
def test_a_backup_from_another_installation_does_not_verify_here(golden):
    result = _verify(golden, secret="la-clave-de-otra-instalacion")

    assert result.signature is Signature.OTRA_CLAVE
    assert not result.ok
    # El contenido en sí está bien: es la procedencia lo que no se puede confirmar.
    assert result.files_ok == result.files_total


# --- Listar -----------------------------------------------------------------------------


@needs_tools
def test_backups_are_listed_newest_first_with_what_they_hold(app, migrated, tmp_path):
    older = _create(app, MOMENT - timedelta(days=1))
    newer = _create(app, MOMENT)
    folder = Path(app.config["BACKUPS_DIR"])
    (folder / "notas.txt").write_text("no es un respaldo", encoding="utf-8")
    broken = folder / "workdesk-respaldo-20261120-000000Z.zip"
    broken.write_bytes(b"roto")
    package.checksum_path(older.path).unlink()

    listed = list_backups(folder, SECRET)

    assert [info.name for info in listed] == [newer.path.name, older.path.name, broken.name]
    assert listed[0].created_at == MOMENT
    assert listed[0].signature is Signature.VALIDA and listed[0].has_checksum
    assert not listed[1].has_checksum
    assert listed[2].problem == "No es un .zip válido."
    assert listed[0].content["tickets"] == 0
    assert list_backups(folder, "otra")[0].signature is Signature.OTRA_CLAVE


def test_an_empty_or_absent_folder_lists_nothing(tmp_path):
    assert list_backups(tmp_path / "no-existe", SECRET) == []
    assert package.leftover_temporaries(tmp_path / "no-existe") == []


def test_the_latest_backup_is_found_by_name_order(tmp_path):
    for name in ("workdesk-respaldo-20261126-000000Z.zip", "workdesk-respaldo-20261127-000000Z.zip", "otro.zip"):
        (tmp_path / name).write_bytes(b"")

    assert package.resolve_backup(tmp_path, None).name == "workdesk-respaldo-20261127-000000Z.zip"
    assert package.resolve_backup(tmp_path, "otro.zip") == tmp_path / "otro.zip"

    with pytest.raises(FileNotFoundError):
        package.resolve_backup(tmp_path / "vacia", None)


# --- Comandos ---------------------------------------------------------------------------


def _run(app, *arguments):
    return app.test_cli_runner().invoke(args=list(arguments))


@needs_tools
def test_the_commands_create_verify_and_list(app, seeded, migrated):
    created = _run(app, "backup-create")

    assert created.exit_code == 0, created.output
    assert re.search(r"^Respaldo creado: .*workdesk-respaldo-\d{8}-\d{6}Z\.zip$", created.output, re.MULTILINE)
    assert "Contenido: " in created.output and "tickets" in created.output
    assert re.search(r"^SHA-256: [0-9a-f]{64}$", created.output, re.MULTILINE)

    verified = _run(app, "backup-verify")

    assert verified.exit_code == 0, verified.output
    assert "Huella del paquete: correcta" in verified.output
    assert "Firma: de esta instalación" in verified.output
    assert "Resultado: el respaldo está completo y es de esta instalación." in verified.output

    listed = _run(app, "backup-list")

    assert listed.exit_code == 0
    assert "firma: de esta instalación" in listed.output


@needs_tools
def test_verifying_an_altered_backup_ends_with_an_error(app, golden):
    folder = Path(app.config["BACKUPS_DIR"])
    folder.mkdir(parents=True, exist_ok=True)
    members = _members(golden)
    altered = _tamper_attachment_content(members, None)
    _rewrite(folder / golden.name, list(altered.items()))

    result = _run(app, "backup-verify", golden.name)

    assert result.exit_code == 1
    assert "Problema: " in result.output
    assert "El respaldo no se debe restaurar." in result.output


def test_verifying_without_backups_says_so(app):
    result = _run(app, "backup-verify")

    assert result.exit_code == 1
    assert "No hay respaldos" in result.output


def test_the_list_points_out_interrupted_backups(app):
    folder = Path(app.config["BACKUPS_DIR"])
    (folder / f"{package.TEMP_PREFIX}abc").mkdir(parents=True)

    result = _run(app, "backup-list")

    assert "No hay respaldos" in result.output
    assert f"{package.TEMP_PREFIX}abc" in result.output


def test_a_failed_creation_ends_with_an_error(app, monkeypatch):
    monkeypatch.setitem(app.config, "PG_BIN_DIR", str(Path(app.config["BACKUPS_DIR"]) / "sin-herramientas"))

    result = _run(app, "backup-create")

    assert result.exit_code == 1
    assert "No se creó el respaldo." in result.output
    assert "PG_BIN_DIR" in result.output
    assert [row.resultado for row in _audit_rows(app)] == [AuditResult.FALLIDO]
