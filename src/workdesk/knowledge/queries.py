"""Lectura de la base de conocimiento: quién ve qué y la búsqueda.

**La visibilidad se resuelve en la consulta**, nunca en la plantilla: la lista, la búsqueda y
sus contadores parten de `visible_articles_condition`, que es el equivalente en SQL de
`can_view_article`. Un test comprueba que coinciden.
"""

from sqlalchemy import false, func, true
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models import Article, Categoria
from ..search import text_search_query
from ..security import PUBLIC_ARTICLE, RoleCode, has_any_role

ARTICLES_PER_PAGE = 20
MAX_QUERY_LENGTH = 100

# Cuántos destacados, recientes y relacionados se muestran.
FEATURED_LIMIT = 4
RECENT_LIMIT = 5
RELATED_LIMIT = 3

# Las vistas de la pantalla de gestión (la clave viaja en la URL).
MANAGE_ALL = "todos"
MANAGE_DRAFTS = "borradores"
MANAGE_PUBLISHED = "publicados"
MANAGE_INACTIVE = "desactivados"


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


def _newest(statement, limit: int) -> list[Article]:
    return list(
        db.session.scalars(
            statement.options(joinedload(Article.categoria))
            .order_by(Article.fecha_publicacion.desc(), Article.id.desc())
            .limit(limit)
        )
    )


def featured_articles(user, *, limit: int = FEATURED_LIMIT) -> list[Article]:
    """Los artículos destacados que `user` puede leer, del más reciente al más antiguo."""
    return _newest(
        db.select(Article).where(
            published_articles_condition(user), Article.destacado.is_(True)
        ),
        limit,
    )


def recent_articles(user, *, limit: int = RECENT_LIMIT) -> list[Article]:
    """Los últimos artículos publicados que `user` puede leer."""
    return _newest(db.select(Article).where(published_articles_condition(user)), limit)


def related_articles(user, article: Article, *, limit: int = RELATED_LIMIT) -> list[Article]:
    """Otros artículos legibles de la misma categoría."""
    return _newest(
        db.select(Article).where(
            published_articles_condition(user),
            Article.categoria_id == article.categoria_id,
            Article.id != article.id,
        ),
        limit,
    )


def categories_with_articles(user) -> list[tuple[Categoria, int]]:
    """Las categorías con artículos legibles para `user` y cuántos tiene cada una, en el
    orden del catálogo. Una sola consulta."""
    rows = db.session.execute(
        db.select(Categoria, func.count(Article.id))
        .join(Article, Article.categoria_id == Categoria.id)
        .where(published_articles_condition(user))
        .group_by(Categoria.id)
        .order_by(Categoria.orden.asc().nulls_last(), Categoria.nombre)
    )

    return [(category, count) for category, count in rows]


def manage_articles(user, view: str = MANAGE_ALL, *, page: int = 1):
    """Los artículos que `user` puede gestionar o revisar, paginados y por estado.

    Parte de la visibilidad completa (con borradores y, para el Administrador, los
    desactivados): es la pantalla del personal. Una vista desconocida se trata como
    «todos»; los desactivados solo existen para quien puede verlos.
    """
    statement = (
        db.select(Article)
        .options(joinedload(Article.categoria), joinedload(Article.autor))
        .where(visible_articles_condition(user))
    )

    if view == MANAGE_DRAFTS:
        statement = statement.where(Article.activo.is_(True), Article.publicado.is_(False))
    elif view == MANAGE_PUBLISHED:
        statement = statement.where(Article.activo.is_(True), Article.publicado.is_(True))
    elif view == MANAGE_INACTIVE:
        statement = statement.where(Article.activo.is_(False))

    changed = func.coalesce(Article.fecha_modificacion, Article.fecha_creacion)

    return db.paginate(
        statement.order_by(changed.desc(), Article.id.desc()),
        page=page,
        per_page=ARTICLES_PER_PAGE,
        max_per_page=ARTICLES_PER_PAGE,
        error_out=False,
    )
