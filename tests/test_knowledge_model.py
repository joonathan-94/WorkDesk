"""La base de conocimiento: modelo, permisos, escritura, búsqueda y datos de demostración
(docs/04, RF-102 y RF-103; docs/06, RN-173; docs/09, 23)."""

import pytest
from flask_login import AnonymousUserMixin
from sqlalchemy.exc import IntegrityError

from src.workdesk.audit import AuditAction
from src.workdesk.extensions import db
from src.workdesk.knowledge.queries import (
    get_article,
    published_articles_condition,
    search_articles,
    visible_articles_condition,
)
from src.workdesk.knowledge.service import (
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
from src.workdesk.models import (
    Article,
    ArticleLinkType,
    ArticleVisibility,
    Categoria,
    TicketArticle,
    User,
)
from src.workdesk.search import without_accents
from src.workdesk.security import (
    PUBLIC_ARTICLE,
    can_create_article,
    can_deactivate_article,
    can_edit_article,
    can_publish_article,
    can_view_article,
)
from src.workdesk.seeds import seed_catalogs, seed_demo_users, seed_roles
from src.workdesk.seeds.demo_articles import (
    DemoArticlesError,
    seed_demo_articles,
)
from src.workdesk.seeds.demo_articles_data import DEMO_ARTICLES
from tests.ticket_helpers import audit_entries, make_ticket, run_in_threads

ROLES = ("SOLICITANTE", "TECNICO", "SUPERVISOR", "ADMINISTRADOR")


@pytest.fixture()
def people(make_user):
    users = {
        role: make_user(role, username=f"{role.lower()}_kb") for role in ROLES
    }
    users["TECNICO_B"] = make_user("TECNICO", username="tecnico_b_kb")

    return users


@pytest.fixture()
def ctx(app, people, seeded_catalogs):
    """Un app context con los usuarios y la categoría de respaldo cargados."""
    with app.app_context():
        yield {
            name: db.session.get(User, data["id"]) for name, data in people.items()
        }


def _category() -> Categoria:
    return db.session.scalar(db.select(Categoria).order_by(Categoria.id))


def _article(ctx, *, author="TECNICO", publish=False, public=True, **overrides) -> Article:
    values = {
        "title": "La impresora no imprime",
        "content": "Revisa el papel y la cola de impresión.",
        "category_id": _category().id,
        "visibility": (
            ArticleVisibility.PUBLICO if public else ArticleVisibility.PRIVADO
        ),
    }
    values.update(overrides)
    article = create_article(actor=ctx[author], **values)

    if publish:
        publish_article(article, actor=ctx["SUPERVISOR"], expected_version=article.version)

    db.session.commit()

    return article


def test_the_public_code_of_the_policy_matches_the_model():
    assert PUBLIC_ARTICLE == ArticleVisibility.PUBLICO.value


# --- Crear -------------------------------------------------------------------------------


def test_a_new_article_is_a_private_draft_by_default(ctx):
    article = create_article(
        actor=ctx["TECNICO"],
        title="  Un   título  ",
        content="  Cuerpo\r\ncon dos líneas  ",
        category_id=_category().id,
    )
    db.session.commit()

    assert article.titulo == "Un título"
    assert article.contenido == "Cuerpo\ncon dos líneas"
    assert article.es_privado
    assert (article.publicado, article.destacado, article.activo) == (False, False, True)
    assert article.version == 1
    assert article.autor_usuario_id == ctx["TECNICO"].id

    entry = audit_entries()[-1]
    assert entry.accion == AuditAction.ARTICULO_CREADO
    assert (entry.entidad_tipo, entry.entidad_id) == ("articulo_conocimiento", article.id)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"title": "   "}, "título es obligatorio"),
        ({"title": "x" * 201}, "200"),
        ({"content": " \n "}, "contenido es obligatorio"),
        ({"content": "x" * 20_001}, "20000"),
        ({"category_id": 999_999}, "categoría disponible"),
        ({"category_id": None}, "categoría disponible"),
        ({"visibility": "SECRETO"}, "público o privado"),
    ],
)
def test_invalid_data_is_rejected(ctx, overrides, message):
    with pytest.raises(ArticleRuleError, match=message):
        _article(ctx, **overrides)

    db.session.rollback()
    assert db.session.scalar(db.select(db.func.count(Article.id))) == 0


