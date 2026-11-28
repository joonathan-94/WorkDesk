"""Listado de tickets con búsqueda, filtros, orden y paginación (docs/06,
RN-154).
"""

from dataclasses import dataclass
from datetime import date

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ... import settings
from ...catalogs.service import (
    list_categories,
    list_locations,
    list_priorities,
    list_states,
)
from ...configuration import value_of
from ...dashboard.requester import local_today
from ...exports import (
    EXPORTS_BUSY_MESSAGE,
    MAX_EXPORT_ROWS,
    begin_consistent_read,
    export_response,
    export_slot,
    parse_format,
    record_export,
    too_many_rows_message,
)
from ...extensions import db
from ...query_params import choice_arg
from ...security import STAFF_ROLES, current_actor, has_any_role
from ...sla import periods as sla_periods
from ...sla.evaluation import evaluate_tickets_sla
from ...sla.queries import SLA_FILTER_LABELS, parse_filter
from .. import bp
from ..export import count_ticket_rows, ticket_table
from ..queries import (
    DEFAULT_SORT,
    DEFAULT_TAB,
    MAX_SEARCH_LENGTH,
    SORT_LABELS,
    SORT_SLA,
    SORT_SLA_LABEL,
    UNASSIGNED_VALUE,
    VALID_TABS,
    TicketFilters,
    count_tickets_by_tab,
    list_group_options,
    list_technician_options,
    list_tickets,
    listing_params,
)


@bp.get("")
@login_required
def list_tickets_page():
    """Tickets que el usuario puede ver, con búsqueda, filtros y orden.

    La visibilidad la aplica la propia consulta (`list_tickets`). Los valores
    inválidos de la URL se ignoran en lugar de producir un error.
    """
    listing = _read_listing()
    is_staff, filters, tab, sort = listing.is_staff, listing.filters, listing.tab, listing.sort
    options = listing.options

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
        evaluate_tickets_sla([t.id for t in pagination.items], now)
        if is_staff
        else {}
    )

    # Lo que deben conservar los enlaces (pestañas, páginas, limpiar...).
    filter_params = listing_params(filters) | {
        "orden": None if sort == DEFAULT_SORT else sort
    }

    return render_template(
        "tickets/list.html",
        pagination=pagination,
        counts=count_tickets_by_tab(current_user, filters, now),
        tab=tab,
        sort=sort,
        sort_labels=listing.sort_labels,
        sla_labels=SLA_FILTER_LABELS,
        slas=slas,
        filters=filters,
        filter_params=filter_params,
        # La exportación lleva también la pestaña: trae lo que se ve.
        export_params=filter_params | {"vista": tab},
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
                filters.resolved_from,
                filters.resolved_to,
                filters.technician_id,
                filters.group_id,
                filters.unassigned or None,
                filters.active_only or None,
                filters.pending_review or None,
                filters.inactive or None,
            )
        ),
        states=options["states"],
        priorities=options["priorities"],
        categories=options["categories"],
        locations=options["locations"],
        technicians=options["technicians"],
        groups=options["groups"],
        unassigned_value=UNASSIGNED_VALUE,
        is_staff=is_staff,
        # Con 0 días la marca está apagada y la casilla no se ofrece.
        inactive_days=value_of(settings.INACTIVE_TICKET_DAYS),
    )


@dataclass(frozen=True)
class _ListingRequest:
    """Lo que la URL pide al listado, ya validado: lo comparten la pantalla y la
    exportación, así que un archivo exportado trae las filas que se ven."""

    is_staff: bool
    options: dict
    filters: TicketFilters
    tab: str
    sort: str
    sort_labels: dict


