"""Las pantallas de configuración del Administrador (`/admin/settings/<grupo>`)."""

import re

import pytest

from src.workdesk import settings
from src.workdesk.admin.settings_screens import GROUPS
from src.workdesk.audit import AuditAction
from src.workdesk.configuration import (
    has_own_value,
    save_setting,
    state_token,
    value_of,
)
from src.workdesk.extensions import db
from src.workdesk.models import Configuracion, User
from src.workdesk.settings import ALL_SETTINGS, BOOL_SETTINGS
from tests.ticket_helpers import audit_entries, login, plain_text

CLOSING = "/admin/settings/cierre"


@pytest.fixture()
def admin(client, make_user):
    user = make_user("ADMINISTRADOR")
    login(client, user)

    return user


def _token_in(response) -> str:
    html = response.get_data(as_text=True)

    return re.search(r'name="base"[^>]*value="([^"]*)"', html).group(1)


def _post(client, url, data):
    """Abre la pantalla (para saber qué se vio) y envía lo que cambia sobre sus valores."""
    opened = client.get(url)

    return client.post(url, data={"base": _token_in(opened), **data})


def _closing_data(**changes):
    return {
        "AUTO_CLOSE_ENABLED": "y",
        "AUTO_CLOSE_HOURS": "24",
        "REOPEN_WINDOW_DAYS": "30",
        "motivo": "",
        **changes,
    }


def _values(app, *wanted):
    with app.app_context():
        return [value_of(setting) for setting in wanted]


def _count_rows(app):
    with app.app_context():
        return db.session.scalar(db.select(db.func.count(Configuracion.id)))


# --- Qué pantallas hay y quién entra ------------------------------------------------------


def test_every_setting_but_the_sla_switch_has_exactly_one_screen():
    listed = [field.setting for group in GROUPS for field in group.fields]

    assert len(listed) == len(set(listed))
    # El interruptor del SLA vive en la pantalla «SLA» (UI-022).
    assert set(ALL_SETTINGS) - set(listed) == {settings.SLA_ENABLED}
    assert set(BOOL_SETTINGS) - set(listed) == {settings.SLA_ENABLED}


@pytest.mark.parametrize("group", GROUPS, ids=lambda g: g.slug)
def test_each_screen_opens_with_its_fields_and_current_values(client, admin, group):
    response = client.get(f"/admin/settings/{group.slug}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert group.title in html

    for field in group.fields:
        assert f'name="{field.setting.key}"' in html
        assert field.label in html


def test_the_upload_screen_shows_kilobytes_and_the_allowed_types(client, admin):
    html = client.get("/admin/settings/archivos").get_data(as_text=True)

    assert re.search(r'name="UPLOAD_MAX_BYTES"[^>]*value="10240"', html)
    assert "pdf" in html and "docx" in html


@pytest.mark.parametrize("role", ["SOLICITANTE", "TECNICO", "SUPERVISOR"])
def test_only_the_administrator_can_use_the_screens(app, client, make_user, role):
    login(client, make_user(role))

    assert client.get(CLOSING).status_code == 403
    assert client.post(CLOSING, data=_closing_data()).status_code == 403
    assert client.post(f"{CLOSING}/reset/AUTO_CLOSE_HOURS").status_code == 403
    assert _count_rows(app) == 0


def test_an_unknown_screen_or_setting_is_not_found(client, admin):
    assert client.get("/admin/settings/inventada").status_code == 404
    # Un parámetro de otra pantalla no se puede restablecer desde esta.
    assert client.post(f"{CLOSING}/reset/SESSION_IDLE_MINUTES").status_code == 404


# --- Guardar -------------------------------------------------------------------------------


def test_saving_changes_only_what_changed_and_audits_it(app, client, admin):
    response = _post(client, CLOSING, _closing_data(AUTO_CLOSE_HOURS="48", motivo="Más plazo"))

    assert response.status_code == 302
    assert "se guardó correctamente" in plain_text(client.get(response.headers["Location"]))
    assert _values(app, settings.AUTO_CLOSE_HOURS, settings.REOPEN_WINDOW_DAYS) == [48, 30]
    assert _count_rows(app) == 1

    with app.app_context():
        entry = audit_entries()[-1]

        assert entry.accion == AuditAction.CONFIGURACION_MODIFICADA
        assert entry.motivo == "Más plazo"


def test_unchecking_a_switch_saves_it_as_off(app, client, admin):
    data = _closing_data()
    del data["AUTO_CLOSE_ENABLED"]

    _post(client, CLOSING, data)

    assert _values(app, settings.AUTO_CLOSE_ENABLED) == [False]


def test_saving_without_changes_says_so_and_writes_nothing(app, client, admin):
    response = _post(client, CLOSING, _closing_data())

    assert "No hay cambios" in plain_text(client.get(response.headers["Location"]))
    assert _count_rows(app) == 0


def test_a_saved_value_is_marked_as_own_with_the_initial_one(app, client, admin):
    _post(client, CLOSING, _closing_data(AUTO_CLOSE_HOURS="48"))

    text = plain_text(client.get(CLOSING))

    assert "Valor propio" in text
    assert "Inicial: 24 horas" in text


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("0", "entre 1 y 8760"),
        ("999999999999", "entre 1 y 8760"),
        ("abc", "número entero"),
        ("", "número entero"),
    ],
)
def test_an_invalid_value_is_explained_next_to_the_field_and_saves_nothing(
    app, client, admin, value, message
):
    response = _post(client, CLOSING, _closing_data(AUTO_CLOSE_HOURS=value))

    assert response.status_code == 200
    assert message in plain_text(response)
    assert _count_rows(app) == 0


