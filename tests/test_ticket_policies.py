from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest
from flask_login import AnonymousUserMixin

from src.workdesk.security import (
    can_choose_requesters,
    can_create_ticket,
    can_view_ticket,
)

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