def _read_listing() -> _ListingRequest:
    is_staff = has_any_role(current_user, *STAFF_ROLES)
    options = {
        "states": list_states(),
        "priorities": list_priorities(""),
        "categories": list_categories(""),
        "locations": list_locations(""),
        # Técnico y grupo son solo del personal (el grupo es un dato interno).
        "technicians": list_technician_options() if is_staff else [],
        "groups": list_group_options() if is_staff else [],
    }
    filters = read_listing_filters(is_staff=is_staff, **options)

    tab = request.args.get("vista", DEFAULT_TAB)

    if tab not in VALID_TABS:
        tab = DEFAULT_TAB

    sort_labels = dict(SORT_LABELS)

    if is_staff and sla_periods.sla_enabled():
        sort_labels[SORT_SLA] = SORT_SLA_LABEL

    sort = request.args.get("orden", DEFAULT_SORT)

    if sort not in sort_labels:
        sort = DEFAULT_SORT

    return _ListingRequest(is_staff, options, filters, tab, sort, sort_labels)


@bp.get("/export")
@login_required
def export_tickets():
    """El listado tal como se ve (visibilidad, filtros, pestaña y orden), en CSV o XLSX
    (RF-099 a RF-101). Cada exportación queda en la auditoría (RN-180)."""
    fmt = parse_format(request.args.get("formato"))

    if fmt is None:
        abort(404)

    listing = _read_listing()
    params = listing_params(listing.filters) | {"vista": listing.tab, "orden": listing.sort}

    with export_slot() as free:
        if not free:
            flash(EXPORTS_BUSY_MESSAGE, "warning")

            return redirect(url_for("tickets.list_tickets_page", **params))

        # Contar, auditar y leer las filas por tramos, todo con la misma foto de la base.
        begin_consistent_read()
        now = sla_periods.current_time() if listing.is_staff else None
        rows = count_ticket_rows(current_user, listing.filters, listing.tab, now)

        if rows > MAX_EXPORT_ROWS:
            flash(too_many_rows_message(rows), "warning")

            return redirect(url_for("tickets.list_tickets_page", **params))

        record_export(
            current_actor(),
            what="tickets",
            label="Listado de tickets",
            fmt=fmt,
            rows=rows,
            filters=params,
        )
        table = ticket_table(
            current_user, listing.filters, tab=listing.tab, sort=listing.sort, now=now
        )
        response = export_response(
            fmt, [table], f"workdesk-tickets-{local_today(now).isoformat()}"
        )
        # La auditoría se confirma con el archivo ya escrito y antes de enviarlo.
        db.session.commit()

        return response


def read_listing_filters(
    *, is_staff, states, priorities, categories, locations, technicians, groups
) -> TicketFilters:
    """Los filtros del listado tal como llegan en la URL de la petición actual. Un valor
    que no corresponde a ninguna opción (o una fecha mal escrita) se ignora.

    Es el camino inverso de `listing_params`: un test comprueba que cada enlace de los
    reportes, leído por aquí, reproduce exactamente los filtros con que se contó."""
    unassigned = is_staff and request.args.get("tecnico") == UNASSIGNED_VALUE

    return TicketFilters(
        query_text=request.args.get("q", "").strip()[:MAX_SEARCH_LENGTH],
        state_id=choice_arg("estado", states),
        priority_id=choice_arg("prioridad", priorities),
        category_id=choice_arg("categoria", categories),
        location_id=choice_arg("ubicacion", locations),
        created_from=_date_arg("desde"),
        created_to=_date_arg("hasta"),
        # El SLA es solo del personal: para un Solicitante el parámetro no existe.
        sla=(
            parse_filter(request.args.get("sla"))
            if is_staff and sla_periods.sla_enabled()
            else None
        ),
        technician_id=None if unassigned else choice_arg("tecnico", technicians),
        unassigned=unassigned,
        group_id=choice_arg("grupo", groups),
        active_only=request.args.get("activos") == "1",
        # Solo un Solicitante tiene resoluciones que revisar.
        pending_review=not is_staff and request.args.get("revision") == "1",
        closed_from=_date_arg("cerrado_desde"),
        resolved_from=_date_arg("resuelto_desde"),
        resolved_to=_date_arg("resuelto_hasta"),
        # Como el SLA, solo del personal: para un Solicitante el parámetro no existe.
        inactive=is_staff and request.args.get("sin_actividad") == "1",
    )


def _date_arg(name: str) -> date | None:
    try:
        return date.fromisoformat(request.args.get(name, ""))
    except ValueError:
        return None