def test_an_error_keeps_what_was_typed(client, admin):
    response = _post(
        client, CLOSING, _closing_data(AUTO_CLOSE_HOURS="0", REOPEN_WINDOW_DAYS="11")
    )

    html = response.get_data(as_text=True)

    assert re.search(r'name="REOPEN_WINDOW_DAYS"[^>]*value="11"', html)


def test_the_kilobytes_are_saved_as_bytes(app, client, admin):
    _post(
        client,
        "/admin/settings/archivos",
        {"UPLOAD_MAX_BYTES": "2048", "UPLOAD_MAX_FILES_PER_TICKET": "20"},
    )

    assert _values(app, settings.UPLOAD_MAX_BYTES) == [2 * 1024 * 1024]


def test_a_value_the_person_did_not_touch_is_not_rewritten_by_rounding(app, client, admin):
    # Un tope que no es múltiplo de 1 KB (definido por entorno) se muestra redondeado: si la
    # persona no lo toca, no debe guardarse el redondeo.
    app.config["UPLOAD_MAX_BYTES"] = 1500

    response = _post(
        client,
        "/admin/settings/archivos",
        {"UPLOAD_MAX_BYTES": "1", "UPLOAD_MAX_FILES_PER_TICKET": "20"},
    )

    assert response.status_code == 302
    assert _count_rows(app) == 0
    assert _values(app, settings.UPLOAD_MAX_BYTES) == [1500]


def test_two_related_values_that_do_not_fit_are_explained_with_their_labels(
    app, client, admin
):
    response = _post(
        client,
        "/admin/settings/colaboracion",
        {
            "COMMENT_EDIT_WINDOW_MINUTES": "30",
            "EDIT_LOCK_TTL_SECONDS": "30",
            "EDIT_LOCK_HEARTBEAT_SECONDS": "45",
        },
    )
    text = plain_text(response)

    assert response.status_code == 200
    assert "«Renovación del bloqueo» debe ser menor que «Duración del bloqueo" in text
    assert "EDIT_LOCK" not in text
    assert _count_rows(app) == 0


