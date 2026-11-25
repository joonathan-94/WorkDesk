"""Configuración de notificaciones (RF-087 y RF-121; docs/06, RN-97 y RN-172; UI-024).

Lo que estas pruebas fijan:

- El Administrador solo puede **apagar** avisos del catálogo: nunca hacer llegar algo interno
  a un Solicitante, ni apagar lo que una regla de negocio exige (RN-95 y RN-96).
- **Apagar un aviso lo apaga en todas las operaciones que lo envían**, y solo ese.
- **Ningún envío esquiva el catálogo** (ni uno nuevo puede quedar fuera de él).
"""

import logging
import re
from pathlib import Path

import pytest

from src.workdesk.audit import AuditAction
from src.workdesk.configuration import SettingConflictError, forget_cached_settings
from src.workdesk.extensions import db
from src.workdesk.models import (
    Configuracion,
    Notificacion,
    NotificationEvent,
    User,
)
from src.workdesk.notifications import events as dispatch
from src.workdesk.notifications.preferences import (
    RULES,
    TABLE_KEY,
    Audience,
    disabled_keys,
    is_enabled,
    preferences_token,
    save_disabled_keys,
)
from src.workdesk.tickets.assignment import assign_technician
from src.workdesk.tickets.comments import add_comment
from tests.sla_helpers import work_on
from tests.ticket_helpers import (
    audit_entries,
    login,
    make_ticket,
    person,
    plain_text,
    ticket_by_public_id,
)

SCREEN = "/admin/notifications"
ROOT = Path(__file__).resolve().parents[1]
E = NotificationEvent

# Lo que nunca puede ir a un Solicitante (docs/06, RN-168): notas, SLA, reasignaciones.
INTERNAL_EVENTS = {
    E.NOTA_INTERNA,
    E.TICKET_REASIGNADO,
    E.SLA_PROXIMO_A_VENCER,
    E.SLA_VENCIDO,
    E.SLA_PRIORIDAD_BAJADA,
}


def _admin(user_data):
    return db.session.get(User, user_data["id"])


def _turn_off(app, admin_user, *keys):
    with app.app_context():
        save_disabled_keys(keys, actor=_admin(admin_user))
        db.session.commit()


# --- El catálogo -----------------------------------------------------------------------


def test_no_rule_sends_something_internal_to_a_requester():
    leaks = [
        rule.key
        for rule in RULES
        if rule.audience is Audience.SOLICITANTES and rule.event in INTERNAL_EVENTS
    ]

    assert leaks == []


def test_every_key_is_unique_and_the_mandatory_ones_are_locked():
    keys = [rule.key for rule in RULES]
    locked = {rule.key for rule in RULES if rule.locked}

    assert len(keys) == len(set(keys))
    assert locked == {"VALIDACION_PENDIENTE:SOLICITANTES", "TICKET_REABIERTO:TECNICOS"}


def test_asking_about_a_notice_that_is_not_in_the_catalogue_is_a_programming_error(app):
    with app.app_context(), pytest.raises(ValueError, match="catálogo"):
        is_enabled(E.NOTA_INTERNA, Audience.SOLICITANTES)


def test_only_the_dispatch_function_sends_notices():
    # Si alguien llamara a `notify_many` fuera de `_send`, el Administrador no podría apagar
    # ese aviso y el catálogo mentiría.
    source = Path(dispatch.__file__).read_text(encoding="utf-8")
    calls = re.findall(r"\bnotify(?:_many)?\(", source)

    assert calls == ["notify_many("]


# --- Guardar -----------------------------------------------------------------------------


@pytest.fixture()
def admin(app, admin_user):
    with app.app_context():
        yield _admin(admin_user)


def test_without_anything_saved_everything_is_sent(admin):
    assert disabled_keys() == frozenset()
    assert all(is_enabled(rule.event, rule.audience) for rule in RULES)


