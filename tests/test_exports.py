"""La exportación a CSV y XLSX (`exports.py`; RF-099 a RF-101, RN-180).

Lo importante:
- **Nada se ejecuta al abrir el archivo.** Un texto que empieza como una fórmula llega como
  texto: con un apóstrofo en CSV y con el tipo «texto» en XLSX (se mira el XML, donde una
  fórmula sería un `<f>`).
- **El archivo trae lo que se ve:** las mismas filas, en el mismo orden y con las mismas
  columnas que el listado, los reportes o la auditoría de quien exporta, y nada que esa
  persona no pueda ver.
- **Cada exportación queda en la auditoría**, y una demasiado grande pide acotar los filtros.
"""

import csv
import io
import re
import zipfile
from datetime import UTC, date, datetime

import pytest
from openpyxl import load_workbook
from sqlalchemy import event

from src.workdesk import exports, settings
from src.workdesk.audit import AuditAction
from src.workdesk.audit.queries import AuditFilters, AuditView, count_audit_rows
from src.workdesk.configuration import save_setting
from src.workdesk.exports import (
    FORMULA_STARTS,
    ExportFormat,
    Table,
    csv_value,
    neutralize,
    parse_format,
    to_csv,
    to_xlsx,
)
from src.workdesk.extensions import db
from src.workdesk.models import AdminAuditLog, Prioridad, Ticket, User
from src.workdesk.reports import ReportFilters, build_report, preset_period
from src.workdesk.sla import periods as sla_periods
from src.workdesk.sla.evaluation import evaluate_tickets_sla
from src.workdesk.sla.queries import SLA_FILTER_LABELS, filter_of
from src.workdesk.tickets.queries import TAB_ALL, TicketFilters, list_tickets
from tests.demo_data import DEMO_PASSWORD, NOW, SOLICITANTES
from tests.ticket_helpers import login, make_ticket, person

FORMULA = '=HYPERLINK("http://ejemplo.invalid","clic")'


def sign_in(client, username):
    login(client, {"username": username, "password": DEMO_PASSWORD})


def read_csv(response) -> list[list[str]]:
    assert response.data.startswith("﻿".encode())

    return list(csv.reader(io.StringIO(response.data.decode("utf-8-sig"))))


def read_xlsx(response):
    return load_workbook(io.BytesIO(response.data))


def sheet_xml(data: bytes) -> str:
    archive = zipfile.ZipFile(io.BytesIO(data))

    return "".join(
        archive.read(name).decode("utf-8")
        for name in archive.namelist()
        if name.startswith("xl/worksheets/")
    )


# --- Valores y formatos (sin base de datos) ----------------------------------------------


@pytest.mark.parametrize("start", FORMULA_STARTS)
def test_text_that_starts_like_a_formula_is_neutralized(start):
    assert neutralize(f"{start}1+1") == f"'{start}1+1"


@pytest.mark.parametrize("text", ["=1+1", "+1", "-1", "@SUM(A1)", "\t=1", "\r=1"])
def test_every_formula_start_from_owasp_is_covered(text):
    """La lista escrita a mano (no la del módulo): si alguien quitara uno, falla."""
    assert neutralize(text) == "'" + text


@pytest.mark.parametrize("text", ["impresora", "1+1", "correo=caído", "", "'ya citado"])
def test_ordinary_text_is_left_alone(text):
    assert neutralize(text) == text


def test_numbers_are_numbers_and_not_neutralized():
    assert csv_value(-5) == "-5"
    assert csv_value(2.5) == "2.5"
    assert csv_value(None) == ""
    assert csv_value(True) == "Sí"


def test_dates_are_written_in_local_time(app):
    app.config["APP_TIMEZONE"] = "America/Santiago"

    with app.app_context():
        # Las 13:00 UTC son las 10:00 en Santiago en noviembre (UTC-3).
        assert csv_value(datetime(2026, 11, 18, 13, 0, tzinfo=UTC)) == "2026-11-18 10:00"
        assert csv_value(date(2026, 11, 18)) == "2026-11-18"


