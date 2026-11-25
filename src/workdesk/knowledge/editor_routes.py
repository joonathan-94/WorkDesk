"""La gestión de artículos (docs/11, UI-011): el listado del personal, el editor y las
acciones editoriales, cada una con su pantalla de confirmación.

El personal escribe borradores; publicar, destacar y desactivar dependen de las políticas.
Un artículo que no se puede leer responde 404; uno que se lee pero no permite la acción,
403. Las reglas están en `knowledge/service.py`.
"""

from dataclasses import dataclass

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from ..extensions import db
from ..models import ArticleLinkType
from ..security import (
    STAFF_ROLES,
    can_deactivate_article,
    can_edit_article,
    can_publish_article,
    can_view_ticket,
    current_actor,
    roles_required,
)
from ..tickets.service import (
    TicketRuleError,
    categories_for_selection,
    get_ticket_by_public_id,
)
from ..users.forms import MAX_REASON_LENGTH, ReasonForm
from . import bp
from .forms import ArticleForm
from .queries import (
    MANAGE_ALL,
    MANAGE_DRAFTS,
    MANAGE_INACTIVE,
    MANAGE_PUBLISHED,
    manage_articles,
)
from .routes import article_or_404
from .service import (
    ArticleConflictError,
    ArticleRuleError,
    activate_article,
    create_article,
    deactivate_article,
    publish_article,
    set_featured,
    unpublish_article,
    update_article,
)

staff_only = roles_required(*STAFF_ROLES)

PUBLISH_BUTTON = "publicar"


@bp.get("/manage")
@staff_only
def manage():
    views = {
        MANAGE_ALL: "Todos",
        MANAGE_DRAFTS: "Borradores",
        MANAGE_PUBLISHED: "Publicados",
    }

    if can_deactivate_article(current_user):
        views[MANAGE_INACTIVE] = "Desactivados"

    view = request.args.get("estado", MANAGE_ALL)
    view = view if view in views else MANAGE_ALL
    page = max(request.args.get("page", 1, type=int), 1)

    return render_template(
        "knowledge/manage.html",
        articles=manage_articles(current_user, view, page=page),
        views=views,
        view=view,
        can_edit=lambda article: can_edit_article(current_user, article),
    )


# --- Editor ----------------------------------------------------------------------------------


def _category_choices(current=None) -> list[tuple[int, str]]:
    """Las categorías activas y, al editar, la que el artículo ya tiene aunque esté
    desactivada."""
    choices = [(category.id, category.nombre) for category in categories_for_selection()]

    if current is not None and current.id not in {code for code, _name in choices}:
        choices.append((current.id, f"{current.nombre} (inactiva)"))

    return choices


def _render_editor(form, article=None, *, error: str | None = None, source=None):
    return render_template(
        "knowledge/form.html",
        form=form,
        article=article,
        error=error,
        source=source,
        can_publish=can_publish_article(current_user)
        and (article is None or (article.activo and not article.publicado)),
        publish_button=PUBLISH_BUTTON,
    )


def _wants_to_publish() -> bool:
    if PUBLISH_BUTTON not in request.form:
        return False

    if not can_publish_article(current_user):
        abort(403)

    return True


def _source_ticket():
    """El ticket cuya resolución se convierte en artículo, si la petición lo indica.

    Debe poder verlo la persona y tener una resolución escrita; si no, 404 (como un ticket
    inexistente)."""
    number = request.values.get("ticket", "").strip()

    if not number:
        return None

    ticket = get_ticket_by_public_id(number) if number.isdecimal() else None

    if (
        ticket is None
        or not can_view_ticket(current_user, ticket)
        or not ticket.resolucion
    ):
        abort(404)

    return ticket


def _prefill(form, ticket) -> None:
    """Propone título, categoría y contenido; la persona los revisa antes de guardar. La
    descripción del ticket no se copia: puede tener datos personales."""
    form.titulo.data = ticket.titulo
    form.contenido.data = ticket.resolucion

    if ticket.categoria_id in {code for code, _name in form.category_choices}:
        form.categoria.data = ticket.categoria_id


@bp.route("/new", methods=["GET", "POST"])
@staff_only
def new_article():
    source = _source_ticket()
    form = ArticleForm(category_choices=_category_choices())

    if request.method == "GET":
        form.visibilidad.data = form.visibility_choices[0][0]

        if source is not None:
            _prefill(form, source)

    if not form.validate_on_submit():
        return _render_editor(form, source=source)

    publish = _wants_to_publish()

    try:
        article = create_article(
            actor=current_actor(),
            title=form.titulo.data,
            content=form.contenido.data,
            category_id=form.categoria.data,
            visibility=form.visibilidad.data,
        )

        if publish:
            publish_article(article, actor=current_actor(), expected_version=article.version)

        if source is not None:
            # Importado aquí: `tickets.knowledge_links` usa este paquete, así que
            # importarlo arriba cerraría un ciclo al cargar la aplicación.
            from ..tickets.knowledge_links import link_article

            # En la misma transacción: o quedan el artículo y su vínculo, o ninguno.
            link_article(
                source,
                article.id,
                actor=current_actor(),
                kind=ArticleLinkType.ORIGEN_RESOLUCION,
            )
    except (ArticleRuleError, TicketRuleError) as error:
        db.session.rollback()

        return _render_editor(form, error=str(error), source=source)

    db.session.commit()
    flash(
        "El artículo se publicó." if publish else "El borrador se guardó.",
        "success",
    )

    return redirect(url_for("knowledge.detail", article_id=article.id))


