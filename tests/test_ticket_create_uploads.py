"""Adjuntos desde el formulario de creación de un ticket (docs/06, RN-160)."""

from io import BytesIO
from pathlib import Path

import pytest

from src.workdesk.extensions import db
from src.workdesk.models import Attachment, Ticket, TicketEvent, TicketHistory
from tests.ticket_helpers import login, plain_text

PNG = b"\x89PNG\r\n\x1a\n" + b"fake-image-data" * 10
TEXT = "Línea de log\n".encode()


@pytest.fixture()
def people(make_user, catalog):
    return {
        "req": make_user("SOLICITANTE", username="req_up"),
        "otro": make_user("SOLICITANTE", username="otro_up"),
        "tec": make_user("TECNICO", username="tec_up"),
    }


def _files_on_disk(app):
    return sorted(p for p in Path(app.config["UPLOADS_DIR"]).rglob("*") if p.is_file())


def _data(app, catalog, **changes):
    with app.app_context():
        values = {
            "titulo": "Pantalla con rayas",
            "descripcion": "Adjunto una foto.",
            "categoria": str(catalog["hardware"]),
            "prioridad": str(catalog["medium"]),
        }

    values.update(changes)

    return values


def _post(client, data, *files):
    payload = dict(data)
    payload["archivos"] = [(BytesIO(content), name) for name, content in files]

    return client.post("/tickets/new", data=payload, content_type="multipart/form-data")


def _counts(app):
    with app.app_context():
        return (
            db.session.scalar(db.select(db.func.count(Ticket.id))),
            db.session.scalar(db.select(db.func.count(Attachment.id))),
        )


def test_the_form_accepts_files_and_says_its_limits(client, people):
    login(client, people["req"])

    html = client.get("/tickets/new").get_data(as_text=True)

    assert 'enctype="multipart/form-data"' in html
    assert 'type="file"' in html and 'name="archivos"' in html
    assert "Hasta 5 archivos de 10 MB" in plain_text(client.get("/tickets/new"))


@pytest.mark.parametrize("who", ["req", "tec"])
def test_a_ticket_is_created_with_its_files(app, client, catalog, people, who):
    login(client, people[who])

    response = _post(
        client, _data(app, catalog), ("foto.png", PNG), ("traza.log", TEXT)
    )

    assert response.status_code == 302
    assert _counts(app) == (1, 2)
    assert len(_files_on_disk(app)) == 2
    detail = client.get(response.headers["Location"])
    assert "foto.png" in plain_text(detail) and "traza.log" in plain_text(detail)

    with app.app_context():
        events = db.session.scalars(
            db.select(TicketHistory.tipo_evento).order_by(TicketHistory.id)
        ).all()

    assert events.count(TicketEvent.ARCHIVO_ADJUNTADO.value) == 2
    assert events[0] == TicketEvent.TICKET_CREADO.value


def test_the_files_belong_to_the_ticket_and_the_requester_can_download_them(
    app, client, catalog, people
):
    login(client, people["req"])
    response = _post(client, _data(app, catalog), ("foto.png", PNG))
    number = response.headers["Location"].rsplit("/", 1)[1]

    with app.app_context():
        attachment = db.session.scalar(db.select(Attachment))
        assert attachment.comentario_id is None
        assert attachment.usuario_subida_id == people["req"]["id"]
        attachment_id = attachment.id

    download = client.get(f"/tickets/{number}/attachments/{attachment_id}/download")

    assert download.status_code == 200
    assert download.data == PNG
    client.post("/logout")
    login(client, people["otro"])
    assert client.get(f"/tickets/{number}/attachments/{attachment_id}/download").status_code == 404


def test_without_files_it_works_as_before(app, client, catalog, people):
    login(client, people["req"])

    response = _post(client, _data(app, catalog))

    assert response.status_code == 302
    assert _counts(app) == (1, 0)


@pytest.mark.parametrize(
    ("files", "message"),
    [
        ([("programa.exe", b"MZ" * 20)], "no está permitido"),
        ([("foto.png", b"esto no es una imagen" * 5)], "no coincide con su extensión"),
        ([("vacio.txt", b"")], "vacío"),
        ([(f"f{n}.txt", TEXT) for n in range(6)], "hasta 5 archivos"),
    ],
)
def test_a_rejected_file_creates_neither_ticket_nor_files(
    app, client, catalog, people, files, message
):
    login(client, people["req"])

    response = _post(client, _data(app, catalog), ("bueno.png", PNG), *files)

    assert response.status_code == 200
    assert message in plain_text(response)
    # Nada a medias: ni el ticket, ni los registros, ni los archivos en disco.
    assert _counts(app) == (0, 0)
    assert _files_on_disk(app) == []
    assert "Adjunto una foto." in response.get_data(as_text=True)
    assert "Vuelve a elegir tus archivos" in plain_text(response)


def test_the_configured_limits_apply(app, client, catalog, people):
    app.config["UPLOAD_MAX_FILES_PER_TICKET"] = 1
    login(client, people["req"])

    response = _post(client, _data(app, catalog), ("a.txt", TEXT), ("b.txt", TEXT))

    assert "hasta 1 archivos" in plain_text(response)
    assert _counts(app) == (0, 0)


def test_form_errors_ask_to_choose_the_files_again(app, client, catalog, people):
    login(client, people["req"])

    response = _post(client, _data(app, catalog, titulo=""), ("a.png", PNG))

    assert "Vuelve a elegir tus archivos" in plain_text(response)
    assert _counts(app) == (0, 0)
    assert _files_on_disk(app) == []


def test_without_files_no_one_is_asked_to_choose_them(app, client, catalog, people):
    login(client, people["req"])

    response = _post(client, _data(app, catalog, titulo=""))

    assert "Vuelve a elegir" not in plain_text(response)


def test_the_duplicate_warning_keeps_nothing_on_disk(app, client, catalog, people):
    login(client, people["req"])
    assert _post(client, _data(app, catalog)).status_code == 302

    warned = _post(client, _data(app, catalog), ("a.png", PNG))

    assert "Puede que ya exista" in plain_text(warned)
    assert "Vuelve a elegir tus archivos" in plain_text(warned)
    assert _counts(app) == (1, 0)
    assert _files_on_disk(app) == []


def test_a_failure_while_saving_leaves_no_files_behind(
    app, client, catalog, people, monkeypatch
):
    login(client, people["req"])

    def broken_commit():
        raise RuntimeError("la base de datos falló")

    monkeypatch.setattr(db.session, "commit", broken_commit)

    with pytest.raises(RuntimeError):
        _post(client, _data(app, catalog), ("a.png", PNG))

    monkeypatch.undo()
    assert _files_on_disk(app) == []