def test_a_csv_has_a_bom_crlf_and_proper_quoting(app):
    table = Table("T", ["Título", "Nota"], [["con, coma", 'con "comillas"\ny salto'], [FORMULA, None]])

    with app.app_context():
        data = to_csv(table)

    assert data.startswith("﻿".encode())
    assert b"\r\n" in data
    rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig"))))
    assert rows == [
        ["Título", "Nota"],
        ["con, coma", 'con "comillas"\ny salto'],
        ["'" + FORMULA, ""],
    ]


def test_an_xlsx_never_turns_text_into_a_formula(app):
    table = Table("T", ["A", "B", "C", "D"], [[FORMULA, "@SUM(A1)", "-2+3", "#N/A"]])

    with app.app_context():
        data = to_xlsx([table])

    xml = sheet_xml(data)
    sheet = load_workbook(io.BytesIO(data)).active

    assert "<f>" not in xml
    assert [(cell.value, cell.data_type) for cell in sheet[2]] == [
        (FORMULA, "s"),
        ("@SUM(A1)", "s"),
        ("-2+3", "s"),
        # Un código de error de Excel escrito como texto sigue siendo texto.
        ("#N/A", "s"),
    ]


def test_control_characters_never_reach_the_file(app):
    dirty = "uno\x00dos\x07tres\ttab\nlínea"
    table = Table("T", ["Texto"], [[dirty]])

    with app.app_context():
        workbook = load_workbook(io.BytesIO(to_xlsx([table])))
        text = to_csv(table).decode("utf-8-sig")

    assert workbook.active["A2"].value == "unodostres\ttab\nlínea"
    assert "\x00" not in text and "\x07" not in text


def test_an_xlsx_has_typed_cells_a_bold_header_and_a_frozen_first_row(app):
    app.config["APP_TIMEZONE"] = "America/Santiago"
    moment = datetime(2026, 11, 18, 13, 0, tzinfo=UTC)
    table = Table("Datos", ["Número", "Fecha", "Horas"], [[7, moment, 2.5]])

    with app.app_context():
        sheet = load_workbook(io.BytesIO(to_xlsx([table])))["Datos"]

    assert sheet["A1"].font.bold
    assert sheet.freeze_panes == "A2"
    assert sheet["A2"].value == 7
    # Excel no guarda zonas horarias: llega la hora local, sin zona.
    assert sheet["B2"].value == datetime(2026, 11, 18, 10, 0)  # noqa: DTZ001
    assert sheet["B2"].number_format == "dd-mm-yyyy hh:mm"
    assert sheet["C2"].value == 2.5


def test_sheet_names_are_valid_and_never_repeat(app):
    tables = [Table("Por: estado/[x]", ["A"], []), Table("Por: estado/[x]", ["A"], []), Table("x" * 40, ["A"], [])]

    with app.app_context():
        names = load_workbook(io.BytesIO(to_xlsx(tables))).sheetnames

    assert names[0] == "Por  estado  x"
    assert names[1] == "Por  estado  x (2)"
    assert len(names[2]) == 31


@pytest.mark.parametrize(("value", "expected"), [("csv", ExportFormat.CSV), ("xlsx", ExportFormat.XLSX), ("pdf", None), (None, None)])
def test_only_the_two_formats_exist(value, expected):
    assert parse_format(value) is expected


# --- Listado de tickets ------------------------------------------------------------------


def _listing_numbers(app, username, filters, tab, sort="recientes"):
    with app.app_context():
        user = db.session.scalar(db.select(User).where(User.username == username))
        items = list_tickets(user, filters, tab=tab, sort=sort, per_page=1000, now=NOW).items

        return [int(ticket.public_id) for ticket in items]


@pytest.mark.parametrize(
    ("query", "filters", "tab", "sort"),
    [
        ("vista=todos", TicketFilters(), TAB_ALL, "recientes"),
        ("vista=abiertos&orden=prioridad", TicketFilters(), "abiertos", "prioridad"),
        ("vista=todos&q=impresora&orden=antiguos", TicketFilters(query_text="impresora"), TAB_ALL, "antiguos"),
    ],
)
def test_the_listing_export_has_the_rows_of_the_listing_in_its_order(seeded, app, client, query, filters, tab, sort):
    sign_in(client, "camila.rojas")
    rows = read_csv(client.get(f"/tickets/export?formato=csv&{query}"))

    assert [int(row[0]) for row in rows[1:]] == _listing_numbers(app, "camila.rojas", filters, tab, sort)


