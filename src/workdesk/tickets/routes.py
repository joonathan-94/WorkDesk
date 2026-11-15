from datetime import date

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..catalogs.service import (
    list_categories,
    list_locations,
    list_priorities,
)
from ..extensions import db
from ..models.ticket import MAX_DESCRIPTION_LENGTH, MAX_TITLE_LENGTH
from ..security import (
    STAFF_ROLES,
    can_change_priority,
    can_choose_requesters,
    can_create_ticket,
    can_edit_ticket,
    can_view_ticket,
    has_any_role,
)
from . import bp
from .editing import (
    MAX_REASON_LENGTH,
    TicketClosedError,
    TicketConflictError,
    change_priority,
    describe_history_changes,
    update_ticket,
)
from .forms import PriorityChangeForm, TicketEditForm, TicketForm
from .service import (
    CLOSED_STATE_CODE,
    DEFAULT_SORT,
    DEFAULT_TAB,
    MAX_SEARCH_LENGTH,
    SORT_LABELS,
    VALID_TABS,
    TicketFilters,
    TicketRuleError,
    categories_for_selection,
    count_tickets_by_tab,
    create_ticket,
    get_ticket_by_public_id,
    list_requester_candidates,
    list_states,
    list_ticket_history,
    list_tickets,
)

# Prioridad que se ofrece preseleccionada al crear un ticket (docs/11, UI-004).
DEFAULT_PRIORITY_CODE = "MEDIA"


# --- Listado ----------------------------------------------------------


@bp.get("")
@login_required
def list_tickets_page():
    """Tickets que el usuario puede ver, con búsqueda, filtros y orden.

    La visibilidad la aplica la propia consulta (`list_tickets`). Los valores
    inválidos de la URL se ignoran en lugar de producir un error.
    """
    states = list_states()
    priorities = list_priorities("")
    categories = list_categories("")
    locations = list_locations("")

    filters = TicketFilters(
        query_text=request.args.get("q", "").strip()[:MAX_SEARCH_LENGTH],
        state_id=_choice_arg("estado", states),
        priority_id=_choice_arg("prioridad", priorities),
        category_id=_choice_arg("categoria", categories),
        location_id=_choice_arg("ubicacion", locations),
        created_from=_date_arg("desde"),
        created_to=_date_arg("hasta"),
    )

    tab = request.args.get("vista", DEFAULT_TAB)

    if tab not in VALID_TABS:
        tab = DEFAULT_TAB

    sort = request.args.get("orden", DEFAULT_SORT)

    if sort not in SORT_LABELS:
        sort = DEFAULT_SORT

    page = max(request.args.get("page", 1, type=int), 1)

    pagination = list_tickets(
        current_user,
        filters,
        tab=tab,
        sort=sort,
        page=page,
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
        "orden": None if sort == DEFAULT_SORT else sort,
    }

    return render_template(
        "tickets/list.html",
        pagination=pagination,
        counts=count_tickets_by_tab(current_user, filters),
        tab=tab,
        sort=sort,
        sort_labels=SORT_LABELS,
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
            )
        ),
        states=states,
        priorities=priorities,
        categories=categories,
        locations=locations,
        is_staff=has_any_role(current_user, *STAFF_ROLES),
    )


