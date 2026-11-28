"""La pantalla de auditoría (UI-027, RF-108 y RF-109), solo para el Administrador.

La ruta lee y valida los filtros de la URL; un valor que no corresponde (una acción que no
existe, una fecha mal escrita, una IP imposible) se ignora, como en el resto de filtros de
WorkDesk, y nunca llega crudo a la consulta. Las consultas están en `audit/queries.py`.
"""

import ipaddress
import json
from datetime import date

from flask import abort, flash, redirect, render_template, request, url_for

from ..audit.export import audit_table
from ..audit.labels import AUDIT_ACTION_LABELS, action_label, entity_label
from ..audit.queries import (
    MAX_PERSON_LENGTH,
    VIEW_LABELS,
    AuditFilters,
    AuditView,
    audit_page,
    count_audit_rows,
    entity_types,
    page_context,
)
from ..audit.service import AuditAction
from ..dashboard.requester import local_today
from ..exports import (
    EXPORTS_BUSY_MESSAGE,
    MAX_EXPORT_ROWS,
    begin_consistent_read,
    export_response,
    export_slot,
    parse_format,
    record_export,
    too_many_rows_message,
)
from ..extensions import db
from ..models import AuthEventType, TicketEvent
from ..models.admin_audit_log import AuditResult
from ..models.auth_event import AUTH_EVENT_LABELS
from ..models.ticket_history import TICKET_EVENT_LABELS
from ..security import admin_only, can_view_audit, current_actor
from ..tickets.history import describe_history_changes
from . import bp

# Las opciones del filtro «Qué pasó» de cada pestaña: código y nombre, por nombre.
KIND_OPTIONS = {
    AuditView.ADMINISTRATIVA: sorted(
        ((action.value, AUDIT_ACTION_LABELS[action]) for action in AuditAction),
        key=lambda option: option[1],
    ),
    AuditView.ACCESOS: [(kind.value, AUTH_EVENT_LABELS[kind]) for kind in AuthEventType],
    AuditView.TICKETS: sorted(
        ((event.value, TICKET_EVENT_LABELS[event]) for event in TicketEvent),
        key=lambda option: option[1],
    ),
}

RESULT_OPTIONS = [
    (AuditResult.EXITOSO.value, "Correcto"),
    (AuditResult.FALLIDO.value, "Fallido"),
]


@bp.get("/audit")
@admin_only
def audit():
    view, known_entities, filters = _read_audit()
    pagination = audit_page(view, filters, page=request.args.get("page", 1, type=int))
    context = page_context(view, pagination.items)

    return render_template(
        "admin/audit.html",
        view=view,
        views=VIEW_LABELS,
        filters=filters,
        pagination=pagination,
        context=context,
        kind_options=KIND_OPTIONS[view],
        result_options=RESULT_OPTIONS,
        entity_options=[(code, entity_label(code)) for code in known_entities],
        params=_params(view, filters),
        action_label=action_label,
        entity_label=entity_label,
        changes_of=describe_history_changes,
        pretty=_pretty_json,
    )


@bp.get("/audit/export")
@admin_only
def export_audit():
    """La pestaña que se ve, con sus filtros, en CSV o XLSX. Exportar la auditoría también
    queda en la auditoría (RN-180)."""
    fmt = parse_format(request.args.get("formato"))

    if fmt is None:
        abort(404)

    view, _known, filters = _read_audit()
    params = _params(view, filters)

    with export_slot() as free:
        if not free:
            flash(EXPORTS_BUSY_MESSAGE, "warning")

            return redirect(url_for("admin.audit", **params))

        # Contar, auditar y leer las filas por tramos, todo con la misma foto de la base: los
        # accesos y los eventos llegan sin parar y van primero en el orden.
        begin_consistent_read()
        rows = count_audit_rows(view, filters)

        if rows > MAX_EXPORT_ROWS:
            flash(too_many_rows_message(rows), "warning")

            return redirect(url_for("admin.audit", **params))

        record_export(
            current_actor(),
            what="auditoria",
            label=f"Auditoría, pestaña {VIEW_LABELS[view]}",
            fmt=fmt,
            rows=rows,
            filters=params,
        )
        response = export_response(
            fmt,
            [audit_table(view, filters)],
            f"workdesk-auditoria-{view.value}-{local_today().isoformat()}",
        )
        # La auditoría se confirma con el archivo ya escrito y antes de enviarlo.
        db.session.commit()

        return response


# --- Lectura de la URL --------------------------------------------------------------------


def _read_audit():
    """La pestaña y sus filtros, ya validados (la pantalla y la exportación)."""
    # `admin_only` ya lo exige; la política es la que nombra el requisito (RNF-025) y
    # mantiene la regla en un solo lugar si algún día otro rol puede consultar.
    if not can_view_audit(current_actor()):
        abort(403)

    view = _view_arg()
    known_entities = entity_types() if view is AuditView.ADMINISTRATIVA else []

    return view, known_entities, _filters(view, known_entities)


def _view_arg() -> AuditView:
    try:
        return AuditView(request.args.get("vista", AuditView.ADMINISTRATIVA))
    except ValueError:
        return AuditView.ADMINISTRATIVA


def _filters(view: AuditView, known_entities: list[str]) -> AuditFilters:
    kinds = {code for code, _ in KIND_OPTIONS[view]}
    kind = request.args.get("tipo")
    entity = request.args.get("entidad")
    result = request.args.get("resultado")

    return AuditFilters(
        since=_date_arg("desde"),
        until=_date_arg("hasta"),
        person=request.args.get("persona", "").strip()[:MAX_PERSON_LENGTH],
        kind=kind if kind in kinds else None,
        entity_type=entity if entity in known_entities else None,
        entity_id=request.args.get("entidad_id", type=int) if view is AuditView.ADMINISTRATIVA else None,
        result=result if result in {code for code, _ in RESULT_OPTIONS} else None,
        ip=_ip_arg() if view is AuditView.ACCESOS else None,
        ticket=_ticket_arg() if view is AuditView.TICKETS else None,
    )


def _date_arg(name: str) -> date | None:
    try:
        return date.fromisoformat(request.args.get(name, ""))
    except ValueError:
        return None


def _ip_arg() -> str | None:
    value = request.args.get("ip", "").strip()

    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return None


def _ticket_arg() -> str | None:
    value = request.args.get("ticket", "").strip().lstrip("#")

    return value if value.isascii() and value.isdigit() else None


def _params(view: AuditView, filters: AuditFilters) -> dict:
    """Los filtros aplicados, para que la paginación los conserve."""
    values = {
        "vista": view.value,
        "desde": None if filters.since is None else filters.since.isoformat(),
        "hasta": None if filters.until is None else filters.until.isoformat(),
        "persona": filters.person or None,
        "tipo": filters.kind,
        "entidad": filters.entity_type,
        "entidad_id": filters.entity_id,
        "resultado": filters.result,
        "ip": filters.ip,
        "ticket": filters.ticket,
    }

    return {name: value for name, value in values.items() if value is not None}


def _pretty_json(value) -> str:
    """Un valor JSON legible (la plantilla lo escapa)."""
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str)
