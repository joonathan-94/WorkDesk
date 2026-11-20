from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from ..extensions import db
from ..security import (
    RoleCode,
    admin_only,
    can_manage_group_members,
    can_manage_groups,
    can_view_group,
    current_actor,
    roles_required,
)
from ..users.forms import ReasonForm
from . import bp
from .forms import GroupForm, UserPickForm
from .service import (
    VALID_STATUSES,
    GroupRuleError,
    activate_group,
    add_member,
    create_group,
    deactivate_group,
    designate_supervisor,
    get_group,
    list_groups,
    list_member_candidates,
    list_supervisor_candidates,
    remove_member,
    remove_supervisor,
    update_group,
)

# El área de grupos es del Administrador y de los Supervisores; el resto de
# roles recibe 403. Dentro del área, cada acción se vuelve a comprobar aquí,
# en backend: ocultar un botón no autoriza nada.
area_only = roles_required(RoleCode.ADMINISTRADOR, RoleCode.SUPERVISOR)


# --- Listado y detalle ------------------------------------------------


@bp.get("")
@area_only
def list_groups_page():
    status = request.args.get("estado", "")
    status = status if status in VALID_STATUSES else ""

    return render_template(
        "groups/list.html",
        groups=list_groups(current_actor(), status),
        status=status,
        crumbs=_crumbs(),
        can_manage=can_manage_groups(current_user),
    )


@bp.get("/<int:group_id>")
@area_only
def detail(group_id: int):
    group = _visible_group_or_404(group_id)
    is_admin = can_manage_groups(current_user)
    can_members = can_manage_group_members(current_user, group) and group.activo

    return render_template(
        "groups/detail.html",
        group=group,
        crumbs=_crumbs(group),
        is_admin=is_admin,
        can_members=can_members,
        # Solo hacen falta los candidatos si se va a mostrar el formulario.
        member_form=(
            UserPickForm(
                choices=_choices(list_member_candidates(group)),
                message="Elige un técnico de la lista.",
            )
            if can_members
            else None
        ),
        supervisor_form=(
            UserPickForm(
                choices=_choices(list_supervisor_candidates(group)),
                message="Elige un supervisor de la lista.",
            )
            if is_admin and group.activo
            else None
        ),
    )


# --- Alta y edición (solo Administrador) ------------------------------


@bp.route("/new", methods=["GET", "POST"])
@admin_only
def new_group():
    form = GroupForm()

    if form.validate_on_submit():
        try:
            group = create_group(
                actor=current_actor(),
                nombre=form.nombre.data,
                descripcion=form.descripcion.data,
            )
            db.session.commit()
        except GroupRuleError as error:
            db.session.rollback()
            form.nombre.errors.append(str(error))
        else:
            flash(f"El grupo «{group.nombre}» fue creado.", "success")

            return redirect(url_for("groups.detail", group_id=group.id))

    return render_template(
        "groups/form.html",
        form=form,
        group=None,
        crumbs=_crumbs(last="Nuevo grupo"),
    )


@bp.route("/<int:group_id>/edit", methods=["GET", "POST"])
@area_only
def edit_group(group_id: int):
    group = _visible_group_or_404(group_id)
    _require_admin()

    form = GroupForm(obj=group)

    if form.validate_on_submit():
        try:
            changed = update_group(
                group,
                actor=current_actor(),
                nombre=form.nombre.data,
                descripcion=form.descripcion.data,
            )
            db.session.commit()
        except GroupRuleError as error:
            db.session.rollback()
            form.nombre.errors.append(str(error))
        else:
            if changed:
                flash(f"El grupo «{group.nombre}» se actualizó.", "success")
            else:
                flash("No había cambios que guardar.", "warning")

            return redirect(url_for("groups.detail", group_id=group.id))

    return render_template(
        "groups/form.html",
        form=form,
        group=group,
        crumbs=_crumbs(group, "Editar"),
    )


@bp.route("/<int:group_id>/deactivate", methods=["GET", "POST"])
@area_only
def deactivate(group_id: int):
    return _status_page(group_id, deactivate=True)


