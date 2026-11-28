"""Exportar tablas a CSV y a XLSX (RF-099 a RF-101; docs/12, fase 8).

Lo usan el listado de tickets, los reportes y la auditoría. Cada pantalla decide **qué**
filas y columnas exporta, con sus mismos filtros y permisos; aquí solo se escriben.

Las dos reglas de seguridad viven aquí, una sola vez:

- **Nada se convierte en fórmula al abrir el archivo** (CSV injection, OWASP). En CSV, un
  texto que empieza por `=`, `+`, `-`, `@`, tabulador o retorno de carro se escribe con un
  apóstrofo delante, y la hoja de cálculo lo muestra como texto. En XLSX todo texto se
  escribe con el tipo «texto»: `openpyxl` convertiría por su cuenta en fórmula cualquier
  texto que empiece por `=` (por ejemplo, un título `=HYPERLINK(...)`).
- **Ningún carácter de control llega al archivo:** el XML de un XLSX no los admite y un
  texto escrito por una persona (o un navegador, en la auditoría) podría traerlos.

El CSV va en UTF-8 con BOM (así Excel reconoce las tildes), separado por comas y con fin
de línea `\\r\\n` (RFC 4180). Las fechas se escriben en la hora local de la aplicación.
"""

import csv
import io
import re
import threading
from collections.abc import Iterable, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from flask import Response
from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from .audit import AuditAction, record_admin_event
from .extensions import db
from .formatting import app_zone

# Lo más que se exporta de una vez: más filas piden acotar los filtros.
MAX_EXPORT_ROWS = 50_000

# Exportaciones a la vez en este proceso. Una de 50 000 filas en Excel ocupa un hilo del
# servidor y un núcleo durante unos 10 s (medido en el cierre de `v0.8.0`): sin tope, unas
# pocas personas exportando a la vez dejarían sin hilos libres a todas las demás. Con el tope
# ocupado se pide reintentar, sin hacer esperar a nadie.
MAX_CONCURRENT_EXPORTS = 2
_EXPORT_SLOTS = threading.BoundedSemaphore(MAX_CONCURRENT_EXPORTS)
EXPORTS_BUSY_MESSAGE = "Hay otras exportaciones en curso. Inténtalo de nuevo en unos segundos."

# Lo que hace que una hoja de cálculo interprete un texto como fórmula (OWASP).
FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")

# Los caracteres de control que el XML no admite (los mismos que rechaza `openpyxl`).
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

DATETIME_FORMAT = "%Y-%m-%d %H:%M"
DATE_FORMAT = "%Y-%m-%d"
XLSX_DATETIME_FORMAT = "dd-mm-yyyy hh:mm"
XLSX_DATE_FORMAT = "dd-mm-yyyy"
MAX_SHEET_TITLE = 31


class ExportFormat(StrEnum):
    CSV = "csv"
    XLSX = "xlsx"