def test_a_requester_cannot_write(ctx):
    with pytest.raises(PermissionError):
        _article(ctx, author="SOLICITANTE")


def test_a_disabled_category_cannot_be_chosen_but_can_be_kept(ctx):
    article = _article(ctx)
    category = _category()
    category.activo = False
    db.session.commit()

    with pytest.raises(ArticleRuleError, match="categoría disponible"):
        _article(ctx, title="Otro")

    db.session.rollback()
    changed = update_article(
        article,
        actor=ctx["TECNICO"],
        expected_version=article.version,
        title="Nuevo título",
        content=article.contenido,
        category_id=category.id,
        visibility=article.visibilidad,
    )

    assert changed is True


# --- La base de datos --------------------------------------------------------------------


@pytest.mark.parametrize(
    "changes",
    [
        {"publicado": True},  # sin fecha de publicación
        {"destacado": True},  # sin publicar
        {"activo": False},  # sin fecha de desactivación
        {"visibilidad": "OTRA"},
        {"titulo": "  \n "},
        {"version": 0},
    ],
)
def test_the_database_refuses_incoherent_articles(ctx, changes):
    article = _article(ctx)

    with pytest.raises(IntegrityError):
        db.session.execute(
            db.update(Article).where(Article.id == article.id).values(**changes)
        )

    db.session.rollback()


def test_a_ticket_is_linked_to_an_article_only_once(app, ctx, catalog):
    article = _article(ctx, publish=True)
    number = make_ticket(app, catalog, ctx["SUPERVISOR"].id)
    ticket_id = db.session.scalar(
        db.text("SELECT id FROM tickets WHERE public_id = :n"), {"n": str(number)}
    )

    for _ in range(2):
        db.session.add(
            TicketArticle(
                ticket_id=ticket_id,
                articulo_id=article.id,
                tipo_vinculacion=ArticleLinkType.REFERENCIA.value,
                usuario_creacion_id=ctx["SUPERVISOR"].id,
            )
        )

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


# --- Editar y publicar ---------------------------------------------------------------------


def test_editing_records_what_changed_without_copying_the_content(ctx):
    article = _article(ctx)

    changed = update_article(
        article,
        actor=ctx["TECNICO"],
        expected_version=1,
        title="Título nuevo",
        content="Contenido nuevo y secreto",
        category_id=article.categoria_id,
        visibility="PRIVADO",
    )
    db.session.commit()
    entry = audit_entries()[-1]

    assert changed is True
    assert article.version == 2
    assert article.usuario_modificacion_id == ctx["TECNICO"].id
    assert entry.valor_anterior == {
        "titulo": "La impresora no imprime",
        "visibilidad": "PUBLICO",
    }
    assert entry.valor_nuevo == {
        "titulo": "Título nuevo",
        "visibilidad": "PRIVADO",
        "contenido": "modificado",
    }
    assert "secreto" not in str(entry.valor_nuevo)


def test_saving_the_same_content_changes_nothing(ctx):
    article = _article(ctx)
    entries = len(audit_entries())

    changed = update_article(
        article,
        actor=ctx["TECNICO"],
        expected_version=1,
        title=article.titulo,
        content=article.contenido,
        category_id=article.categoria_id,
        visibility=article.visibilidad,
    )

    assert changed is False
    assert article.version == 1
    assert len(audit_entries()) == entries


def test_an_old_version_is_a_conflict_and_nothing_is_overwritten(ctx):
    article = _article(ctx)
    publish_article(article, actor=ctx["SUPERVISOR"], expected_version=1)
    db.session.commit()

    for content in ("Otro contenido", article.contenido):
        with pytest.raises(ArticleConflictError):
            update_article(
                article,
                actor=ctx["SUPERVISOR"],
                expected_version=1,
                title=article.titulo,
                content=content,
                category_id=article.categoria_id,
                visibility=article.visibilidad,
            )

    db.session.rollback()
    assert article.version == 2


