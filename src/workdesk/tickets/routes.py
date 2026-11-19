from datetime import UTC, date, datetime

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required
from flask_wtf import FlaskForm

from ..catalogs.service import (
    list_categories,
    list_locations,
    list_priorities,
    list_wait_reasons,
)
from ..extensions import db
from ..models import CommentType
from ..models.comment import MAX_COMMENT_LENGTH
from ..models.ticket import MAX_DESCRIPTION_LENGTH, MAX_TITLE_LENGTH
from ..security import (
    STAFF_ROLES,
    can_assign_self,
    can_attach_files,
    can_change_priority,
    can_choose_requesters,
    can_comment_publicly,
    can_create_ticket,
    can_delete_attachment,
    can_delete_comment,
    can_edit_comment,
    can_edit_ticket,
    can_manage_assignments,
    can_manage_requesters,
    can_view_ticket,
    can_write_internal_note,
    has_any_role,
)
from ..users.forms import ReasonForm
from . import bp
from .assignment import (
    assign_technician,
    escalate_ticket,
    list_assignable_technicians,
    list_escalation_technicians,
    list_groups_for_ticket,
    set_group,
    unassign_technician,
)
from .attachments import (
    add_attachments,
    attachment_path,
    delete_attachment,
    discard_files,
    get_attachment,
    list_attachments,
)
from .comments import (
    add_comment,
    delete_comment,
    edit_comment,
    get_comment,
    list_comments,
)
from .editing import (
    MAX_REASON_LENGTH,
    change_priority,
    describe_history_changes,
    update_ticket,
)
from .forms import (
    CommentEditForm,
    CommentForm,
    EscalationForm,
    GroupChangeForm,
    PriorityChangeForm,
    RequesterPickForm,
    StateChangeForm,
    TechnicianPickForm,
    TicketEditForm,
    TicketForm,
)
from .lifecycle import (
    ACTION_BY_SLUG,
    MAX_WAIT_TEXT_LENGTH,
    StateTransitionError,
    available_actions,
    change_state,
)
from .requesters import add_requester, list_addable_requesters, remove_requester
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
from .storage import MAX_FILES_PER_REQUEST, allowed_extensions
from .versioning import TicketClosedError, TicketConflictError

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
            _requester_choices(list_requester_candidates())
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
    return _render_detail(_visible_ticket_or_404(public_id), CommentForm())