def test_turning_notices_off_is_stored_and_audited(admin):
    changed = save_disabled_keys(
        ["NOTA_INTERNA:TECNICOS", "SLA_VENCIDO:SUPERVISORES"], actor=admin, reason="Ruido"
    )
    db.session.commit()
    row = db.session.scalar(db.select(Configuracion).where(Configuracion.clave == TABLE_KEY))
    entry = audit_entries()[-1]

    assert changed is True
    assert (row.tipo_dato, row.categoria) == ("JSON", "notificaciones")
    assert disabled_keys() == {"NOTA_INTERNA:TECNICOS", "SLA_VENCIDO:SUPERVISORES"}
    assert entry.accion == AuditAction.CONFIGURACION_MODIFICADA
    assert entry.detalle == TABLE_KEY
    assert entry.valor_anterior == {"valor": []}
    assert entry.motivo == "Ruido"


def test_turning_everything_back_on_removes_the_row(admin):
    save_disabled_keys(["NOTA_INTERNA:TECNICOS"], actor=admin)
    db.session.commit()

    assert save_disabled_keys([], actor=admin) is True
    db.session.commit()

    assert db.session.scalar(db.select(db.func.count(Configuracion.id))) == 0
    assert audit_entries()[-1].accion == AuditAction.CONFIGURACION_RESTABLECIDA


def test_saving_the_same_again_changes_nothing(admin):
    save_disabled_keys(["NOTA_INTERNA:TECNICOS"], actor=admin)
    db.session.commit()
    entries = len(audit_entries())

    assert save_disabled_keys(["NOTA_INTERNA:TECNICOS"], actor=admin) is False
    assert len(audit_entries()) == entries


def test_locked_and_unknown_notices_are_ignored(admin):
    changed = save_disabled_keys(
        [
            "VALIDACION_PENDIENTE:SOLICITANTES",
            "TICKET_REABIERTO:TECNICOS",
            "NOTA_INTERNA:SOLICITANTES",
            "INVENTADO:NADIE",
        ],
        actor=admin,
    )

    assert changed is False
    assert is_enabled(E.VALIDACION_PENDIENTE, Audience.SOLICITANTES)


@pytest.mark.parametrize("bad", ["no es json", '{"a": 1}', "[1, 2]", '"texto"'])
def test_a_corrupt_stored_value_sends_everything_with_a_warning(admin, caplog, bad):
    db.session.add(Configuracion(clave=TABLE_KEY, valor=bad, tipo_dato="JSON"))
    db.session.commit()
    forget_cached_settings()

    with caplog.at_level(logging.WARNING):
        assert disabled_keys() == frozenset()

    assert TABLE_KEY in caplog.text


def test_a_stored_locked_notice_cannot_silence_it(admin):
    # Aunque alguien lo escriba a mano en la tabla, lo obligatorio se sigue enviando.
    db.session.add(
        Configuracion(
            clave=TABLE_KEY,
            valor='["TICKET_REABIERTO:TECNICOS", "NOTA_INTERNA:TECNICOS"]',
            tipo_dato="JSON",
        )
    )
    db.session.commit()
    forget_cached_settings()

    assert disabled_keys() == {"NOTA_INTERNA:TECNICOS"}


@pytest.mark.parametrize("role", ["SOLICITANTE", "TECNICO", "SUPERVISOR"])
def test_only_the_administrator_can_save(app, make_user, role):
    other = make_user(role)

    with app.app_context(), pytest.raises(PermissionError):
        save_disabled_keys(["NOTA_INTERNA:TECNICOS"], actor=_admin(other))


def test_a_stale_token_is_a_conflict(admin):
    seen = preferences_token()
    save_disabled_keys(["NOTA_INTERNA:TECNICOS"], actor=admin)
    db.session.commit()

    with pytest.raises(SettingConflictError):
        save_disabled_keys([], actor=admin, base_token=seen)


# --- En las operaciones reales -----------------------------------------------------------


@pytest.fixture()
def chief(make_user):
    return make_user("ADMINISTRADOR", username="jefa_aviso")