def test_two_people_saving_at_once_do_not_overwrite_each_other(app, ctx):
    article_id = _article(ctx).id
    author_id = ctx["TECNICO"].id
    boss_id = ctx["SUPERVISOR"].id

    def save(user_id, title):
        def task():
            article = db.session.get(Article, article_id)
            update_article(
                article,
                actor=db.session.get(User, user_id),
                expected_version=1,
                title=title,
                content=article.contenido,
                category_id=article.categoria_id,
                visibility=article.visibilidad,
            )

        return task

    outcomes = run_in_threads(
        app,
        [save(author_id, "Del autor"), save(boss_id, "De la jefa")],
        rule_errors=(ArticleRuleError,),
    )

    assert outcomes.count("ok") == 1
    assert any("Otra persona cambió" in outcome for outcome in outcomes)


def test_publishing_featuring_and_unpublishing(ctx):
    article = _article(ctx)
    boss = ctx["SUPERVISOR"]

    with pytest.raises(ArticleRuleError, match="publicado"):
        set_featured(article, True, actor=boss, expected_version=1)

    assert publish_article(article, actor=boss, expected_version=1) is True
    assert article.fecha_publicacion is not None
    assert publish_article(article, actor=boss, expected_version=2) is False
    assert set_featured(article, True, actor=boss, expected_version=2) is True
    assert set_featured(article, True, actor=boss, expected_version=3) is False
    assert unpublish_article(article, actor=boss, expected_version=3) is True

    assert (article.publicado, article.destacado, article.fecha_publicacion) == (
        False,
        False,
        None,
    )
    assert unpublish_article(article, actor=boss, expected_version=4) is False


def test_deactivating_hides_it_and_keeps_the_publication(ctx):
    article = _article(ctx, publish=True)
    admin = ctx["ADMINISTRADOR"]
    set_featured(article, True, actor=admin, expected_version=article.version)

    deactivate_article(article, actor=admin, expected_version=article.version, reason="Viejo")
    db.session.commit()

    assert (article.activo, article.destacado, article.publicado) == (False, False, True)
    assert article.usuario_desactivacion_id == admin.id
    assert audit_entries()[-1].motivo == "Viejo"

    with pytest.raises(ArticleRuleError, match="Reactiva"):
        publish_article(article, actor=admin, expected_version=article.version)

    assert activate_article(article, actor=admin, expected_version=article.version) is True
    assert article.activo and article.fecha_desactivacion is None


@pytest.mark.parametrize("role", ["TECNICO", "SOLICITANTE"])
def test_only_reviewers_publish(ctx, role):
    article = _article(ctx)

    for operation in (publish_article, unpublish_article, deactivate_article):
        with pytest.raises(PermissionError):
            operation(article, actor=ctx[role], expected_version=1)

    with pytest.raises(PermissionError):
        set_featured(article, True, actor=ctx[role], expected_version=1)


def test_a_supervisor_cannot_deactivate(ctx):
    article = _article(ctx)

    with pytest.raises(PermissionError):
        deactivate_article(article, actor=ctx["SUPERVISOR"], expected_version=1)


def test_a_technician_only_edits_their_own_draft(ctx):
    mine = _article(ctx)
    theirs = _article(ctx, author="TECNICO_B", title="De otra persona")
    published = _article(ctx, publish=True, title="Publicado")

    assert can_edit_article(ctx["TECNICO"], mine)
    assert not can_edit_article(ctx["TECNICO"], theirs)
    assert not can_edit_article(ctx["TECNICO"], published)
    assert can_edit_article(ctx["SUPERVISOR"], published)
    assert can_edit_article(ctx["SUPERVISOR"], theirs)


# --- Quién ve qué ---------------------------------------------------------------------------


@pytest.fixture()
def library(ctx):
    """Un artículo de cada tipo: borrador o publicado, público o privado, activo o no, de
    dos autores."""
    made = {}

    for author in ("TECNICO", "TECNICO_B"):
        for publish in (False, True):
            for public in (False, True):
                for active in (False, True):
                    article = _article(
                        ctx,
                        author=author,
                        publish=publish,
                        public=public,
                        title=f"{author} {publish} {public} {active}",
                    )

                    if not active:
                        deactivate_article(
                            article,
                            actor=ctx["ADMINISTRADOR"],
                            expected_version=article.version,
                        )

                    made[(author, publish, public, active)] = article

    db.session.commit()

    return made


