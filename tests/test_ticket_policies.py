from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest
from flask_login import AnonymousUserMixin

from src.workdesk.models import CommentType
from src.workdesk.security import (
    can_assign_self,
    can_change_priority,
    can_change_state,
    can_choose_requesters,
    can_comment_publicly,
    can_create_ticket,
    can_delete_comment,
    can_edit_comment,
    can_edit_ticket,
    can_manage_assignments,
    can_manage_requesters,
    can_view_comment,
    can_view_ticket,
    can_write_internal_note,
)
from src.workdesk.security.authorization import INTERNAL_COMMENT_TYPE

ALL_ROLES = ("SOLICITANTE", "TECNICO", "SUPERVISOR", "ADMINISTRADOR")
STAFF_ROLES = ("TECNICO", "SUPERVISOR", "ADMINISTRADOR")


@dataclass
class StubRole:
    codigo: str


@dataclass
class StubUser:
    rol: StubRole
    id: int = 10
    is_authenticated: bool = True
    is_active: bool = True


@dataclass
class StubRequester:
    solicitante_id: int
    fecha_retiro: datetime | None = None


@dataclass
class StubTicket:
    creado_por_usuario_id: int = 1
    solicitantes: list = field(default_factory=list)


def user(role_code: str, **kwargs) -> StubUser:
    return StubUser(rol=StubRole(role_code), **kwargs)


# --- Crear tickets ----------------------------------------------------


@pytest.mark.parametrize("role_code", ALL_ROLES)
def test_every_role_can_create_tickets(role_code):
    assert can_create_ticket(user(role_code)) is True


def test_inactive_and_anonymous_users_cannot_create_tickets():
    assert can_create_ticket(user("TECNICO", is_active=False)) is False
    assert can_create_ticket(AnonymousUserMixin()) is False


# --- Elegir solicitantes ----------------------------------------------


@pytest.mark.parametrize("role_code", STAFF_ROLES)
def test_staff_can_choose_requesters(role_code):
    assert can_choose_requesters(user(role_code)) is True


def test_a_solicitante_cannot_choose_requesters():
    assert can_choose_requesters(user("SOLICITANTE")) is False


def test_inactive_and_anonymous_users_cannot_choose_requesters():
    assert can_choose_requesters(user("TECNICO", is_active=False)) is False
    assert can_choose_requesters(AnonymousUserMixin()) is False


# --- Ver un ticket ----------------------------------------------------


@pytest.mark.parametrize("role_code", STAFF_ROLES)
def test_staff_can_view_any_ticket(role_code):
    stranger = user(role_code, id=99)

    assert can_view_ticket(stranger, StubTicket()) is True


def test_a_solicitante_can_view_the_tickets_they_created():
    ticket = StubTicket(creado_por_usuario_id=10)

    assert can_view_ticket(user("SOLICITANTE", id=10), ticket) is True


def test_a_solicitante_can_view_the_tickets_where_they_are_a_requester():
    ticket = StubTicket(solicitantes=[StubRequester(solicitante_id=10)])

    assert can_view_ticket(user("SOLICITANTE", id=10), ticket) is True


def test_a_removed_requester_loses_access():
    ticket = StubTicket(
        solicitantes=[
            StubRequester(
                solicitante_id=10,
                fecha_retiro=datetime.now(UTC),
            )
        ]
    )

    assert can_view_ticket(user("SOLICITANTE", id=10), ticket) is False


def test_a_solicitante_cannot_view_someone_elses_ticket():
    ticket = StubTicket(
        creado_por_usuario_id=1,
        solicitantes=[StubRequester(solicitante_id=2)],
    )

    assert can_view_ticket(user("SOLICITANTE", id=10), ticket) is False


def test_a_removed_requester_who_created_the_ticket_still_sees_it():
    # El creador original no deja de serlo aunque cambien los solicitantes.
    ticket = StubTicket(
        creado_por_usuario_id=10,
        solicitantes=[
            StubRequester(solicitante_id=10, fecha_retiro=datetime.now(UTC))
        ],
    )

    assert can_view_ticket(user("SOLICITANTE", id=10), ticket) is True


def test_inactive_and_anonymous_users_cannot_view_tickets():
    ticket = StubTicket(creado_por_usuario_id=10)

    assert (
        can_view_ticket(user("SOLICITANTE", id=10, is_active=False), ticket)
        is False
    )
    assert can_view_ticket(user("TECNICO", is_active=False), ticket) is False
    assert can_view_ticket(AnonymousUserMixin(), ticket) is False


# --- Editar, cambiar la prioridad y cambiar el estado -----------------


_EDIT_POLICIES = [can_edit_ticket, can_change_priority, can_change_state]


