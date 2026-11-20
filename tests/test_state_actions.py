"""Catálogo de las acciones de estado (`tickets/state_actions.py`).

Es información declarativa que otras partes dan por buena: la pantalla de
administración de estados y transiciones muestra quién ejecuta cada acción y
cuáles son esenciales, y las pantallas de confirmación muestran sus textos.
Estos tests comprueban que lo declarado coincide con lo que el código hace de
verdad, para que no pueda desfasarse sin que alguien lo note.
"""

import re

import pytest

from src.workdesk.extensions import db
from src.workdesk.models import StateAction, Ticket, User
from src.workdesk.models.transicion_estado import STATE_ACTION_LABELS
from src.workdesk.security import RoleCode
from src.workdesk.tickets.state_actions import (
    ACTION_BY_SLUG,
    AUTOMATIC_ACTIONS,
    ESSENTIAL_ACTIONS,
    ESSENTIAL_REASONS,
    RETURN_ACTIONS,
    STATE_ACTIONS,
)
from tests.ticket_helpers import make_ticket, set_state

# Los nombres con los que el seed carga los estados: ningún texto del catálogo
# puede escribirlos a mano, porque el Administrador puede renombrarlos.
DEFAULT_STATE_NAMES = (
    "Nuevo",
    "Asignado",
    "En progreso",
    "En espera",
    "Resuelto",
    "Cerrado",
)


def test_every_action_is_described_exactly_once():
    # Una acción nueva en el vocabulario obliga a decidir si la ejecuta una
    # persona (STATE_ACTIONS) o no (AUTOMATIC_ACTIONS).
    described = set(STATE_ACTIONS) | set(AUTOMATIC_ACTIONS)

    assert described == set(StateAction)
    assert not set(STATE_ACTIONS) & set(AUTOMATIC_ACTIONS)


def test_every_action_has_a_neutral_label():
    assert set(STATE_ACTION_LABELS) == set(StateAction)
    assert all(label.strip() for label in STATE_ACTION_LABELS.values())


def test_the_slugs_are_unique_and_url_friendly():
    assert len(ACTION_BY_SLUG) == len(STATE_ACTIONS)
    assert all(re.fullmatch(r"[a-z]+(-[a-z]+)*", slug) for slug in ACTION_BY_SLUG)


def test_essential_and_return_actions_belong_to_the_vocabulary():
    assert ESSENTIAL_ACTIONS <= set(StateAction)
    assert RETURN_ACTIONS <= set(StateAction)
    assert ESSENTIAL_ACTIONS == set(ESSENTIAL_REASONS)
    assert all(reason.strip() for reason in ESSENTIAL_REASONS.values())


def test_the_texts_do_not_hardcode_the_state_names():
    """Si el Administrador renombra un estado, ningún texto del catálogo debe
    seguir diciendo el nombre antiguo: el estado de destino se escribe con
    `{destination}`."""
    texts = [
        *(info.description for info in STATE_ACTIONS.values()),
        *(info.text_hint for info in STATE_ACTIONS.values()),
        *AUTOMATIC_ACTIONS.values(),
        *ESSENTIAL_REASONS.values(),
    ]

    for text in texts:
        for name in DEFAULT_STATE_NAMES:
            assert name not in text, f"«{name}» está escrito a mano en: {text}"


@pytest.mark.parametrize("info", list(STATE_ACTIONS.values()), ids=lambda i: i.slug)
def test_a_description_is_filled_with_the_destination_name(info):
    described = info.describe("Estado de prueba")

    # No queda ningún marcador sin rellenar y, si lo había, aparece el nombre.
    assert "{" not in described and "}" not in described
    assert ("Estado de prueba" in described) == ("{destination}" in info.description)


def test_the_declared_roles_match_the_authorization_policy(
    app,
    make_user,
    catalog,
):
    """Los roles que declara cada acción son los que su política autoriza.

    Se comprueba con un ticket cerrado del que el Solicitante es solicitante:
    así cada política (de rol, de solicitante y de reapertura) tiene a quién
    autorizar.
    """
    users = {
        role: make_user(role.value, username=role.value.lower())
        for role in RoleCode
    }
    public_id = make_ticket(
        app,
        catalog,
        users[RoleCode.TECNICO]["id"],
        requester_ids=[users[RoleCode.SOLICITANTE]["id"]],
    )
    set_state(app, public_id, "CERRADO")

    with app.app_context():
        ticket = db.session.scalar(
            db.select(Ticket).where(Ticket.public_id == public_id)
        )

        for info in STATE_ACTIONS.values():
            allowed = {
                role
                for role, data in users.items()
                if info.policy(db.session.get(User, data["id"]), ticket)
            }

            assert allowed == set(info.roles), info.slug
