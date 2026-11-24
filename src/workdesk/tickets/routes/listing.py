"""Listado de tickets con búsqueda, filtros, orden y paginación (docs/06,
RN-154).
"""

from datetime import date

from flask import render_template, request
from flask_login import current_user, login_required

from ...catalogs.service import list_categories, list_locations, list_priorities
from ...security import STAFF_ROLES, has_any_role
from ...sla import periods as sla_periods
from ...sla.queries import SLA_FILTER_LABELS, parse_filter
from .. import bp
from ..queries import (
    DEFAULT_SORT,
    DEFAULT_TAB,
    MAX_SEARCH_LENGTH,
    SORT_LABELS,
    SORT_SLA,
    SORT_SLA_LABEL,
    VALID_TABS,
    TicketFilters,
    count_tickets_by_tab,
    list_group_options,
    list_states,
    list_technician_options,
    list_tickets,
)

# Valor de `tecnico` para «sin técnico asignado».
UNASSIGNED_VALUE = "ninguno"


@bp.get("")
@login_required
def list_tickets_page():
    """Tickets que el usuario puede ver, con búsqueda, filtros y orden.

    La visibilidad la aplica la propia consulta (`list_tickets`). Los valores
    inválidos de la URL se ignoran en lugar de producir un error.
    """
    is_staff = has_any_role(current_user, *STAFF_ROLES)
    states = list_states()
    priorities = list_priorities("")
    categories = list_categories("")
    locations = list_locations("")
    # Técnico y grupo son solo del personal (el grupo es un dato interno).
    technicians = list_technician_options() if is_staff else []
    groups = list_group_options() if is_staff else []
    unassigned = is_staff and request.args.get("tecnico") == UNASSIGNED_VALUE

    filters = TicketFilters(
        query_text=request.args.get("q", "").strip()[:MAX_SEARCH_LENGTH],
        state_id=_choice_arg("estado", states),
        priority_id=_choice_arg("prioridad", priorities),
        category_id=_choice_arg("categoria", categories),
        location_id=_choice_arg("ubicacion", locations),
        created_from=_date_arg("desde"),
        created_to=_date_arg("hasta"),
        # El SLA es solo del personal: para un Solicitante el parámetro no existe.
        sla=parse_filter(request.args.get("sla")) if is_staff else None,
        technician_id=None if unassigned else _choice_arg("tecnico", technicians),
        unassigned=unassigned,
        group_id=_choice_arg("grupo", groups),
        active_only=request.args.get("activos") == "1",
        # Solo un Solicitante tiene resoluciones que revisar.
        pending_review=not is_staff and request.args.get("revision") == "1",
        closed_from=_date_arg("cerrado_desde"),
    )

    tab = request.args.get("vista", DEFAULT_TAB)

    if tab not in VALID_TABS:
        tab = DEFAULT_TAB

    sort_labels = dict(SORT_LABELS)

    if is_staff:
        sort_labels[SORT_SLA] = SORT_SLA_LABEL

    sort = request.args.get("orden", DEFAULT_SORT)

    if sort not in sort_labels:
        sort = DEFAULT_SORT

    page = max(request.args.get("page", 1, type=int), 1)

    # El mismo instante decide el filtro, las cuentas y las insignias de esta pantalla.
    now = sla_periods.current_time() if is_staff else None

    pagination = list_tickets(
        current_user,
        filters,
        tab=tab,
        sort=sort,
        page=page,
        now=now,
    )
    # El SLA de las filas de la página, en un número fijo de consultas (solo personal).
    slas = (
        sla_periods.evaluate_tickets_sla([t.id for t in pagination.items], now)
        if is_staff
        else {}
    )

    # Lo que deben conservar los enlaces (pestañas, páginas, limpiar...).
    filter_params = {
        "q": filters.query_text or None,
        "estado": filters.state_id,
        "prioridad": filters.priority_id,
        "categoria": filters.category_id,
        "ubicacion": filters.location_id,
        "desde": _iso(filters.created_from),
        "hasta": _iso(filters.created_to),
        "sla": filters.sla.value if filters.sla else None,
        "tecnico": UNASSIGNED_VALUE if filters.unassigned else filters.technician_id,
        "grupo": filters.group_id,
        "activos": "1" if filters.active_only else None,
        "revision": "1" if filters.pending_review else None,
        "cerrado_desde": _iso(filters.closed_from),
        "orden": None if sort == DEFAULT_SORT else sort,
    }

    return render_template(
        "tickets/list.html",
        pagination=pagination,
        counts=count_tickets_by_tab(current_user, filters, now),
        tab=tab,
        sort=sort,
        sort_labels=sort_labels,
        sla_labels=SLA_FILTER_LABELS,
        slas=slas,
        filters=filters,
        filter_params=filter_params,
        # Hay búsqueda o filtros activos (la pestaña y el orden no cuentan).
        is_filtered=any(
            value is not None
            for key, value in filter_params.items()
            if key != "orden"
        ),
        # "Más filtros" se abre solo si alguno de sus campos está aplicado.
        more_filters_open=any(
            value is not None
            for value in (
                filters.category_id,
                filters.location_id,
                filters.created_from,
                filters.created_to,
                filters.closed_from,
                filters.technician_id,
                filters.group_id,
                filters.unassigned or None,
                filters.active_only or None,
                filters.pending_review or None,
            )
        ),
        states=states,
        priorities=priorities,
        categories=categories,
        locations=locations,
        technicians=technicians,
        groups=groups,
        unassigned_value=UNASSIGNED_VALUE,
        is_staff=is_staff,
    )


def _choice_arg(name: str, options) -> int | None:
    """Id recibido por la URL si corresponde a una de las opciones."""
    value = request.args.get(name, type=int)

    return value if value in {option.id for option in options} else None


def _date_arg(name: str) -> date | None:
    try:
        return date.fromisoformat(request.args.get(name, ""))
    except ValueError:
        return None


def _iso(value: date | None) -> str | None:
    return None if value is None else value.isoformat()
