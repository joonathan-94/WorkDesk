"""Las pantallas de la base de conocimiento (docs/11, UI-009 a UI-011).

Lo esencial que fijan:

- **Un artículo que no se puede leer responde 404** (como uno inexistente); uno que se lee
  pero no permite la acción, 403.
- **El Solicitante no ve nada editorial**: ni borradores, ni estados, ni botones.
- **Editar no pierde ni pisa**: un conflicto conserva el texto escrito sin guardar nada.
"""

import re

import pytest
from sqlalchemy import event

from src.workdesk.extensions import db
from src.workdesk.knowledge.service import (
    create_article,
    deactivate_article,
    publish_article,
    set_featured,
)
from src.workdesk.models import Article, ArticleVisibility, Categoria, User
from tests.ticket_helpers import login, plain_text

ROLES = ("SOLICITANTE", "TECNICO", "SUPERVISOR", "ADMINISTRADOR")


@pytest.fixture()
def people(make_user):
    users = {role: make_user(role, username=f"{role.lower()}_ui") for role in ROLES}
    users["TECNICO_B"] = make_user("TECNICO", username="otro_tec_ui")

    return users


@pytest.fixture()
def category(app, seeded_catalogs):
    with app.app_context():
        return db.session.scalar(db.select(Categoria.id).order_by(Categoria.id))


@pytest.fixture()
def make_article(app, people, category):
    def make(
        title="La impresora no imprime",
        content="Revisa el papel y la cola.",
        author="TECNICO",
        publish=True,
        public=True,
        featured=False,
        active=True,
        category_id=None,
    ):
        with app.app_context():
            user = lambda role: db.session.get(User, people[role]["id"])
            article = create_article(
                actor=user(author),
                title=title,
                content=content,
                category_id=category_id or category,
                visibility=(
                    ArticleVisibility.PUBLICO if public else ArticleVisibility.PRIVADO
                ),
            )

            if publish:
                publish_article(
                    article, actor=user("SUPERVISOR"), expected_version=article.version
                )

            if featured:
                set_featured(
                    article, True, actor=user("SUPERVISOR"), expected_version=article.version
                )

            if not active:
                deactivate_article(
                    article,
                    actor=user("ADMINISTRADOR"),
                    expected_version=article.version,
                )

            db.session.commit()

            return article.id

    return make


@pytest.fixture()
def sign_in(client, people):
    def enter(role):
        login(client, people[role])

    return enter


def _get_article(app, article_id) -> Article:
    with app.app_context():
        article = db.session.get(Article, article_id)
        db.session.expunge(article)

        return article


def _article_count(app):
    with app.app_context():
        return db.session.scalar(db.select(db.func.count(Article.id)))


def _main(response) -> str:
    html = response.get_data(as_text=True)

    return html[html.index("<main") : html.index("</main>")]


def _hidden_version(response) -> str:
    return re.search(
        r'name="version" value="(\d+)"', response.get_data(as_text=True)
    ).group(1)


def _editor_data(category, **changes):
    return {
        "titulo": "Un artículo nuevo",
        "contenido": "Primera línea\r\nSegunda línea",
        "categoria": str(category),
        "visibilidad": "PUBLICO",
        **changes,
    }


# --- La portada ----------------------------------------------------------------------------


@pytest.mark.parametrize("role", ROLES)
def test_every_role_opens_the_home_with_the_menu_entry(client, sign_in, category, role):
    sign_in(role)

    response = client.get("/knowledge")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'href="/knowledge"' in html
    assert "Buscar en la base de conocimiento" in html
    assert 'href="/tickets/new"' in _main(response)


def test_anonymous_users_are_sent_to_the_login(client):
    response = client.get("/knowledge")

    assert response.status_code == 302
    assert "/login" in response.location


def test_the_home_shows_featured_recent_and_categories(client, sign_in, make_article):
    make_article("Destacado de impresoras", featured=True)
    make_article("Uno corriente")
    sign_in("SOLICITANTE")

    text = plain_text(client.get("/knowledge"))

    assert "Artículos destacados" in text
    assert "Artículos recientes" in text
    assert "Destacado de impresoras" in text and "Uno corriente" in text
    assert re.search(r"\( ?2 ?\)", text)


def test_an_empty_library_says_so(client, sign_in, category):
    sign_in("SOLICITANTE")

    assert "Todavía no hay artículos publicados" in plain_text(client.get("/knowledge"))


