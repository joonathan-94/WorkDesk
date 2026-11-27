"""La pantalla de auditoría (UI-027, RF-108 y RF-109), solo para el Administrador.

La ruta lee y valida los filtros de la URL; un valor que no corresponde (una acción que no
existe, una fecha mal escrita, una IP imposible) se ignora, como en el resto de filtros de
WorkDesk, y nunca llega crudo a la consulta. Las consultas están en `audit/queries.py`.
"""

import ipaddress
import json
from datetime import date

from flask import abort, render_template, request

from ..audit.labels import AUDIT_ACTION_LABELS, action_label, entity_label
from ..audit.queries import (
    MAX_PERSON_LENGTH,
    VIEW_LABELS,
    AuditFilters,
    AuditView,
    audit_page,
    entity_types,
    page_context,
)
from ..audit.service import AuditAction
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
    # `admin_only` ya lo exige; la política es la que nombra el requisito (RNF-025) y
    # mantiene la regla en un solo lugar si algún día otro rol puede consultar.
    if not can_view_audit(current_actor()):
        abort(403)

    view = _view_arg()
    known_entities = entity_types() if view is AuditView.ADMINISTRATIVA else []
    filters = _filters(view, known_entities)
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


# --- Lectura de la URL --------------------------------------------------------------------


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

    return value if value.isdigit() else None


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