def test_the_listing_export_follows_the_listing_filters(seeded, app, client):
    with app.app_context():
        critical = db.session.scalar(db.select(Prioridad.id).where(Prioridad.codigo == "CRITICA"))

    sign_in(client, "camila.rojas")
    rows = read_csv(client.get(f"/tickets/export?formato=csv&vista=todos&prioridad={critical}"))

    assert len(rows) > 2
    assert {row[3] for row in rows[1:]} == {"Crítica"}


@pytest.mark.parametrize("username", SOLICITANTES[:3])
def test_a_requester_exports_only_their_tickets_and_nothing_internal(seeded, app, client, username):
    sign_in(client, username)
    response = client.get("/tickets/export?formato=xlsx&vista=todos")
    sheet = read_xlsx(response).active
    headers = [cell.value for cell in sheet[1]]
    numbers = [row[0] for row in sheet.iter_rows(min_row=2, values_only=True)]

    assert numbers == _listing_numbers(app, username, TicketFilters(), TAB_ALL)
    for internal in ("Solicitantes", "Técnicos", "Grupo", "SLA"):
        assert internal not in headers


def test_the_staff_export_has_the_internal_columns(seeded, client):
    sign_in(client, "diego.soto")
    headers = read_csv(client.get("/tickets/export?formato=csv&vista=todos"))[0]

    assert headers[:10] == [
        "Número", "Título", "Estado", "Prioridad", "Categoría", "Ubicación",
        "Solicitantes", "Técnicos", "Grupo", "SLA",
    ]


def test_a_title_written_as_a_formula_arrives_as_text(app, client, make_user, catalog):
    requester = make_user("SOLICITANTE", username="pide")
    make_ticket(app, catalog, requester["id"], requester_ids=[requester["id"]], title=FORMULA)
    login(client, requester)

    rows = read_csv(client.get("/tickets/export?formato=csv&vista=todos"))
    xlsx = client.get("/tickets/export?formato=xlsx&vista=todos")

    assert rows[1][1] == "'" + FORMULA
    assert "<f>" not in sheet_xml(xlsx.data)
    assert read_xlsx(xlsx).active["B2"].value == FORMULA


def test_the_file_is_a_private_download(seeded, client):
    sign_in(client, "camila.rojas")
    response = client.get("/tickets/export?formato=xlsx&vista=todos")

    assert response.status_code == 200
    assert response.mimetype == exports.MIMETYPES[ExportFormat.XLSX]
    assert re.fullmatch(
        r'attachment; filename="workdesk-tickets-\d{4}-\d{2}-\d{2}\.xlsx"',
        response.headers["Content-Disposition"],
    )
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_an_unknown_format_is_not_found(seeded, client):
    sign_in(client, "camila.rojas")

    assert client.get("/tickets/export?formato=pdf").status_code == 404
    assert client.get("/tickets/export").status_code == 404


def test_without_a_session_nothing_is_exported(client):
    response = client.get("/tickets/export?formato=csv")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_too_many_rows_asks_to_narrow_the_filters(seeded, client, monkeypatch):
    monkeypatch.setattr("src.workdesk.tickets.routes.listing.MAX_EXPORT_ROWS", 10)
    sign_in(client, "camila.rojas")

    response = client.get("/tickets/export?formato=csv&vista=todos&q=a", follow_redirects=True)

    assert response.mimetype == "text/html"
    assert "acota los filtros" in response.get_data(as_text=True)


def _exports_in_audit():
    return list(
        db.session.scalars(
            db.select(AdminAuditLog).where(AdminAuditLog.accion == AuditAction.DATOS_EXPORTADOS)
        )
    )


def test_every_export_is_recorded_with_who_what_and_how(seeded, app, client):
    sign_in(client, "camila.rojas")
    rows = read_csv(client.get("/tickets/export?formato=csv&vista=abiertos&q=impresora"))

    with app.app_context():
        (entry,) = _exports_in_audit()
        actor = db.session.get(User, entry.actor_usuario_id)

        assert actor.username == "camila.rojas"
        assert entry.entidad_tipo == "exportacion"
        assert entry.valor_nuevo == {
            "exportacion": "tickets",
            "formato": "csv",
            "filas": len(rows) - 1,
            "filtros": {"q": "impresora", "vista": "abiertos", "orden": "recientes"},
        }