def test_a_requester_sees_nothing_editorial(client, sign_in, make_article):
    make_article("Público publicado")
    make_article("Borrador secreto", publish=False)
    make_article("Privado secreto", public=False)
    make_article("Desactivado secreto", active=False)
    sign_in("SOLICITANTE")

    main = _main(client.get("/knowledge"))

    assert "Público publicado" in main
    assert "secreto" not in main
    assert "Gestionar artículos" not in main
    assert "Nuevo artículo" not in main


def test_searching_shows_results_and_keeps_the_text(client, sign_in, make_article):
    make_article("Configuración del correo", content="Pasos de la cuenta.")
    make_article("La impresora atascada", content="Hojas.")
    sign_in("SOLICITANTE")

    response = client.get("/knowledge?q=configuracion")
    main = _main(response)

    assert "1 resultado" in plain_text(response)
    assert "Configuración del correo" in main
    assert "impresora atascada" not in main
    assert 'value="configuracion"' in main
    assert "Artículos destacados" not in main


def test_a_search_without_results_suggests_what_to_do(client, sign_in, make_article):
    make_article()
    sign_in("SOLICITANTE")

    text = plain_text(client.get("/knowledge?q=submarino"))

    assert "No encontramos artículos" in text


def test_exploring_a_category_filters_and_ignores_unknown_ones(
    app, client, sign_in, make_article
):
    with app.app_context():
        other = Categoria(nombre="Redes de prueba")
        db.session.add(other)
        db.session.commit()
        other_id = other.id

    make_article("En la primera")
    make_article("De redes", category_id=other_id)
    sign_in("SOLICITANTE")

    filtered = _main(client.get(f"/knowledge?categoria={other_id}"))
    ignored = _main(client.get("/knowledge?categoria=999999"))

    assert "De redes" in filtered and "En la primera" not in filtered
    assert "En la primera" in ignored and "Artículos recientes" in ignored


def test_the_search_text_is_escaped(client, sign_in, category):
    sign_in("SOLICITANTE")

    html = client.get("/knowledge?q=<script>alert(1)</script>").get_data(as_text=True)

    assert "<script>alert(1)</script>" not in html


# --- El detalle ------------------------------------------------------------------------------


def test_the_detail_escapes_html_and_keeps_line_breaks(client, sign_in, make_article):
    article_id = make_article(
        title="<b>Título</b>", content="Línea uno\n<script>x()</script>"
    )
    sign_in("SOLICITANTE")

    html = client.get(f"/knowledge/{article_id}").get_data(as_text=True)

    assert "<script>x()</script>" not in html
    assert "&lt;script&gt;x()&lt;/script&gt;" in html
    assert "&lt;b&gt;Título&lt;/b&gt;" in html
    assert 'class="ticket-text">Línea uno\n&lt;script' in html


def test_the_requester_detail_has_no_staff_information(client, sign_in, make_article):
    article_id = make_article(featured=True)
    make_article("Otro de la misma categoría")
    sign_in("SOLICITANTE")

    response = client.get(f"/knowledge/{article_id}")
    main = _main(response)

    assert "Publicado el" in plain_text(response)
    assert "Otro de la misma categoría" in main
    assert "Artículos relacionados" in main

    for editorial in ("Escrito por", "Destacado", "Editar", "Retirar", "Desactivar", "Borrador"):
        assert editorial not in main, editorial


@pytest.mark.parametrize(
    ("kwargs", "allowed"),
    [
        ({"publish": False}, {"TECNICO", "SUPERVISOR", "ADMINISTRADOR"}),
        ({"public": False}, {"TECNICO", "TECNICO_B", "SUPERVISOR", "ADMINISTRADOR"}),
        ({"active": False}, {"ADMINISTRADOR"}),
        ({}, {*ROLES, "TECNICO_B"}),
    ],
)
def test_who_can_open_each_article(client, sign_in, make_article, kwargs, allowed):
    article_id = make_article(**kwargs)

    for role in (*ROLES, "TECNICO_B"):
        client.post("/logout")
        sign_in(role)
        response = client.get(f"/knowledge/{article_id}")

        assert response.status_code == (200 if role in allowed else 404), role


def test_a_missing_article_is_not_found(client, sign_in, category):
    sign_in("ADMINISTRADOR")

    assert client.get("/knowledge/999999").status_code == 404
    assert client.get("/knowledge/999999/edit").status_code == 404
    assert client.get("/knowledge/999999/actions/publish").status_code == 404


@pytest.mark.parametrize(
    ("role", "visible", "hidden"),
    [
        ("TECNICO", [], ["Editar", "Retirar de publicación", "Desactivar"]),
        ("SUPERVISOR", ["Editar", "Retirar de publicación", "Destacar"], ["Desactivar"]),
        ("ADMINISTRADOR", ["Editar", "Desactivar", "Destacar"], []),
    ],
)
def test_the_detail_buttons_follow_the_permissions(
    client, sign_in, make_article, role, visible, hidden
):
    article_id = make_article()
    sign_in(role)

    main = _main(client.get(f"/knowledge/{article_id}"))

    for text in visible:
        assert text in main, text

    for text in hidden:
        assert text not in main, text


