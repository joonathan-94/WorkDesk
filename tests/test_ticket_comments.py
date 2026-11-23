"""Comentarios públicos y notas internas de un ticket (docs/06, RN-159).

Cubre el modelo, el servicio (`tickets/comments.py`), lo que genera en el
historial, la visibilidad por rol (la nota interna nunca llega al Solicitante)
y las pantallas.
"""

import re
from datetime import UTC, datetime, timedelta

import pytest
from flask_login import AnonymousUserMixin
from sqlalchemy import event, update
from sqlalchemy.exc import IntegrityError

from src.workdesk import create_app
from src.workdesk.extensions import db
from src.workdesk.models import (
    Comment,
    CommentType,
    HistoryVisibility,
    TicketEvent,
    TicketHistory,
    User,
)
from src.workdesk.models.comment import MAX_COMMENT_LENGTH
from src.workdesk.models.ticket_history import (
    DEFAULT_EVENT_VISIBILITY,
    TICKET_EVENT_LABELS,
)
from src.workdesk.security import can_view_comment
from src.workdesk.tickets.comments import (
    add_comment,
    clean_comment_content,
    delete_comment,
    edit_comment,
    get_comment,
    list_comments,
    visible_comments_condition,
)
from src.workdesk.tickets.history import describe_history_changes
from src.workdesk.tickets.service import TicketRuleError, list_ticket_history
from src.workdesk.tickets.versioning import TicketClosedError
from tests.ticket_helpers import (
    login,
    make_ticket,
    plain_text,
    run_in_threads,
    set_state,
    ticket_by_public_id,
)

PUBLIC = CommentType.PUBLICO
NOTE = CommentType.INTERNO
STAFF = ("tec", "sup", "admin")


# --- Ayudas -----------------------------------------------------------


@pytest.fixture()
def team(make_user, catalog):
    """Dos Solicitantes y una persona de cada rol del personal (dos técnicos)."""
    return {
        "req": make_user("SOLICITANTE", username="req1", nombre="Javiera", apellido="Torres"),
        "other": make_user("SOLICITANTE", username="req2", nombre="Paula", apellido="Contreras"),
        "tec": make_user("TECNICO", username="tec1", nombre="Diego", apellido="Soto"),
        "tec2": make_user("TECNICO", username="tec2", nombre="Valentina", apellido="Pizarro"),
        "sup": make_user("SUPERVISOR", username="sup1", nombre="Camila", apellido="Rojas"),
        "admin": make_user("ADMINISTRADOR", username="admin1", nombre="Ana", apellido="Admin"),
    }


def user(team, key) -> User:
    return db.session.get(User, team[key]["id"])


def new_ticket(app, catalog, team):
    """Ticket que crea el Solicitante `req` (queda como su solicitante)."""
    return make_ticket(
        app,
        catalog,
        team["req"]["id"],
        requester_ids=[team["req"]["id"]],
    )


def add(public_id, team, who="req", text="Hola", kind=PUBLIC) -> Comment:
    comment = add_comment(
        ticket_by_public_id(public_id),
        actor=user(team, who),
        content=text,
        kind=kind,
    )
    db.session.commit()

    return comment


def events(ticket_id, *types):
    statement = (
        db.select(TicketHistory)
        .where(TicketHistory.ticket_id == ticket_id)
        .order_by(TicketHistory.id)
    )

    if types:
        statement = statement.where(
            TicketHistory.tipo_evento.in_([t.value for t in types])
        )

    return list(db.session.scalars(statement))


def make_older(comment_id, minutes):
    """Retrasa la publicación de un comentario (para agotar el plazo de edición)."""
    db.session.execute(
        update(Comment.__table__)
        .where(Comment.__table__.c.id == comment_id)
        .values(fecha_creacion=datetime.now(UTC) - timedelta(minutes=minutes))
    )
    db.session.commit()


def html_of(client, public_id) -> str:
    return client.get(f"/tickets/{public_id}").get_data(as_text=True)


def strip_tags(html: str) -> str:
    """Texto visible de un HTML: sin etiquetas y con los espacios colapsados."""
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


NOTE_PHRASES = ("Nota interna", "NOTA INTERNA", "Solo visible para soporte")


# --- Vocabulario y configuración --------------------------------------


@pytest.mark.parametrize(
    "kind",
    [
        TicketEvent.COMENTARIO_AGREGADO,
        TicketEvent.COMENTARIO_EDITADO,
        TicketEvent.COMENTARIO_ELIMINADO,
    ],
)
def test_comment_events_default_to_internal_and_have_a_name(kind):
    # El valor por defecto es el seguro: la visibilidad real la indica quien
    # registra el evento según el tipo del comentario.
    assert DEFAULT_EVENT_VISIBILITY[kind] is HistoryVisibility.INTERNO
    assert TICKET_EVENT_LABELS[kind]


@pytest.mark.parametrize("value", [0, -5])
def test_the_app_rejects_a_non_positive_edit_window(value):
    config = {
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "COMMENT_EDIT_WINDOW_MINUTES": value,
    }

    with pytest.raises(RuntimeError, match="COMMENT_EDIT_WINDOW_MINUTES"):
        create_app(config)


def test_the_default_edit_window_is_thirty_minutes(app):
    assert app.config["COMMENT_EDIT_WINDOW_MINUTES"] == 30