# --- Creación ---------------------------------------------------------


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new_ticket():
    # La autorización se comprueba en backend; ocultar el enlace no basta.
    if not can_create_ticket(current_user):
        abort(403)

    choose_requesters = can_choose_requesters(current_user)
    priorities = list_priorities("activo")

    form = TicketForm(
        category_choices=[
            (category.id, category.nombre)
            for category in categories_for_selection()
        ],
        priority_choices=[
            (priority.id, priority.nombre) for priority in priorities
        ],
        location_choices=[
            (location.id, location.nombre)
            for location in list_locations("activo")
        ],
        requester_choices=(
            [
                (user.id, f"{user.apellido}, {user.nombre} ({user.username})")
                for user in list_requester_candidates()
            ]
            if choose_requesters
            else None
        ),
        # Solo al abrir el formulario: un envío sin prioridad debe fallar en
        # lugar de quedar en Media sin que nadie la haya elegido.
        **_initial_values(priorities, is_new_form=request.method == "GET"),
    )

    if form.validate_on_submit():
        # El Solicitante siempre es su propio solicitante; el personal
        # elige a quién (puede ser nadie).
        requester_ids = (
            form.solicitantes.data if choose_requesters else [current_user.id]
        )

        try:
            ticket = create_ticket(
                actor=_actor(),
                title=form.titulo.data,
                description=form.descripcion.data,
                category_id=form.categoria.data,
                priority_id=form.prioridad.data,
                location_id=form.ubicacion.data,
                requester_ids=requester_ids,
            )
            db.session.commit()
        except TicketRuleError as error:
            # Por ejemplo, un valor de catálogo desactivado mientras se
            # rellenaba el formulario.
            db.session.rollback()
            flash(str(error), "error")
        else:
            flash(f"Ticket #{ticket.public_id} creado correctamente.", "success")

            return redirect(
                url_for("tickets.detail", public_id=ticket.public_id)
            )

    return render_template(
        "tickets/new.html",
        form=form,
        choose_requesters=choose_requesters,
        max_title=MAX_TITLE_LENGTH,
        max_description=MAX_DESCRIPTION_LENGTH,
    )


# --- Detalle ----------------------------------------------------------


@bp.get("/<public_id>")
@login_required
def detail(public_id: str):
    ticket = _visible_ticket_or_404(public_id)
    is_staff = has_any_role(current_user, *STAFF_ROLES)
    is_closed = _is_closed(ticket)

    # El motivo de un cambio de prioridad es una nota interna del equipo: el
    # Solicitante ve qué cambió, pero no por qué (docs/06, RN-155).
    history = [
        {
            "entry": entry,
            "changes": describe_history_changes(entry),
            "reason": (entry.contexto or {}).get("motivo") if is_staff else None,
        }
        for entry in list_ticket_history(ticket)
    ]

    return render_template(
        "tickets/detail.html",
        ticket=ticket,
        history=history,
        is_staff=is_staff,
        is_closed=is_closed,
        # Solo para decidir qué botones mostrar; las rutas de edición
        # comprueban la autorización por sí mismas.
        show_edit=can_edit_ticket(current_user) and not is_closed,
        show_priority=can_change_priority(current_user) and not is_closed,
    )


# --- Edición ----------------------------------------------------------


@bp.route("/<public_id>/edit", methods=["GET", "POST"])
@login_required
def edit_ticket(public_id: str):
    ticket = _visible_ticket_or_404(public_id)

    # Quien ve el ticket pero no puede editarlo recibe un 403: la existencia
    # del ticket no es un secreto para él.
    if not can_edit_ticket(current_user):
        abort(403)

    if _is_closed(ticket):
        return _closed_redirect(ticket)

    # Solo al abrir el formulario se rellena con los datos actuales; al
    # enviarlo manda lo que se envió.
    initial = _edit_initial_values(ticket) if request.method == "GET" else {}

    form = TicketEditForm(
        category_choices=[
            (category.id, _label(category))
            for category in _choices_with_current(
                categories_for_selection(),
                ticket.categoria,
            )
        ],
        location_choices=[
            (location.id, _label(location))
            for location in _choices_with_current(
                list_locations("activo"),
                ticket.ubicacion,
            )
        ],
        **initial,
    )

    if form.validate_on_submit():
        try:
            changed = update_ticket(
                ticket,
                actor=_actor(),
                expected_version=form.version.data,
                title=form.titulo.data,
                description=form.descripcion.data,
                category_id=form.categoria.data,
                location_id=form.ubicacion.data,
            )
            db.session.commit()
        except TicketConflictError as error:
            # Otra persona lo modificó: se vuelven a mostrar los datos
            # actuales para no pisar su cambio sin haberlo visto.
            db.session.rollback()
            flash(str(error), "error")

            return redirect(url_for("tickets.edit_ticket", public_id=public_id))
        except TicketClosedError as error:
            db.session.rollback()
            flash(str(error), "error")

            return redirect(url_for("tickets.detail", public_id=public_id))
        except TicketRuleError as error:
            db.session.rollback()
            flash(str(error), "error")
        else:
            if changed:
                flash(f"Ticket #{public_id} actualizado.", "success")
            else:
                flash("No había cambios que guardar.", "warning")

            return redirect(url_for("tickets.detail", public_id=public_id))

    return render_template(
        "tickets/edit.html",
        ticket=ticket,
        form=form,
        max_title=MAX_TITLE_LENGTH,
        max_description=MAX_DESCRIPTION_LENGTH,
    )