# --- Gestión ----------------------------------------------------------------------------------


def test_the_management_list_is_for_the_staff(client, sign_in, make_article):
    make_article()
    sign_in("SOLICITANTE")

    assert client.get("/knowledge/manage").status_code == 403


def test_a_technician_manages_what_they_can_see_filtered_by_state(
    client, sign_in, make_article
):
    make_article("Mi borrador", publish=False)
    make_article("Borrador ajeno", publish=False, author="TECNICO_B")
    make_article("Ya publicado")
    sign_in("TECNICO")

    everything = _main(client.get("/knowledge/manage"))
    drafts = _main(client.get("/knowledge/manage?estado=borradores"))
    published = _main(client.get("/knowledge/manage?estado=publicados"))
    inactive = _main(client.get("/knowledge/manage?estado=desactivados"))

    assert "Mi borrador" in everything and "Ya publicado" in everything
    assert "Borrador ajeno" not in everything
    assert "Mi borrador" in drafts and "Ya publicado" not in drafts
    assert "Ya publicado" in published and "Mi borrador" not in published
    # Los desactivados son cosa del Administrador: para otros la vista no existe.
    assert "Desactivados" not in inactive
    assert "Ya publicado" in inactive


def test_the_administrator_sees_the_inactive_view(client, sign_in, make_article):
    make_article("Retirado", active=False)
    make_article("Vigente")
    sign_in("ADMINISTRADOR")

    main = _main(client.get("/knowledge/manage?estado=desactivados"))

    assert "Retirado" in main and "Vigente" not in main


# --- Escribir -----------------------------------------------------------------------------------


def test_a_technician_saves_a_draft(app, client, sign_in, category):
    sign_in("TECNICO")
    response = client.post("/knowledge/new", data=_editor_data(category))

    assert response.status_code == 302
    page = client.get(response.headers["Location"])
    assert "El borrador se guardó" in plain_text(page)

    with app.app_context():
        article = db.session.scalar(db.select(Article))
        assert article.publicado is False
        assert article.contenido == "Primera línea\nSegunda línea"


def test_the_editor_offers_publishing_only_to_reviewers(client, sign_in, category):
    for role, offered in (("TECNICO", False), ("SUPERVISOR", True)):
        client.post("/logout")
        sign_in(role)
        html = client.get("/knowledge/new").get_data(as_text=True)

        assert ('name="publicar"' in html) is offered, role


def test_a_reviewer_publishes_from_the_editor(app, client, sign_in, category):
    sign_in("SUPERVISOR")

    client.post("/knowledge/new", data=_editor_data(category, publicar="1"))

    with app.app_context():
        assert db.session.scalar(db.select(Article.publicado)) is True


def test_a_technician_cannot_publish_by_adding_the_button_by_hand(
    app, client, sign_in, category
):
    sign_in("TECNICO")

    response = client.post("/knowledge/new", data=_editor_data(category, publicar="1"))

    assert response.status_code == 403
    assert _article_count(app) == 0


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"titulo": " "}, "El título es obligatorio"),
        ({"contenido": ""}, "El contenido es obligatorio"),
        ({"categoria": ""}, "Elige una categoría disponible"),
        ({"categoria": "999999"}, "Elige una categoría disponible"),
        ({"visibilidad": "SECRETA"}, "público o privado"),
        ({"titulo": "x" * 201}, "Máximo 200"),
    ],
)
def test_errors_are_shown_and_what_was_typed_is_kept(
    app, client, sign_in, category, changes, message
):
    sign_in("TECNICO")
    data = _editor_data(category, **changes)

    response = client.post("/knowledge/new", data=data)

    assert response.status_code == 200
    assert message in plain_text(response)
    assert "Segunda línea" in response.get_data(as_text=True) or "contenido" in changes
    assert _article_count(app) == 0


def test_an_edit_opens_with_the_current_values_and_saves(
    app, client, sign_in, make_article, category
):
    article_id = make_article("Antes", publish=False)
    sign_in("TECNICO")
    opened = client.get(f"/knowledge/{article_id}/edit")

    assert 'value="Antes"' in opened.get_data(as_text=True)

    response = client.post(
        f"/knowledge/{article_id}/edit",
        data=_editor_data(category, titulo="Después", version=_hidden_version(opened)),
    )

    assert response.status_code == 302
    assert _get_article(app, article_id).titulo == "Después"