# --- Base de datos ----------------------------------------------------


@pytest.mark.parametrize(
    "values",
    [
        {"tipo": "SECRETO"},
        {"contenido": "   "},
        # Activo con datos de eliminación.
        {"fecha_eliminacion": datetime(2026, 1, 1, tzinfo=UTC)},
        # Eliminado sin fecha.
        {"activo": False},
        # Editado sin fecha de modificación.
        {"editado": True},
    ],
)
def test_the_database_rejects_inconsistent_comments(app, catalog, team, values):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        base = {
            "ticket_id": ticket_by_public_id(public_id).id,
            "autor_usuario_id": team["req"]["id"],
            "tipo": "PUBLICO",
            "contenido": "Hola",
        }
        db.session.add(Comment(**{**base, **values}))

        with pytest.raises(IntegrityError):
            db.session.flush()

        db.session.rollback()


# --- Servicio: agregar ------------------------------------------------


def test_a_public_comment_is_stored_and_recorded_as_a_public_event(
    app,
    catalog,
    team,
):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        comment = add(public_id, team, "req", "No puedo enviar correos desde ayer.")
        ticket = ticket_by_public_id(public_id)

        assert comment.tipo == "PUBLICO"
        assert comment.contenido == "No puedo enviar correos desde ayer."
        assert comment.autor_usuario_id == team["req"]["id"]
        assert comment.activo is True
        assert comment.editado is False
        assert comment.fecha_modificacion is None

        # Es aditivo: no sube la versión ni cuenta como una modificación.
        assert ticket.version == 1
        assert ticket.fecha_modificacion is None
        assert ticket.usuario_modificacion_id is None

        (entry,) = events(ticket.id, TicketEvent.COMENTARIO_AGREGADO)

        assert entry.visibilidad == "PUBLICO"
        assert entry.actor_usuario_id == team["req"]["id"]
        assert entry.detalle == "Comentario público agregado."
        assert entry.valor_nuevo == {"comentario_id": comment.id, "tipo": "PUBLICO"}
        assert entry.contexto == {"comentario_id": comment.id}


@pytest.mark.parametrize("who", STAFF)
def test_an_internal_note_is_recorded_as_an_internal_event(app, catalog, team, who):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        comment = add(public_id, team, who, "El servidor de correo está saturado.", NOTE)

        (entry,) = events(ticket_by_public_id(public_id).id, TicketEvent.COMENTARIO_AGREGADO)

        assert comment.tipo == "INTERNO"
        assert comment.es_nota_interna is True
        assert entry.visibilidad == "INTERNO"
        assert entry.detalle == "Nota interna agregada."


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  hola  ", "hola"),
        ("uno\r\ndos\rtres", "uno\ndos\ntres"),
        ("<b>hola</b> & más", "<b>hola</b> & más"),
        ("x" * MAX_COMMENT_LENGTH, "x" * MAX_COMMENT_LENGTH),
    ],
)
def test_the_content_is_trimmed_and_line_breaks_unified(raw, expected):
    assert clean_comment_content(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "\r\n\n", None])
def test_an_empty_comment_is_rejected(raw):
    with pytest.raises(TicketRuleError, match="Escribe el comentario"):
        clean_comment_content(raw)


def test_a_comment_over_the_limit_is_rejected():
    with pytest.raises(TicketRuleError, match="5000 caracteres"):
        clean_comment_content("x" * (MAX_COMMENT_LENGTH + 1))


