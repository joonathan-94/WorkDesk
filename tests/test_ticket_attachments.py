"""Adjuntos de un ticket (docs/06, RN-160).

Cubre el almacenamiento local (`tickets/storage.py`), el servicio
(`tickets/attachments.py`), la visibilidad (el adjunto de una nota interna
nunca llega al Solicitante) y las pantallas, incluida la descarga.
"""

import hashlib
import re
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path

import pytest
from flask_login import AnonymousUserMixin
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from werkzeug.datastructures import FileStorage

from src.workdesk import create_app
from src.workdesk.extensions import db
from src.workdesk.models import (
    Attachment,
    Comment,
    CommentType,
    Ticket,
    TicketEvent,
    TicketHistory,
    User,
)
from src.workdesk.models.ticket_history import (
    DEFAULT_EVENT_VISIBILITY,
    TICKET_EVENT_LABELS,
)
from src.workdesk.security import can_view_attachment
from src.workdesk.tickets import storage
from src.workdesk.tickets.attachments import (
    add_attachments,
    attachment_path,
    delete_attachment,
    discard_files,
    get_attachment,
    list_attachments,
    visible_attachments_condition,
)
from src.workdesk.tickets.comments import add_comment, delete_comment
from src.workdesk.tickets.editing import describe_history_changes
from src.workdesk.tickets.service import TicketRuleError, list_ticket_history
from src.workdesk.tickets.versioning import TicketClosedError
from tests.ticket_helpers import login, make_ticket, plain_text, set_state

PNG = b"\x89PNG\r\n\x1a\n" + b"fake-image-data" * 10
PDF = b"%PDF-1.4\n" + b"fake-pdf" * 10
ZIP = b"PK\x03\x04" + b"fake-docx" * 10
JPG = b"\xff\xd8\xff\xe0" + b"fake-jpg" * 10
GIF = b"GIF89a" + b"fake-gif" * 10
TEXT = "Línea de log\nOtra línea\n".encode()
STAFF = ("tec", "sup", "admin")


# --- Ayudas -----------------------------------------------------------


def upload(name, data=PNG, content_type=None):
    return FileStorage(stream=BytesIO(data), filename=name, content_type=content_type)


def files_in(root):
    """Archivos físicos (no directorios) bajo la raíz."""
    return sorted(p for p in Path(root).rglob("*") if p.is_file())


@pytest.fixture()
def team(make_user, catalog):
    return {
        "req": make_user("SOLICITANTE", username="req1", nombre="Javiera", apellido="Torres"),
        "other": make_user("SOLICITANTE", username="req2", nombre="Paula", apellido="Contreras"),
        "tec": make_user("TECNICO", username="tec1", nombre="Diego", apellido="Soto"),
        "tec2": make_user("TECNICO", username="tec2", nombre="Valentina", apellido="Pizarro"),
        "sup": make_user("SUPERVISOR", username="sup1", nombre="Camila", apellido="Rojas"),
        "admin": make_user("ADMINISTRADOR", username="admin1", nombre="Ana", apellido="Admin"),
    }


def user(team, key) -> User:
    return db.session.get(User, team[key]["id"])


def get_ticket(public_id) -> Ticket:
    return db.session.scalar(db.select(Ticket).where(Ticket.public_id == public_id))


def new_ticket(app, catalog, team):
    return make_ticket(
        app, catalog, team["req"]["id"], requester_ids=[team["req"]["id"]]
    )


def attach(public_id, team, who="req", files=None, comment=None):
    created = add_attachments(
        get_ticket(public_id),
        actor=user(team, who),
        uploads=[upload("captura.png")] if files is None else files,
        comment=comment,
    )
    db.session.commit()

    return created


def comment_on(public_id, team, who="tec", kind=CommentType.PUBLICO, text="Hola"):
    comment = add_comment(get_ticket(public_id), actor=user(team, who), content=text, kind=kind)
    db.session.commit()

    return comment


def events(ticket_id, *types):
    statement = (
        db.select(TicketHistory)
        .where(TicketHistory.ticket_id == ticket_id)
        .order_by(TicketHistory.id)
    )

    if types:
        statement = statement.where(TicketHistory.tipo_evento.in_([t.value for t in types]))

    return list(db.session.scalars(statement))