@pytest.fixture()
def scene(app, catalog, make_user):
    """Un ticket de un solicitante con dos técnicos asignados."""
    people = {
        "req": make_user("SOLICITANTE", username="req_aviso"),
        "tec": make_user("TECNICO", username="tec_aviso"),
        "tec2": make_user("TECNICO", username="tec2_aviso"),
        "sup": make_user("SUPERVISOR", username="sup_aviso"),
    }
    number = make_ticket(app, catalog, people["req"]["id"], requester_ids=[people["req"]["id"]])

    return {"number": number, "people": people}


def _notices(app, user_data):
    with app.app_context():
        return [
            notice.tipo_evento
            for notice in db.session.scalars(
                db.select(Notificacion)
                .where(Notificacion.usuario_id == user_data["id"])
                .order_by(Notificacion.id)
            )
        ]


def _clear_notices(app):
    with app.app_context():
        db.session.execute(db.delete(Notificacion))
        db.session.commit()


def _assign_both(app, scene):
    with app.app_context():
        ticket = ticket_by_public_id(scene["number"])

        for name in ("tec", "tec2"):
            assign_technician(ticket, scene["people"][name]["id"], actor=person(scene["people"]["sup"]["id"]))

        db.session.commit()

    _clear_notices(app)


def test_the_assignment_notice_of_one_audience_can_be_silenced_alone(app, scene, chief):
    _turn_off(app, chief, "TICKET_ASIGNADO:SOLICITANTES")

    with app.app_context():
        assign_technician(
            ticket_by_public_id(scene["number"]),
            scene["people"]["tec"]["id"],
            actor=person(scene["people"]["sup"]["id"]),
        )
        db.session.commit()

    assert _notices(app, scene["people"]["req"]) == []
    assert _notices(app, scene["people"]["tec"]) == [E.TICKET_ASIGNADO.value]


def test_a_state_change_respects_each_audience(app, scene, chief):
    _assign_both(app, scene)
    _turn_off(app, chief, "ESTADO_CAMBIADO:TECNICOS")

    with app.app_context():
        work_on(ticket_by_public_id(scene["number"]), scene["people"]["tec"]["id"])
        db.session.commit()

    assert _notices(app, scene["people"]["req"]) == [E.ESTADO_CAMBIADO.value]
    assert _notices(app, scene["people"]["tec2"]) == []


def test_silencing_internal_notes_does_not_silence_public_comments(app, scene, chief):
    _assign_both(app, scene)
    _turn_off(app, chief, "NOTA_INTERNA:TECNICOS")

    with app.app_context():
        ticket = ticket_by_public_id(scene["number"])
        add_comment(ticket, actor=person(scene["people"]["tec"]["id"]), content="Nota", kind="INTERNO")
        add_comment(
            ticket, actor=person(scene["people"]["tec"]["id"]), content="Respuesta", kind="PUBLICO"
        )
        db.session.commit()

    assert _notices(app, scene["people"]["tec2"]) == []
    assert _notices(app, scene["people"]["req"]) == [E.COMENTARIO_PUBLICO.value]


# --- La pantalla ----------------------------------------------------------------------------


@pytest.fixture()
def browser(client, make_user):
    login(client, make_user("ADMINISTRADOR", username="admin_pantalla"))

    return client


def _checked(response) -> set[str]:
    html = response.get_data(as_text=True)

    return set(re.findall(r'value="([A-Z_]+:[A-Z]+)"[^>]*checked', html))


def _token_in(response) -> str:
    return re.search(r'name="base"[^>]*value="([^"]*)"', response.get_data(as_text=True)).group(1)


def _send(browser, enabled, **extra):
    opened = browser.get(SCREEN)

    return browser.post(
        SCREEN, data={"base": _token_in(opened), "avisos": list(enabled), **extra}
    )


def _togglable():
    return [rule.key for rule in RULES if rule.locked is None]