@pytest.mark.parametrize("role", [*ROLES, "TECNICO_B", "INACTIVO", "ANONIMO"])
def test_the_query_and_the_policy_agree_for_everyone(ctx, library, role):
    if role == "ANONIMO":
        user = AnonymousUserMixin()
    elif role == "INACTIVO":
        user = ctx["ADMINISTRADOR"]
        user.activo = False
        db.session.commit()
    else:
        user = ctx[role]

    by_query = set(
        db.session.scalars(db.select(Article.id).where(visible_articles_condition(user)))
    )
    by_policy = {a.id for a in library.values() if can_view_article(user, a)}

    assert by_query == by_policy
    offered = set(
        db.session.scalars(db.select(Article.id).where(published_articles_condition(user)))
    )
    assert offered == {a.id for a in library.values() if a.id in by_policy and a.publicado and a.activo}


def test_the_expected_visibility_by_role(ctx, library):
    seen = {
        role: sum(can_view_article(ctx[role], a) for a in library.values())
        for role in ROLES
    }

    # 16 artículos: 2 autores × publicado × público × activo.
    assert seen == {
        # Publicados, públicos y activos (uno por autor).
        "SOLICITANTE": 2,
        # Publicados y activos (4) más sus propios borradores activos (2).
        "TECNICO": 6,
        # Todos los activos.
        "SUPERVISOR": 8,
        # Todos.
        "ADMINISTRADOR": 16,
    }


def test_the_roles_that_can_create_publish_and_deactivate(ctx):
    table = {
        role: (
            can_create_article(ctx[role]),
            can_publish_article(ctx[role]),
            can_deactivate_article(ctx[role]),
        )
        for role in ROLES
    }

    assert table == {
        "SOLICITANTE": (False, False, False),
        "TECNICO": (True, False, False),
        "SUPERVISOR": (True, True, False),
        "ADMINISTRADOR": (True, True, True),
    }


def test_an_article_the_user_cannot_read_is_not_returned(ctx):
    private = _article(ctx, publish=True, public=False)

    assert get_article(ctx["SOLICITANTE"], private.id) is None
    assert get_article(ctx["TECNICO"], private.id).id == private.id
    assert get_article(ctx["ADMINISTRADOR"], 999_999) is None


# --- Búsqueda -------------------------------------------------------------------------------


def _titles(page):
    return [article.titulo for article in page.items]


@pytest.fixture()
def searchable(ctx):
    _article(
        ctx,
        publish=True,
        title="Impresoras: atasco de papel",
        content="Cómo retirar hojas atascadas.",
    )
    _article(
        ctx,
        publish=True,
        title="Configuración del correo",
        content="Pasos para configurar la cuenta en el teléfono.",
    )
    _article(
        ctx,
        publish=True,
        title="Contraseña olvidada",
        content="Pide un restablecimiento. Menciona la impresora solo de pasada.",
    )
    _article(ctx, title="Borrador sobre impresora", content="Pendiente.")
    _article(
        ctx,
        publish=True,
        public=False,
        title="Interno: cola de impresión",
        content="Solo soporte.",
    )


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        # Singular y plural.
        ("impresora", "Impresoras: atasco de papel"),
        ("impresoras", "Impresoras: atasco de papel"),
        # Sin tildes ni eñes.
        ("configuracion", "Configuración del correo"),
        ("configuración", "Configuración del correo"),
        ("contrasena", "Contraseña olvidada"),
        ("CONTRASEÑA", "Contraseña olvidada"),
        # Otra forma de la palabra.
        ("configurar correo", "Configuración del correo"),
        # En el contenido.
        ("atascadas", "Impresoras: atasco de papel"),
    ],
)
def test_the_search_understands_spanish_with_and_without_accents(
    ctx, searchable, query, expected
):
    assert expected in _titles(search_articles(ctx["SOLICITANTE"], query))


def test_a_match_in_the_title_ranks_above_one_in_the_content(ctx, searchable):
    titles = _titles(search_articles(ctx["SOLICITANTE"], "impresora"))

    assert titles == ["Impresoras: atasco de papel", "Contraseña olvidada"]


def test_every_word_must_appear(ctx, searchable):
    assert _titles(search_articles(ctx["SOLICITANTE"], "impresora correo")) == []


