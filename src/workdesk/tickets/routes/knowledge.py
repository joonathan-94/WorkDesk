"""Los artículos de conocimiento vinculados a un ticket; solo para el personal (docs/06,
RN-174). El Solicitante ve en el detalle los artículos que puede leer, sin gestionarlos."""

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm

from ...knowledge.queries import MAX_QUERY_LENGTH, search_articles
from ...security import can_link_articles, current_actor
from .. import bp
from ..knowledge_links import get_link, link_article, list_links, unlink_article
from .common import run_ticket_operation, visible_ticket_or_404

PAGE_ENDPOINT = "tickets.knowledge_page"

# Cuántos resultados ofrece el buscador para vincular.
SEARCH_RESULTS = 10


def _staff_ticket(public_id: str):
    ticket = visible_ticket_or_404(public_id)

    if not can_link_articles(current_user):
        abort(403)

    return ticket


@bp.get("/<public_id>/knowledge")
@login_required
def knowledge_page(public_id: str):
    ticket = _staff_ticket(public_id)
    links = list_links(ticket, current_user)
    query = request.args.get("q", "").strip()[:MAX_QUERY_LENGTH]
    results = []

    if query:
        linked = {link.articulo_id for link in links}
        found = search_articles(current_user, query, per_page=SEARCH_RESULTS)
        results = [article for article in found.items if article.id not in linked]

    return render_template(
        "tickets/knowledge.html",
        ticket=ticket,
        links=links,
        query=query,
        query_max=MAX_QUERY_LENGTH,
        results=results,
        form=FlaskForm(),
    )


@bp.post("/<public_id>/knowledge/add")
@login_required
def add_ticket_article(public_id: str):
    ticket = _staff_ticket(public_id)
    article_id = request.form.get("article_id", type=int)

    if article_id is None or not FlaskForm().validate_on_submit():
        flash("No se pudo vincular el artículo.", "error")

        return redirect(url_for(PAGE_ENDPOINT, public_id=ticket.public_id))

    return run_ticket_operation(
        ticket,
        lambda: link_article(ticket, article_id, actor=current_actor()),
        "Artículo vinculado al ticket.",
        back=PAGE_ENDPOINT,
    )


@bp.route("/<public_id>/knowledge/<int:link_id>/remove", methods=["GET", "POST"])
@login_required
def remove_ticket_article(public_id: str, link_id: int):
    ticket = _staff_ticket(public_id)
    link = get_link(ticket, link_id, current_user)

    if link is None:
        abort(404)

    form = FlaskForm()

    if form.validate_on_submit():
        return run_ticket_operation(
            ticket,
            lambda: unlink_article(ticket, link_id, actor=current_actor()),
            "Artículo desvinculado del ticket.",
            back=PAGE_ENDPOINT,
        )

    return render_template(
        "tickets/knowledge_remove.html", ticket=ticket, link=link, form=form
    )