MIMETYPES = {
    ExportFormat.CSV: "text/csv; charset=utf-8",
    ExportFormat.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def parse_format(value: str | None) -> ExportFormat | None:
    """El formato pedido en la URL, o None si no es uno de los dos."""
    try:
        return ExportFormat(value)
    except ValueError:
        return None


@dataclass(frozen=True)
class Table:
    """Una tabla para exportar: `title` nombra su hoja en un XLSX."""

    title: str
    headers: Sequence[str]
    rows: Iterable[Sequence]


# --- Valores -------------------------------------------------------------------------


def clean_text(value: str) -> str:
    """El texto sin caracteres de control (los saltos de línea y tabuladores se quedan)."""
    return _CONTROL.sub("", value)


def neutralize(value: str) -> str:
    """Un texto que una hoja de cálculo no ejecutará como fórmula al abrir un CSV."""
    return "'" + value if value.startswith(FORMULA_STARTS) else value


def _local(value: datetime) -> datetime:
    """La fecha en la hora local de la aplicación y sin zona (Excel no guarda zonas)."""
    if value.tzinfo is not None:
        value = value.astimezone(app_zone())

    return value.replace(tzinfo=None)


def csv_value(value) -> str:
    if value is None:
        return ""

    if isinstance(value, bool):
        return "Sí" if value else "No"

    if isinstance(value, datetime):
        return _local(value).strftime(DATETIME_FORMAT)

    if isinstance(value, date):
        return value.strftime(DATE_FORMAT)

    if isinstance(value, int | float):
        return str(value)

    return neutralize(clean_text(str(value)))


# --- Formatos ------------------------------------------------------------------------


def to_csv(table: Table) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow([csv_value(header) for header in table.headers])

    for row in table.rows:
        writer.writerow([csv_value(value) for value in row])

    return ("﻿" + buffer.getvalue()).encode("utf-8")


def to_xlsx(tables: Sequence[Table]) -> bytes:
    """Un libro con una hoja por tabla, en modo de solo escritura (no guarda en memoria
    las celdas ya escritas)."""
    workbook = Workbook(write_only=True)
    workbook.properties.creator = "WorkDesk"
    used_titles: set[str] = set()

    for table in tables:
        sheet = workbook.create_sheet(_sheet_title(table.title, used_titles))
        sheet.freeze_panes = "A2"

        for index, header in enumerate(table.headers, start=1):
            sheet.column_dimensions[get_column_letter(index)].width = max(12, min(len(header) + 4, 40))

        bold = Font(bold=True)
        sheet.append([_xlsx_cell(sheet, header, font=bold) for header in table.headers])

        for row in table.rows:
            sheet.append([_xlsx_cell(sheet, value) for value in row])

    buffer = io.BytesIO()
    workbook.save(buffer)

    return buffer.getvalue()


def _xlsx_cell(sheet, value, font=None):
    if isinstance(value, datetime):
        value = _local(value)
    elif isinstance(value, bool):
        value = "Sí" if value else "No"
    elif value is not None and not isinstance(value, int | float | date):
        value = clean_text(str(value))

    cell = WriteOnlyCell(sheet, value=value)

    if isinstance(value, str):
        # Texto, siempre: `openpyxl` haría una fórmula de lo que empieza por `=`.
        cell.data_type = "s"
    elif isinstance(value, datetime):
        cell.number_format = XLSX_DATETIME_FORMAT
    elif isinstance(value, date):
        cell.number_format = XLSX_DATE_FORMAT

    if font is not None:
        cell.font = font

    return cell


def _sheet_title(title: str, used: set[str]) -> str:
    """Un nombre de hoja válido (sin `[]:*?/\\`, hasta 31 caracteres) y sin repetir."""
    base = re.sub(r"[\[\]:*?/\\]", " ", title).strip()[:MAX_SHEET_TITLE] or "Hoja"
    candidate, number = base, 2

    while candidate.lower() in used:
        suffix = f" ({number})"
        candidate, number = base[: MAX_SHEET_TITLE - len(suffix)] + suffix, number + 1

    used.add(candidate.lower())

    return candidate


# --- Rastro y respuesta -------------------------------------------------------------


@contextmanager
def export_slot():
    """Reserva un lugar para exportar: entrega `True` si lo había y `False` si no, sin esperar."""
    acquired = _EXPORT_SLOTS.acquire(blocking=False)

    try:
        yield acquired
    finally:
        if acquired:
            _EXPORT_SLOTS.release()


def begin_consistent_read() -> None:
    """Hace que el resto de la petición lea una sola foto de la base (`REPEATABLE READ`).

    Una exportación cuenta sus filas y después las lee por tramos. Con el aislamiento por
    defecto (`READ COMMITTED`) cada consulta ve lo confirmado hasta ese momento: un ticket o un
    evento nuevo, que va primero en el orden, desplazaría las filas entre un tramo y el
    siguiente, y una saldría dos veces y otra ninguna (y las filas auditadas no serían las
    exportadas). Termina antes la transacción que la petición ya había abierto (cargar a la
    persona, leer la configuración), que solo había leído.
    """
    db.session.commit()
    db.session.connection(execution_options={"isolation_level": "REPEATABLE READ"})


def record_export(actor, *, what: str, label: str, fmt: ExportFormat, rows: int, filters: dict):
    """Deja en la auditoría quién exportó qué, en qué formato, cuántas filas y con qué
    filtros (RN-180). Sin commit: lo confirma quien llama, antes de enviar el archivo."""
    record_admin_event(
        AuditAction.DATOS_EXPORTADOS,
        actor=actor,
        entity_type="exportacion",
        detail=f"{label} ({fmt.value.upper()}, {rows} {'fila' if rows == 1 else 'filas'})",
        new_value={
            "exportacion": what,
            "formato": fmt.value,
            "filas": rows,
            "filtros": {key: value for key, value in filters.items() if value not in (None, "")},
        },
    )


def too_many_rows_message(rows: int) -> str:
    return (
        f"La exportación tendría {rows:,} filas y el máximo es {MAX_EXPORT_ROWS:,}: "
        "acota los filtros e inténtalo de nuevo."
    ).replace(",", ".")


def export_response(fmt: ExportFormat, tables: Sequence[Table], basename: str) -> Response:
    """El archivo para descargar. En CSV va la primera tabla (quien llama prepara una sola);
    en XLSX, todas, una por hoja. `basename` debe ser ASCII y sin extensión."""
    body = to_csv(tables[0]) if fmt is ExportFormat.CSV else to_xlsx(tables)
    response = Response(body, mimetype=MIMETYPES[fmt])
    response.headers["Content-Disposition"] = f'attachment; filename="{basename}.{fmt.value}"'
    # Un dato personal no se queda en ninguna caché (las cabeceras comunes ya lo piden).
    response.headers["Cache-Control"] = "no-store"

    return response
