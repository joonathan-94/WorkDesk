"""Escritura de la base de conocimiento (docs/04, RF-102 y RF-103; docs/06, RN-173).

Nada hace commit: la operación y su auditoría se confirman o se revierten juntas.

**Concurrencia.** Todo cambio es un `UPDATE ... WHERE id = :id AND version = :esperada` que
sube la versión: si otra persona cambió el artículo mientras se editaba, no se pisa nada.

**Autorización.** Cada operación la comprueba aquí con las políticas de `security` (además de
la ruta): un usuario sin permiso recibe `PermissionError`.
"""

from sqlalchemy import func, update

from ..audit import AuditAction, record_admin_event
from ..extensions import db
from ..models import Article, ArticleVisibility, Categoria
from ..models.article import MAX_ARTICLE_CONTENT_LENGTH, MAX_ARTICLE_TITLE_LENGTH
from ..security import (
    can_create_article,
    can_deactivate_article,
    can_edit_article,
    can_publish_article,
)

ENTITY = "articulo_conocimiento"
MAX_REASON_LENGTH = 500


class ArticleRuleError(ValueError):
    """La operación no es válida; el mensaje se muestra tal cual."""


class ArticleConflictError(ArticleRuleError):
    """Otra persona cambió el artículo mientras se editaba."""

    def __init__(self) -> None:
        super().__init__(
            "Otra persona cambió este artículo mientras lo editabas. Revisa la versión "
            "actual y vuelve a intentarlo."
        )


# --- Validación ----------------------------------------------------------------------------


def _require(allowed: bool) -> None:
    if not allowed:
        raise PermissionError("No tienes permiso para esta acción sobre el artículo.")


def _clean_title_and_content(title: str, content: str) -> tuple[str, str]:
    title = " ".join((title or "").split())
    content = (content or "").replace("\r\n", "\n").replace("\r", "\n").strip()

    if not title:
        raise ArticleRuleError("El título es obligatorio.")

    if len(title) > MAX_ARTICLE_TITLE_LENGTH:
        raise ArticleRuleError(
            f"El título no puede superar los {MAX_ARTICLE_TITLE_LENGTH} caracteres."
        )

    if not content:
        raise ArticleRuleError("El contenido es obligatorio.")

    if len(content) > MAX_ARTICLE_CONTENT_LENGTH:
        raise ArticleRuleError(
            f"El contenido no puede superar los {MAX_ARTICLE_CONTENT_LENGTH} caracteres."
        )

    return title, content


def _clean_visibility(visibility: str) -> str:
    try:
        return ArticleVisibility(visibility).value
    except ValueError as error:
        raise ArticleRuleError("Elige si el artículo es público o privado.") from error


def _active_category(category_id: int, *, current: int | None = None) -> Categoria:
    """La categoría, que debe estar activa (salvo que sea la que el artículo ya tiene)."""
    category = db.session.get(Categoria, category_id) if category_id is not None else None

    if category is None or (not category.activo and category.id != current):
        raise ArticleRuleError("Elige una categoría disponible.")

    return category


def _clean_reason(reason: str | None) -> str | None:
    reason = (reason or "").strip()

    if len(reason) > MAX_REASON_LENGTH:
        raise ArticleRuleError(f"El motivo no puede superar los {MAX_REASON_LENGTH} caracteres.")

    return reason or None


# --- Escritura -----------------------------------------------------------------------------


def _apply(article: Article, actor, expected_version: int, changes: dict) -> None:
    """Aplica `changes` solo si la versión sigue siendo la esperada."""
    result = db.session.execute(
        update(Article)
        .where(Article.id == article.id, Article.version == expected_version)
        .values(
            **changes,
            version=Article.version + 1,
            fecha_modificacion=func.now(),
            usuario_modificacion_id=actor.id,
        )
    )

    if result.rowcount != 1:
        raise ArticleConflictError()

    db.session.refresh(article)


def _audit(action, article: Article, actor, *, old=None, new=None, reason=None) -> None:
    record_admin_event(
        action,
        actor=actor,
        entity_type=ENTITY,
        entity_id=article.id,
        detail=article.titulo,
        old_value=old,
        new_value=new,
        reason=reason,
    )


def create_article(
    *,
    actor,
    title: str,
    content: str,
    category_id: int,
    visibility: str = ArticleVisibility.PRIVADO.value,
) -> Article:
    """Crea un artículo como borrador."""
    _require(can_create_article(actor))
    title, content = _clean_title_and_content(title, content)
    visibility = _clean_visibility(visibility)
    category = _active_category(category_id)

    article = Article(
        titulo=title,
        contenido=content,
        categoria_id=category.id,
        visibilidad=visibility,
        autor_usuario_id=actor.id,
    )
    db.session.add(article)
    db.session.flush()

    _audit(
        AuditAction.ARTICULO_CREADO,
        article,
        actor,
        new={"visibilidad": visibility, "categoria": category.nombre},
    )

    return article


