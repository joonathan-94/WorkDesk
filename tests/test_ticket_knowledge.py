"""Artículos vinculados a un ticket y artículo desde la resolución (RF-104 y RF-105;
docs/06, RN-174)."""

import pytest

from src.workdesk.extensions import db
from src.workdesk.knowledge.service import (
    create_article,
    deactivate_article,
    publish_article,
)
from src.workdesk.models import (
    Article,
    ArticleLinkType,
    ArticleVisibility,
    Categoria,
    Ticket,
    TicketArticle,
    TicketEvent,
    User,
)
from src.workdesk.tickets.history import describe_history_changes
from src.workdesk.tickets.knowledge_links import (
    link_article,
    list_links,
    unlink_article,
)
from src.workdesk.tickets.service import TicketRuleError, list_ticket_history
from tests.ticket_helpers import (
    login,
    make_ticket,
    plain_text,
    run_in_threads,
    set_state,
    ticket_by_public_id,
)

ROLES = ("SOLICITANTE", "TECNICO", "SUPERVISOR", "ADMINISTRADOR")


@pytest.fixture()
def people(make_user, catalog):
    users = {role: make_user(role, username=f"{role.lower()}_kt") for role in ROLES}
    users["TECNICO_B"] = make_user("TECNICO", username="otro_kt")
    users["AJENO"] = make_user("SOLICITANTE", username="ajeno_kt")

    return users


@pytest.fixture()
def ticket_number(app, catalog, people):
    return make_ticket(
        app,
        catalog,
        people["SOLICITANTE"]["id"],
        requester_ids=[people["SOLICITANTE"]["id"]],
        title="La impresora no imprime",
    )


@pytest.fixture()
def article_of(app, people):
    def make(title="Guía de impresoras", *, publish=True, public=True, author="TECNICO"):
        with app.app_context():
            user = db.session.get(User, people[author]["id"])
            boss = db.session.get(User, people["SUPERVISOR"]["id"])
            category = db.session.scalar(db.select(Categoria.id).order_by(Categoria.id))
            article = create_article(
                actor=user,
                title=title,
                content="Pasos para resolverlo.",
                category_id=category,
                visibility=(
                    ArticleVisibility.PUBLICO if public else ArticleVisibility.PRIVADO
                ),
            )

            if publish:
                publish_article(article, actor=boss, expected_version=1)

            db.session.commit()

            return article.id

    return make


def _actor(people, role):
    return db.session.get(User, people[role]["id"])


def _link(app, people, number, article_id, role="TECNICO", **kwargs):
    with app.app_context():
        link = link_article(
            ticket_by_public_id(number), article_id, actor=_actor(people, role), **kwargs
        )
        db.session.commit()

        return link.id


def _linked_titles(app, people, number, role):
    with app.app_context():
        return [
            link.articulo.titulo
            for link in list_links(ticket_by_public_id(number), _actor(people, role))
        ]


def _events(app, number, viewer_id):
    with app.app_context():
        ticket = ticket_by_public_id(number)

        return [
            (entry.tipo_evento, describe_history_changes(entry))
            for entry in list_ticket_history(ticket, db.session.get(User, viewer_id))
        ]


# --- El servicio ------------------------------------------------------------------------


def test_linking_records_an_internal_event_and_changes_nothing_else(
    app, people, ticket_number, article_of
):
    article_id = article_of()

    with app.app_context():
        before = ticket_by_public_id(ticket_number)
        version, updated = before.version, before.fecha_actualizacion

    _link(app, people, ticket_number, article_id)

    with app.app_context():
        after = ticket_by_public_id(ticket_number)
        assert (after.version, after.fecha_actualizacion) == (version, updated)

    staff = _events(app, ticket_number, people["TECNICO"]["id"])
    requester = _events(app, ticket_number, people["SOLICITANTE"]["id"])

    assert (
        TicketEvent.ARTICULO_VINCULADO.value,
        ["Artículo: «Guía de impresoras»"],
    ) in staff
    assert TicketEvent.ARTICULO_VINCULADO.value not in [name for name, _ in requester]


def test_the_same_article_is_linked_only_once(app, people, ticket_number, article_of):
    article_id = article_of()
    _link(app, people, ticket_number, article_id)

    with pytest.raises(TicketRuleError, match="ya está vinculado"):
        _link(app, people, ticket_number, article_id, role="SUPERVISOR")


def test_two_people_linking_at_once_leave_one_link(app, people, ticket_number, article_of):
    article_id = article_of()

    def link(role):
        def task():
            link_article(
                ticket_by_public_id(ticket_number),
                article_id,
                actor=_actor(people, role),
            )

        return task

    outcomes = run_in_threads(app, [link("TECNICO"), link("SUPERVISOR")])

    assert outcomes.count("ok") == 1

    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(TicketArticle.id))) == 1


