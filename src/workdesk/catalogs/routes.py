from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from ..extensions import db
from ..models import Categoria, Prioridad, Ubicacion
from ..models.ubicacion import LOCATION_TYPE_LABELS, LocationType
from ..security import RoleCode, roles_required
from ..users.forms import ReasonForm
from . import bp
from .forms import CategoryForm, LocationForm, PriorityForm
from .screens import CATEGORIES, LOCATIONS, PRIORITIES, CatalogScreen
from .service import (
    VALID_STATUSES,
    CatalogRuleError,
    DuplicateNameError,
    activate_item,
    create_category,
    create_location,
    deactivate_item,
    deactivation_blocker,
    get_item,
    list_categories,
    list_locations,
    list_priorities,
    update_category,
    update_location,
    update_priority,
)

# Todas las rutas de este módulo son exclusivas del Administrador. La
# autorización se comprueba aquí, en backend; ocultar enlaces no la sustituye.
admin_only = roles_required(RoleCode.ADMINISTRADOR)

LOCATION_TYPE_CHOICES = [
    (location_type.value, LOCATION_TYPE_LABELS[location_type])
    for location_type in LocationType
]


# --- Categorías -------------------------------------------------------


@bp.get("/categories")
@admin_only
def categories_list():
    status = _status_filter()

    return _list_page(CATEGORIES, list_categories(status), status)


@bp.route("/categories/new", methods=["GET", "POST"])
@admin_only
def category_new():
    form = CategoryForm()

    def save():
        category = create_category(
            actor=_actor(),
            nombre=form.nombre.data,
            descripcion=form.descripcion.data,
            orden=form.orden.data,
        )

        return category.nombre, True

    return _form_page(CATEGORIES, form, item=None, save=save)


@bp.route("/categories/<int:item_id>/edit", methods=["GET", "POST"])
@admin_only
def category_edit(item_id: int):
    category = _get_or_404(Categoria, item_id)

    # En GET rellena el formulario con los datos actuales; en POST manda
    # lo enviado.
    form = CategoryForm(obj=category)

    def save():
        changed = update_category(
            category,
            actor=_actor(),
            nombre=form.nombre.data,
            descripcion=form.descripcion.data,
            orden=form.orden.data,
        )

        return category.nombre, changed

    return _form_page(CATEGORIES, form, item=category, save=save)


@bp.route("/categories/<int:item_id>/deactivate", methods=["GET", "POST"])
@admin_only
def category_deactivate(item_id: int):
    return _status_page(CATEGORIES, Categoria, item_id, deactivate=True)


@bp.route("/categories/<int:item_id>/activate", methods=["GET", "POST"])
@admin_only
def category_activate(item_id: int):
    return _status_page(CATEGORIES, Categoria, item_id, deactivate=False)


# --- Prioridades ------------------------------------------------------
# No hay alta: son exactamente cuatro (docs/11, UI-019).


@bp.get("/priorities")
@admin_only
def priorities_list():
    status = _status_filter()

    return _list_page(PRIORITIES, list_priorities(status), status)


@bp.route("/priorities/<int:item_id>/edit", methods=["GET", "POST"])
@admin_only
def priority_edit(item_id: int):
    priority = _get_or_404(Prioridad, item_id)
    form = PriorityForm(obj=priority)

    def save():
        changed = update_priority(
            priority,
            actor=_actor(),
            nombre=form.nombre.data,
            descripcion=form.descripcion.data,
        )

        return priority.nombre, changed

    return _form_page(PRIORITIES, form, item=priority, save=save)


@bp.route("/priorities/<int:item_id>/deactivate", methods=["GET", "POST"])
@admin_only
def priority_deactivate(item_id: int):
    return _status_page(PRIORITIES, Prioridad, item_id, deactivate=True)


@bp.route("/priorities/<int:item_id>/activate", methods=["GET", "POST"])
@admin_only
def priority_activate(item_id: int):
    return _status_page(PRIORITIES, Prioridad, item_id, deactivate=False)


# --- Ubicaciones ------------------------------------------------------


@bp.get("/locations")
@admin_only
def locations_list():
    status = _status_filter()

    return _list_page(LOCATIONS, list_locations(status), status)