def test_the_search_only_returns_what_the_person_can_read(ctx, searchable):
    requester = _titles(search_articles(ctx["SOLICITANTE"], "impresión"))
    staff = _titles(search_articles(ctx["TECNICO"], "impresión"))

    assert "Interno: cola de impresión" not in requester
    assert "Interno: cola de impresión" in staff
    # Un borrador no aparece en la búsqueda, ni siquiera a su autor.
    assert "Borrador sobre impresora" not in _titles(
        search_articles(ctx["TECNICO"], "impresora")
    )


@pytest.mark.parametrize(
    "query",
    ["", "   ", "'", '"', "& | !", "impresora &", "-", "or", "%_\\", "x" * 500, "de la"],
)
def test_any_text_can_be_searched_without_errors(ctx, searchable, query):
    page = search_articles(ctx["SOLICITANTE"], query)

    assert page.total >= 0


def test_without_a_query_the_newest_come_first_and_can_be_filtered(ctx, searchable):
    page = search_articles(ctx["SOLICITANTE"])

    assert _titles(page) == [
        "Contraseña olvidada",
        "Configuración del correo",
        "Impresoras: atasco de papel",
    ]
    assert search_articles(ctx["SOLICITANTE"], category_id=999_999).total == 0
    assert search_articles(ctx["SOLICITANTE"], per_page=1, page=2).items[0].titulo == (
        "Configuración del correo"
    )


def test_removing_accents():
    assert without_accents("Impresión ÑANDÚ") == "impresion nandu"


# --- Datos de demostración --------------------------------------------------------------------


def test_the_demo_articles_cover_every_case_and_are_idempotent(app, seeded_catalogs):
    with app.app_context():
        seed_catalogs()
        seed_roles()
        seed_demo_users("ContraseñaDemo123!")
        first = seed_demo_articles()
        second = seed_demo_articles()
        articles = list(db.session.scalars(db.select(Article)))

        assert first.created == len(DEMO_ARTICLES) == len(articles)
        assert (second.created, second.skipped) == (0, len(DEMO_ARTICLES))
        # Sin las categorías de ejemplo se usa la de respaldo y se avisa.
        assert first.warnings
        assert any(a.publicado for a in articles)
        assert any(not a.publicado for a in articles)
        assert any(a.es_privado for a in articles)
        assert any(a.destacado for a in articles)
        dates = [a.fecha_publicacion for a in articles if a.publicado]
        assert len(set(dates)) == len(dates)


def test_the_demo_articles_need_the_demo_users(app, seeded_catalogs):
    with app.app_context(), pytest.raises(DemoArticlesError, match="seed-demo"):
        seed_demo_articles()


def test_the_command_refuses_production(app):
    app.config["APP_ENV"] = "production"

    result = app.test_cli_runner().invoke(args=["seed-demo-articles"])

    assert result.exit_code != 0
    assert "producción" in result.output


@pytest.mark.parametrize("role", ["TECNICO_B", "SOLICITANTE"])
def test_editing_someone_elses_draft_is_refused_by_the_service(ctx, role):
    # La política sola no basta: el servicio debe aplicarla, aunque la ruta ya lo haga.
    article = _article(ctx)

    with pytest.raises(PermissionError):
        update_article(
            article,
            actor=ctx[role],
            expected_version=1,
            title="Tomado",
            content=article.contenido,
            category_id=article.categoria_id,
            visibility=article.visibilidad,
        )

    db.session.rollback()
    assert article.titulo == "La impresora no imprime"


def test_a_technician_cannot_edit_their_article_once_it_is_published(ctx):
    article = _article(ctx, publish=True)

    with pytest.raises(PermissionError):
        update_article(
            article,
            actor=ctx["TECNICO"],
            expected_version=article.version,
            title="Cambio tardío",
            content=article.contenido,
            category_id=article.categoria_id,
            visibility=article.visibilidad,
        )


def test_the_demo_articles_are_linked_to_the_demo_tickets_once(seeded, app):
    with app.app_context():
        first = seed_demo_articles()
        second = seed_demo_articles()
        links = db.session.scalar(db.select(db.func.count(TicketArticle.id)))
        expected = sum(1 for item in DEMO_ARTICLES if item.ticket_key)

        assert first.linked == expected == links == 5
        assert second.linked == 0
