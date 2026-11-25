"""Carga de los artículos de demostración (solo desarrollo).

Usa los servicios reales (así valida y audita como la aplicación) y reconoce cada artículo
por su título: volver a ejecutarlo no duplica ni toca lo que ya existe. Las fechas se
escriben aparte, porque los servicios sellan la hora actual y los «artículos recientes»
necesitan antigüedades distintas.
"""

from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import func, update

from ..extensions import db
from ..knowledge.service import create_article, publish_article, set_featured
from ..models import Article, ArticleVisibility, Categoria, User
from ..models.categoria import FALLBACK_CATEGORY_CODE
from .demo_articles_data import DEMO_ARTICLES

# Quién publica (el personal que escribe solo crea borradores).
PUBLISHER = "camila.rojas"


class DemoArticlesError(RuntimeError):
    """Faltan datos para cargar la demostración; el mensaje dice cuáles."""


@dataclass
class DemoArticlesResult:
    created: int = 0
    skipped: int = 0
    warnings: list[str] = field(default_factory=list)


def _users() -> dict[str, User]:
    wanted = {article.author for article in DEMO_ARTICLES} | {PUBLISHER}
    found = {
        user.username: user
        for user in db.session.scalars(db.select(User).where(User.username.in_(wanted)))
        if user.activo
    }

    if missing := sorted(wanted - set(found)):
        raise DemoArticlesError(
            f"Faltan usuarios de demostración activos ({', '.join(missing)}): "
            "ejecuta antes seed-demo."
        )

    return found


def _category_finder(result: DemoArticlesResult):
    fallback = db.session.scalar(
        db.select(Categoria).where(Categoria.codigo == FALLBACK_CATEGORY_CODE)
    )

    if fallback is None:
        raise DemoArticlesError("Faltan las categorías: ejecuta antes seed-catalogs.")

    cache: dict[str, Categoria] = {}

    def find(name: str) -> Categoria:
        if name not in cache:
            category = db.session.scalar(
                db.select(Categoria).where(
                    func.lower(Categoria.nombre) == name.lower(),
                    Categoria.activo.is_(True),
                )
            )

            if category is None:
                result.warnings.append(
                    f"No existe la categoría activa «{name}»: se usa «{fallback.nombre}»."
                )
                category = fallback

            cache[name] = category

        return cache[name]

    return find


def seed_demo_articles() -> DemoArticlesResult:
    """Crea los artículos que falten, en una sola transacción."""
    result = DemoArticlesResult()

    try:
        users = _users()
        category_of = _category_finder(result)
        existing = set(db.session.scalars(db.select(Article.titulo)))

        for item in DEMO_ARTICLES:
            if item.title in existing:
                result.skipped += 1
                continue

            _create(item, users, category_of(item.category))
            result.created += 1

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return result


def _create(item, users: dict[str, User], category: Categoria) -> None:
    article = create_article(
        actor=users[item.author],
        title=item.title,
        content=item.content,
        category_id=category.id,
        visibility=(
            ArticleVisibility.PUBLICO if item.public else ArticleVisibility.PRIVADO
        ),
    )

    if item.published_days_ago is None:
        return

    publisher = users[PUBLISHER]
    publish_article(article, actor=publisher, expected_version=article.version)

    if item.featured:
        set_featured(article, True, actor=publisher, expected_version=article.version)

    published = func.now() - timedelta(days=item.published_days_ago)
    db.session.execute(
        update(Article)
        .where(Article.id == article.id)
        .values(
            fecha_publicacion=published,
            fecha_creacion=published - timedelta(days=1),
        )
        .execution_options(synchronize_session=False)
    )