def post_files(client, url, *files, data=None):
    payload = dict(data or {})
    payload["archivos"] = [(BytesIO(content), name) for name, content in files]

    return client.post(url, data=payload, content_type="multipart/form-data")


def strip_tags(html):
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


# --- Almacenamiento ---------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("captura.png", "captura.png"),
        ("../../etc/passwd", "passwd"),
        ("C:\\Users\\yo\\informe.pdf", "informe.pdf"),
        ("con\x00control\x1f.txt", "concontrol.txt"),
        ("  ..oculto.txt  ", "oculto.txt"),
        ("", "archivo"),
        (None, "archivo"),
        ("///", "archivo"),
        ("ñandú año.txt", "ñandú año.txt"),
    ],
)
def test_the_filename_is_cleaned_and_never_a_path(raw, expected):
    assert storage.clean_filename(raw) == expected


def test_a_long_name_is_shortened_keeping_its_extension():
    cleaned = storage.clean_filename("x" * 400 + ".pdf")

    assert len(cleaned) == storage.MAX_NAME_LENGTH
    assert cleaned.endswith(".pdf")


@pytest.mark.parametrize(
    "name",
    ["virus.exe", "pagina.html", "dibujo.svg", "script.js", "shell.php", "todo.zip",
     "sinextension", "doble.png.exe", ".png", "bat.cmd"],
)
def test_types_outside_the_whitelist_are_rejected(tmp_path, name):
    with pytest.raises(storage.UploadError, match="no está permitido"):
        storage.store_upload(upload(name), tmp_path, 1000)

    assert files_in(tmp_path) == []


@pytest.mark.parametrize(
    ("name", "data"),
    [
        ("falsa.png", TEXT),
        ("falsa.jpg", PNG),
        ("falsa.gif", PDF),
        ("falsa.pdf", PNG),
        ("falsa.docx", PDF),
        ("falsa.xlsx", TEXT),
        ("binario.txt", b"abc\x00def"),
    ],
)
def test_the_content_must_match_the_extension(tmp_path, name, data):
    with pytest.raises(storage.UploadError):
        storage.store_upload(upload(name, data), tmp_path, 1000)

    assert files_in(tmp_path) == []


