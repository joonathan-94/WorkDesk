"""Lectura de la base de conocimiento: quién ve qué y la búsqueda.

**La visibilidad se resuelve en la consulta**, nunca en la plantilla: la lista, la búsqueda y
sus contadores parten de `visible_articles_condition`, que es el equivalente en SQL de
`can_view_article`. Un test comprueba que coinciden.
"""

from sqlalchemy import false, func, true
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models import Article
from ..search import text_search_query
from ..security import PUBLIC_ARTICLE, RoleCode, has_any_role

ARTICLES_PER_PAGE = 20
MAX_QUERY_LENGTH = 100


def visible_articles_condition(user):
    """Condición SQL con los artículos que `user` puede leer (ver `can_view_article`)."""
    if has_any_role(user, RoleCode.ADMINISTRADOR):
        return true()

    if has_any_role(user, RoleCode.SUPERVISOR):
        return Article.activo.is_(True)

    if has_any_role(user, RoleCode.TECNICO):
        return Article.activo.is_(True) & (
            Article.publicado.is_(True) | (Article.autor_usuario_id == user.id)
        )

    if has_any_role(user, RoleCode.SOLICITANTE):
        return (
            Article.activo.is_(True)
            & Article.publicado.is_(True)
            & (Article.visibilidad == PUBLIC_ARTICLE)
        )

    return false()


def published_articles_condition(user):
    """Los artículos que se ofrecen para leer: publicados, activos y visibles para `user`.

    La búsqueda y los destacados parten de esta condición: un borrador o un artículo
    desactivado solo se ve donde se gestiona.
    """
    return (
        visible_articles_condition(user)
        & Article.publicado.is_(True)
        & Article.activo.is_(True)
    )


def get_article(user, article_id: int) -> Article | None:
    """El artículo, si existe y `user` puede leerlo (si no, `None`: la ruta responde 404)."""
    return db.session.scalar(
        db.select(Article)
        .options(joinedload(Article.categoria), joinedload(Article.autor))
        .where(Article.id == article_id, visible_articles_condition(user))
    )


def search_articles(
    user,
    query: str = "",
    *,
    category_id: int | None = None,
    page: int = 1,
    per_page: int = ARTICLES_PER_PAGE,
):
    """Los artículos publicados que `user` puede leer, paginados.

    Con texto, por relevancia (el título pesa más) y solo los que contienen todas las
    palabras; sin texto, del más reciente al más antiguo.
    """
    statement = (
        db.select(Article)
        .options(joinedload(Article.categoria), joinedload(Article.autor))
        .where(published_articles_condition(user))
    )

    if category_id is not None:
        statement = statement.where(Article.categoria_id == category_id)

    query = (query or "").strip()[:MAX_QUERY_LENGTH]
    newest = (Article.fecha_publicacion.desc(), Article.id.desc())

    if query:
        tsquery = text_search_query(query)
        statement = statement.where(Article.vector_busqueda.op("@@")(tsquery)).order_by(
            func.ts_rank(Article.vector_busqueda, tsquery).desc(), *newest
        )
    else:
        statement = statement.order_by(*newest)

    return db.paginate(
        statement, page=page, per_page=per_page, max_per_page=per_page, error_out=False
    )