def test_a_refused_export_is_not_recorded(seeded, app, client, monkeypatch):
    monkeypatch.setattr("src.workdesk.tickets.routes.listing.MAX_EXPORT_ROWS", 1)
    sign_in(client, "camila.rojas")
    client.get("/tickets/export?formato=csv&vista=todos")

    with app.app_context():
        assert _exports_in_audit() == []


def _queries(app, client, url):
    seen = []

    def count(*_args):
        seen.append(1)

    with app.app_context():
        event.listen(db.engine, "before_cursor_execute", count)
        try:
            assert client.get(url).status_code == 200
        finally:
            event.remove(db.engine, "before_cursor_execute", count)

    return len(seen)


def test_the_listing_export_reads_in_chunks_without_losing_or_repeating_rows(
    seeded, app, client, monkeypatch
):
    """Con tramos de 7 tickets, los 108 de demostración cruzan muchos tramos."""
    monkeypatch.setattr("src.workdesk.tickets.export.CHUNK", 7)
    sign_in(client, "camila.rojas")
    rows = read_csv(client.get("/tickets/export?formato=csv&vista=todos&orden=prioridad"))

    assert [int(row[0]) for row in rows[1:]] == _listing_numbers(
        app, "camila.rojas", TicketFilters(), TAB_ALL, "prioridad"
    )


def test_the_exported_sla_is_the_one_python_computes(seeded, app, client, monkeypatch):
    """La columna sale de SQL; aquí se compara, ticket a ticket, con la evaluación en
    Python en el mismo instante."""
    monkeypatch.setattr(sla_periods, "current_time", lambda: NOW)
    sign_in(client, "camila.rojas")
    rows = read_csv(client.get("/tickets/export?formato=csv&vista=todos"))
    column = rows[0].index("SLA")
    exported = {int(row[0]): row[column] for row in rows[1:]}

    with app.app_context():
        ids = dict(db.session.execute(db.select(Ticket.public_id, Ticket.id)).all())
        snapshots = evaluate_tickets_sla(list(ids.values()), NOW)
        expected = {
            int(number): SLA_FILTER_LABELS[filter_of(snapshots.get(ticket_id))]
            for number, ticket_id in ids.items()
        }

    assert exported == expected
    assert len(set(exported.values())) >= 4


def test_with_the_sla_off_the_listing_export_has_no_sla_column(seeded, app, client, make_user):
    admin = make_user("ADMINISTRADOR", username="admin_export")

    with app.app_context():
        save_setting(settings.SLA_ENABLED, False, actor=person(admin["id"]))
        db.session.commit()

    sign_in(client, "camila.rojas")
    headers = read_csv(client.get("/tickets/export?formato=csv&vista=todos"))[0]

    assert "Grupo" in headers and "SLA" not in headers


def test_the_listing_export_does_not_cost_a_query_per_row(seeded, app, client):
    sign_in(client, "camila.rojas")
    few = _queries(app, client, "/tickets/export?formato=csv&vista=todos&q=impresora")
    many = _queries(app, client, "/tickets/export?formato=csv&vista=todos")

    assert many == few


# --- Reportes ----------------------------------------------------------------------------


@pytest.mark.parametrize("fmt", ["csv", "xlsx"])
def test_a_requester_cannot_export_the_reports(seeded, client, fmt):
    sign_in(client, SOLICITANTES[0])

    assert client.get(f"/reports/export?formato={fmt}").status_code == 403


def test_the_report_export_has_the_figures_of_the_screen(seeded, app, client):
    sign_in(client, "camila.rojas")
    workbook = read_xlsx(client.get("/reports/export?formato=xlsx&periodo=90"))

    with app.app_context():
        user = db.session.scalar(db.select(User).where(User.username == "camila.rojas"))
        report = build_report(user, ReportFilters(preset_period(90, datetime.now(UTC).astimezone(NOW.tzinfo).date())))

    summary = {row[0]: row[1] for row in workbook["Resumen"].iter_rows(min_row=2, values_only=True)}

    assert workbook.sheetnames == ["Resumen", "Por estado", "Por categoría", "Por prioridad", "Por semana", "Por técnico"]
    assert summary["Tickets creados"] == report.created.current.value
    assert summary["Tickets resueltos"] == report.resolved.current.value
    assert summary["Fuera de SLA"] == report.breached.current.value
    assert [row[1] for row in workbook["Por estado"].iter_rows(min_row=2, values_only=True)] == [
        row.count.value for row in report.by_state
    ]


