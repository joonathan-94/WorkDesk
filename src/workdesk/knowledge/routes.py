"""Lectura de la base de conocimiento (docs/11, UI-009 y UI-010), para los cuatro roles.

Qué artículos ve cada persona lo deciden las consultas; un artículo que no puede leer
responde 404, igual que uno inexistente.
"""

from flask import abort, render_template, request
from flask_login import current_user, login_required

from ..security import (
    can_create_article,
    can_deactivate_article,
    can_edit_article,
    can_publish_article,
)
from . import bp
from .queries import (
    MAX_QUERY_LENGTH,
    categories_with_articles,
    featured_articles,
    get_article,
    recent_articles,
    related_articles,
    search_articles,
)


def article_or_404(article_id: int):
    article = get_article(current_user, article_id)

    if article is None:
        abort(404)

    return article


@bp.get("")
@login_required
def index():
    query = request.args.get("q", "").strip()[:MAX_QUERY_LENGTH]
    categories = categories_with_articles(current_user)
    names = {category.id: category.nombre for category, _count in categories}
    category_id = request.args.get("categoria", type=int)

    # Una categoría sin artículos legibles (o inventada) no filtra: se ignora.
    if category_id not in names:
        category_id = None

    page = max(request.args.get("page", 1, type=int), 1)
    searching = bool(query) or category_id is not None

    return render_template(
        "knowledge/index.html",
        query=query,
        query_max=MAX_QUERY_LENGTH,
        categories=categories,
        category_id=category_id,
        category_name=names.get(category_id),
        searching=searching,
        results=(
            search_articles(current_user, query, category_id=category_id, page=page)
            if searching
            else None
        ),
        featured=[] if searching else featured_articles(current_user),
        recent=[] if searching else recent_articles(current_user),
        can_write=can_create_article(current_user),
    )


@bp.get("/<int:article_id>")
@login_required
def detail(article_id: int):
    article = article_or_404(article_id)

    return render_template(
        "knowledge/detail.html",
        article=article,
        related=related_articles(current_user, article),
        # Solo decide qué botones se muestran; cada acción lo vuelve a comprobar.
        is_staff=can_create_article(current_user),
        can_edit=can_edit_article(current_user, article),
        can_publish=can_publish_article(current_user),
        can_deactivate=can_deactivate_article(current_user),
    )