@pytest.mark.parametrize("policy", _EDIT_POLICIES)
@pytest.mark.parametrize("role_code", STAFF_ROLES)
def test_staff_can_edit_change_the_priority_and_change_the_state(
    policy,
    role_code,
):
    assert policy(user(role_code)) is True


@pytest.mark.parametrize("policy", _EDIT_POLICIES)
def test_a_solicitante_can_only_read(policy):
    # Ni siquiera en un ticket propio: el Solicitante no edita (RN-153).
    assert policy(user("SOLICITANTE")) is False


@pytest.mark.parametrize("policy", _EDIT_POLICIES)
def test_inactive_and_anonymous_users_cannot_edit(policy):
    assert policy(user("TECNICO", is_active=False)) is False
    assert policy(AnonymousUserMixin()) is False


# --- Asignación ---------------------------------------------------------


@pytest.mark.parametrize(
    ("role_code", "self_assign", "manage"),
    [
        ("SOLICITANTE", False, False),
        ("TECNICO", True, False),
        ("SUPERVISOR", False, True),
        ("ADMINISTRADOR", False, True),
    ],
)
def test_assignment_policies_by_role(role_code, self_assign, manage):
    # El Técnico solo se asigna a sí mismo; Supervisor y Administrador
    # asignan a otros pero no se asignan (solo un Técnico puede ser técnico
    # de un ticket).
    assert can_assign_self(user(role_code)) is self_assign
    assert can_manage_assignments(user(role_code)) is manage


@pytest.mark.parametrize("policy", [can_assign_self, can_manage_assignments])
def test_inactive_and_anonymous_users_cannot_assign(policy):
    for role_code in ("TECNICO", "SUPERVISOR", "ADMINISTRADOR"):
        assert policy(user(role_code, is_active=False)) is False

    assert policy(AnonymousUserMixin()) is False


# --- Agregar y retirar solicitantes -----------------------------------


@pytest.mark.parametrize("role_code", STAFF_ROLES)
def test_staff_can_manage_requesters(role_code):
    assert can_manage_requesters(user(role_code)) is True


def test_a_solicitante_cannot_manage_requesters():
    # Ni siquiera en un ticket propio: decidir quiénes más figuran en un
    # ticket es del personal.
    assert can_manage_requesters(user("SOLICITANTE")) is False


def test_inactive_and_anonymous_users_cannot_manage_requesters():
    for role_code in STAFF_ROLES:
        assert can_manage_requesters(user(role_code, is_active=False)) is False

    assert can_manage_requesters(AnonymousUserMixin()) is False


def test_managing_requesters_follows_the_same_rule_as_choosing_them():
    # Elegirlos al crear y gestionarlos después son la misma decisión (RN-10
    # y RN-11): si una cambia, la otra debe cambiar con ella.
    for role_code in ALL_ROLES:
        assert can_manage_requesters(user(role_code)) is can_choose_requesters(
            user(role_code)
        )


# --- Comentarios y notas internas -------------------------------------


@dataclass
class StubComment:
    autor_usuario_id: int = 1
    tipo: str = "PUBLICO"
    fecha_creacion: datetime = field(
        default_factory=lambda: datetime(2026, 11, 18, 12, 0, tzinfo=UTC)
    )


NOW = datetime(2026, 11, 18, 12, 10, tzinfo=UTC)  # 10 minutos después
INTERNAL = StubComment(tipo="INTERNO")


def test_the_internal_type_matches_the_model():
    # La política repite el código para no depender de los modelos.
    assert INTERNAL_COMMENT_TYPE == CommentType.INTERNO.value


@pytest.mark.parametrize("role_code", STAFF_ROLES)
def test_staff_can_write_internal_notes(role_code):
    assert can_write_internal_note(user(role_code)) is True


def test_a_solicitante_never_writes_internal_notes():
    assert can_write_internal_note(user("SOLICITANTE")) is False


def test_inactive_and_anonymous_users_cannot_write_internal_notes():
    assert can_write_internal_note(user("TECNICO", is_active=False)) is False
    assert can_write_internal_note(AnonymousUserMixin()) is False


@pytest.mark.parametrize("role_code", STAFF_ROLES)
def test_staff_comment_publicly_on_any_ticket(role_code):
    assert can_comment_publicly(user(role_code, id=99), StubTicket()) is True


def test_a_solicitante_comments_publicly_only_on_their_tickets():
    mine = StubTicket(creado_por_usuario_id=10)
    shared = StubTicket(solicitantes=[StubRequester(solicitante_id=10)])
    retired = StubTicket(
        solicitantes=[
            StubRequester(solicitante_id=10, fecha_retiro=datetime.now(UTC))
        ]
    )
    someone_elses = StubTicket(creado_por_usuario_id=1)
    requester = user("SOLICITANTE", id=10)

    assert can_comment_publicly(requester, mine) is True
    assert can_comment_publicly(requester, shared) is True
    assert can_comment_publicly(requester, retired) is False
    assert can_comment_publicly(requester, someone_elses) is False