def update_article(
    article: Article,
    *,
    actor,
    expected_version: int,
    title: str,
    content: str,
    category_id: int,
    visibility: str,
) -> bool:
    """Cambia el texto, la categoría o la visibilidad. `False` si nada cambió."""
    _require(can_edit_article(actor, article))
    title, content = _clean_title_and_content(title, content)
    visibility = _clean_visibility(visibility)
    category = _active_category(category_id, current=article.categoria_id)

    old: dict = {}
    new: dict = {}
    changes: dict = {}

    for column, label, before, after, shown in (
        ("titulo", "titulo", article.titulo, title, (article.titulo, title)),
        (
            "categoria_id",
            "categoria",
            article.categoria_id,
            category.id,
            (article.categoria.nombre, category.nombre),
        ),
        (
            "visibilidad",
            "visibilidad",
            article.visibilidad,
            visibility,
            (article.visibilidad, visibility),
        ),
    ):
        if before != after:
            changes[column] = after
            old[label], new[label] = shown

    if content != article.contenido:
        changes["contenido"] = content
        # El texto completo no va a la auditoría: basta con saber que cambió.
        new["contenido"] = "modificado"

    if not changes:
        if article.version != expected_version:
            raise ArticleConflictError()

        return False

    _apply(article, actor, expected_version, changes)
    _audit(AuditAction.ARTICULO_MODIFICADO, article, actor, old=old or None, new=new)

    return True


def publish_article(
    article: Article, *, actor, expected_version: int, reason: str | None = None
) -> bool:
    """Publica un borrador. `False` si ya estaba publicado."""
    _require(can_publish_article(actor))
    reason = _clean_reason(reason)

    if not article.activo:
        raise ArticleRuleError("Reactiva el artículo antes de publicarlo.")

    if article.publicado:
        return False

    _apply(
        article,
        actor,
        expected_version,
        {"publicado": True, "fecha_publicacion": func.now()},
    )
    _audit(AuditAction.ARTICULO_PUBLICADO, article, actor, reason=reason)

    return True


def unpublish_article(
    article: Article, *, actor, expected_version: int, reason: str | None = None
) -> bool:
    """Vuelve un artículo a borrador (deja de estar destacado). `False` si ya lo era."""
    _require(can_publish_article(actor))
    reason = _clean_reason(reason)

    if not article.publicado:
        return False

    _apply(
        article,
        actor,
        expected_version,
        {"publicado": False, "fecha_publicacion": None, "destacado": False},
    )
    _audit(AuditAction.ARTICULO_DESPUBLICADO, article, actor, reason=reason)

    return True


def set_featured(
    article: Article, featured: bool, *, actor, expected_version: int
) -> bool:
    """Destaca o deja de destacar un artículo publicado. `False` si ya estaba así."""
    _require(can_publish_article(actor))

    if article.destacado == featured:
        return False

    if featured and not (article.publicado and article.activo):
        raise ArticleRuleError("Solo se puede destacar un artículo publicado.")

    _apply(article, actor, expected_version, {"destacado": featured})
    _audit(
        AuditAction.ARTICULO_DESTACADO,
        article,
        actor,
        old={"destacado": not featured},
        new={"destacado": featured},
    )

    return True


def deactivate_article(
    article: Article, *, actor, expected_version: int, reason: str | None = None
) -> bool:
    """Retira un artículo sin borrarlo (deja de estar destacado)."""
    _require(can_deactivate_article(actor))
    reason = _clean_reason(reason)

    if not article.activo:
        return False

    _apply(
        article,
        actor,
        expected_version,
        {
            "activo": False,
            "destacado": False,
            "fecha_desactivacion": func.now(),
            "usuario_desactivacion_id": actor.id,
        },
    )
    _audit(AuditAction.ARTICULO_DESACTIVADO, article, actor, reason=reason)

    return True


def activate_article(
    article: Article, *, actor, expected_version: int, reason: str | None = None
) -> bool:
    """Reactiva un artículo desactivado; vuelve con su estado de publicación."""
    _require(can_deactivate_article(actor))
    reason = _clean_reason(reason)

    if article.activo:
        return False

    _apply(
        article,
        actor,
        expected_version,
        {"activo": True, "fecha_desactivacion": None, "usuario_desactivacion_id": None},
    )
    _audit(AuditAction.ARTICULO_ACTIVADO, article, actor, reason=reason)

    return True