@bp.route("/<int:group_id>/activate", methods=["GET", "POST"])
@area_only
def activate(group_id: int):
    return _status_page(group_id, deactivate=False)


# --- Miembros ---------------------------------------------------------


@bp.post("/<int:group_id>/members/add")
@area_only
def add_group_member(group_id: int):
    group = _visible_group_or_404(group_id)
    _require_members_permission(group)

    form = UserPickForm(
        choices=_choices(list_member_candidates(group)),
        message="Elige un técnico de la lista.",
    )

    if form.validate_on_submit():
        try:
            link = add_member(group, form.usuario.data, actor=current_actor())
            db.session.commit()
        except GroupRuleError as error:
            db.session.rollback()
            flash(str(error), "error")
        else:
            flash(
                f"{_full_name(link.usuario)} se agregó al grupo.",
                "success",
            )
    else:
        flash(_first_error(form), "error")

    return redirect(url_for("groups.detail", group_id=group.id))


@bp.route(
    "/<int:group_id>/members/<int:membership_id>/remove",
    methods=["GET", "POST"],
)
@area_only
def remove_group_member(group_id: int, membership_id: int):
    group = _visible_group_or_404(group_id)
    _require_members_permission(group)

    link = next(
        (m for m in group.miembros_vigentes if m.id == membership_id),
        None,
    )

    if link is None:
        flash("Esa persona ya no es miembro del grupo.", "error")

        return redirect(url_for("groups.detail", group_id=group.id))

    return _confirm_page(
        group,
        form_action=url_for(
            "groups.remove_group_member",
            group_id=group.id,
            membership_id=membership_id,
        ),
        heading="Retirar del grupo",
        subject=_full_name(link.usuario),
        message=(
            "La persona deja de ser miembro del grupo. La membresía queda "
            "como historial y se puede volver a agregar más adelante."
        ),
        button="Retirar del grupo",
        danger=True,
        operation=lambda reason: remove_member(
            group,
            membership_id,
            actor=current_actor(),
            reason=reason,
        ),
        success=f"{_full_name(link.usuario)} fue retirado del grupo.",
        crumb="Retirar miembro",
    )


# --- Supervisores responsables (solo Administrador) -------------------


@bp.post("/<int:group_id>/supervisors/add")
@area_only
def add_group_supervisor(group_id: int):
    group = _visible_group_or_404(group_id)
    _require_admin()

    form = UserPickForm(
        choices=_choices(list_supervisor_candidates(group)),
        message="Elige un supervisor de la lista.",
    )

    if form.validate_on_submit():
        try:
            designation = designate_supervisor(
                group,
                form.usuario.data,
                actor=current_actor(),
            )
            db.session.commit()
        except GroupRuleError as error:
            db.session.rollback()
            flash(str(error), "error")
        else:
            flash(
                f"{_full_name(designation.supervisor)} es ahora responsable "
                "del grupo.",
                "success",
            )
    else:
        flash(_first_error(form), "error")

    return redirect(url_for("groups.detail", group_id=group.id))


@bp.route(
    "/<int:group_id>/supervisors/<int:designation_id>/remove",
    methods=["GET", "POST"],
)
@area_only
def remove_group_supervisor(group_id: int, designation_id: int):
    group = _visible_group_or_404(group_id)
    _require_admin()

    designation = next(
        (d for d in group.supervisores_vigentes if d.id == designation_id),
        None,
    )

    if designation is None:
        flash("Esa persona ya no es responsable del grupo.", "error")

        return redirect(url_for("groups.detail", group_id=group.id))

    return _confirm_page(
        group,
        form_action=url_for(
            "groups.remove_group_supervisor",
            group_id=group.id,
            designation_id=designation_id,
        ),
        heading="Retirar supervisor responsable",
        subject=_full_name(designation.supervisor),
        message=(
            "Deja de ser responsable del grupo y ya no podrá gestionar sus "
            "miembros. La designación queda como historial. Un grupo sin "
            "supervisor es válido: solo el Administrador gestiona entonces "
            "sus miembros."
        ),
        button="Retirar responsable",
        danger=True,
        operation=lambda reason: remove_supervisor(
            group,
            designation_id,
            actor=current_actor(),
            reason=reason,
        ),
        success=(
            f"{_full_name(designation.supervisor)} ya no es responsable del "
            "grupo."
        ),
        crumb="Retirar responsable",
    )