def test_an_unknown_kind_is_rejected(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context(), pytest.raises(TicketRuleError, match="tipo de comentario"):
        add(public_id, team, "tec", "Hola", "SECRETO")

    with app.app_context():
        assert db.session.scalars(db.select(Comment)).all() == []


def test_a_closed_ticket_admits_no_comments(app, catalog, team):
    public_id = new_ticket(app, catalog, team)
    set_state(app, public_id, "CERRADO")

    with app.app_context(), pytest.raises(TicketClosedError, match="reabrir"):
        add(public_id, team, "tec")


def test_an_inactive_actor_cannot_comment(app, catalog, team, make_user):
    inactive = make_user("TECNICO", username="tec_off", activo=False)
    public_id = new_ticket(app, catalog, team)

    with app.app_context(), pytest.raises(TicketRuleError, match="no está activo"):
        add_comment(
            ticket_by_public_id(public_id),
            actor=db.session.get(User, inactive["id"]),
            content="Hola",
            kind=PUBLIC,
        )


def test_adding_a_comment_does_not_commit(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        add_comment(ticket_by_public_id(public_id), actor=user(team, "tec"), content="Hola", kind=PUBLIC)
        db.session.rollback()

        assert db.session.scalars(db.select(Comment)).all() == []
        assert events(ticket_by_public_id(public_id).id, TicketEvent.COMENTARIO_AGREGADO) == []


# --- Servicio: editar -------------------------------------------------


def test_editing_changes_the_content_and_keeps_the_old_one_in_the_history(
    app,
    catalog,
    team,
):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        comment = add(public_id, team, "req", "Texto viejo")
        ticket = ticket_by_public_id(public_id)

        changed = edit_comment(ticket, comment.id, actor=user(team, "sup"), content="Texto nuevo")
        db.session.commit()

        db.session.refresh(comment)

        assert changed is True
        assert comment.contenido == "Texto nuevo"
        assert comment.editado is True
        assert comment.fecha_modificacion is not None
        assert comment.usuario_modificacion_id == team["sup"]["id"]
        # El autor y el tipo no cambian.
        assert comment.autor_usuario_id == team["req"]["id"]
        assert comment.tipo == "PUBLICO"
        assert ticket_by_public_id(public_id).version == 1

        (entry,) = events(ticket.id, TicketEvent.COMENTARIO_EDITADO)

        assert entry.visibilidad == "PUBLICO"
        assert entry.actor_usuario_id == team["sup"]["id"]
        assert entry.detalle == "Comentario público editado."
        assert entry.valor_anterior == {"contenido": "Texto viejo"}
        assert entry.valor_nuevo == {"contenido": "Texto nuevo"}
        assert entry.contexto == {"comentario_id": comment.id, "tipo": "PUBLICO"}


def test_editing_a_note_records_an_internal_event(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        note = add(public_id, team, "tec", "Antes", NOTE)

        edit_comment(ticket_by_public_id(public_id), note.id, actor=user(team, "tec"), content="Después")
        db.session.commit()

        (entry,) = events(ticket_by_public_id(public_id).id, TicketEvent.COMENTARIO_EDITADO)

        assert entry.visibilidad == "INTERNO"
        assert entry.detalle == "Nota interna editada."


def test_editing_without_changes_does_nothing(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        comment = add(public_id, team, "req", "Igual")

        changed = edit_comment(ticket_by_public_id(public_id), comment.id, actor=user(team, "req"), content="  Igual  ")
        db.session.commit()

        db.session.refresh(comment)

        assert changed is False
        assert comment.editado is False
        assert comment.fecha_modificacion is None
        assert events(ticket_by_public_id(public_id).id, TicketEvent.COMENTARIO_EDITADO) == []


def test_editing_rejects_empty_and_too_long_content(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        comment = add(public_id, team, "req", "Original")

        for content, message in (("  ", "Escribe"), ("x" * 5001, "5000 caracteres")):
            with pytest.raises(TicketRuleError, match=message):
                edit_comment(ticket_by_public_id(public_id), comment.id, actor=user(team, "req"), content=content)

            db.session.rollback()

        db.session.refresh(comment)

        assert comment.contenido == "Original"


def test_editing_or_deleting_an_unknown_foreign_or_deleted_comment_is_rejected(
    app,
    catalog,
    team,
):
    first = new_ticket(app, catalog, team)
    second = new_ticket(app, catalog, team)

    with app.app_context():
        mine = add(first, team, "req").id
        foreign = add(second, team, "req").id
        gone = add(first, team, "req", "Se va").id

        delete_comment(ticket_by_public_id(first), gone, actor=user(team, "sup"))
        db.session.commit()

        # Inexistente, de otro ticket y ya eliminado.
        for comment_id in (999_999, foreign, gone):
            with pytest.raises(TicketRuleError, match="ya no existe"):
                edit_comment(ticket_by_public_id(first), comment_id, actor=user(team, "sup"), content="Otro")

            db.session.rollback()

            with pytest.raises(TicketRuleError, match="ya no existe"):
                delete_comment(ticket_by_public_id(first), comment_id, actor=user(team, "sup"))

            db.session.rollback()

        assert db.session.get(Comment, mine).activo is True


def test_a_closed_ticket_cannot_have_its_comments_changed(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        comment_id = add(public_id, team, "req").id

    set_state(app, public_id, "CERRADO")

    with app.app_context():
        with pytest.raises(TicketClosedError, match="reabrir"):
            edit_comment(ticket_by_public_id(public_id), comment_id, actor=user(team, "sup"), content="Otro")

        db.session.rollback()

        with pytest.raises(TicketClosedError, match="reabrir"):
            delete_comment(ticket_by_public_id(public_id), comment_id, actor=user(team, "sup"))


# --- Servicio: eliminar -----------------------------------------------


def test_deleting_is_logical_and_keeps_the_content_in_the_history(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        comment = add(public_id, team, "req", "Me equivoqué de ticket")

        delete_comment(ticket_by_public_id(public_id), comment.id, actor=user(team, "sup"))
        db.session.commit()

        db.session.refresh(comment)

        # La fila se conserva, con quién y cuándo la eliminó.
        assert comment.activo is False
        assert comment.fecha_eliminacion is not None
        assert comment.usuario_eliminacion_id == team["sup"]["id"]
        assert comment.contenido == "Me equivoqué de ticket"
        assert ticket_by_public_id(public_id).version == 1

        (entry,) = events(ticket_by_public_id(public_id).id, TicketEvent.COMENTARIO_ELIMINADO)

        assert entry.visibilidad == "PUBLICO"
        assert entry.detalle == "Comentario público eliminado."
        assert entry.valor_anterior == {
            "contenido": "Me equivoqué de ticket",
            "tipo": "PUBLICO",
        }
        assert entry.contexto == {"comentario_id": comment.id, "tipo": "PUBLICO"}

        # Ya no se lista para nadie.
        for key in ("req", "tec", "sup", "admin"):
            assert list_comments(ticket_by_public_id(public_id), user(team, key)) == []

        with pytest.raises(TicketRuleError, match="ya no existe"):
            delete_comment(ticket_by_public_id(public_id), comment.id, actor=user(team, "sup"))


def test_deleting_a_note_records_an_internal_event(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        note = add(public_id, team, "tec", "Nota", NOTE)

        delete_comment(ticket_by_public_id(public_id), note.id, actor=user(team, "tec"))
        db.session.commit()

        (entry,) = events(ticket_by_public_id(public_id).id, TicketEvent.COMENTARIO_ELIMINADO)

        assert entry.visibilidad == "INTERNO"
        assert entry.detalle == "Nota interna eliminada."


# --- Consultas y visibilidad ------------------------------------------


def test_comments_are_listed_in_order_and_the_requester_never_gets_the_notes(
    app,
    catalog,
    team,
):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        add(public_id, team, "req", "Uno")
        add(public_id, team, "tec", "Nota", NOTE)
        add(public_id, team, "sup", "Tres")

        ticket = ticket_by_public_id(public_id)

        def texts(key):
            return [c.contenido for c in list_comments(ticket, user(team, key))]

        assert texts("tec") == texts("sup") == texts("admin") == ["Uno", "Nota", "Tres"]
        assert texts("req") == ["Uno", "Tres"]


def test_get_comment_hides_notes_from_the_requester_and_other_tickets(
    app,
    catalog,
    team,
):
    public_id = new_ticket(app, catalog, team)
    other_ticket = new_ticket(app, catalog, team)

    with app.app_context():
        public = add(public_id, team, "req").id
        note = add(public_id, team, "tec", "Nota", NOTE).id
        ticket = ticket_by_public_id(public_id)

        assert get_comment(ticket, public, user(team, "req")).id == public
        assert get_comment(ticket, note, user(team, "tec")).id == note
        assert get_comment(ticket, note, user(team, "req")) is None
        assert get_comment(ticket_by_public_id(other_ticket), public, user(team, "tec")) is None
        assert get_comment(ticket, 999_999, user(team, "tec")) is None


def test_the_sql_visibility_matches_the_policy(app, catalog, team, make_user):
    """La consulta (SQL) y la política (Python) deben decidir siempre igual."""
    inactive = make_user("SOLICITANTE", username="req_off")
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        comments = [
            add(public_id, team, "req", "Pública"),
            add(public_id, team, "tec", "Nota", NOTE),
        ]
        db.session.get(User, inactive["id"]).activo = False
        db.session.commit()

        people = [user(team, key) for key in team]
        people += [db.session.get(User, inactive["id"]), AnonymousUserMixin()]

        for person in people:
            visible = {
                c.id
                for c in db.session.scalars(
                    db.select(Comment).where(visible_comments_condition(person))
                )
            }

            for comment in comments:
                assert (comment.id in visible) is can_view_comment(person, comment), (
                    getattr(person, "username", "anónimo"),
                    comment.tipo,
                )

        # Y el resultado concreto, para que la comparación no sea vacía.
        def seen(key):
            return {
                c.contenido
                for c in db.session.scalars(
                    db.select(Comment).where(visible_comments_condition(user(team, key)))
                )
            }

        assert seen("req") == {"Pública"}
        assert seen("tec") == {"Pública", "Nota"}


def test_listing_comments_does_not_query_per_comment(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        for index in range(6):
            add(public_id, team, ("req", "tec", "sup")[index % 3], f"Comentario {index}")

        db.session.expire_all()
        statements = []

        def count(conn, cursor, statement, *args):
            statements.append(statement)

        viewer = user(team, "tec")
        ticket = ticket_by_public_id(public_id)
        # El rol del visor se necesita para el filtro: se carga antes de contar.
        assert viewer.rol.codigo == "TECNICO"
        statements.clear()

        event.listen(db.engine, "before_cursor_execute", count)

        try:
            rows = [
                (c.autor.nombre, c.autor.rol.nombre, c.fecha_creacion)
                for c in list_comments(ticket, viewer)
            ]
        finally:
            event.remove(db.engine, "before_cursor_execute", count)

        assert len(rows) == 6
        # Una sola consulta: el autor y su rol vienen con la lista.
        assert len(statements) == 1


# --- Historial: la nota interna no llega al Solicitante ---------------


def test_the_requester_never_sees_the_note_events_nor_any_content_in_the_history(
    app,
    catalog,
    team,
):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        public = add(public_id, team, "req", "Texto viejo")
        note = add(public_id, team, "tec", "Secreto técnico", NOTE)
        ticket = ticket_by_public_id(public_id)

        edit_comment(ticket, public.id, actor=user(team, "req"), content="Texto nuevo")
        edit_comment(ticket, note.id, actor=user(team, "tec"), content="Otro secreto")
        delete_comment(ticket, note.id, actor=user(team, "tec"))
        db.session.commit()

        requester_view = list_ticket_history(ticket_by_public_id(public_id), user(team, "req"))
        staff_view = list_ticket_history(ticket_by_public_id(public_id), user(team, "tec"))

        def kinds(entries):
            return [e.tipo_evento for e in entries if e.tipo_evento.startswith("COMENTARIO")]

        # El Solicitante solo recibe los eventos del comentario público.
        assert kinds(requester_view) == ["COMENTARIO_AGREGADO", "COMENTARIO_EDITADO"]
        assert len(kinds(staff_view)) == 5


def test_the_history_lines_describe_the_type_and_never_the_text(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        public = add(public_id, team, "req", "Texto privado del solicitante")
        note = add(public_id, team, "tec", "Texto de la nota", NOTE)
        ticket = ticket_by_public_id(public_id)

        edit_comment(ticket, public.id, actor=user(team, "req"), content="Cambiado")
        delete_comment(ticket, note.id, actor=user(team, "tec"))
        db.session.commit()

        lines = [
            (e.tipo_evento, describe_history_changes(e))
            for e in events(
                ticket.id,
                TicketEvent.COMENTARIO_AGREGADO,
                TicketEvent.COMENTARIO_EDITADO,
                TicketEvent.COMENTARIO_ELIMINADO,
            )
        ]

        assert lines == [
            ("COMENTARIO_AGREGADO", ["Comentario público"]),
            ("COMENTARIO_AGREGADO", ["Nota interna"]),
            ("COMENTARIO_EDITADO", ["Comentario público"]),
            ("COMENTARIO_ELIMINADO", ["Nota interna"]),
        ]


# --- Concurrencia -----------------------------------------------------


def test_two_simultaneous_edits_are_applied_one_after_the_other(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        comment_id = add(public_id, team, "req", "Original").id

    def attempt(who, text):
        def task():
            edit_comment(ticket_by_public_id(public_id), comment_id, actor=user(team, who), content=text)

        return task

    outcomes = run_in_threads(
        app,
        [attempt("sup", "Versión A"), attempt("admin", "Versión B")],
    )

    assert outcomes == ["ok", "ok"]

    with app.app_context():
        first, second = events(ticket_by_public_id(public_id).id, TicketEvent.COMENTARIO_EDITADO)

        # El contenido anterior del segundo es el nuevo del primero: no se
        # pisaron a ciegas.
        assert first.valor_anterior == {"contenido": "Original"}
        assert second.valor_anterior == first.valor_nuevo
        assert db.session.get(Comment, comment_id).contenido == second.valor_nuevo["contenido"]


def test_two_simultaneous_deletions_delete_it_once(app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        comment_id = add(public_id, team, "req").id

    def attempt(who):
        def task():
            delete_comment(ticket_by_public_id(public_id), comment_id, actor=user(team, who))

        return task

    outcomes = run_in_threads(app, [attempt("sup"), attempt("admin")])

    assert sorted(outcomes) == ["Ese comentario ya no existe.", "ok"]

    with app.app_context():
        assert len(events(ticket_by_public_id(public_id).id, TicketEvent.COMENTARIO_ELIMINADO)) == 1


# --- Pantallas: publicar ----------------------------------------------


def test_a_requester_publishes_a_comment_on_their_ticket(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)
    login(client, team["req"])

    response = client.post(
        f"/tickets/{public_id}/comments",
        data={"contenido": "Sigue sin funcionar", "tipo": "PUBLICO"},
    )

    assert response.status_code == 302

    with app.app_context():
        (comment,) = db.session.scalars(db.select(Comment)).all()

        assert response.headers["Location"].endswith(f"#comentario-{comment.id}")

    page = plain_text(client.get(f"/tickets/{public_id}"))

    assert "Actividad (1)" in page
    assert "Sigue sin funcionar" in page
    assert "Javiera Torres" in page
    assert "Solicitante" in page
    assert "Comentario agregado" in page


def test_the_confirmation_message_follows_the_type(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)
    login(client, team["tec"])
    url = f"/tickets/{public_id}/comments"

    public = client.post(url, data={"contenido": "Hola", "tipo": "PUBLICO"}, follow_redirects=True)
    note = client.post(url, data={"contenido": "Interno", "tipo": "INTERNO"}, follow_redirects=True)

    assert "Comentario publicado." in plain_text(public)
    assert "Nota interna registrada." in plain_text(note)


def test_the_type_defaults_to_public_when_it_is_not_sent(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)
    login(client, team["tec"])

    client.post(f"/tickets/{public_id}/comments", data={"contenido": "Sin tipo"})

    with app.app_context():
        assert db.session.scalar(db.select(Comment)).tipo == "PUBLICO"


def test_a_requester_cannot_write_an_internal_note_even_by_hand(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)
    login(client, team["req"])

    response = client.post(
        f"/tickets/{public_id}/comments",
        data={"contenido": "Me hago pasar por soporte", "tipo": "INTERNO"},
    )

    assert response.status_code == 403

    with app.app_context():
        assert db.session.scalars(db.select(Comment)).all() == []


def test_someone_without_access_gets_a_404_on_every_comment_route(
    client,
    app,
    catalog,
    team,
):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        comment_id = add(public_id, team, "req").id

    login(client, team["other"])
    base = f"/tickets/{public_id}/comments"

    assert client.post(base, data={"contenido": "Hola"}).status_code == 404

    for suffix in ("edit", "delete"):
        url = f"{base}/{comment_id}/{suffix}"

        assert client.get(url).status_code == 404
        assert client.post(url, data={"contenido": "Hola"}).status_code == 404

    with app.app_context():
        assert db.session.get(Comment, comment_id).contenido == "Hola"


def test_nonexistent_tickets_are_404_on_every_comment_route(client, team):
    login(client, team["sup"])

    for public_id in ("999999", "abc"):
        for method, path in (
            ("post", "/comments"),
            ("get", "/comments/1/edit"),
            ("post", "/comments/1/edit"),
            ("get", "/comments/1/delete"),
            ("post", "/comments/1/delete"),
        ):
            url = f"/tickets/{public_id}{path}"

            assert getattr(client, method)(url).status_code == 404, url


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"contenido": "   "}, "Escribe el comentario."),
        ({"contenido": ""}, "Escribe el comentario."),
        ({"contenido": "x" * 5001}, "Máximo 5000 caracteres."),
        ({"contenido": "Hola", "tipo": "SECRETO"}, "Elige el tipo de comentario."),
    ],
)
def test_the_form_shows_its_errors_and_keeps_what_was_typed(
    client,
    app,
    catalog,
    team,
    data,
    message,
):
    public_id = new_ticket(app, catalog, team)
    login(client, team["tec"])

    response = client.post(f"/tickets/{public_id}/comments", data=data)

    assert response.status_code == 200
    assert message in plain_text(response)

    # Lo escrito no se pierde, y no se guardó nada.
    if data["contenido"].strip():
        assert data["contenido"] in response.get_data(as_text=True)

    with app.app_context():
        assert db.session.scalars(db.select(Comment)).all() == []


def test_the_comment_text_is_shown_escaped(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        add(public_id, team, "req", "<script>alert(1)</script> & <b>negrita</b>")

    login(client, team["tec"])
    html = html_of(client, public_id)

    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>alert(1)" not in html
    assert "<b>negrita</b>" not in html


def test_line_breaks_are_kept(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        add(public_id, team, "req", "Primera línea\r\nSegunda línea")

    login(client, team["req"])

    assert "Primera línea\nSegunda línea" in html_of(client, public_id)


def test_a_closed_ticket_shows_the_comments_but_no_form(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        add(public_id, team, "req", "Comentario antiguo")

    set_state(app, public_id, "CERRADO")

    for key in ("req", "tec"):
        client.post("/logout")
        login(client, team[key])
        html = html_of(client, public_id)

        assert "Comentario antiguo" in html
        assert f"/tickets/{public_id}/comments" not in html
        assert "Un ticket cerrado no admite comentarios nuevos." in " ".join(html.split())

    response = client.post(
        f"/tickets/{public_id}/comments",
        data={"contenido": "Tarde"},
        follow_redirects=True,
    )

    assert "Un ticket cerrado no se puede modificar." in plain_text(response)

    with app.app_context():
        assert len(db.session.scalars(db.select(Comment)).all()) == 1


def test_comments_do_not_change_the_updated_date(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)
    login(client, team["tec"])

    client.post(f"/tickets/{public_id}/comments", data={"contenido": "Uno"})

    with app.app_context():
        ticket = ticket_by_public_id(public_id)

        assert ticket.fecha_modificacion is None
        assert ticket.version == 1


# --- Pantallas: la nota interna y el Solicitante ----------------------


def test_the_requester_never_receives_the_note_in_any_form(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        public = add(public_id, team, "req", "Sigue sin ir").id
        note = add(public_id, team, "tec", "Secreto: es el servidor X", NOTE).id
        edit_comment(ticket_by_public_id(public_id), note, actor=user(team, "tec"), content="Secreto editado Y")
        db.session.commit()

    login(client, team["req"])
    html = html_of(client, public_id)
    visible = strip_tags(html)

    # Ni el texto, ni las marcas de nota interna, ni el historial de la nota,
    # ni siquiera en el conteo (solo cuenta lo que ve).
    assert "Secreto" not in html
    assert "servidor X" not in html
    for phrase in NOTE_PHRASES:
        assert phrase not in html
    assert "Actividad (1)" in visible
    assert "Sigue sin ir" in visible

    # Tampoco puede llegar a sus pantallas: 404, igual que si no existiera.
    assert client.get(f"/tickets/{public_id}/comments/{note}/edit").status_code == 404
    assert client.post(f"/tickets/{public_id}/comments/{note}/edit", data={"contenido": "x"}).status_code == 404
    assert client.get(f"/tickets/{public_id}/comments/{note}/delete").status_code == 404
    assert client.post(f"/tickets/{public_id}/comments/{note}/delete").status_code == 404

    # Y la nota sigue intacta.
    with app.app_context():
        assert db.session.get(Comment, note).contenido == "Secreto editado Y"
        assert db.session.get(Comment, note).activo is True
        assert db.session.get(Comment, public).activo is True


@pytest.mark.parametrize("key", STAFF)
def test_staff_sees_the_note_marked_as_internal(client, app, catalog, team, key):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        add(public_id, team, "req", "Pública")
        add(public_id, team, "tec", "Es un tema del servidor", NOTE)

    login(client, team[key])
    page = plain_text(client.get(f"/tickets/{public_id}"))

    assert "Actividad (2)" in page
    assert "Es un tema del servidor" in page
    assert "NOTA INTERNA" in page
    assert "Solo visible para soporte" in page
    # La nota tiene su estilo propio.
    assert "comment--internal" in html_of(client, public_id)


def test_the_history_of_a_note_is_shown_only_to_staff(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        add(public_id, team, "tec", "Nota", NOTE)
        add(public_id, team, "tec", "Pública")

    login(client, team["req"])
    requester = plain_text(client.get(f"/tickets/{public_id}"))

    # Del historial solo ve el evento del comentario público.
    assert requester.count("Comentario agregado") == 1
    assert "Nota interna" not in requester

    client.post("/logout")
    login(client, team["tec"])
    staff = plain_text(client.get(f"/tickets/{public_id}"))

    assert staff.count("Comentario agregado") == 2


def test_editing_never_leaks_the_old_text_into_the_history(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        comment_id = add(public_id, team, "req", "Dato sensible equivocado").id
        edit_comment(ticket_by_public_id(public_id), comment_id, actor=user(team, "req"), content="Dato corregido")
        db.session.commit()

    for key in ("req", "tec"):
        client.post("/logout")
        login(client, team[key])
        html = html_of(client, public_id)

        assert "Dato corregido" in html
        assert "Dato sensible equivocado" not in html
        assert "Comentario editado" in html


def test_the_composer_depends_on_the_role(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    login(client, team["req"])
    html = html_of(client, public_id)

    assert f"/tickets/{public_id}/comments" in html
    assert 'name="tipo"' not in html

    client.post("/logout")
    login(client, team["tec"])
    html = html_of(client, public_id)

    assert 'name="tipo"' in html
    assert 'value="INTERNO"' in html


# --- Pantallas: editar ------------------------------------------------


def test_an_author_edits_their_comment_from_the_screen(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        comment_id = add(public_id, team, "req", "Texto con error").id

    login(client, team["req"])
    url = f"/tickets/{public_id}/comments/{comment_id}/edit"

    page = client.get(url)

    assert page.status_code == 200
    assert "Texto con error" in page.get_data(as_text=True)
    assert "El texto anterior queda en el historial del ticket." in plain_text(page)

    response = client.post(url, data={"contenido": "Texto corregido"})

    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"#comentario-{comment_id}")

    detail = plain_text(client.get(f"/tickets/{public_id}"))

    assert "Texto corregido" in detail
    assert "(editado)" in detail


def test_the_edit_screen_flashes_the_result(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        comment_id = add(public_id, team, "req", "Igual").id

    login(client, team["req"])
    url = f"/tickets/{public_id}/comments/{comment_id}/edit"

    same = client.post(url, data={"contenido": "Igual"}, follow_redirects=True)
    changed = client.post(url, data={"contenido": "Distinto"}, follow_redirects=True)

    assert "No había cambios que guardar." in plain_text(same)
    assert "Comentario actualizado." in plain_text(changed)


def test_the_edit_screen_never_changes_the_type(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        comment_id = add(public_id, team, "tec", "Pública").id

    login(client, team["tec"])
    client.post(
        f"/tickets/{public_id}/comments/{comment_id}/edit",
        data={"contenido": "Editada", "tipo": "INTERNO"},
    )

    with app.app_context():
        comment = db.session.get(Comment, comment_id)

        assert comment.contenido == "Editada"
        assert comment.tipo == "PUBLICO"


def test_the_edit_screen_rejects_empty_and_too_long_content(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        comment_id = add(public_id, team, "req", "Original").id

    login(client, team["req"])
    url = f"/tickets/{public_id}/comments/{comment_id}/edit"

    empty = client.post(url, data={"contenido": " "})
    long = client.post(url, data={"contenido": "x" * 5001})

    assert empty.status_code == long.status_code == 200
    assert "Escribe el comentario." in plain_text(empty)
    assert "Máximo 5000 caracteres." in plain_text(long)

    with app.app_context():
        assert db.session.get(Comment, comment_id).contenido == "Original"


def test_the_edit_window_closes_for_the_author_but_not_for_a_supervisor(
    client,
    app,
    catalog,
    team,
):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        comment_id = add(public_id, team, "tec", "Respuesta").id
        make_older(comment_id, 31)

    url = f"/tickets/{public_id}/comments/{comment_id}/edit"

    login(client, team["tec"])

    assert client.get(url).status_code == 403
    assert client.post(url, data={"contenido": "Tarde"}).status_code == 403

    client.post("/logout")
    login(client, team["sup"])

    assert client.get(url).status_code == 200
    assert client.post(url, data={"contenido": "Corregida por supervisión"}).status_code == 302

    with app.app_context():
        assert db.session.get(Comment, comment_id).contenido == "Corregida por supervisión"


def test_the_edit_window_follows_the_configuration(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)
    app.config["COMMENT_EDIT_WINDOW_MINUTES"] = 5

    with app.app_context():
        comment_id = add(public_id, team, "tec", "Respuesta").id
        make_older(comment_id, 6)

    login(client, team["tec"])

    assert client.get(f"/tickets/{public_id}/comments/{comment_id}/edit").status_code == 403


@pytest.mark.parametrize(
    ("author", "editor", "status"),
    [
        ("tec", "tec2", 403),  # un Técnico no edita lo de otro
        ("req", "tec", 403),  # ni el comentario de un Solicitante
        ("tec", "req", 403),  # ni un Solicitante el de soporte
        ("req", "sup", 200),
        ("tec", "sup", 200),
        ("req", "admin", 200),
        ("tec", "admin", 200),
    ],
)
def test_who_can_open_the_edit_screen_of_someone_elses_comment(
    client,
    app,
    catalog,
    team,
    author,
    editor,
    status,
):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        comment_id = add(public_id, team, author, "Ajeno").id

    login(client, team[editor])

    assert client.get(f"/tickets/{public_id}/comments/{comment_id}/edit").status_code == status


def test_a_supervisor_can_edit_a_note_written_by_a_technician(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        note_id = add(public_id, team, "tec", "Nota", NOTE).id

    login(client, team["sup"])

    assert client.post(
        f"/tickets/{public_id}/comments/{note_id}/edit",
        data={"contenido": "Nota revisada"},
    ).status_code == 302

    with app.app_context():
        assert db.session.get(Comment, note_id).contenido == "Nota revisada"


def test_the_edit_and_delete_links_follow_the_permissions(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        mine = add(public_id, team, "req", "Mío").id
        theirs = add(public_id, team, "tec", "De soporte").id

    def links(key):
        client.post("/logout")
        login(client, team[key])
        html = html_of(client, public_id)

        return {
            f"/comments/{mine}/edit" in html,
            f"/comments/{theirs}/edit" in html,
        }

    # El autor ve solo los suyos; el Supervisor, los de todos; un Técnico
    # ajeno, ninguno.
    assert links("req") == {True, False}
    assert links("sup") == {True}
    assert links("tec2") == {False}

    with app.app_context():
        make_older(mine, 31)
        make_older(theirs, 31)

    # Vencido el plazo, el autor ya no ve los enlaces; el Supervisor sí.
    assert links("req") == {False}
    assert links("sup") == {True}


def test_a_closed_ticket_shows_no_edit_links_and_the_screens_redirect(
    client,
    app,
    catalog,
    team,
):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        comment_id = add(public_id, team, "req").id

    set_state(app, public_id, "CERRADO")
    login(client, team["sup"])

    assert "/comments/" not in html_of(client, public_id)

    for suffix in ("edit", "delete"):
        response = client.get(
            f"/tickets/{public_id}/comments/{comment_id}/{suffix}",
            follow_redirects=True,
        )

        assert "Un ticket cerrado no se puede modificar." in plain_text(response)

    assert client.post(
        f"/tickets/{public_id}/comments/{comment_id}/edit",
        data={"contenido": "Otro"},
        follow_redirects=True,
    ).status_code == 200

    with app.app_context():
        assert db.session.get(Comment, comment_id).contenido == "Hola"


# --- Pantallas: eliminar ----------------------------------------------


def test_deleting_asks_for_confirmation_and_then_hides_the_comment(
    client,
    app,
    catalog,
    team,
):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        comment_id = add(public_id, team, "req", "Me equivoqué de ticket").id

    login(client, team["req"])
    url = f"/tickets/{public_id}/comments/{comment_id}/delete"

    page = plain_text(client.get(url))

    assert "Eliminar comentario" in page
    assert "Me equivoqué de ticket" in page
    assert "dejará de mostrarse a todas las personas" in page

    # Abrir la confirmación no elimina nada.
    with app.app_context():
        assert db.session.get(Comment, comment_id).activo is True

    response = client.post(url, follow_redirects=True)

    assert "Comentario eliminado." in plain_text(response)

    for key in ("req", "tec"):
        client.post("/logout")
        login(client, team[key])
        html = html_of(client, public_id)

        assert "Me equivoqué de ticket" not in html
        assert "Actividad (0)" in strip_tags(html)

    with app.app_context():
        comment = db.session.get(Comment, comment_id)

        assert comment.activo is False
        assert comment.usuario_eliminacion_id == team["req"]["id"]


def test_deleting_a_note_says_so(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        note_id = add(public_id, team, "tec", "Nota", NOTE).id

    login(client, team["tec"])
    url = f"/tickets/{public_id}/comments/{note_id}/delete"

    assert "Eliminar nota interna" in plain_text(client.get(url))
    assert "Nota interna eliminada." in plain_text(client.post(url, follow_redirects=True))


def test_the_delete_window_follows_the_same_rule_as_editing(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        comment_id = add(public_id, team, "req", "Hola").id
        make_older(comment_id, 31)

    url = f"/tickets/{public_id}/comments/{comment_id}/delete"

    login(client, team["req"])

    assert client.get(url).status_code == 403
    assert client.post(url).status_code == 403

    client.post("/logout")
    login(client, team["admin"])

    assert client.post(url).status_code == 302

    with app.app_context():
        assert db.session.get(Comment, comment_id).activo is False


def test_a_comment_id_from_another_ticket_is_a_404(client, app, catalog, team):
    first = new_ticket(app, catalog, team)
    second = new_ticket(app, catalog, team)

    with app.app_context():
        foreign = add(second, team, "req").id

    login(client, team["sup"])

    for suffix in ("edit", "delete"):
        assert client.get(f"/tickets/{first}/comments/{foreign}/{suffix}").status_code == 404

    assert client.get(f"/tickets/{first}/comments/999999/edit").status_code == 404


def test_deleting_an_already_deleted_comment_is_a_404(client, app, catalog, team):
    public_id = new_ticket(app, catalog, team)

    with app.app_context():
        comment_id = add(public_id, team, "req").id
        delete_comment(ticket_by_public_id(public_id), comment_id, actor=user(team, "sup"))
        db.session.commit()

    login(client, team["sup"])
    url = f"/tickets/{public_id}/comments/{comment_id}"

    assert client.get(f"{url}/edit").status_code == 404
    assert client.get(f"{url}/delete").status_code == 404
    assert client.post(f"{url}/delete").status_code == 404