@bp.route("/locations/new", methods=["GET", "POST"])
@admin_only
def location_new():
    form = LocationForm()

    def save():
        location = create_location(
            actor=_actor(),
            nombre=form.nombre.data,
            descripcion=form.descripcion.data,
            tipo=form.tipo.data,
        )

        return location.nombre, True

    return _form_page(LOCATIONS, form, item=None, save=save)


@bp.route("/locations/<int:item_id>/edit", methods=["GET", "POST"])
@admin_only
def location_edit(item_id: int):
    location = _get_or_404(Ubicacion, item_id)
    form = LocationForm(obj=location)

    def save():
        changed = update_location(
            location,
            actor=_actor(),
            nombre=form.nombre.data,
            descripcion=form.descripcion.data,
            tipo=form.tipo.data,
        )

        return location.nombre, changed

    return _form_page(LOCATIONS, form, item=location, save=save)


@bp.route("/locations/<int:item_id>/deactivate", methods=["GET", "POST"])
@admin_only
def location_deactivate(item_id: int):
    return _status_page(LOCATIONS, Ubicacion, item_id, deactivate=True)


@bp.route("/locations/<int:item_id>/activate", methods=["GET", "POST"])
@admin_only
def location_activate(item_id: int):
    return _status_page(LOCATIONS, Ubicacion, item_id, deactivate=False)


# --- Piezas comunes ---------------------------------------------------


def _list_page(screen: CatalogScreen, items: list, status: str):
    # Qué registros no pueden desactivarse, para no ofrecer esa acción.
    blockers = {
        item.id: deactivation_blocker(item) for item in items if item.activo
    }

    return render_template(
        "catalogs/list.html",
        screen=screen,
        items=items,
        status=status,
        blockers=blockers,
    )


def _form_page(screen: CatalogScreen, form, *, item, save):
    """Muestra el formulario y, si es válido, ejecuta `save`.

    `save()` devuelve el nombre del registro y si hubo cambios (un alta
    siempre los tiene). `item` es None al crear.
    """
    if form.validate_on_submit():
        try:
            name, changed = save()
            db.session.commit()
        except DuplicateNameError:
            db.session.rollback()
            form.nombre.errors.append(screen.duplicate_message)
        except CatalogRuleError as error:
            db.session.rollback()
            flash(str(error), "error")
        else:
            if item is None:
                flash(screen.created_message.format(name=name), "success")
            elif changed:
                flash(screen.updated_message.format(name=name), "success")
            else:
                flash("No había cambios que guardar.", "warning")

            return redirect(url_for(screen.list_endpoint))

    return render_template(
        "catalogs/form.html",
        screen=screen,
        form=form,
        item=item,
        location_types=LOCATION_TYPE_CHOICES,
    )


def _status_page(screen: CatalogScreen, model, item_id: int, *, deactivate):
    """Confirmación y ejecución de desactivar o reactivar un registro."""
    item = _get_or_404(model, item_id)

    # Se comprueba también en GET para no mostrar una confirmación de algo
    # que no se puede hacer.
    if deactivate:
        if not item.activo:
            return _blocked(screen, "Este elemento ya está desactivado.")

        blocker = deactivation_blocker(item)

        if blocker is not None:
            return _blocked(screen, blocker)
    elif item.activo:
        return _blocked(screen, "Este elemento ya está activo.")

    form = ReasonForm()

    if form.validate_on_submit():
        name = item.nombre
        operation = deactivate_item if deactivate else activate_item

        try:
            operation(item, actor=_actor(), reason=form.motivo.data)
            db.session.commit()
        except CatalogRuleError as error:
            return _blocked(screen, str(error))

        message = (
            screen.deactivated_message
            if deactivate
            else screen.activated_message
        )
        flash(message.format(name=name), "success")

        return redirect(url_for(screen.list_endpoint))

    return render_template(
        "catalogs/status_confirm.html",
        screen=screen,
        item=item,
        form=form,
        deactivating=deactivate,
    )


def _blocked(screen: CatalogScreen, message: str):
    """Una regla impide la acción: avisa y vuelve al listado."""
    db.session.rollback()
    flash(message, "error")

    return redirect(url_for(screen.list_endpoint))


def _status_filter() -> str:
    # Un filtro inválido se ignora en lugar de producir un error.
    status = request.args.get("estado", "")

    return status if status in VALID_STATUSES else ""


def _get_or_404(model, item_id: int):
    item = get_item(model, item_id)

    if item is None:
        abort(404)

    return item


def _actor():
    return current_user._get_current_object()