def test_a_closed_ticket_can_still_be_linked(app, people, ticket_number, article_of):
    # No cambia el ticket y es cuando una resolución suele convertirse en conocimiento.
    set_state(app, ticket_number, "CERRADO")

    _link(app, people, ticket_number, article_of())

    assert _linked_titles(app, people, ticket_number, "TECNICO") == ["Guía de impresoras"]


@pytest.mark.parametrize("problem", ["inexistente", "borrador ajeno", "desactivado"])
def test_only_an_available_article_can_be_linked(
    app, people, ticket_number, article_of, problem
):
    if problem == "inexistente":
        article_id = 999_999
    elif problem == "borrador ajeno":
        article_id = article_of(publish=False, author="TECNICO_B")
    else:
        article_id = article_of()

        with app.app_context():
            article = db.session.get(Article, article_id)
            deactivate_article(
                article,
                actor=_actor(people, "ADMINISTRADOR"),
                expected_version=article.version,
            )
            db.session.commit()

    role = "ADMINISTRADOR" if problem == "desactivado" else "TECNICO"

    with pytest.raises(TicketRuleError, match="no está disponible"):
        _link(app, people, ticket_number, article_id, role=role)


def test_a_requester_cannot_link_or_unlink(app, people, ticket_number, article_of):
    article_id = article_of()
    link_id = _link(app, people, ticket_number, article_id)

    with app.app_context(), pytest.raises(PermissionError):
        link_article(
            ticket_by_public_id(ticket_number),
            article_id,
            actor=_actor(people, "SOLICITANTE"),
        )

    with app.app_context(), pytest.raises(PermissionError):
        unlink_article(
            ticket_by_public_id(ticket_number),
            link_id,
            actor=_actor(people, "SOLICITANTE"),
        )


def test_each_person_receives_only_the_articles_they_can_read(
    app, people, ticket_number, article_of
):
    for title, kwargs in (
        ("Público", {}),
        ("Interno", {"public": False}),
        ("Borrador propio", {"publish": False}),
    ):
        _link(app, people, ticket_number, article_of(title, **kwargs))

    assert _linked_titles(app, people, ticket_number, "SOLICITANTE") == ["Público"]
    assert _linked_titles(app, people, ticket_number, "TECNICO") == [
        "Público",
        "Interno",
        "Borrador propio",
    ]
    assert _linked_titles(app, people, ticket_number, "TECNICO_B") == ["Público", "Interno"]


def test_unlinking_removes_the_link_and_records_it(app, people, ticket_number, article_of):
    link_id = _link(app, people, ticket_number, article_of())

    with app.app_context():
        unlink_article(
            ticket_by_public_id(ticket_number), link_id, actor=_actor(people, "TECNICO")
        )
        db.session.commit()

    assert _linked_titles(app, people, ticket_number, "TECNICO") == []
    names = [name for name, _ in _events(app, ticket_number, people["TECNICO"]["id"])]
    assert TicketEvent.ARTICULO_DESVINCULADO.value in names

    with app.app_context(), pytest.raises(TicketRuleError, match="ya no está vinculado"):
        unlink_article(
            ticket_by_public_id(ticket_number), link_id, actor=_actor(people, "TECNICO")
        )


# --- Las pantallas --------------------------------------------------------------------------


def _page(number):
    return f"/tickets/{number}/knowledge"


def test_the_detail_shows_the_requester_only_what_they_can_read(
    app, client, people, ticket_number, article_of
):
    login(client, people["SOLICITANTE"])
    assert 'id="knowledge-title"' not in client.get(f"/tickets/{ticket_number}").get_data(
        as_text=True
    )

    _link(app, people, ticket_number, article_of("Ayuda pública"))
    _link(app, people, ticket_number, article_of("Nota para soporte", public=False))
    html = client.get(f"/tickets/{ticket_number}").get_data(as_text=True)

    assert "Ayuda pública" in html
    assert "Nota para soporte" not in html
    assert f'href="{_page(ticket_number)}"' not in html
    assert "Crear artículo desde la resolución" not in html


@pytest.mark.parametrize("role", ["SOLICITANTE", "AJENO"])
def test_the_management_page_is_only_for_the_staff(
    client, people, ticket_number, role
):
    login(client, people[role])
    expected = 403 if role == "SOLICITANTE" else 404

    assert client.get(_page(ticket_number)).status_code == expected
    assert client.post(f"{_page(ticket_number)}/add").status_code == expected
    assert client.get(f"{_page(ticket_number)}/1/remove").status_code == expected


def test_searching_and_linking_from_the_page(
    app, client, people, ticket_number, article_of
):
    article_id = article_of("Cómo destrabar la impresora")
    login(client, people["TECNICO"])

    results = client.get(f"{_page(ticket_number)}?q=impresora")
    assert "Cómo destrabar la impresora" in plain_text(results)

    response = client.post(
        f"{_page(ticket_number)}/add", data={"article_id": str(article_id)}
    )

    assert "Artículo vinculado" in plain_text(client.get(response.headers["Location"]))
    # Lo ya vinculado deja de ofrecerse.
    again = client.get(f"{_page(ticket_number)}?q=impresora")
    assert "No hay artículos para vincular" in plain_text(again)