@bp.route("/<public_id>/priority", methods=["GET", "POST"])
@login_required
def change_ticket_priority(public_id: str):
    ticket = _visible_ticket_or_404(public_id)

    if not can_change_priority(current_user):
        abort(403)

    if _is_closed(ticket):
        return _closed_redirect(ticket)

    initial = {"version": ticket.version} if request.method == "GET" else {}

    form = PriorityChangeForm(
        priority_choices=[
            (
                priority.id,
                f"{priority.nombre} (actual)"
                if priority.id == ticket.prioridad_id
                else priority.nombre,
            )
            for priority in _choices_with_current(
                list_priorities("activo"),
                ticket.prioridad,
            )
        ],
        **initial,
    )

    if form.validate_on_submit():
        try:
            changed = change_priority(
                ticket,
                actor=_actor(),
                expected_version=form.version.data,
                priority_id=form.prioridad.data,
                reason=form.motivo.data,
            )
            db.session.commit()
        except TicketConflictError as error:
            db.session.rollback()
            flash(str(error), "error")

            return redirect(
                url_for("tickets.change_ticket_priority", public_id=public_id)
            )
        except TicketClosedError as error:
            db.session.rollback()
            flash(str(error), "error")

            return redirect(url_for("tickets.detail", public_id=public_id))
        except TicketRuleError as error:
            db.session.rollback()
            flash(str(error), "error")
        else:
            if changed:
                flash(
                    f"La prioridad del ticket #{public_id} se actualizó.",
                    "success",
                )
            else:
                flash("El ticket ya tiene esa prioridad.", "warning")

            return redirect(url_for("tickets.detail", public_id=public_id))

    return render_template(
        "tickets/priority.html",
        ticket=ticket,
        form=form,
        max_reason=MAX_REASON_LENGTH,
    )


# --- Utilidades -------------------------------------------------------


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


def _initial_values(priorities, *, is_new_form: bool) -> dict:
    """Valores con los que arranca el formulario recién abierto."""
    if not is_new_form:
        return {}

    default = next(
        (p for p in priorities if p.codigo == DEFAULT_PRIORITY_CODE),
        None,
    )

    return {} if default is None else {"prioridad": default.id}


def _visible_ticket_or_404(public_id: str):
    """Ticket que el usuario puede ver; 404 en cualquier otro caso.

    Un identificador que no sea un número no puede existir. Un ticket ajeno
    responde igual que uno inexistente (404): los números son correlativos y,
    con un 403, cualquiera podría descubrir cuáles existen.
    """
    if not (public_id.isascii() and public_id.isdecimal()):
        abort(404)

    ticket = get_ticket_by_public_id(public_id)

    if ticket is None or not can_view_ticket(current_user, ticket):
        abort(404)

    return ticket


def _is_closed(ticket) -> bool:
    return ticket.estado.codigo == CLOSED_STATE_CODE


def _closed_redirect(ticket):
    flash(
        "Un ticket cerrado no se puede editar. Primero debe reabrirse.",
        "error",
    )

    return redirect(url_for("tickets.detail", public_id=ticket.public_id))


def _choices_with_current(items, current) -> list:
    """Elementos de catálogo activos, más el que el ticket ya tiene.

    Si el valor actual se desactivó después de crear el ticket, sigue
    pudiendo conservarse (aunque no pueda elegirse en otros tickets).
    """
    items = list(items)

    if current is not None and all(item.id != current.id for item in items):
        items.append(current)

    return items


def _label(item) -> str:
    """Nombre de un elemento de catálogo, marcando los desactivados."""
    name = item.nombre if hasattr(item, "nombre") else item.nombre_visible

    return name if item.activo else f"{name} (inactiva)"


def _edit_initial_values(ticket) -> dict:
    """Valores con los que arranca el formulario de edición."""
    return {
        "titulo": ticket.titulo,
        "descripcion": ticket.descripcion,
        "categoria": ticket.categoria_id,
        "ubicacion": ticket.ubicacion_id,
        "version": ticket.version,
    }


def _actor():
    return current_user._get_current_object()