def test_the_screen_lists_every_notice_and_marks_the_mandatory_ones(browser):
    response = browser.get(SCREEN)
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert _checked(response) == {rule.key for rule in RULES}

    for rule in RULES:
        assert f'value="{rule.key}"' in html

    assert plain_text(response).count("Siempre activo.") == 2


def test_unchecking_a_notice_saves_it_as_off(app, browser):
    enabled = [key for key in _togglable() if key != "NOTA_INTERNA:TECNICOS"]

    response = _send(browser, enabled, motivo="Demasiadas")

    assert response.status_code == 302
    assert "se guardó correctamente" in plain_text(browser.get(response.headers["Location"]))
    assert "NOTA_INTERNA:TECNICOS" not in _checked(browser.get(SCREEN))

    with app.app_context():
        assert disabled_keys() == {"NOTA_INTERNA:TECNICOS"}


def test_submitting_without_the_locked_checkboxes_keeps_them_on(app, browser):
    # El navegador no envía las casillas deshabilitadas.
    _send(browser, _togglable())

    with app.app_context():
        assert disabled_keys() == frozenset()


def test_saving_without_changes_says_so(browser):
    response = _send(browser, _togglable())

    assert "No hay cambios" in plain_text(browser.get(response.headers["Location"]))


def test_a_change_by_someone_else_while_editing_saves_nothing(app, browser, make_user):
    opened = browser.get(SCREEN)
    other = make_user("ADMINISTRADOR", username="otro_admin")
    _turn_off(app, other, "NOTA_INTERNA:TECNICOS")

    response = browser.post(SCREEN, data={"base": _token_in(opened), "avisos": []})

    assert "Otra persona cambió" in plain_text(browser.get(response.headers["Location"]))

    with app.app_context():
        assert disabled_keys() == {"NOTA_INTERNA:TECNICOS"}


def test_a_submission_without_what_was_seen_saves_nothing(app, browser):
    browser.post(SCREEN, data={"avisos": []})

    with app.app_context():
        assert disabled_keys() == frozenset()


def test_the_screen_requires_the_csrf_token(app, browser):
    app.config["WTF_CSRF_ENABLED"] = True

    assert browser.post(SCREEN, data={"avisos": []}).status_code == 400


@pytest.mark.parametrize("role", ["SOLICITANTE", "TECNICO", "SUPERVISOR"])
def test_only_the_administrator_can_use_the_screen(client, make_user, role):
    login(client, make_user(role))

    assert client.get(SCREEN).status_code == 403
    assert client.post(SCREEN, data={"avisos": []}).status_code == 403


def test_every_state_notice_is_in_the_catalogue():
    # Un estado nuevo que avise a alguien sin declararlo en el catálogo fallaría en
    # producción: esta lo detecta antes.
    keys = {rule.key for rule in RULES}
    missing = [
        f"{notice[0].value}:{audience.value}"
        for notices in dispatch.STATE_NOTICES.values()
        for audience, notice in zip(
            (Audience.SOLICITANTES, Audience.TECNICOS), notices, strict=True
        )
        if f"{notice[0].value}:{audience.value}" not in keys
    ]

    assert missing == []


def test_silencing_technicians_does_not_divert_the_sla_warning_to_supervisors(
    app, scene, chief
):
    _assign_both(app, scene)
    _turn_off(app, chief, "SLA_PROXIMO_A_VENCER:TECNICOS")

    with app.app_context():
        dispatch.notify_sla_warning(ticket_by_public_id(scene["number"]))
        db.session.commit()

    assert _notices(app, scene["people"]["tec"]) == []
    assert _notices(app, scene["people"]["sup"]) == []


def test_each_sla_breach_audience_is_switched_separately(app, scene, chief):
    _assign_both(app, scene)
    _turn_off(app, chief, "SLA_VENCIDO:SUPERVISORES")

    with app.app_context():
        dispatch.notify_sla_breach(ticket_by_public_id(scene["number"]))
        db.session.commit()

    assert _notices(app, scene["people"]["tec"]) == [E.SLA_VENCIDO.value]
    assert _notices(app, scene["people"]["sup"]) == []
