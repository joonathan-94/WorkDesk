"""La pantalla de carga de trabajo (docs/11, UI-006). Solo la ven Técnico, Supervisor y
Administrador: es información de todo el equipo, y la autorización real está aquí, en el
backend (la entrada del menú solo es presentación).

Es una pantalla para *analizar*, no un ranking: cada cifra enlaza con el listado de tickets
que la explica y su valor es el total de ese listado.
"""

from flask import render_template, request, url_for

from ..catalogs.service import list_priorities
from ..models.estado import IN_PROGRESS_STATE_CODE, ON_HOLD_STATE_CODE
from ..models.prioridad import CRITICAL_PRIORITY_CODE
from ..security import (
    STAFF_ROLES,
    can_manage_assignments,
    current_actor,
    roles_required,
)
from ..sla.periods import STOPPING_STATES
from ..tickets.queries import list_group_options, list_states
from . import bp
from .queries import WorkloadFilters, workload_overview

staff_only = roles_required(*STAFF_ROLES)

MAX_SEARCH_LENGTH = 100

# Orden de la tabla por técnico: (clave de la URL, nombre, función de orden).
SORTS = {
    "activos": "Más tickets activos",
    "criticos": "Más críticos",
    "riesgo": "Más SLA en riesgo",
    "nombre": "Nombre",
}
DEFAULT_SORT = "activos"


@bp.get("")
@staff_only
def workload_page():
    groups = list_group_options()
    priorities = list_priorities("")
    # Solo los estados en los que un ticket cuenta como carga.
    all_states = list_states()
    states = [state for state in all_states if state.codigo not in STOPPING_STATES]

    filters = WorkloadFilters(
        group_id=_choice_arg("grupo", groups),
        priority_id=_choice_arg("prioridad", priorities),
        state_id=_choice_arg("estado", states),
    )
    data = workload_overview(current_actor(), filters)

    # Filtros que solo afectan a la tabla por técnico: los indicadores siguen siendo los
    # del equipo completo.
    technician_id = _choice_arg("tecnico", [row.user for row in data.technicians])
    search = request.args.get("q", "").strip()[:MAX_SEARCH_LENGTH]
    sort = request.args.get("orden", DEFAULT_SORT)
    sort = sort if sort in SORTS else DEFAULT_SORT

    rows = _filter_and_sort(data.technicians, technician_id, search, sort)

    # Los enlaces al listado conservan los filtros de grupo, prioridad y estado: así el
    # total del listado sigue coincidiendo con la cifra.
    carried = {
        "grupo": filters.group_id,
        "prioridad": filters.priority_id,
        "estado": filters.state_id,
    }

    def list_link(**params) -> str:
        merged = {**carried, **params, "vista": "todos"}

        return url_for(
            "tickets.list_tickets_page",
            **{key: value for key, value in merged.items() if value is not None},
        )

    state_ids = {state.codigo: state.id for state in all_states}
    critical = next(
        (p.id for p in priorities if p.codigo == CRITICAL_PRIORITY_CODE), None
    )
    max_active = max((row.active for row in data.technicians), default=0)

    return render_template(
        "workload/index.html",
        data=data,
        rows=rows,
        max_active=max_active,
        list_link=list_link,
        critical_id=critical,
        in_progress_id=state_ids.get(IN_PROGRESS_STATE_CODE),
        on_hold_id=state_ids.get(ON_HOLD_STATE_CODE),
        can_reassign=can_manage_assignments(current_actor()),
        groups=groups,
        priorities=priorities,
        states=states,
        technician_options=[row.user for row in data.technicians],
        selected={
            "grupo": filters.group_id,
            "prioridad": filters.priority_id,
            "estado": filters.state_id,
            "tecnico": technician_id,
            "q": search,
            "orden": sort,
        },
        sorts=SORTS,
        filtered=any((filters.group_id, filters.priority_id, filters.state_id, technician_id, search)),
    )


def _filter_and_sort(rows, technician_id, search, sort):
    if technician_id is not None:
        rows = [row for row in rows if row.user.id == technician_id]

    if search:
        needle = search.casefold()
        rows = [
            row
            for row in rows
            if needle
            in f"{row.user.nombre} {row.user.apellido} {row.user.username}".casefold()
        ]

    keys = {
        "activos": lambda row: (-row.active, row.user.apellido.casefold()),
        "criticos": lambda row: (-row.critical, -row.active, row.user.apellido.casefold()),
        "riesgo": lambda row: (-row.at_risk, -row.active, row.user.apellido.casefold()),
        "nombre": lambda row: (
            row.user.apellido.casefold(),
            row.user.nombre.casefold(),
        ),
    }

    return sorted(rows, key=keys[sort])


def _choice_arg(name: str, options) -> int | None:
    """Id recibido por la URL si corresponde a una de las opciones."""
    value = request.args.get(name, type=int)

    return value if value in {option.id for option in options} else None