def _render_detail(ticket, comment_form):
    """Muestra el detalle del ticket. Lo comparten el GET del detalle y el
    envío de un comentario que no pasa la validación (para mostrar los errores
    sin perder lo escrito)."""
    is_staff = has_any_role(current_user, *STAFF_ROLES)
    is_closed = _is_closed(ticket)
    now = datetime.now(UTC)

    # Los comentarios salen de una consulta que ya filtra por tipo: la nota
    # interna no llega nunca al Solicitante (docs/10, sección 57). Los
    # permisos de editar y eliminar solo deciden qué enlaces se muestran;
    # cada ruta vuelve a comprobarlos.
    comments = [
        {
            "comment": comment,
            "can_edit": can_edit_comment(current_user, comment, now=now),
            "can_delete": can_delete_comment(current_user, comment, now=now),
        }
        for comment in list_comments(ticket, _actor())
    ]

    # Adjuntos (ya filtrados por la consulta): los de cada comentario se
    # muestran bajo él y los del ticket, en la tarjeta «Archivos».
    files = [
        {
            "file": attachment,
            "can_delete": can_delete_attachment(current_user, attachment, now=now),
        }
        for attachment in list_attachments(ticket, _actor())
    ]
    files_by_comment: dict = {}

    for row in files:
        files_by_comment.setdefault(row["file"].comentario_id, []).append(row)

    # El motivo de un cambio de prioridad es una nota interna del equipo: el
    # Solicitante ve qué cambió, pero no por qué (docs/06, RN-155).
    history = [
        {
            "entry": entry,
            "changes": describe_history_changes(entry),
            "reason": (entry.contexto or {}).get("motivo") if is_staff else None,
            # El motivo de espera, como el de prioridad, es solo del personal.
            "wait_reason": (
                entry.motivo_espera.nombre
                if is_staff and entry.motivo_espera is not None
                else None
            ),
        }
        for entry in list_ticket_history(ticket, _actor())
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
        # Cambios de estado ofrecidos ahora (ya filtrados por transición
        # activa y por rol). Cada ruta vuelve a comprobarlos.
        state_actions=available_actions(ticket, current_user),
        # Asignación: lo que se ofrece según el rol (cada ruta lo comprueba).
        can_self_assign=can_assign_self(current_user) and not is_closed,
        my_assignment=_my_assignment(ticket),
        show_assignment=can_manage_assignments(current_user) and not is_closed,
        show_requesters=can_manage_requesters(current_user) and not is_closed,
        # Comentarios: el formulario se ofrece mientras el ticket esté abierto y
        # el selector de nota interna solo al personal.
        comments=comments,
        files_by_comment=files_by_comment,
        ticket_files=files_by_comment.get(None, []),
        show_uploader=can_attach_files(current_user, ticket) and not is_closed,
        max_files=MAX_FILES_PER_REQUEST,
        max_upload_mb=current_app.config["UPLOAD_MAX_BYTES"] // (1024 * 1024),
        allowed_extensions=allowed_extensions(),
        comment_form=comment_form,
        show_composer=can_comment_publicly(current_user, ticket) and not is_closed,
        can_write_note=can_write_internal_note(current_user),
        max_comment=MAX_COMMENT_LENGTH,
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


# --- Cambios de estado ------------------------------------------------


@bp.route("/<public_id>/status/<action_slug>", methods=["GET", "POST"])
@login_required
def change_ticket_state(public_id: str, action_slug: str):
    ticket = _visible_ticket_or_404(public_id)
    info = ACTION_BY_SLUG.get(action_slug)

    # Una acción que no existe es un 404; una que existe pero el rol no
    # puede ejecutar, un 403 (quien ve el ticket no necesita que se le oculte).
    if info is None:
        abort(404)

    if not info.policy(current_user):
        abort(403)

    if _is_closed(ticket):
        return _closed_redirect(ticket, _CLOSED_MODIFY_MESSAGE)

    # Se comprueba también en GET: una pantalla abierta antes de que otra
    # persona cambiara el estado ya no corresponde al ticket.
    option = next(
        (a for a in available_actions(ticket, current_user) if a.info is info),
        None,
    )

    if option is None:
        flash(
            "Esta acción no está disponible para el estado actual del ticket.",
            "error",
        )

        return redirect(url_for("tickets.detail", public_id=public_id))

    wait_reasons = list_wait_reasons("activo")
    initial = {"version": ticket.version} if request.method == "GET" else {}

    form = StateChangeForm(
        wait_reason_choices=[(reason.id, reason.nombre) for reason in wait_reasons],
        **initial,
    )

    if form.validate_on_submit():
        try:
            new_state = change_state(
                ticket,
                actor=_actor(),
                action=info.action,
                expected_version=form.version.data,
                wait_reason_id=form.motivo_espera.data,
                text=form.texto.data,
            )
            db.session.commit()
        except TicketConflictError as error:
            # Otra persona lo modificó: se vuelve a abrir la pantalla con los
            # datos actuales (si la acción ya no corresponde, avisa).
            db.session.rollback()
            flash(str(error), "error")

            return redirect(
                url_for(
                    "tickets.change_ticket_state",
                    public_id=public_id,
                    action_slug=action_slug,
                )
            )
        except TicketClosedError as error:
            db.session.rollback()
            flash(str(error), "error")

            return redirect(url_for("tickets.detail", public_id=public_id))
        except StateTransitionError as error:
            db.session.rollback()
            flash(str(error), "error")

            return redirect(url_for("tickets.detail", public_id=public_id))
        except TicketRuleError as error:
            db.session.rollback()
            flash(str(error), "error")
        else:
            flash(
                info.success_message.format(
                    number=public_id,
                    state=new_state.nombre_visible,
                ),
                "success",
            )

            return redirect(url_for("tickets.detail", public_id=public_id))

    return render_template(
        "tickets/state_change.html",
        ticket=ticket,
        form=form,
        info=info,
        destination=option.destination,
        wait_reasons=wait_reasons,
        max_text=MAX_WAIT_TEXT_LENGTH,
    )


# --- Asignación, grupo y escalamiento ---------------------------------


@bp.post("/<public_id>/assign-me")
@login_required
def assign_me(public_id: str):
    """Un Técnico se asigna a sí mismo el ticket."""
    ticket = _visible_ticket_or_404(public_id)

    if not can_assign_self(current_user):
        abort(403)

    return _run_assignment(
        ticket,
        lambda: assign_technician(ticket, current_user.id, actor=_actor()),
        f"Te asignaste el ticket #{public_id}.",
        back="tickets.detail",
    )


@bp.post("/<public_id>/unassign-me")
@login_required
def unassign_me(public_id: str):
    """Un Técnico deja de estar asignado al ticket."""
    ticket = _visible_ticket_or_404(public_id)

    if not can_assign_self(current_user):
        abort(403)

    mine = _my_assignment(ticket)

    if mine is None:
        flash("No estás asignado a este ticket.", "warning")

        return redirect(url_for("tickets.detail", public_id=public_id))

    return _run_assignment(
        ticket,
        lambda: unassign_technician(ticket, mine.id, actor=_actor()),
        f"Dejaste de estar asignado al ticket #{public_id}.",
        back="tickets.detail",
    )


@bp.get("/<public_id>/assignment")
@login_required
def assignment_page(public_id: str):
    """Técnicos y grupo del ticket (Supervisor y Administrador)."""
    ticket = _visible_ticket_or_404(public_id)

    if not can_manage_assignments(current_user):
        abort(403)

    if _is_closed(ticket):
        return _closed_redirect(ticket, _CLOSED_MODIFY_MESSAGE)

    technician_form = TechnicianPickForm(
        choices=_people(list_assignable_technicians(ticket))
    )
    group_form = GroupChangeForm(
        choices=_group_choices(ticket),
        version=ticket.version,
        grupo=ticket.grupo_id,
    )

    return render_template(
        "tickets/assignment.html",
        ticket=ticket,
        technician_form=technician_form,
        group_form=group_form,
    )


@bp.post("/<public_id>/assignment/technicians/add")
@login_required
def add_ticket_technician(public_id: str):
    ticket = _visible_ticket_or_404(public_id)

    if not can_manage_assignments(current_user):
        abort(403)

    form = TechnicianPickForm(
        choices=_people(list_assignable_technicians(ticket))
    )

    if not form.validate_on_submit():
        flash(
            form.tecnico.errors[0]
            if form.tecnico.errors
            else "No se pudo asignar.",
            "error",
        )

        return redirect(url_for("tickets.assignment_page", public_id=public_id))

    return _run_assignment(
        ticket,
        lambda: assign_technician(ticket, form.tecnico.data, actor=_actor()),
        "Técnico asignado.",
        back="tickets.assignment_page",
    )


@bp.post("/<public_id>/assignment/technicians/<int:assignment_id>/remove")
@login_required
def remove_ticket_technician(public_id: str, assignment_id: int):
    ticket = _visible_ticket_or_404(public_id)
    assignment = next(
        (a for a in ticket.tecnicos_vigentes if a.id == assignment_id),
        None,
    )

    # Supervisor y Administrador quitan a cualquiera; un Técnico, solo a sí
    # mismo.
    is_own = (
        assignment is not None
        and can_assign_self(current_user)
        and assignment.tecnico_id == current_user.id
    )

    if not (can_manage_assignments(current_user) or is_own):
        abort(403)

    return _run_assignment(
        ticket,
        lambda: unassign_technician(
            ticket,
            assignment_id,
            actor=_actor(),
            reason=request.form.get("motivo"),
        ),
        "Técnico desasignado.",
        back=(
            "tickets.assignment_page"
            if can_manage_assignments(current_user)
            else "tickets.detail"
        ),
    )


@bp.post("/<public_id>/assignment/group")
@login_required
def set_ticket_group(public_id: str):
    ticket = _visible_ticket_or_404(public_id)

    if not can_manage_assignments(current_user):
        abort(403)

    form = GroupChangeForm(choices=_group_choices(ticket))

    if not form.validate_on_submit():
        flash(
            (form.grupo.errors or form.version.errors or ["No se pudo cambiar."])[0],
            "error",
        )

        return redirect(url_for("tickets.assignment_page", public_id=public_id))

    holder = {}

    def run():
        holder["changed"] = set_group(
            ticket,
            form.grupo.data,
            actor=_actor(),
            expected_version=form.version.data,
        )

    response = _run_assignment(
        ticket,
        run,
        "El grupo del ticket se actualizó.",
        back="tickets.assignment_page",
        quiet=True,
    )

    if holder.get("changed") is False:
        flash("El ticket ya tiene ese grupo.", "warning")
    elif holder.get("changed"):
        flash("El grupo del ticket se actualizó.", "success")

    return response


@bp.route("/<public_id>/escalate", methods=["GET", "POST"])
@login_required
def escalate(public_id: str):
    ticket = _visible_ticket_or_404(public_id)

    if not can_manage_assignments(current_user):
        abort(403)

    if _is_closed(ticket):
        return _closed_redirect(ticket, _CLOSED_MODIFY_MESSAGE)

    initial = {"version": ticket.version} if request.method == "GET" else {}

    form = EscalationForm(
        group_choices=_group_choices(ticket, active_only=True),
        technician_choices=_people(list_escalation_technicians()),
        **initial,
    )

    if form.validate_on_submit():
        try:
            escalate_ticket(
                ticket,
                actor=_actor(),
                expected_version=form.version.data,
                group_id=form.grupo.data,
                technician_id=form.tecnico.data,
                reason=form.motivo.data,
            )
            db.session.commit()
        except TicketConflictError as error:
            db.session.rollback()
            flash(str(error), "error")

            return redirect(url_for("tickets.escalate", public_id=public_id))
        except TicketClosedError as error:
            db.session.rollback()
            flash(str(error), "error")

            return redirect(url_for("tickets.detail", public_id=public_id))
        except TicketRuleError as error:
            db.session.rollback()
            flash(str(error), "error")
        else:
            flash(f"El ticket #{public_id} fue escalado.", "success")

            return redirect(url_for("tickets.detail", public_id=public_id))

    return render_template(
        "tickets/escalate.html",
        ticket=ticket,
        form=form,
        max_reason=MAX_REASON_LENGTH,
    )


# --- Solicitantes -----------------------------------------------------


@bp.get("/<public_id>/requesters")
@login_required
def requesters_page(public_id: str):
    """Solicitantes del ticket: el personal los ve, agrega y retira."""
    ticket = _visible_ticket_or_404(public_id)

    if not can_manage_requesters(current_user):
        abort(403)

    if _is_closed(ticket):
        return _closed_redirect(ticket, _CLOSED_MODIFY_MESSAGE)

    return render_template(
        "tickets/requesters.html",
        ticket=ticket,
        requester_form=RequesterPickForm(
            choices=_requester_choices(list_addable_requesters(ticket))
        ),
    )


@bp.post("/<public_id>/requesters/add")
@login_required
def add_ticket_requester(public_id: str):
    ticket = _visible_ticket_or_404(public_id)

    if not can_manage_requesters(current_user):
        abort(403)

    form = RequesterPickForm(
        choices=_requester_choices(list_addable_requesters(ticket))
    )

    if not form.validate_on_submit():
        flash(
            form.solicitante.errors[0]
            if form.solicitante.errors
            else "No se pudo agregar al solicitante.",
            "error",
        )

        return redirect(url_for("tickets.requesters_page", public_id=public_id))

    return _run_assignment(
        ticket,
        lambda: add_requester(ticket, form.solicitante.data, actor=_actor()),
        "Solicitante agregado.",
        back="tickets.requesters_page",
    )


@bp.route(
    "/<public_id>/requesters/<int:participation_id>/remove",
    methods=["GET", "POST"],
)
@login_required
def remove_ticket_requester(public_id: str, participation_id: int):
    """Confirmación (con motivo opcional) para retirar a un solicitante.

    Retirarlo le quita el acceso al ticket, así que no es un clic sin más (a
    diferencia de quitar un técnico, que es solo organizativo).
    """
    ticket = _visible_ticket_or_404(public_id)

    if not can_manage_requesters(current_user):
        abort(403)

    if _is_closed(ticket):
        return _closed_redirect(ticket, _CLOSED_MODIFY_MESSAGE)

    link = next(
        (r for r in ticket.solicitantes_vigentes if r.id == participation_id),
        None,
    )

    if link is None:
        flash("Esa persona ya no es solicitante del ticket.", "error")

        return redirect(url_for("tickets.requesters_page", public_id=public_id))

    form = ReasonForm()

    if form.validate_on_submit():
        name = f"{link.solicitante.nombre} {link.solicitante.apellido}"

        return _run_assignment(
            ticket,
            lambda: remove_requester(
                ticket,
                participation_id,
                actor=_actor(),
                reason=form.motivo.data,
            ),
            f"{name} dejó de ser solicitante del ticket.",
            back="tickets.requesters_page",
        )

    return render_template(
        "tickets/requester_remove.html",
        ticket=ticket,
        link=link,
        form=form,
        max_reason=MAX_REASON_LENGTH,
    )


# --- Comentarios y notas internas -------------------------------------


@bp.post("/<public_id>/comments")
@login_required
def add_ticket_comment(public_id: str):
    """Publica un comentario o una nota interna (formulario del detalle)."""
    ticket = _visible_ticket_or_404(public_id)

    if not can_comment_publicly(current_user, ticket):
        abort(403)

    form = CommentForm()

    if not form.validate_on_submit():
        # Se vuelve al detalle con los errores y lo que ya se había escrito.
        return _render_detail(ticket, form)

    kind = CommentType(form.tipo.data)

    # Una nota interna es solo del personal: enviar el tipo a mano no basta.
    if kind is CommentType.INTERNO and not can_write_internal_note(current_user):
        abort(403)

    paths: list[str] = []

    try:
        comment = add_comment(
            ticket,
            actor=_actor(),
            content=form.contenido.data,
            kind=kind,
        )
        # Los archivos del mismo envío cuelgan del comentario y heredan su
        # visibilidad. Si alguno falla, no se guarda ni el comentario.
        attachments = add_attachments(
            ticket,
            actor=_actor(),
            uploads=request.files.getlist("archivos"),
            comment=comment,
        )
        paths = [attachment.ruta_archivo for attachment in attachments]
        db.session.commit()
    except TicketClosedError as error:
        db.session.rollback()
        flash(str(error), "error")

        return redirect(url_for("tickets.detail", public_id=public_id))
    except TicketRuleError as error:
        # Por ejemplo, un archivo no permitido: se vuelve al detalle con lo
        # escrito para no perderlo.
        db.session.rollback()
        flash(str(error), "error")

        return _render_detail(ticket, form)
    except Exception:
        # Si la base de datos falla tras guardar los archivos, se borran.
        db.session.rollback()
        discard_files(paths)

        raise

    flash(
        "Nota interna registrada."
        if kind is CommentType.INTERNO
        else "Comentario publicado.",
        "success",
    )

    return redirect(
        url_for(
            "tickets.detail",
            public_id=public_id,
            _anchor=f"comentario-{comment.id}",
        )
    )


@bp.route("/<public_id>/comments/<int:comment_id>/edit", methods=["GET", "POST"])
@login_required
def edit_ticket_comment(public_id: str, comment_id: int):
    ticket = _visible_ticket_or_404(public_id)
    comment = _visible_comment_or_404(ticket, comment_id)

    # Quien ve el comentario pero no puede editarlo (no es suyo, o venció el
    # plazo) recibe un 403.
    if not can_edit_comment(current_user, comment):
        abort(403)

    if _is_closed(ticket):
        return _closed_redirect(ticket, _CLOSED_MODIFY_MESSAGE)

    initial = {"contenido": comment.contenido} if request.method == "GET" else {}
    form = CommentEditForm(**initial)

    if form.validate_on_submit():
        try:
            changed = edit_comment(
                ticket,
                comment_id,
                actor=_actor(),
                content=form.contenido.data,
            )
            db.session.commit()
        except TicketRuleError as error:
            db.session.rollback()
            flash(str(error), "error")

            return redirect(url_for("tickets.detail", public_id=public_id))

        flash(
            "Comentario actualizado."
            if changed
            else "No había cambios que guardar.",
            "success" if changed else "warning",
        )

        return redirect(
            url_for(
                "tickets.detail",
                public_id=public_id,
                _anchor=f"comentario-{comment_id}",
            )
        )

    return render_template(
        "tickets/comment_edit.html",
        ticket=ticket,
        comment=comment,
        form=form,
        max_comment=MAX_COMMENT_LENGTH,
    )


@bp.route("/<public_id>/comments/<int:comment_id>/delete", methods=["GET", "POST"])
@login_required
def delete_ticket_comment(public_id: str, comment_id: int):
    """Confirmación para eliminar un comentario o nota (eliminación lógica)."""
    ticket = _visible_ticket_or_404(public_id)
    comment = _visible_comment_or_404(ticket, comment_id)

    if not can_delete_comment(current_user, comment):
        abort(403)

    if _is_closed(ticket):
        return _closed_redirect(ticket, _CLOSED_MODIFY_MESSAGE)

    form = FlaskForm()

    if form.validate_on_submit():
        was_note = comment.es_nota_interna

        try:
            delete_comment(ticket, comment_id, actor=_actor())
            db.session.commit()
        except TicketRuleError as error:
            db.session.rollback()
            flash(str(error), "error")
        else:
            flash(
                "Nota interna eliminada." if was_note else "Comentario eliminado.",
                "success",
            )

        return redirect(url_for("tickets.detail", public_id=public_id))

    return render_template(
        "tickets/comment_delete.html",
        ticket=ticket,
        comment=comment,
        form=form,
    )


# --- Adjuntos ---------------------------------------------------------


@bp.post("/<public_id>/attachments")
@login_required
def add_ticket_attachments(public_id: str):
    """Sube archivos al ticket (tarjeta «Archivos»)."""
    ticket = _visible_ticket_or_404(public_id)

    if not can_attach_files(current_user, ticket):
        abort(403)

    form = FlaskForm()

    if not form.validate_on_submit():
        abort(400)

    paths: list[str] = []
    back = url_for("tickets.detail", public_id=public_id, _anchor="archivos")

    try:
        attachments = add_attachments(
            ticket,
            actor=_actor(),
            uploads=request.files.getlist("archivos"),
        )
        paths = [attachment.ruta_archivo for attachment in attachments]
        db.session.commit()
    except TicketRuleError as error:
        db.session.rollback()
        flash(str(error), "error")

        return redirect(back)
    except Exception:
        db.session.rollback()
        discard_files(paths)

        raise

    if not attachments:
        flash("Elige al menos un archivo.", "warning")
    else:
        flash(
            "Archivo adjuntado."
            if len(attachments) == 1
            else f"{len(attachments)} archivos adjuntados.",
            "success",
        )

    return redirect(back)


@bp.get("/<public_id>/attachments/<int:attachment_id>/download")
@login_required
def download_ticket_attachment(public_id: str, attachment_id: int):
    """Descarga autenticada: se comprueba el acceso al ticket y al adjunto, y
    el archivo se envía siempre como descarga (nunca se interpreta en el
    navegador)."""
    ticket = _visible_ticket_or_404(public_id)
    attachment = _visible_attachment_or_404(ticket, attachment_id)

    try:
        path = attachment_path(attachment)
    except ValueError:
        abort(404)

    if not path.is_file():
        current_app.logger.error(
            "Adjunto sin archivo físico: archivo_id=%s", attachment.id
        )
        abort(404)

    response = send_file(
        path,
        mimetype=attachment.mime_type,
        as_attachment=True,
        download_name=attachment.nombre_original,
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "private, no-store"

    return response


@bp.route(
    "/<public_id>/attachments/<int:attachment_id>/delete",
    methods=["GET", "POST"],
)
@login_required
def delete_ticket_attachment(public_id: str, attachment_id: int):
    """Confirmación para eliminar un adjunto (eliminación lógica)."""
    ticket = _visible_ticket_or_404(public_id)
    attachment = _visible_attachment_or_404(ticket, attachment_id)

    if not can_delete_attachment(current_user, attachment):
        abort(403)

    if _is_closed(ticket):
        return _closed_redirect(ticket, _CLOSED_MODIFY_MESSAGE)

    form = FlaskForm()

    if form.validate_on_submit():
        try:
            delete_attachment(ticket, attachment_id, actor=_actor())
            db.session.commit()
        except TicketRuleError as error:
            db.session.rollback()
            flash(str(error), "error")
        else:
            flash("Archivo eliminado.", "success")

        return redirect(url_for("tickets.detail", public_id=public_id))

    return render_template(
        "tickets/attachment_delete.html",
        ticket=ticket,
        attachment=attachment,
        form=form,
    )


# --- Utilidades -------------------------------------------------------


def _visible_attachment_or_404(ticket, attachment_id: int):
    """Adjunto del ticket que el usuario puede ver; 404 en cualquier otro caso
    (no existe, es de otro ticket, está eliminado o cuelga de una nota
    interna que no puede ver)."""
    attachment = get_attachment(ticket, attachment_id, _actor())

    if attachment is None:
        abort(404)

    return attachment


def _visible_comment_or_404(ticket, comment_id: int):
    """Comentario del ticket que el usuario puede ver; 404 en cualquier otro
    caso (no existe, es de otro ticket, está eliminado o es una nota interna
    y el usuario es un Solicitante)."""
    comment = get_comment(ticket, comment_id, _actor())

    if comment is None:
        abort(404)

    return comment


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


# Aviso de las operaciones que cuelgan del ticket (asignación, escalamiento,
# solicitantes...) cuando el ticket ya está cerrado.
_CLOSED_MODIFY_MESSAGE = (
    "Un ticket cerrado no se puede modificar. Primero debe reabrirse."
)


def _closed_redirect(
    ticket,
    message="Un ticket cerrado no se puede editar. Primero debe reabrirse.",
):
    flash(message, "error")

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


def _run_assignment(ticket, operation, success_message, *, back, quiet=False):
    """Ejecuta una operación que cuelga del ticket (asignación, solicitantes),
    confirma y vuelve a `back`.

    Un ticket cerrado, un conflicto de versión o una regla incumplida se
    muestran como aviso sin guardar nada.
    """
    public_id = ticket.public_id

    try:
        operation()
        db.session.commit()
    except TicketClosedError as error:
        db.session.rollback()
        flash(str(error), "error")

        return redirect(url_for("tickets.detail", public_id=public_id))
    except (TicketConflictError, TicketRuleError) as error:
        db.session.rollback()
        flash(str(error), "error")
    else:
        if not quiet:
            flash(success_message, "success")

    return redirect(url_for(back, public_id=public_id))


def _my_assignment(ticket):
    """La asignación vigente del usuario actual en el ticket, si es técnico y
    está asignado."""
    if not can_assign_self(current_user):
        return None

    return next(
        (a for a in ticket.tecnicos_vigentes if a.tecnico_id == current_user.id),
        None,
    )


def _people(users) -> list[tuple[int, str]]:
    return [(user.id, f"{user.nombre} {user.apellido}") for user in users]


def _requester_choices(users) -> list[tuple[int, str]]:
    """Opciones para elegir solicitantes. Incluyen el usuario para distinguir
    a personas con el mismo nombre."""
    return [
        (user.id, f"{user.apellido}, {user.nombre} ({user.username})")
        for user in users
    ]


def _group_choices(ticket, *, active_only=False) -> list[tuple[int, str]]:
    groups = list_groups_for_ticket(ticket)

    if active_only:
        groups = [g for g in groups if g.activo]

    return [(g.id, g.nombre if g.activo else f"{g.nombre} (inactivo)") for g in groups]


def _actor():
    return current_user._get_current_object()