def test_saving_without_changes_says_so(app, client, sign_in, make_article, category):
    article_id = make_article("Igual", content="Mismo", publish=False)
    sign_in("TECNICO")
    opened = client.get(f"/knowledge/{article_id}/edit")

    response = client.post(
        f"/knowledge/{article_id}/edit",
        data=_editor_data(
            category, titulo="Igual", contenido="Mismo", version=_hidden_version(opened)
        ),
    )

    assert "No hay cambios" in plain_text(client.get(response.headers["Location"]))
    assert _get_article(app, article_id).version == 1


def test_a_conflict_keeps_the_typed_text_and_overwrites_nothing(
    app, client, sign_in, make_article, category, people
):
    article_id = make_article("Original", publish=False)
    sign_in("SUPERVISOR")
    opened = client.get(f"/knowledge/{article_id}/edit")

    with app.app_context():
        publish_article(
            db.session.get(Article, article_id),
            actor=db.session.get(User, people["SUPERVISOR"]["id"]),
            expected_version=1,
        )
        db.session.commit()

    response = client.post(
        f"/knowledge/{article_id}/edit",
        data=_editor_data(
            category, titulo="Mi cambio largo", version=_hidden_version(opened)
        ),
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Otra persona cambió este artículo" in plain_text(response)
    assert 'value="Mi cambio largo"' in html
    # La versión sigue siendo la antigua: reenviar no puede pisar el cambio ajeno.
    assert _hidden_version(response) == "1"
    assert _get_article(app, article_id).titulo == "Original"


def test_a_submission_without_version_saves_nothing(
    app, client, sign_in, make_article, category
):
    article_id = make_article("Original", publish=False)
    sign_in("TECNICO")

    client.post(f"/knowledge/{article_id}/edit", data=_editor_data(category, titulo="Otro"))

    assert _get_article(app, article_id).titulo == "Original"


def test_a_technician_cannot_edit_a_published_or_foreign_article(
    client, sign_in, make_article
):
    published = make_article()
    foreign = make_article("Ajeno", publish=False, author="TECNICO_B")
    sign_in("TECNICO")

    assert client.get(f"/knowledge/{published}/edit").status_code == 403
    # Un borrador ajeno ni siquiera se puede leer.
    assert client.get(f"/knowledge/{foreign}/edit").status_code == 404


def test_a_disabled_category_stays_selectable_for_the_article_that_has_it(
    app, client, sign_in, make_article, category
):
    article_id = make_article(publish=False)

    with app.app_context():
        db.session.get(Categoria, category).activo = False
        db.session.commit()

    sign_in("TECNICO")

    assert "(inactiva)" in plain_text(client.get(f"/knowledge/{article_id}/edit"))
    assert "(inactiva)" not in plain_text(client.get("/knowledge/new"))


# --- Acciones editoriales -------------------------------------------------------------------------


def _act(client, article_id, action, *, motivo=""):
    opened = client.get(f"/knowledge/{article_id}/actions/{action}")

    assert opened.status_code == 200, action

    return client.post(
        f"/knowledge/{article_id}/actions/{action}",
        data={"version": _hidden_version(opened), "motivo": motivo},
    )


def test_the_editorial_cycle_through_the_confirmation_screens(
    app, client, sign_in, make_article
):
    article_id = make_article(publish=False)
    sign_in("ADMINISTRADOR")

    for action, check in (
        ("publish", lambda a: a.publicado),
        ("feature", lambda a: a.destacado),
        ("unfeature", lambda a: not a.destacado),
        ("unpublish", lambda a: not a.publicado),
        ("deactivate", lambda a: not a.activo),
        ("activate", lambda a: a.activo),
    ):
        response = _act(client, article_id, action, motivo="Prueba")

        assert response.status_code == 302, action
        assert check(_get_article(app, article_id)), action


def test_opening_a_confirmation_changes_nothing(app, client, sign_in, make_article):
    article_id = make_article(publish=False)
    sign_in("SUPERVISOR")

    client.get(f"/knowledge/{article_id}/actions/publish")

    assert _get_article(app, article_id).publicado is False


def test_an_action_that_no_longer_applies_goes_back_with_a_notice(
    client, sign_in, make_article
):
    article_id = make_article()
    sign_in("SUPERVISOR")

    response = client.get(f"/knowledge/{article_id}/actions/publish")

    assert response.status_code == 302
    assert "ya no corresponde" in plain_text(client.get(response.headers["Location"]))


def test_an_action_over_a_changed_article_is_refused(
    app, client, sign_in, make_article
):
    article_id = make_article(publish=False)
    sign_in("SUPERVISOR")

    response = client.post(
        f"/knowledge/{article_id}/actions/publish", data={"version": "99"}
    )

    assert "Otra persona cambió" in plain_text(client.get(response.headers["Location"]))
    assert _get_article(app, article_id).publicado is False


@pytest.mark.parametrize(
    ("role", "action", "expected"),
    [
        ("SOLICITANTE", "publish", 403),
        ("TECNICO", "publish", 403),
        ("TECNICO", "deactivate", 403),
        ("SUPERVISOR", "deactivate", 403),
        ("SUPERVISOR", "publish", 200),
        ("ADMINISTRADOR", "publish", 200),
    ],
)
def test_who_may_use_each_action(client, sign_in, make_article, role, action, expected):
    article_id = make_article(publish=False)
    sign_in(role)

    url = f"/knowledge/{article_id}/actions/{action}"

    assert client.get(url).status_code == expected
    assert client.post(url, data={"version": "1"}).status_code in (
        {403} if expected == 403 else {302}
    )


def test_an_unknown_action_is_not_found(client, sign_in, make_article):
    article_id = make_article()
    sign_in("ADMINISTRADOR")

    assert client.get(f"/knowledge/{article_id}/actions/borrar").status_code == 404


def test_the_actions_require_the_csrf_token(app, client, sign_in, make_article):
    article_id = make_article(publish=False)
    sign_in("SUPERVISOR")
    app.config["WTF_CSRF_ENABLED"] = True

    response = client.post(
        f"/knowledge/{article_id}/actions/publish", data={"version": "1"}
    )

    assert response.status_code == 400


# --- Coste ------------------------------------------------------------------------------------


def _queries(app, client, url):
    seen = []

    def count(*_args):
        seen.append(1)

    with app.app_context():
        event.listen(db.engine, "before_cursor_execute", count)
        try:
            assert client.get(url).status_code == 200
        finally:
            event.remove(db.engine, "before_cursor_execute", count)

    return len(seen)


@pytest.mark.parametrize(
    "url", ["/knowledge", "/knowledge?q=articulo", "/knowledge/manage"]
)
def test_the_screens_cost_the_same_queries_with_many_articles(
    app, client, sign_in, make_article, url
):
    make_article("Articulo 0", featured=True)
    sign_in("ADMINISTRADOR")
    one = _queries(app, client, url)

    for number in range(1, 14):
        make_article(f"Articulo {number}", featured=number % 2 == 0)

    assert _queries(app, client, url) == one


def test_a_requester_can_only_use_the_reading_routes(app, client, sign_in, make_article):
    # Cualquier ruta nueva de la base de conocimiento queda cubierta: todo lo que no sea
    # leer responde 403 a un Solicitante, en GET y en POST.
    article_id = make_article()
    sign_in("SOLICITANTE")
    reading = {"knowledge.index", "knowledge.detail"}
    checked = 0

    for rule in app.url_map.iter_rules():
        if not rule.endpoint.startswith("knowledge.") or rule.endpoint in reading:
            continue

        url = rule.rule.replace("<int:article_id>", str(article_id)).replace(
            "<action>", "publish"
        )

        for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
            checked += 1
            assert client.open(url, method=method).status_code == 403, (method, url)

    assert checked >= 7


def _section(response, title_id) -> str:
    """El HTML de una sección de la portada o del detalle, por el id de su título."""
    html = response.get_data(as_text=True)
    start = html.index(f'id="{title_id}"')

    return html[start : html.index("</section>", start)]


def test_the_featured_section_holds_only_featured_articles_the_person_can_read(
    client, sign_in, make_article
):
    make_article("Destacado público", featured=True)
    make_article("Destacado interno", featured=True, public=False)
    make_article("Sin destacar")
    sign_in("SOLICITANTE")

    featured = _section(client.get("/knowledge"), "featured-title")

    assert "Destacado público" in featured
    assert "Destacado interno" not in featured
    assert "Sin destacar" not in featured


def test_related_articles_respect_what_the_person_can_read(client, sign_in, make_article):
    article_id = make_article("El que se lee")
    make_article("Vecino público")
    make_article("Vecino interno", public=False)
    make_article("Vecino borrador", publish=False)
    make_article("Vecino retirado", active=False)
    sign_in("SOLICITANTE")

    related = _section(client.get(f"/knowledge/{article_id}"), "related-title")

    assert "Vecino público" in related
    assert "El que se lee" not in related

    for hidden in ("interno", "borrador", "retirado"):
        assert f"Vecino {hidden}" not in related