@pytest.mark.parametrize(
    ("name", "data", "mime"),
    [
        ("a.png", PNG, "image/png"),
        ("a.JPG", JPG, "image/jpeg"),
        ("a.jpeg", JPG, "image/jpeg"),
        ("a.gif", GIF, "image/gif"),
        ("a.pdf", PDF, "application/pdf"),
        ("a.txt", TEXT, "text/plain"),
        ("a.log", TEXT, "text/plain"),
        ("a.csv", b"a,b\n1,2\n", "text/csv"),
        ("a.docx", ZIP, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("a.xlsx", ZIP, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ],
)
def test_valid_files_are_stored_with_an_internal_name_and_their_hash(
    tmp_path, name, data, mime
):
    stored = storage.store_upload(upload(name, data), tmp_path, 1_000_000)
    now = datetime.now(UTC)

    assert stored.mime_type == mime
    assert stored.size == len(data)
    assert stored.sha256 == hashlib.sha256(data).hexdigest()
    assert re.fullmatch(r"[0-9a-f]{32}", stored.internal_name)
    assert stored.relative_path == f"{now:%Y}/{now:%m}/{stored.internal_name}"
    assert (tmp_path / stored.relative_path).read_bytes() == data
    # Solo queda el archivo final: ningún temporal.
    assert files_in(tmp_path) == [tmp_path / stored.relative_path]


def test_the_physical_name_never_contains_the_original(tmp_path):
    stored = storage.store_upload(upload("informe secreto.pdf", PDF), tmp_path, 1000)

    assert "informe" not in stored.relative_path
    assert stored.original_name == "informe secreto.pdf"


def test_the_declared_mime_type_is_ignored(tmp_path):
    stored = storage.store_upload(
        upload("a.png", PNG, content_type="text/html"), tmp_path, 1000
    )

    assert stored.mime_type == "image/png"


def test_the_size_limit_is_exact_and_leaves_nothing_behind(tmp_path):
    data = PNG + b"x" * 100

    assert storage.store_upload(upload("ok.png", data), tmp_path, len(data)).size == len(data)

    with pytest.raises(storage.UploadError, match="tamaño máximo"):
        storage.store_upload(upload("big.png", data), tmp_path, len(data) - 1)

    assert len(files_in(tmp_path)) == 1


def test_a_file_bigger_than_one_chunk_is_hashed_in_blocks(tmp_path):
    data = PNG + b"z" * (storage.CHUNK_SIZE * 3 + 17)
    stored = storage.store_upload(upload("grande.png", data), tmp_path, len(data))

    assert stored.sha256 == hashlib.sha256(data).hexdigest()
    assert stored.size == len(data)


def test_an_empty_file_is_rejected(tmp_path):
    with pytest.raises(storage.UploadError, match="vacío"):
        storage.store_upload(upload("vacio.txt", b""), tmp_path, 1000)

    assert files_in(tmp_path) == []


def test_paths_cannot_leave_the_storage_root(tmp_path):
    assert storage.absolute_path(tmp_path, "2026/11/abc") == (tmp_path / "2026/11/abc").resolve()

    for relative in ("../fuera", "2026/../../fuera", "/etc/passwd"):
        with pytest.raises(ValueError):
            storage.absolute_path(tmp_path, relative)

    outside = tmp_path.parent / "intacto.txt"
    outside.write_text("no me borres")
    storage.remove_file(tmp_path, "../intacto.txt")

    assert outside.exists()


# --- Modelo y configuración -------------------------------------------


@pytest.mark.parametrize("key", ["UPLOAD_MAX_BYTES", "UPLOAD_MAX_FILES_PER_TICKET"])
def test_the_app_rejects_non_positive_upload_limits(key):
    config = {
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        key: 0,
    }

    with pytest.raises(RuntimeError, match=key):
        create_app(config)


def test_the_defaults_and_the_request_limit(app):
    assert app.config["UPLOAD_MAX_BYTES"] == 10 * 1024 * 1024
    assert app.config["UPLOAD_MAX_FILES_PER_TICKET"] == 20
    assert app.config["MAX_CONTENT_LENGTH"] > app.config["UPLOAD_MAX_BYTES"]
    # Fuera de `static/`.
    assert "static" not in Path(app.config["UPLOADS_DIR"]).parts


@pytest.mark.parametrize(
    "kind", [TicketEvent.ARCHIVO_ADJUNTADO, TicketEvent.ARCHIVO_ELIMINADO]
)
def test_file_events_default_to_internal_and_have_a_name(kind):
    assert DEFAULT_EVENT_VISIBILITY[kind].value == "INTERNO"
    assert TICKET_EVENT_LABELS[kind]


def test_the_database_rejects_inconsistent_attachments(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        base = {
            "ticket_id": get_ticket(public_id).id,
            "nombre_original": "a.png",
            "nombre_interno": "i" * 32,
            "ruta_archivo": "2026/11/x",
            "mime_type": "image/png",
            "tamano_bytes": 1,
            "hash": "h" * 64,
            "usuario_subida_id": team["req"]["id"],
        }

        for values in ({"activo": False}, {"tamano_bytes": -1}):
            db.session.add(Attachment(**{**base, **values}))

            with pytest.raises(IntegrityError):
                db.session.flush()

            db.session.rollback()

        # El nombre interno es único.
        db.session.add(Attachment(**base))
        db.session.add(Attachment(**base))

        with pytest.raises(IntegrityError):
            db.session.flush()

        db.session.rollback()


# --- Servicio: subir --------------------------------------------------


def test_an_attachment_is_stored_with_its_metadata_and_a_public_event(
    app, catalog, team
):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        (item,) = attach(public_id, team, "req", [upload("captura.png", PNG)])
        ticket = get_ticket(public_id)

        assert item.nombre_original == "captura.png"
        assert item.mime_type == "image/png"
        assert item.tamano_bytes == len(PNG)
        assert item.hash == hashlib.sha256(PNG).hexdigest()
        assert item.usuario_subida_id == team["req"]["id"]
        assert item.comentario_id is None
        assert item.activo is True
        assert attachment_path(item).read_bytes() == PNG

        # Es aditivo: no sube la versión ni cuenta como una modificación.
        assert ticket.version == 1
        assert ticket.fecha_modificacion is None

        (entry,) = events(ticket.id, TicketEvent.ARCHIVO_ADJUNTADO)

        assert entry.visibilidad == "PUBLICO"
        assert entry.detalle == "Archivo adjuntado: captura.png."
        assert entry.valor_nuevo == {
            "archivo_id": item.id,
            "nombre": "captura.png",
            "tamano_bytes": len(PNG),
            "comentario_id": None,
        }
        assert entry.contexto == {"archivo_id": item.id}
        assert describe_history_changes(entry) == ["Archivo: «captura.png»"]


def test_an_attachment_on_a_note_records_an_internal_event(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        note = comment_on(public_id, team, "tec", CommentType.INTERNO, "Nota")
        (item,) = attach(public_id, team, "tec", comment=note)

        (entry,) = events(get_ticket(public_id).id, TicketEvent.ARCHIVO_ADJUNTADO)

        assert item.comentario_id == note.id
        assert entry.visibilidad == "INTERNO"


def test_empty_form_parts_are_ignored(app, catalog, team, tmp_path):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        # El navegador envía una parte sin nombre cuando no se elige archivo.
        assert attach(public_id, team, files=[upload("", b"")]) == []
        assert attach(public_id, team, files=[]) == []
        assert events(get_ticket(public_id).id, TicketEvent.ARCHIVO_ADJUNTADO) == []


def test_too_many_files_in_one_request_are_rejected_without_leftovers(
    app, catalog, team
):
    public_id = new_ticket(app, catalog, team)
    many = [upload(f"{n}.png") for n in range(storage.MAX_FILES_PER_REQUEST + 1)]

    with app.app_context(), pytest.raises(TicketRuleError, match="hasta 5"):
        attach(public_id, team, files=many)

    with app.app_context():
        assert db.session.scalars(db.select(Attachment)).all() == []
        assert files_in(app.config["UPLOADS_DIR"]) == []


def test_the_ticket_file_limit_counts_active_files_only(app, catalog, team):
    public_id = new_ticket(app, catalog, team)
    app.config["UPLOAD_MAX_FILES_PER_TICKET"] = 2

    with app.app_context():
        first, _ = attach(public_id, team, files=[upload("a.png"), upload("b.png")])

        with pytest.raises(TicketRuleError, match="hasta 2 archivos"):
            attach(public_id, team, files=[upload("c.png")])

        db.session.rollback()
        delete_attachment(get_ticket(public_id), first.id, actor=user(team, "sup"))
        db.session.commit()

        # Eliminado el primero, vuelve a haber lugar.
        attach(public_id, team, files=[upload("c.png")])


def test_a_bad_file_in_a_batch_leaves_no_file_and_no_row(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        with pytest.raises(TicketRuleError, match="no está permitido"):
            attach(public_id, team, files=[upload("ok.png"), upload("malo.exe", b"MZ")])

        db.session.rollback()

        assert db.session.scalars(db.select(Attachment)).all() == []
        assert files_in(app.config["UPLOADS_DIR"]) == []


def test_a_closed_ticket_admits_no_attachments(app, catalog, team):
    public_id = new_ticket(app, catalog, team)
    set_state(app, public_id, "CERRADO")

    with app.app_context(), pytest.raises(TicketClosedError, match="reabrir"):
        attach(public_id, team, "tec")


def test_an_inactive_actor_cannot_attach(app, catalog, team, make_user):
    inactive = make_user("TECNICO", username="tec_off", activo=False)
    public_id = new_ticket(app, catalog, team)

    with app.app_context(), pytest.raises(TicketRuleError, match="no está activo"):
        add_attachments(
            get_ticket(public_id),
            actor=db.session.get(User, inactive["id"]),
            uploads=[upload("a.png")],
        )


def test_a_rolled_back_upload_can_be_discarded(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        (item,) = add_attachments(
            get_ticket(public_id), actor=user(team, "req"), uploads=[upload("a.png")]
        )
        path = attachment_path(item)
        relative = item.ruta_archivo
        db.session.rollback()

        assert db.session.scalars(db.select(Attachment)).all() == []
        assert path.exists()

        discard_files([relative])

        assert not path.exists()


# --- Servicio: eliminar -----------------------------------------------


def test_deleting_is_logical_and_keeps_the_physical_file(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        (item,) = attach(public_id, team)
        path = attachment_path(item)

        delete_attachment(get_ticket(public_id), item.id, actor=user(team, "sup"))
        db.session.commit()
        db.session.refresh(item)

        assert item.activo is False
        assert item.fecha_eliminacion is not None
        assert item.usuario_eliminacion_id == team["sup"]["id"]
        assert path.exists()
        assert list_attachments(get_ticket(public_id), user(team, "tec")) == []

        (entry,) = events(get_ticket(public_id).id, TicketEvent.ARCHIVO_ELIMINADO)

        assert entry.visibilidad == "PUBLICO"
        assert entry.valor_anterior["nombre"] == "captura.png"

        with pytest.raises(TicketRuleError, match="ya no existe"):
            delete_attachment(get_ticket(public_id), item.id, actor=user(team, "sup"))


def test_deleting_an_unknown_or_foreign_attachment_is_rejected(app, catalog, team):
    first = new_ticket(app, catalog, team)
    second = new_ticket(app, catalog, team)

    with app.app_context():
        (foreign,) = attach(second, team)

        for attachment_id in (999_999, foreign.id):
            with pytest.raises(TicketRuleError, match="ya no existe"):
                delete_attachment(get_ticket(first), attachment_id, actor=user(team, "sup"))

            db.session.rollback()


# --- Visibilidad ------------------------------------------------------


def _setup_visibility(public_id, team):
    standalone = attach(public_id, team, "req", [upload("suelto.png")])[0]
    public_comment = comment_on(public_id, team, "tec", CommentType.PUBLICO, "Pública")
    public_file = attach(public_id, team, "tec", [upload("publico.png")], public_comment)[0]
    note = comment_on(public_id, team, "tec", CommentType.INTERNO, "Nota")
    note_file = attach(public_id, team, "tec", [upload("interno.png")], note)[0]

    return standalone, public_file, note_file, note


def test_the_requester_never_gets_the_attachment_of_a_note(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        _, public_file, note_file, _ = _setup_visibility(public_id, team)
        ticket = get_ticket(public_id)

        def names(key):
            return [a.nombre_original for a in list_attachments(ticket, user(team, key))]

        assert names("req") == ["suelto.png", "publico.png"]
        assert names("tec") == names("sup") == ["suelto.png", "publico.png", "interno.png"]
        assert get_attachment(ticket, note_file.id, user(team, "req")) is None
        assert get_attachment(ticket, note_file.id, user(team, "tec")).id == note_file.id
        assert get_attachment(ticket, public_file.id, user(team, "req")).id == public_file.id


def test_deleting_the_comment_hides_its_attachments_from_everyone(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        comment = comment_on(public_id, team, "tec")
        (item,) = attach(public_id, team, "tec", comment=comment)

        delete_comment(get_ticket(public_id), comment.id, actor=user(team, "sup"))
        db.session.commit()

        for key in ("req", "tec", "sup"):
            assert get_attachment(get_ticket(public_id), item.id, user(team, key)) is None


def test_the_sql_visibility_matches_the_policy(app, catalog, team, make_user):
    inactive = make_user("SOLICITANTE", username="req_off")
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        _setup_visibility(public_id, team)
        gone = comment_on(public_id, team, "tec", CommentType.PUBLICO, "Se va")
        gone_file = attach(public_id, team, "tec", [upload("huerfano.png")], gone)[0]
        delete_comment(get_ticket(public_id), gone.id, actor=user(team, "sup"))
        db.session.get(User, inactive["id"]).activo = False
        db.session.commit()

        everything = list(db.session.scalars(db.select(Attachment)))
        people = [user(team, key) for key in team]
        people += [db.session.get(User, inactive["id"]), AnonymousUserMixin()]

        for person in people:
            visible = {
                a.id
                for a in db.session.scalars(
                    db.select(Attachment).where(visible_attachments_condition(person))
                )
            }

            for item in everything:
                assert (item.id in visible) is can_view_attachment(person, item), (
                    getattr(person, "username", "anónimo"),
                    item.nombre_original,
                )

        assert gone_file.id in {a.id for a in everything}


def test_the_requester_does_not_see_note_file_events_in_the_history(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        _setup_visibility(public_id, team)

        def kinds(key):
            return [
                e.detalle
                for e in list_ticket_history(get_ticket(public_id), user(team, key))
                if e.tipo_evento == "ARCHIVO_ADJUNTADO"
            ]

        assert "Archivo adjuntado: interno.png." not in kinds("req")
        assert len(kinds("req")) == 2
        assert len(kinds("tec")) == 3


# --- Pantallas: subir y descargar -------------------------------------


def test_a_requester_uploads_and_downloads_a_file(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)
    login(client, team["req"])

    response = post_files(
        client, f"/tickets/{public_id}/attachments", ("Captura de pantalla.png", PNG),
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("#archivos")

    page = strip_tags(client.get(f"/tickets/{public_id}").get_data(as_text=True))

    assert "Archivos (1)" in page
    assert "Captura de pantalla.png" in page
    assert "Archivo adjuntado" in page

    with app.app_context():
        item = db.session.scalar(db.select(Attachment))
        item_id = item.id

    download = client.get(f"/tickets/{public_id}/attachments/{item_id}/download")

    assert download.status_code == 200
    assert download.data == PNG
    assert download.mimetype == "image/png"
    assert "attachment" in download.headers["Content-Disposition"]
    assert "Captura de pantalla.png" in download.headers["Content-Disposition"]
    assert download.headers["X-Content-Type-Options"] == "nosniff"
    assert "no-store" in download.headers["Cache-Control"]


def test_the_flash_messages_follow_the_result(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)
    login(client, team["tec"])
    url = f"/tickets/{public_id}/attachments"

    one = client.post(url, data={"archivos": (BytesIO(PNG), "a.png")}, follow_redirects=True)
    two = post_files(client, url, ("b.png", PNG), ("c.pdf", PDF))
    none = client.post(url, data={}, follow_redirects=True)
    bad = post_files(client, url, ("malo.exe", b"MZ"))

    assert "Archivo adjuntado." in plain_text(one)
    assert two.status_code == 302
    assert "Elige al menos un archivo." in plain_text(none)
    assert "no está permitido" in plain_text(client.get(bad.headers["Location"]))

    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(Attachment.id))) == 3


def test_an_oversized_file_is_rejected_with_a_message(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)
    app.config["UPLOAD_MAX_BYTES"] = 100
    login(client, team["tec"])

    response = post_files(
        client, f"/tickets/{public_id}/attachments", ("grande.png", PNG + b"x" * 200),
    )

    assert "supera el tamaño máximo" in plain_text(client.get(response.headers["Location"]))

    with app.app_context():
        assert files_in(app.config["UPLOADS_DIR"]) == []


def test_a_request_over_the_total_limit_answers_413(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)
    app.config["MAX_CONTENT_LENGTH"] = 2000
    login(client, team["tec"])

    response = post_files(
        client, f"/tickets/{public_id}/attachments", ("enorme.png", PNG + b"x" * 5000),
    )

    assert response.status_code == 413
    assert "Archivo demasiado grande" in plain_text(response)


def test_someone_without_access_gets_a_404_on_every_attachment_route(
    client, app, catalog, team
):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        item_id = attach(public_id, team)[0].id

    login(client, team["other"])
    base = f"/tickets/{public_id}/attachments"

    assert post_files(client, base, ("a.png", PNG)).status_code == 404
    assert client.get(f"{base}/{item_id}/download").status_code == 404
    assert client.get(f"{base}/{item_id}/delete").status_code == 404
    assert client.post(f"{base}/{item_id}/delete").status_code == 404


def test_nonexistent_tickets_and_attachments_are_404(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)
    login(client, team["sup"])

    for target in ("999999", "abc"):
        assert client.get(f"/tickets/{target}/attachments/1/download").status_code == 404

    assert client.get(f"/tickets/{public_id}/attachments/999999/download").status_code == 404
    assert client.get(f"/tickets/{public_id}/attachments/999999/delete").status_code == 404


def test_an_attachment_id_from_another_ticket_is_a_404(client, app, catalog, team):
    first = new_ticket(app, catalog, team)
    second = new_ticket(app, catalog, team)

    with app.app_context():
        foreign = attach(second, team)[0].id

    login(client, team["sup"])

    assert client.get(f"/tickets/{first}/attachments/{foreign}/download").status_code == 404


def test_the_note_attachment_is_a_404_for_the_requester_but_not_for_staff(
    client, app, catalog, team
):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        _, _, note_file, _ = _setup_visibility(public_id, team)
        note_file_id = note_file.id

    url = f"/tickets/{public_id}/attachments/{note_file_id}"

    login(client, team["req"])
    html = client.get(f"/tickets/{public_id}").get_data(as_text=True)

    assert client.get(f"{url}/download").status_code == 404
    assert client.get(f"{url}/delete").status_code == 404
    assert client.post(f"{url}/delete").status_code == 404
    assert "interno.png" not in html
    assert "Nota interna" not in html

    client.post("/logout")
    login(client, team["tec"])

    assert client.get(f"{url}/download").data == PNG
    assert "interno.png" in client.get(f"/tickets/{public_id}").get_data(as_text=True)


def test_a_comment_with_files_publishes_both_and_shares_visibility(
    client, app, catalog, team
):
    public_id = new_ticket(app, catalog, team)
    login(client, team["tec"])
    url = f"/tickets/{public_id}/comments"

    post_files(client, url, ("log.txt", TEXT), data={"contenido": "Adjunto el log", "tipo": "PUBLICO"})
    post_files(client, url, ("secreto.pdf", PDF), data={"contenido": "Nota con archivo", "tipo": "INTERNO"})

    with app.app_context():
        rows = db.session.scalars(db.select(Attachment).order_by(Attachment.id)).all()
        comments = db.session.scalars(db.select(Comment).order_by(Comment.id)).all()

        assert [(a.nombre_original, a.comentario_id) for a in rows] == [
            ("log.txt", comments[0].id),
            ("secreto.pdf", comments[1].id),
        ]

    client.post("/logout")
    login(client, team["req"])
    html = client.get(f"/tickets/{public_id}").get_data(as_text=True)

    assert "log.txt" in html
    assert "secreto.pdf" not in html
    assert "Nota con archivo" not in html


def test_a_bad_file_with_a_comment_saves_nothing_and_keeps_the_text(
    client, app, catalog, team
):
    public_id = new_ticket(app, catalog, team)
    login(client, team["tec"])

    response = post_files(
        client,
        f"/tickets/{public_id}/comments",
        ("malo.exe", b"MZ"),
        data={"contenido": "Texto que no debe perderse", "tipo": "PUBLICO"},
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "no está permitido" in strip_tags(html)
    assert "Texto que no debe perderse" in html

    with app.app_context():
        assert db.session.scalars(db.select(Comment)).all() == []
        assert db.session.scalars(db.select(Attachment)).all() == []
        assert files_in(app.config["UPLOADS_DIR"]) == []


def test_a_deleted_comment_makes_its_file_undownloadable(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        comment = comment_on(public_id, team, "tec")
        item_id = attach(public_id, team, "tec", comment=comment)[0].id
        delete_comment(get_ticket(public_id), comment.id, actor=user(team, "sup"))
        db.session.commit()

    login(client, team["sup"])

    assert client.get(f"/tickets/{public_id}/attachments/{item_id}/download").status_code == 404


def test_a_missing_or_tampered_physical_file_is_a_404(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        item = attach(public_id, team)[0]
        item_id = item.id
        attachment_path(item).unlink()

    login(client, team["sup"])
    url = f"/tickets/{public_id}/attachments/{item_id}/download"

    assert client.get(url).status_code == 404

    # Una ruta manipulada en la base de datos nunca sale de la raíz.
    with app.app_context():
        db.session.execute(
            update(Attachment.__table__)
            .where(Attachment.__table__.c.id == item_id)
            .values(ruta_archivo="../../etc/passwd")
        )
        db.session.commit()

    assert client.get(url).status_code == 404


def test_a_closed_ticket_has_no_uploader_but_still_allows_downloads(
    client, app, catalog, team
):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        item_id = attach(public_id, team)[0].id

    set_state(app, public_id, "CERRADO")
    login(client, team["req"])
    html = client.get(f"/tickets/{public_id}").get_data(as_text=True)

    assert f"/tickets/{public_id}/attachments\"" not in html
    assert "Un ticket cerrado no admite archivos nuevos." in strip_tags(html)
    assert client.get(f"/tickets/{public_id}/attachments/{item_id}/download").data == PNG

    response = post_files(client, f"/tickets/{public_id}/attachments", ("a.png", PNG))

    assert "Un ticket cerrado no se puede modificar." in plain_text(
        client.get(response.headers["Location"])
    )


def test_uploading_does_not_change_the_updated_date(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)
    login(client, team["tec"])

    post_files(client, f"/tickets/{public_id}/attachments", ("a.png", PNG))

    with app.app_context():
        assert get_ticket(public_id).fecha_modificacion is None
        assert get_ticket(public_id).version == 1


def test_file_names_are_shown_escaped(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        attach(public_id, team, files=[upload("<i>x&.txt", TEXT)])

    login(client, team["tec"])
    html = client.get(f"/tickets/{public_id}").get_data(as_text=True)

    assert "&lt;i&gt;x&amp;.txt" in html
    assert "<i>x&.txt" not in html


# --- Pantallas: eliminar ----------------------------------------------


def test_deleting_asks_for_confirmation_and_then_hides_the_file(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        item_id = attach(public_id, team)[0].id

    login(client, team["req"])
    url = f"/tickets/{public_id}/attachments/{item_id}/delete"

    assert "Eliminar archivo" in plain_text(client.get(url))

    with app.app_context():
        assert db.session.get(Attachment, item_id).activo is True

    response = client.post(url, follow_redirects=True)

    assert "Archivo eliminado." in plain_text(response)
    assert "Archivos (0)" in strip_tags(response.get_data(as_text=True))
    assert client.get(f"/tickets/{public_id}/attachments/{item_id}/download").status_code == 404


def test_the_delete_rule_follows_the_author_window_and_supervision(
    client, app, catalog, team
):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        item_id = attach(public_id, team, "tec")[0].id

    url = f"/tickets/{public_id}/attachments/{item_id}/delete"

    for key, status in (("tec2", 403), ("req", 403), ("tec", 200), ("sup", 200), ("admin", 200)):
        client.post("/logout")
        login(client, team[key])

        assert client.get(url).status_code == status, key

    with app.app_context():
        db.session.execute(
            update(Attachment.__table__)
            .where(Attachment.__table__.c.id == item_id)
            .values(fecha_subida=datetime.now(UTC) - timedelta(minutes=31))
        )
        db.session.commit()

    client.post("/logout")
    login(client, team["tec"])

    assert client.get(url).status_code == 403
    assert client.post(url).status_code == 403

    client.post("/logout")
    login(client, team["sup"])

    assert client.post(url).status_code == 302


def test_the_delete_screen_redirects_for_a_closed_ticket(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        item_id = attach(public_id, team)[0].id

    set_state(app, public_id, "CERRADO")
    login(client, team["sup"])
    response = client.get(
        f"/tickets/{public_id}/attachments/{item_id}/delete", follow_redirects=True
    )

    assert "Un ticket cerrado no se puede modificar." in plain_text(response)

    with app.app_context():
        assert db.session.get(Attachment, item_id).activo is True


def test_the_history_lines_for_files_never_show_content(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        (item,) = attach(public_id, team, files=[upload("informe.pdf", PDF)])
        delete_attachment(get_ticket(public_id), item.id, actor=user(team, "sup"))
        db.session.commit()

        lines = [
            describe_history_changes(e)
            for e in events(
                get_ticket(public_id).id,
                TicketEvent.ARCHIVO_ADJUNTADO,
                TicketEvent.ARCHIVO_ELIMINADO,
            )
        ]

    assert lines == [["Archivo: «informe.pdf»"], ["Archivo: «informe.pdf»"]]