def test_the_report_csv_is_one_long_table(seeded, client):
    sign_in(client, "camila.rojas")
    rows = read_csv(client.get("/reports/export?formato=csv&periodo=90"))

    assert rows[0] == ["Sección", "Elemento", "Medida", "Valor", "Período anterior"]
    assert {row[0] for row in rows[1:]} == {
        "Resumen", "Por estado", "Por categoría", "Por prioridad", "Por semana", "Por técnico",
    }


def test_a_technician_exports_only_their_own_row(seeded, client):
    sign_in(client, "diego.soto")
    sheet = read_xlsx(client.get("/reports/export?formato=xlsx&periodo=90"))["Por técnico"]

    assert [row[0] for row in sheet.iter_rows(min_row=2, values_only=True)] == ["Diego Soto (diego.soto)"]


def test_the_report_export_names_the_filters(seeded, app, client):
    with app.app_context():
        high = db.session.scalar(db.select(Prioridad.id).where(Prioridad.codigo == "ALTA"))

    sign_in(client, "camila.rojas")
    summary = read_xlsx(client.get(f"/reports/export?formato=xlsx&prioridad={high}"))["Resumen"]

    assert ("Prioridad", "Alta", None) in list(summary.iter_rows(min_row=2, values_only=True))


def test_with_the_sla_off_the_report_export_says_nothing_about_it(seeded, app, client, make_user):
    admin = make_user("ADMINISTRADOR", username="admin_export")

    with app.app_context():
        save_setting(settings.SLA_ENABLED, False, actor=person(admin["id"]))
        db.session.commit()

    sign_in(client, "camila.rojas")
    text = client.get("/reports/export?formato=csv&periodo=90").data.decode("utf-8-sig")

    assert "SLA" not in text


# --- Auditoría ---------------------------------------------------------------------------


@pytest.mark.parametrize("username", ["camila.rojas", "diego.soto", SOLICITANTES[0]])
def test_only_the_administrator_exports_the_audit(seeded, client, username):
    sign_in(client, username)

    assert client.get("/admin/audit/export?formato=csv").status_code == 403


@pytest.mark.parametrize("view", list(AuditView))
def test_the_audit_export_has_every_row_of_the_tab(seeded, app, client, make_user, view):
    admin = make_user("ADMINISTRADOR", username="admin_export")
    login(client, admin)

    with app.app_context():
        expected = count_audit_rows(view, AuditFilters())

    rows = read_csv(client.get(f"/admin/audit/export?formato=csv&vista={view.value}"))

    # La propia exportación queda en la auditoría antes de escribir el archivo.
    extra = 1 if view is AuditView.ADMINISTRATIVA else 0
    assert len(rows) - 1 == expected + extra > 0


def test_the_audit_export_reads_in_chunks_without_losing_or_repeating_rows(
    seeded, app, client, make_user, monkeypatch
):
    admin = make_user("ADMINISTRADOR", username="admin_export")
    login(client, admin)
    whole = read_csv(client.get("/admin/audit/export?formato=csv&vista=tickets"))
    monkeypatch.setattr("src.workdesk.audit.export.CHUNK", 9)
    chunked = read_csv(client.get("/admin/audit/export?formato=csv&vista=tickets"))

    assert len(whole) > 100
    assert chunked == whole


def test_the_audit_export_follows_its_filters(seeded, app, client, make_user):
    admin = make_user("ADMINISTRADOR", username="admin_export")
    login(client, admin)
    rows = read_csv(client.get("/admin/audit/export?formato=csv&vista=tickets&ticket=7"))

    assert len(rows) > 1
    assert {row[1] for row in rows[1:]} == {"7"}


def test_exporting_the_audit_is_recorded_too(seeded, app, client, make_user):
    admin = make_user("ADMINISTRADOR", username="admin_export")
    login(client, admin)
    client.get("/admin/audit/export?formato=xlsx&vista=accesos")

    with app.app_context():
        (entry,) = _exports_in_audit()

    assert entry.valor_nuevo["exportacion"] == "auditoria"
    assert entry.valor_nuevo["filtros"] == {"vista": "accesos"}