def test_unlinking_asks_for_confirmation(app, client, people, ticket_number, article_of):
    link_id = _link(app, people, ticket_number, article_of())
    login(client, people["TECNICO"])
    url = f"{_page(ticket_number)}/{link_id}/remove"

    assert client.get(url).status_code == 200
    assert _linked_titles(app, people, ticket_number, "TECNICO") != []

    client.post(url)

    assert _linked_titles(app, people, ticket_number, "TECNICO") == []
    assert client.get(url).status_code == 404


def test_a_link_of_another_ticket_cannot_be_removed(
    app, client, people, catalog, ticket_number, article_of
):
    other = make_ticket(app, catalog, people["TECNICO"]["id"], title="Otro asunto")
    link_id = _link(app, people, other, article_of())
    login(client, people["TECNICO"])

    assert client.post(f"{_page(ticket_number)}/{link_id}/remove").status_code == 404
    assert _linked_titles(app, people, other, "TECNICO") != []


# --- Crear un artículo desde la resolución ---------------------------------------------


def _resolve(app, number, text="Reinicié la cola de impresión.", category=None):
    set_state(app, number, "RESUELTO")

    with app.app_context():
        db.session.execute(
            db.update(Ticket).where(Ticket.public_id == str(number)).values(resolucion=text)
        )
        db.session.commit()


def _editor_data(number, **changes):
    return {
        "ticket": str(number),
        "titulo": "Solución de la impresora",
        "contenido": "Reinicié la cola.",
        "visibilidad": "PRIVADO",
        **changes,
    }


def _category_id(app):
    with app.app_context():
        return db.session.scalar(db.select(Categoria.id).order_by(Categoria.id))


def test_the_editor_proposes_the_resolution_but_not_the_description(
    app, client, people, ticket_number
):
    _resolve(app, ticket_number)

    with app.app_context():
        ticket = ticket_by_public_id(ticket_number)
        ticket_description = ticket.descripcion

    login(client, people["TECNICO"])
    html = client.get(f"/knowledge/new?ticket={ticket_number}").get_data(as_text=True)

    assert 'value="La impresora no imprime"' in html
    assert "Reinicié la cola de impresión." in html
    assert ticket_description not in html
    assert f'name="ticket" value="{ticket_number}"' in html


def test_saving_it_creates_the_article_and_links_it_as_origin(
    app, client, people, ticket_number
):
    _resolve(app, ticket_number)
    login(client, people["TECNICO"])

    response = client.post(
        "/knowledge/new",
        data=_editor_data(ticket_number, categoria=_category_id(app)),
    )

    assert response.status_code == 302

    with app.app_context():
        link = db.session.scalar(db.select(TicketArticle))

        assert link.tipo_vinculacion == ArticleLinkType.ORIGEN_RESOLUCION.value
        assert link.articulo.publicado is False
        assert link.ticket.public_id == str(ticket_number)


def test_a_rejected_article_leaves_neither_article_nor_link(
    app, client, people, ticket_number
):
    _resolve(app, ticket_number)
    login(client, people["TECNICO"])

    response = client.post(
        "/knowledge/new",
        data=_editor_data(ticket_number, categoria=_category_id(app), titulo=""),
    )

    assert response.status_code == 200

    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(Article.id))) == 0
        assert db.session.scalar(db.select(db.func.count(TicketArticle.id))) == 0


@pytest.mark.parametrize("case", ["sin resolución", "inexistente", "texto"])
def test_a_ticket_without_a_resolution_cannot_be_used(
    app, client, people, ticket_number, case
):
    login(client, people["TECNICO"])
    number = {"sin resolución": ticket_number, "inexistente": 999999, "texto": "abc"}[case]

    assert client.get(f"/knowledge/new?ticket={number}").status_code == 404
    assert (
        client.post(
            "/knowledge/new", data=_editor_data(number, categoria=_category_id(app))
        ).status_code
        == 404
    )


def test_a_requester_cannot_use_it(app, client, people, ticket_number):
    _resolve(app, ticket_number)
    login(client, people["SOLICITANTE"])

    assert client.get(f"/knowledge/new?ticket={ticket_number}").status_code == 403


def test_the_detail_offers_it_only_with_a_resolution(app, client, people, ticket_number):
    login(client, people["TECNICO"])
    url = f"/tickets/{ticket_number}"

    assert "Crear artículo desde la resolución" not in plain_text(client.get(url))

    _resolve(app, ticket_number)

    assert "Crear artículo desde la resolución" in plain_text(client.get(url))