def test_two_related_values_can_be_changed_together(app, client, admin):
    response = _post(
        client,
        "/admin/settings/colaboracion",
        {
            "COMMENT_EDIT_WINDOW_MINUTES": "30",
            "EDIT_LOCK_TTL_SECONDS": "600",
            "EDIT_LOCK_HEARTBEAT_SECONDS": "300",
        },
    )

    assert response.status_code == 302
    assert _values(app, settings.EDIT_LOCK_TTL_SECONDS) == [600]


# --- Conflictos ----------------------------------------------------------------------------


def test_a_change_by_someone_else_while_editing_saves_nothing(app, client, admin):
    opened = client.get(CLOSING)

    with app.app_context():
        other = db.session.get(User, admin["id"])
        save_setting(settings.REOPEN_WINDOW_DAYS, 7, actor=other)
        db.session.commit()

    response = client.post(
        CLOSING,
        data={"base": _token_in(opened), **_closing_data(AUTO_CLOSE_HOURS="48")},
    )

    assert response.status_code == 302
    assert "Otra persona cambió" in plain_text(client.get(response.headers["Location"]))
    assert _values(app, settings.AUTO_CLOSE_HOURS, settings.REOPEN_WINDOW_DAYS) == [24, 7]


def test_a_submission_without_what_was_seen_is_a_conflict(app, client, admin):
    client.post(CLOSING, data=_closing_data(AUTO_CLOSE_HOURS="48"))

    assert _count_rows(app) == 0


def test_the_token_follows_what_is_stored(app, admin):
    with app.app_context():
        assert state_token((settings.AUTO_CLOSE_HOURS,)) == "cierre.auto_cierre_horas=-"


# --- Restablecer -----------------------------------------------------------------------------


def test_restoring_returns_to_the_initial_value(app, client, admin):
    _post(client, CLOSING, _closing_data(AUTO_CLOSE_HOURS="48"))

    response = client.post(f"{CLOSING}/reset/AUTO_CLOSE_HOURS", data={"motivo": "Volver"})

    assert response.status_code == 302
    assert "volvió a su valor inicial" in plain_text(client.get(response.headers["Location"]))
    assert _values(app, settings.AUTO_CLOSE_HOURS) == [24]

    with app.app_context():
        assert not has_own_value(settings.AUTO_CLOSE_HOURS)
        assert audit_entries()[-1].motivo == "Volver"


def test_restoring_something_already_initial_says_so(client, admin):
    response = client.post(f"{CLOSING}/reset/AUTO_CLOSE_HOURS")

    assert "ya usaba su valor inicial" in plain_text(client.get(response.headers["Location"]))


def test_restoring_cannot_leave_two_settings_incompatible(app, client, admin):
    _post(
        client,
        "/admin/settings/colaboracion",
        {
            "COMMENT_EDIT_WINDOW_MINUTES": "30",
            "EDIT_LOCK_TTL_SECONDS": "600",
            "EDIT_LOCK_HEARTBEAT_SECONDS": "300",
        },
    )

    response = client.post("/admin/settings/colaboracion/reset/EDIT_LOCK_TTL_SECONDS")

    assert "debe ser menor que" in plain_text(client.get(response.headers["Location"]))
    assert _values(app, settings.EDIT_LOCK_TTL_SECONDS) == [600]


def test_restoring_requires_the_csrf_token(app, client, admin):
    app.config["WTF_CSRF_ENABLED"] = True

    assert client.post(f"{CLOSING}/reset/AUTO_CLOSE_HOURS").status_code == 400


def test_pressing_enter_saves_and_never_restores(client, admin):
    # El navegador usa el primer botón de envío del formulario al pulsar Enter: no puede ser
    # uno de «Restablecer».
    _post(client, CLOSING, _closing_data(AUTO_CLOSE_HOURS="48"))
    html = client.get(CLOSING).get_data(as_text=True)
    form = html[html.index('class="card form-card"') :]
    first_submit = re.search(r"<button[^>]*type=\"submit\"[^>]*>", form).group(0)

    assert "formaction" not in first_submit
    assert "formaction" in form