# --- Piezas comunes ---------------------------------------------------


def _status_page(group_id: int, *, deactivate: bool):
    group = _visible_group_or_404(group_id)
    _require_admin()

    # Se comprueba también en GET para no mostrar la confirmación de algo que
    # no se puede hacer.
    if deactivate and not group.activo:
        flash("El grupo ya está desactivado.", "error")

        return redirect(url_for("groups.detail", group_id=group.id))

    if not deactivate and group.activo:
        flash("El grupo ya está activo.", "error")

        return redirect(url_for("groups.detail", group_id=group.id))

    operation = deactivate_group if deactivate else activate_group
    name = group.nombre

    return _confirm_page(
        group,
        form_action=url_for(
            "groups.deactivate" if deactivate else "groups.activate",
            group_id=group.id,
        ),
        heading="Desactivar grupo" if deactivate else "Reactivar grupo",
        subject=name,
        message=(
            "El grupo dejará de poder usarse. Sus miembros y responsables "
            "se conservan como están y puedes reactivarlo más adelante."
            if deactivate
            else "El grupo volverá a poder usarse."
        ),
        button="Desactivar grupo" if deactivate else "Reactivar grupo",
        danger=deactivate,
        operation=lambda reason: operation(
            group,
            actor=current_actor(),
            reason=reason,
        ),
        success=(
            f"El grupo «{name}» fue desactivado."
            if deactivate
            else f"El grupo «{name}» fue reactivado."
        ),
        crumb="Desactivar" if deactivate else "Reactivar",
    )


def _confirm_page(
    group,
    *,
    form_action,
    heading,
    subject,
    message,
    button,
    danger,
    operation,
    success,
    crumb,
):
    """Confirmación con motivo opcional y ejecución de la acción."""
    form = ReasonForm()

    if form.validate_on_submit():
        try:
            operation(form.motivo.data)
            db.session.commit()
        except GroupRuleError as error:
            db.session.rollback()
            flash(str(error), "error")
        else:
            flash(success, "success")

        return redirect(url_for("groups.detail", group_id=group.id))

    return render_template(
        "groups/confirm.html",
        group=group,
        form=form,
        form_action=form_action,
        heading=heading,
        subject=subject,
        message=message,
        button=button,
        danger=danger,
        crumbs=_crumbs(group, crumb),
    )


def _visible_group_or_404(group_id: int):
    """Grupo que el usuario puede ver; 404 en cualquier otro caso.

    Un Supervisor que no es responsable de un grupo recibe lo mismo que si no
    existiera: no se revela qué grupos hay.
    """
    group = get_group(group_id)

    if group is None or not can_view_group(current_user, group):
        abort(404)

    return group


def _require_admin() -> None:
    if not can_manage_groups(current_user):
        abort(403)


def _require_members_permission(group) -> None:
    if not can_manage_group_members(current_user, group):
        abort(403)


def _crumbs(group=None, last: str | None = None):
    """Ruta de navegación: el Administrador llega desde Administración; el
    Supervisor tiene "Grupos" en su menú. El último elemento no enlaza."""
    crumbs: list[tuple[str, str | None]] = []

    if can_manage_groups(current_user):
        crumbs.append(("Administración", url_for("admin.index")))

    crumbs.append(
        (
            "Grupos",
            None if group is None and last is None
            else url_for("groups.list_groups_page"),
        )
    )

    if group is not None:
        crumbs.append(
            (
                group.nombre,
                None if last is None
                else url_for("groups.detail", group_id=group.id),
            )
        )

    if last is not None:
        crumbs.append((last, None))

    return crumbs


def _first_error(form: UserPickForm) -> str:
    return (
        form.usuario.errors[0]
        if form.usuario.errors
        else "No se pudo completar la acción."
    )


def _choices(users) -> list[tuple[int, str]]:
    return [(user.id, _full_name(user)) for user in users]


def _full_name(user) -> str:
    return f"{user.nombre} {user.apellido}"
