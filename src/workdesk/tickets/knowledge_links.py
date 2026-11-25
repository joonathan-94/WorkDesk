"""El vínculo entre tickets y artículos de conocimiento (RF-104 y RF-105; docs/06, RN-174;
docs/09, 23.2).

Nada hace commit. A diferencia de las demás operaciones de un ticket, **vincular se permite
también en un ticket cerrado**: no cambia el ticket (ni su versión ni «Actualizado») y es
justo al terminar cuando una resolución suele convertirse en conocimiento. Queda en el
historial como evento interno.
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..knowledge.queries import get_article, visible_articles_condition
from ..models import Article, ArticleLinkType, Ticket, TicketArticle, TicketEvent
from ..security import can_link_articles
from .service import TicketRuleError, record_ticket_event
from .versioning import lock_ticket


def list_links(ticket: Ticket, viewer) -> list[TicketArticle]:
    """Los artículos vinculados que `viewer` puede leer, en el orden en que se vincularon.

    El filtro está en la consulta: un Solicitante solo recibe los publicados y públicos.
    No comprueba el acceso al ticket (antes hay que aplicar `can_view_ticket`).
    """
    return list(
        db.session.scalars(
            db.select(TicketArticle)
            .join(Article, Article.id == TicketArticle.articulo_id)
            .options(joinedload(TicketArticle.articulo).joinedload(Article.categoria))
            .where(
                TicketArticle.ticket_id == ticket.id,
                visible_articles_condition(viewer),
            )
            .order_by(TicketArticle.id)
        )
    )


def _require(actor) -> None:
    if not can_link_articles(actor):
        raise PermissionError("No puedes vincular artículos a un ticket.")


def _snapshot(article: Article, kind: str) -> dict:
    return {"articulo_id": article.id, "titulo": article.titulo, "tipo": kind}


def link_article(
    ticket: Ticket,
    article_id: int,
    *,
    actor,
    kind: ArticleLinkType = ArticleLinkType.REFERENCIA,
) -> TicketArticle:
    """Vincula un artículo activo que `actor` pueda leer. Un mismo par, una sola vez."""
    _require(actor)
    kind = ArticleLinkType(kind).value
    lock_ticket(ticket)
    article = get_article(actor, article_id)

    if article is None or not article.activo:
        raise TicketRuleError("Ese artículo no está disponible.")

    link = TicketArticle(
        ticket_id=ticket.id,
        articulo_id=article.id,
        tipo_vinculacion=kind,
        usuario_creacion_id=actor.id,
    )

    try:
        with db.session.begin_nested():
            db.session.add(link)
    except IntegrityError as error:
        raise TicketRuleError("Ese artículo ya está vinculado a este ticket.") from error

    record_ticket_event(
        ticket,
        TicketEvent.ARTICULO_VINCULADO,
        actor=actor,
        new_value=_snapshot(article, kind),
        context={"vinculo_id": link.id},
    )

    return link


def get_link(ticket: Ticket, link_id: int, viewer) -> TicketArticle | None:
    """El vínculo del ticket, si existe y `viewer` puede leer su artículo."""
    return next(
        (link for link in list_links(ticket, viewer) if link.id == link_id), None
    )


def unlink_article(ticket: Ticket, link_id: int, *, actor) -> None:
    """Quita un vínculo (el artículo y el ticket no cambian)."""
    _require(actor)
    lock_ticket(ticket)
    link = get_link(ticket, link_id, actor)

    if link is None:
        raise TicketRuleError("Ese artículo ya no está vinculado.")

    snapshot = _snapshot(link.articulo, link.tipo_vinculacion)
    db.session.delete(link)
    db.session.flush()

    record_ticket_event(
        ticket,
        TicketEvent.ARTICULO_DESVINCULADO,
        actor=actor,
        old_value=snapshot,
        context={"vinculo_id": link_id},
    )