def test_inactive_and_anonymous_users_cannot_comment_publicly():
    ticket = StubTicket(creado_por_usuario_id=10)

    assert (
        can_comment_publicly(user("SOLICITANTE", id=10, is_active=False), ticket)
        is False
    )
    assert can_comment_publicly(AnonymousUserMixin(), ticket) is False


@pytest.mark.parametrize(
    ("role_code", "sees_public", "sees_internal"),
    [
        ("SOLICITANTE", True, False),
        ("TECNICO", True, True),
        ("SUPERVISOR", True, True),
        ("ADMINISTRADOR", True, True),
    ],
)
def test_who_sees_each_comment_type(role_code, sees_public, sees_internal):
    assert can_view_comment(user(role_code), StubComment()) is sees_public
    assert can_view_comment(user(role_code), INTERNAL) is sees_internal


def test_inactive_and_anonymous_users_see_no_comments():
    for person in (user("TECNICO", is_active=False), AnonymousUserMixin()):
        assert can_view_comment(person, StubComment()) is False
        assert can_view_comment(person, INTERNAL) is False


def test_an_author_edits_their_own_comment_inside_the_window():
    comment = StubComment(autor_usuario_id=10)

    # Un comentario público lo edita su autor sea cual sea su rol.
    for role_code in ALL_ROLES:
        author = user(role_code, id=10)

        assert (
            can_edit_comment(author, comment, now=NOW, window_minutes=30) is True
        )


def test_the_window_includes_its_last_second():
    comment = StubComment(autor_usuario_id=10)
    exactly = comment.fecha_creacion + timedelta(minutes=30)
    later = exactly + timedelta(seconds=1)

    for role_code in ("SOLICITANTE", "TECNICO"):
        author = user(role_code, id=10)

        assert can_edit_comment(author, comment, now=exactly, window_minutes=30) is True
        assert can_edit_comment(author, comment, now=later, window_minutes=30) is False


def test_the_window_follows_the_configured_minutes():
    comment = StubComment(autor_usuario_id=10)
    author = user("TECNICO", id=10)

    assert can_edit_comment(author, comment, now=NOW, window_minutes=10) is True
    assert can_edit_comment(author, comment, now=NOW, window_minutes=9) is False


def test_technicians_and_solicitantes_cannot_edit_other_peoples_comments():
    comment = StubComment(autor_usuario_id=1)

    for role_code in ("SOLICITANTE", "TECNICO"):
        assert (
            can_edit_comment(user(role_code, id=10), comment, now=NOW, window_minutes=30)
            is False
        )


@pytest.mark.parametrize("role_code", ["SUPERVISOR", "ADMINISTRADOR"])
def test_supervisors_and_administrators_edit_any_visible_comment_any_time(role_code):
    long_ago = NOW + timedelta(days=400)

    for comment in (StubComment(autor_usuario_id=1), INTERNAL):
        assert (
            can_edit_comment(
                user(role_code, id=10), comment, now=long_ago, window_minutes=30
            )
            is True
        )


def test_a_solicitante_can_neither_edit_nor_delete_an_internal_note():
    note = StubComment(autor_usuario_id=10, tipo="INTERNO")
    person = user("SOLICITANTE", id=10)

    assert can_edit_comment(person, note, now=NOW, window_minutes=30) is False
    assert can_delete_comment(person, note, now=NOW, window_minutes=30) is False


def test_inactive_and_anonymous_users_cannot_edit_comments():
    comment = StubComment(autor_usuario_id=10)

    assert (
        can_edit_comment(
            user("TECNICO", id=10, is_active=False), comment, now=NOW, window_minutes=30
        )
        is False
    )
    assert (
        can_edit_comment(AnonymousUserMixin(), comment, now=NOW, window_minutes=30)
        is False
    )


def test_deleting_follows_the_same_rule_as_editing():
    # Hoy es la misma regla; si cambia una, este test obliga a decidir la otra.
    people = [user(role, id=i) for i, role in enumerate(ALL_ROLES, start=8)]
    comments = [StubComment(autor_usuario_id=10), StubComment(autor_usuario_id=1), INTERNAL]

    for person in people:
        for comment in comments:
            for moment in (NOW, NOW + timedelta(hours=2)):
                assert can_delete_comment(
                    person, comment, now=moment, window_minutes=30
                ) is can_edit_comment(person, comment, now=moment, window_minutes=30)