@bp.route("/<int:article_id>/edit", methods=["GET", "POST"])
@staff_only
def edit_article(article_id: int):
    article = article_or_404(article_id)

    if not can_edit_article(current_user, article):
        abort(403)

    choices = _category_choices(article.categoria)

    if request.method == "GET":
        form = ArticleForm(
            category_choices=choices,
            data={
                "titulo": article.titulo,
                "contenido": article.contenido,
                "categoria": article.categoria_id,
                "visibilidad": article.visibilidad,
                "version": article.version,
            },
        )

        return _render_editor(form, article)

    # En un envío manda lo que llegó: una petición sin versión no se completa sola.
    form = ArticleForm(category_choices=choices)

    if not form.validate_on_submit():
        return _render_editor(form, article)

    publish = _wants_to_publish()

    try:
        changed = update_article(
            article,
            actor=current_actor(),
            expected_version=form.version.data,
            title=form.titulo.data,
            content=form.contenido.data,
            category_id=form.categoria.data,
            visibility=form.visibilidad.data,
        )

        if publish:
            changed = (
                publish_article(
                    article, actor=current_actor(), expected_version=article.version
                )
                or changed
            )
    except ArticleConflictError:
        db.session.rollback()

        # El texto escrito se conserva (puede ser largo) pero con la versión antigua: no se
        # puede guardar encima del cambio ajeno sin haberlo visto.
        return _render_editor(
            form,
            article,
            error=(
                "Otra persona cambió este artículo mientras lo editabas y no se guardó "
                "nada. Tu texto sigue aquí: cópialo, abre la versión actual y aplica "
                "tus cambios sobre ella."
            ),
        )
    except ArticleRuleError as error:
        db.session.rollback()

        return _render_editor(form, article, error=str(error))

    db.session.commit()
    flash(
        "Los cambios se guardaron." if changed else "No hay cambios que guardar.",
        "success" if changed else "info",
    )

    return redirect(url_for("knowledge.detail", article_id=article.id))


# --- Acciones editoriales ---------------------------------------------------------------------


@dataclass(frozen=True)
class EditorialAction:
    """Una acción con pantalla de confirmación: quién puede, cuándo corresponde y qué hace."""

    title: str
    button: str
    explanation: str
    done: str
    allowed: object  # política: recibe al usuario
    applies: object  # recibe el artículo: si tiene sentido ahora
    run: object  # recibe (artículo, actor, versión, motivo)
    asks_reason: bool = True
    danger: bool = False


def _feature(value: bool):
    def run(article, actor, version, reason):
        return set_featured(article, value, actor=actor, expected_version=version)

    return run


def _with_reason(operation):
    def run(article, actor, version, reason):
        return operation(article, actor=actor, expected_version=version, reason=reason)

    return run


ACTIONS = {
    "publish": EditorialAction(
        "Publicar artículo",
        "Publicar",
        "El artículo se podrá leer y buscar según su visibilidad.",
        "El artículo se publicó.",
        can_publish_article,
        lambda a: a.activo and not a.publicado,
        _with_reason(publish_article),
    ),
    "unpublish": EditorialAction(
        "Retirar de publicación",
        "Retirar",
        "Volverá a ser un borrador: dejará de aparecer en la búsqueda y dejará de estar "
        "destacado.",
        "El artículo volvió a borrador.",
        can_publish_article,
        lambda a: a.activo and a.publicado,
        _with_reason(unpublish_article),
        danger=True,
    ),
    "feature": EditorialAction(
        "Destacar artículo",
        "Destacar",
        "Aparecerá en los artículos destacados de la portada.",
        "El artículo quedó destacado.",
        can_publish_article,
        lambda a: a.activo and a.publicado and not a.destacado,
        _feature(True),
        asks_reason=False,
    ),
    "unfeature": EditorialAction(
        "Quitar destacado",
        "Quitar destacado",
        "Dejará de aparecer entre los destacados; sigue publicado.",
        "El artículo dejó de estar destacado.",
        can_publish_article,
        lambda a: a.destacado,
        _feature(False),
        asks_reason=False,
    ),
    "deactivate": EditorialAction(
        "Desactivar artículo",
        "Desactivar",
        "Dejará de verse sin borrarse; conserva su historial y podrás reactivarlo.",
        "El artículo se desactivó.",
        can_deactivate_article,
        lambda a: a.activo,
        _with_reason(deactivate_article),
        danger=True,
    ),
    "activate": EditorialAction(
        "Reactivar artículo",
        "Reactivar",
        "Volverá a verse con el estado de publicación que tenía.",
        "El artículo se reactivó.",
        can_deactivate_article,
        lambda a: not a.activo,
        _with_reason(activate_article),
    ),
}


@bp.route("/<int:article_id>/actions/<action>", methods=["GET", "POST"])
@staff_only
def article_action(article_id: int, action: str):
    spec = ACTIONS.get(action)

    if spec is None:
        abort(404)

    article = article_or_404(article_id)

    if not spec.allowed(current_user):
        abort(403)

    back = url_for("knowledge.detail", article_id=article.id)

    if not spec.applies(article):
        flash("Esa acción ya no corresponde al estado actual del artículo.", "info")

        return redirect(back)

    form = ReasonForm()

    if form.validate_on_submit():
        try:
            spec.run(
                article,
                current_actor(),
                request.form.get("version", type=int),
                form.motivo.data,
            )
        except ArticleRuleError as error:
            db.session.rollback()
            flash(str(error), "warning")

            return redirect(back)

        db.session.commit()
        flash(spec.done, "success")

        return redirect(back)

    return render_template(
        "knowledge/action.html",
        article=article,
        action=action,
        spec=spec,
        form=form,
        reason_max=MAX_REASON_LENGTH,
    )
