"""La configuración administrable: tabla `configuracion`, lectura por petición y cambios
(docs/09, 26.1; `configuration.py`).

Lo esencial que fijan estas pruebas:

- **Sin fila rige el valor inicial** (la variable de entorno o el valor por defecto) y con
  fila rige la del Administrador; borrarla devuelve el valor inicial.
- **Leer cuesta una consulta por petición**, no una por parámetro ni una por lectura, y no
  hay caché entre peticiones: un cambio confirmado lo ve la petición siguiente.
- **Todo el código lee por `value_of`**: ningún módulo vuelve a leer `app.config` de un
  parámetro de `settings.py` (así un valor guardado nunca se ignora en algún rincón).
- **Un cambio se valida, se audita y se serializa**: dos Administradores que cambian a la
  vez dos parámetros relacionados no pueden dejarlos incompatibles.
"""

import logging
import re
import time
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

import pytest
from flask import request
from sqlalchemy import event

from src.workdesk import configuration, settings
from src.workdesk.audit import AuditAction
from src.workdesk.configuration import (
    SettingConflictError,
    SettingRuleError,
    effective_values,
    forget_cached_settings,
    has_own_value,
    initial_value,
    reset_setting,
    save_setting,
    save_settings,
    state_token,
    value_of,
)
from src.workdesk.extensions import db
from src.workdesk.models import Configuracion, User
from src.workdesk.settings import ALL_SETTINGS, INT_SETTINGS
from tests.ticket_helpers import audit_entries, login, run_in_threads

ROOT = Path(__file__).resolve().parents[1]


def _user(user_data):
    return db.session.get(User, user_data["id"])


def _row(setting):
    return db.session.scalar(
        db.select(Configuracion).where(Configuracion.clave == setting.table_key)
    )


@pytest.fixture()
def admin(app, admin_user):
    """El Administrador, con un app context abierto durante el test."""
    with app.app_context():
        yield _user(admin_user)


# --- Qué valor rige ---------------------------------------------------------------------


def test_without_a_row_the_initial_value_rules(admin):
    assert value_of(settings.SESSION_IDLE_MINUTES) == 30
    assert not has_own_value(settings.SESSION_IDLE_MINUTES)
    assert effective_values() == {s.key: s.default for s in ALL_SETTINGS}


def test_the_initial_value_follows_the_app_configuration(app):
    app.config["SESSION_IDLE_MINUTES"] = 45

    with app.app_context():
        assert value_of(settings.SESSION_IDLE_MINUTES) == 45
        assert initial_value(settings.SESSION_IDLE_MINUTES) == 45


def test_an_own_value_replaces_the_initial_one(app, admin):
    save_setting(settings.SESSION_IDLE_MINUTES, 10, actor=admin)
    db.session.commit()

    assert value_of(settings.SESSION_IDLE_MINUTES) == 10
    assert has_own_value(settings.SESSION_IDLE_MINUTES)
    # El resto no cambia.
    assert value_of(settings.SESSION_MAX_HOURS) == 8


def test_a_change_confirmed_elsewhere_is_seen_by_the_next_request(app, admin):
    # No hay caché entre peticiones: otro proceso (el planificador, otro servidor web)
    # ve el cambio en cuanto se confirma.
    save_setting(settings.REOPEN_WINDOW_DAYS, 5, actor=admin)
    db.session.commit()

    with app.app_context():
        assert value_of(settings.REOPEN_WINDOW_DAYS) == 5


def test_a_stored_value_that_is_not_valid_is_ignored_with_a_warning(app, admin, caplog):
    for bad in ("abc", "0", "-5", "3.5"):
        db.session.add(
            Configuracion(clave=settings.SESSION_IDLE_MINUTES.table_key, valor=bad)
        )
        db.session.commit()
        forget_cached_settings()

        with caplog.at_level(logging.WARNING):
            assert value_of(settings.SESSION_IDLE_MINUTES) == 30

        assert "sesion.inactividad_minutos" in caplog.text
        caplog.clear()

        db.session.delete(_row(settings.SESSION_IDLE_MINUTES))
        db.session.commit()


def test_a_row_for_a_key_the_code_does_not_know_is_ignored(admin):
    db.session.add(Configuracion(clave="futuro.parametro", valor="7"))
    db.session.commit()
    forget_cached_settings()

    assert effective_values() == {s.key: s.default for s in ALL_SETTINGS}


# --- Cuánto cuesta leer -----------------------------------------------------------------


def _count_queries(action):
    seen = []

    def record(*_args):
        seen.append(1)

    event.listen(db.engine, "before_cursor_execute", record)
    try:
        action()
    finally:
        event.remove(db.engine, "before_cursor_execute", record)

    return len(seen)


def test_reading_every_setting_costs_one_query(admin):
    forget_cached_settings()

    assert _count_queries(effective_values) == 1


def test_reading_again_in_the_same_request_costs_nothing(admin):
    forget_cached_settings()
    value_of(settings.SESSION_IDLE_MINUTES)

    assert _count_queries(effective_values) == 0


# --- Guardar -----------------------------------------------------------------------------


def test_saving_stores_the_value_and_audits_it(admin):
    changed = save_setting(
        settings.AUTO_CLOSE_HOURS, 48, actor=admin, reason="  Más tiempo para validar  "
    )
    db.session.commit()

    row = _row(settings.AUTO_CLOSE_HOURS)
    entry = audit_entries()[-1]

    assert changed is True
    assert (row.valor, row.tipo_dato, row.categoria) == ("48", "ENTERO", "cierre")
    assert row.usuario_modificacion_id == admin.id
    assert entry.accion == AuditAction.CONFIGURACION_MODIFICADA
    assert (entry.entidad_tipo, entry.entidad_id) == ("configuracion", row.id)
    assert entry.detalle == "cierre.auto_cierre_horas"
    assert entry.valor_anterior == {"valor": 24}
    assert entry.valor_nuevo == {"valor": 48}
    assert entry.motivo == "Más tiempo para validar"
    assert entry.actor_usuario_id == admin.id


def test_the_audit_accepts_the_password_setting_key(admin):
    # La clave contiene «password» y la auditoría rechaza esas palabras como claves de los
    # valores: por eso la clave va en `detalle` y los valores bajo «valor».
    save_setting(settings.PASSWORD_MIN_LENGTH, 14, actor=admin)
    db.session.commit()

    assert audit_entries()[-1].detalle == "autenticacion.password_longitud_minima"


def test_saving_the_value_already_in_force_changes_nothing(admin):
    assert save_setting(settings.AUTO_CLOSE_HOURS, 24, actor=admin) is False
    db.session.commit()

    assert _row(settings.AUTO_CLOSE_HOURS) is None
    assert audit_entries() == []


def test_saving_again_updates_the_same_row(admin):
    save_setting(settings.AUTO_CLOSE_HOURS, 48, actor=admin)
    db.session.commit()
    first = _row(settings.AUTO_CLOSE_HOURS)

    save_setting(settings.AUTO_CLOSE_HOURS, 72, actor=admin)
    db.session.commit()

    rows = db.session.scalars(db.select(Configuracion)).all()

    assert [r.valor for r in rows] == ["72"]
    assert rows[0].id == first.id
    assert audit_entries()[-1].valor_anterior == {"valor": 48}


@pytest.mark.parametrize("setting", INT_SETTINGS, ids=lambda s: s.key)
def test_every_setting_rejects_a_value_below_its_minimum(admin, setting):
    with pytest.raises(SettingRuleError, match=setting.key):
        save_setting(setting, setting.minimum - 1, actor=admin)

    db.session.rollback()

    assert _row(setting) is None
    assert audit_entries() == []


@pytest.mark.parametrize("wrong", ["10", 2.5, None, True])
def test_a_value_that_is_not_an_integer_is_rejected(admin, wrong):
    with pytest.raises(SettingRuleError, match="debe ser un entero"):
        save_setting(settings.SESSION_IDLE_MINUTES, wrong, actor=admin)


def test_the_password_length_stays_inside_its_bounds(admin):
    for wrong in (7, 129):
        with pytest.raises(SettingRuleError, match="entre 8 y 128"):
            save_setting(settings.PASSWORD_MIN_LENGTH, wrong, actor=admin)


def test_a_change_that_breaks_the_relation_between_two_settings_is_rejected(admin):
    # El latido (45) debe ser menor que la duración (120).
    with pytest.raises(SettingRuleError, match="menor que EDIT_LOCK_TTL_SECONDS"):
        save_setting(settings.EDIT_LOCK_TTL_SECONDS, 30, actor=admin)

    with pytest.raises(SettingRuleError, match="menor que EDIT_LOCK_TTL_SECONDS"):
        save_setting(settings.EDIT_LOCK_HEARTBEAT_SECONDS, 120, actor=admin)


def test_the_relation_is_checked_against_the_values_in_force_not_the_initial_ones(admin):
    save_setting(settings.EDIT_LOCK_TTL_SECONDS, 600, actor=admin)
    save_setting(settings.EDIT_LOCK_HEARTBEAT_SECONDS, 300, actor=admin)
    db.session.commit()

    # Con la duración inicial (120) el 300 sería inválido; con la vigente (600) no.
    assert value_of(settings.EDIT_LOCK_HEARTBEAT_SECONDS) == 300

    with pytest.raises(SettingRuleError):
        save_setting(settings.EDIT_LOCK_TTL_SECONDS, 250, actor=admin)


def test_a_reason_that_is_too_long_is_rejected(admin):
    with pytest.raises(SettingRuleError, match="500"):
        save_setting(settings.AUTO_CLOSE_HOURS, 48, actor=admin, reason="x" * 501)


@pytest.mark.parametrize("role", ["SOLICITANTE", "TECNICO", "SUPERVISOR"])
def test_only_an_administrator_can_change_a_setting(app, make_user, role):
    other = make_user(role)

    with app.app_context(), pytest.raises(PermissionError):
        save_setting(settings.AUTO_CLOSE_HOURS, 48, actor=_user(other))

    with app.app_context(), pytest.raises(PermissionError):
        reset_setting(settings.AUTO_CLOSE_HOURS, actor=_user(other))


def test_an_inactive_administrator_cannot_change_a_setting(app, admin_user):
    with app.app_context():
        user = _user(admin_user)
        user.activo = False
        db.session.commit()

        with pytest.raises(PermissionError):
            save_setting(settings.AUTO_CLOSE_HOURS, 48, actor=user)


# --- Restablecer ---------------------------------------------------------------------------


def test_resetting_deletes_the_row_and_the_initial_value_rules_again(admin):
    save_setting(settings.AUTO_CLOSE_HOURS, 48, actor=admin)
    db.session.commit()
    row_id = _row(settings.AUTO_CLOSE_HOURS).id

    assert reset_setting(settings.AUTO_CLOSE_HOURS, actor=admin, reason="Volver") is True
    db.session.commit()

    entry = audit_entries()[-1]

    assert _row(settings.AUTO_CLOSE_HOURS) is None
    assert value_of(settings.AUTO_CLOSE_HOURS) == 24
    assert entry.accion == AuditAction.CONFIGURACION_RESTABLECIDA
    assert entry.entidad_id == row_id
    assert entry.valor_anterior == {"valor": 48}
    assert entry.valor_nuevo == {"valor": 24}
    assert entry.motivo == "Volver"


def test_resetting_a_setting_without_its_own_value_does_nothing(admin):
    assert reset_setting(settings.AUTO_CLOSE_HOURS, actor=admin) is False
    assert audit_entries() == []


def test_resetting_cannot_leave_two_settings_incompatible(admin):
    save_setting(settings.EDIT_LOCK_TTL_SECONDS, 600, actor=admin)
    save_setting(settings.EDIT_LOCK_HEARTBEAT_SECONDS, 300, actor=admin)
    db.session.commit()

    # Volver la duración a 120 dejaría el latido (300) por encima.
    with pytest.raises(SettingRuleError, match="menor que"):
        reset_setting(settings.EDIT_LOCK_TTL_SECONDS, actor=admin)

    db.session.rollback()
    assert value_of(settings.EDIT_LOCK_TTL_SECONDS) == 600


# --- Concurrencia ---------------------------------------------------------------------------


def test_two_administrators_cannot_make_two_related_settings_incompatible(app, admin_user):
    # Solos, los dos cambios son válidos (duración 60 con latido 45; latido 100 con duración
    # 120). Juntos no lo son. El bloqueo hace que el segundo vea el primero ya confirmado.
    def shorten_the_lock():
        save_setting(settings.EDIT_LOCK_TTL_SECONDS, 60, actor=_user(admin_user))
        # Con la transacción aún abierta: sin el bloqueo, el otro Administrador validaría
        # contra la duración confirmada (120) y los dos cambios pasarían.
        time.sleep(0.5)

    def slow_the_heartbeat():
        # Llega mientras el primero aún no confirmó (él espera medio segundo).
        time.sleep(0.2)
        save_setting(settings.EDIT_LOCK_HEARTBEAT_SECONDS, 100, actor=_user(admin_user))

    outcomes = run_in_threads(
        app, [shorten_the_lock, slow_the_heartbeat], rule_errors=(SettingRuleError,)
    )

    assert outcomes.count("ok") == 1
    assert any("menor que" in outcome for outcome in outcomes)

    with app.app_context():
        values = effective_values()

        assert values["EDIT_LOCK_HEARTBEAT_SECONDS"] < values["EDIT_LOCK_TTL_SECONDS"]
        assert db.session.scalar(db.select(db.func.count(Configuracion.id))) == 1


def test_two_administrators_saving_the_same_new_value_leave_one_row_and_one_audit(
    app, admin_user
):
    def save():
        save_setting(settings.AUTO_CLOSE_HOURS, 48, actor=_user(admin_user))

    outcomes = run_in_threads(app, [save, save], rule_errors=(SettingRuleError,))

    assert outcomes == ["ok", "ok"]

    with app.app_context():
        rows = db.session.scalars(db.select(Configuracion)).all()
        entries = [e for e in audit_entries() if e.accion == AuditAction.CONFIGURACION_MODIFICADA]

        assert [r.valor for r in rows] == ["48"]
        # El segundo vio el valor del primero ya vigente: no hubo nada que cambiar.
        assert len(entries) == 1


# --- Lo que cambia en el resto de la aplicación ----------------------------------------------


def _set(app, admin_user, setting, value):
    with app.app_context():
        save_setting(setting, value, actor=_user(admin_user))
        db.session.commit()


def test_the_session_idle_limit_comes_from_the_configuration(app, client, admin_user):
    login(client, admin_user)
    _set(app, admin_user, settings.SESSION_IDLE_MINUTES, 1)

    now = datetime.now(UTC).timestamp()

    with client.session_transaction() as session:
        session["session_started_at"] = now - 300
        session["session_last_activity"] = now - 120

    response = client.get("/dashboard")

    # Con el límite inicial (30 minutos) esta sesión seguiría viva.
    assert response.status_code == 302
    assert "/login" in response.location


def test_the_failed_attempts_limit_comes_from_the_configuration(app, client, admin_user):
    _set(app, admin_user, settings.LOGIN_MAX_FAILED_ATTEMPTS, 2)

    for _ in range(2):
        client.post(
            "/login", data={"username": admin_user["username"], "password": "Incorrecta123!!"}
        )

    with app.app_context():
        assert _user(admin_user).bloqueado_hasta is not None


def test_the_minimum_password_length_comes_from_the_configuration(app, admin_user):
    from src.workdesk.auth.credentials import _min_length

    _set(app, admin_user, settings.PASSWORD_MIN_LENGTH, 20)

    with app.app_context():
        assert _min_length() == 20


def test_the_high_workload_mark_comes_from_the_configuration(app, admin_user):
    _set(app, admin_user, settings.WORKLOAD_HIGH_ACTIVE_TICKETS, 3)

    with app.app_context():
        assert value_of(settings.WORKLOAD_HIGH_ACTIVE_TICKETS) == 3


def _request_limit(app, *, content_type):
    """El tope de tamaño que las comprobaciones previas dejan puesto a una petición."""
    with app.test_request_context(
        "/tickets/1/attachments", method="POST", content_type=content_type
    ):
        app.preprocess_request()

        return request.max_content_length


def test_the_upload_size_limit_follows_the_configuration_without_a_restart(app, admin_user):
    # El tope de Flask se fijaba al iniciar con el valor inicial: bajar el tamaño máximo no
    # surtía efecto sobre el cuerpo de la petición. Ahora la que sube archivos usa el vigente.
    with app.app_context():
        before = _request_limit(app, content_type="multipart/form-data")

    assert before == 10 * 1024 * 1024 * 5 + 1024 * 1024

    _set(app, admin_user, settings.UPLOAD_MAX_BYTES, 100_000)

    with app.app_context():
        after = _request_limit(app, content_type="multipart/form-data")

    assert after == 100_000 * 5 + 1024 * 1024


def test_only_requests_that_carry_files_pay_for_reading_the_configuration(app):
    # Una petición normal no lleva archivos: conserva el tope general y no consulta nada.
    with app.app_context():
        limit = _request_limit(app, content_type="application/x-www-form-urlencoded")

    assert limit == app.config["MAX_CONTENT_LENGTH"]


def test_the_scheduler_does_not_keep_a_value_read_in_a_previous_pass(app, admin_user):
    from src.workdesk import scheduler

    # Otro proceso (el servidor web) cambia el valor mientras el planificador sigue vivo.
    with app.app_context():
        # Un planificador vive en un solo app context durante todas sus pasadas.
        scheduler.run_once()
        assert value_of(settings.AUTO_CLOSE_HOURS) == 24

        other = app.app_context()
        other.push()
        try:
            save_setting(settings.AUTO_CLOSE_HOURS, 96, actor=_user(admin_user))
            db.session.commit()
        finally:
            other.pop()

        scheduler.run_once()
        assert value_of(settings.AUTO_CLOSE_HOURS) == 96


# --- Nadie se salta la configuración ---------------------------------------------------------

# Los únicos módulos que pueden leer estos parámetros de `app.config`: el que lee el entorno,
# el que decide el valor vigente y el que valida al iniciar.
ALLOWED_TO_READ_CONFIG = {
    "config.py",
    "configuration.py",
    "settings.py",
    "__init__.py",
}


def test_no_module_reads_a_setting_from_app_config_directly():
    keys = "|".join(re.escape(s.key) for s in ALL_SETTINGS)
    direct = re.compile(rf"""config(?:\.get\(|\[)\s*["'](?:{keys})["']""")
    offenders = []

    for path in (ROOT / "src" / "workdesk").rglob("*.py"):
        if path.name in ALLOWED_TO_READ_CONFIG and path.parent.name == "workdesk":
            continue

        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if direct.search(line):
                offenders.append(f"{path.relative_to(ROOT)}:{number}")

    assert not offenders, f"Leen la configuración sin pasar por value_of: {offenders}"


def test_the_stored_values_are_not_kept_between_requests():
    # La caché vive en `g`, que Flask descarta con cada app context: este test fija que no
    # se guardó en un módulo (que sobreviviría entre peticiones y procesos de un hilo).
    source = Path(configuration.__file__).read_text(encoding="utf-8")

    assert "lru_cache" not in source
    assert "functools.cache" not in source


def test_each_request_starts_without_what_the_previous_one_read(app, client, admin_user):
    # Con un app context abierto durante varias peticiones (como hacen los tests y un
    # proceso largo) `g` es el mismo: sin descartar la caché al empezar cada petición, un
    # cambio confirmado entre dos de ellas no se vería.
    login(client, admin_user)

    with app.app_context():
        assert client.get("/dashboard").status_code == 200
        assert value_of(settings.REOPEN_WINDOW_DAYS) == 30

        other = app.app_context()
        other.push()
        try:
            save_setting(settings.REOPEN_WINDOW_DAYS, 7, actor=_user(admin_user))
            db.session.commit()
        finally:
            other.pop()

        # La lectura de antes de la petición aún está en `g`...
        assert value_of(settings.REOPEN_WINDOW_DAYS) == 30
        # ...y la siguiente petición la descarta.
        client.get("/dashboard")
        assert value_of(settings.REOPEN_WINDOW_DAYS) == 7


def test_the_upload_limit_is_applied_before_the_csrf_check_reads_the_body(
    app, client, admin_user
):
    # La protección CSRF lee el formulario, y con él el cuerpo entero. Si el tope vigente se
    # pusiera después, esa lectura usaría el general (con el tamaño inicial) y una subida
    # enorme sin token fallaría por CSRF (400) en lugar de por tamaño (413).
    _set(app, admin_user, settings.UPLOAD_MAX_BYTES, 100_000)
    app.config["WTF_CSRF_ENABLED"] = True

    response = client.post(
        "/tickets/1/attachments",
        data={"archivos": (BytesIO(b"a" * (2 * 1024 * 1024)), "grande.txt")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 413


# --- Interruptores y guardado en lote -------------------------------------------------


def test_a_switch_is_stored_as_text_and_read_as_a_boolean(admin):
    assert value_of(settings.SLA_ENABLED) is True

    save_setting(settings.SLA_ENABLED, False, actor=admin)
    db.session.commit()
    row = _row(settings.SLA_ENABLED)

    assert (row.valor, row.tipo_dato, row.categoria) == ("false", "BOOLEANO", "sla")
    assert value_of(settings.SLA_ENABLED) is False
    assert audit_entries()[-1].valor_nuevo == {"valor": False}


@pytest.mark.parametrize("wrong", ["false", 0, 1, None])
def test_a_switch_only_accepts_a_boolean(admin, wrong):
    with pytest.raises(SettingRuleError, match="verdadero o falso"):
        save_setting(settings.AUTO_CLOSE_ENABLED, wrong, actor=admin)


@pytest.mark.parametrize("bad", ["si", "0", "TRUE "])
def test_a_stored_switch_that_is_not_valid_is_ignored(admin, bad):
    db.session.add(Configuracion(clave=settings.SLA_ENABLED.table_key, valor=bad))
    db.session.commit()
    forget_cached_settings()

    assert value_of(settings.SLA_ENABLED) is True


def test_two_related_settings_can_change_together(admin):
    # Uno por uno, 300 de latido sería inválido con 120 de duración; juntos son válidos.
    saved = save_settings(
        {
            settings.EDIT_LOCK_HEARTBEAT_SECONDS: 300,
            settings.EDIT_LOCK_TTL_SECONDS: 600,
        },
        actor=admin,
    )
    db.session.commit()

    assert set(saved) == {settings.EDIT_LOCK_HEARTBEAT_SECONDS, settings.EDIT_LOCK_TTL_SECONDS}
    assert value_of(settings.EDIT_LOCK_HEARTBEAT_SECONDS) == 300


def test_a_batch_with_one_bad_value_saves_nothing(admin):
    with pytest.raises(SettingRuleError):
        save_settings(
            {settings.REOPEN_WINDOW_DAYS: 10, settings.AUTO_CLOSE_HOURS: 0}, actor=admin
        )

    db.session.rollback()

    assert db.session.scalar(db.select(db.func.count(Configuracion.id))) == 0
    assert audit_entries() == []


def test_a_batch_audits_only_what_changed(admin):
    saved = save_settings(
        {settings.REOPEN_WINDOW_DAYS: 10, settings.AUTO_CLOSE_HOURS: 24}, actor=admin
    )
    db.session.commit()

    assert saved == [settings.REOPEN_WINDOW_DAYS]
    assert [e.detalle for e in audit_entries()] == ["reapertura.ventana_dias"]


def test_a_stale_state_token_is_a_conflict(admin):
    group = (settings.REOPEN_WINDOW_DAYS, settings.AUTO_CLOSE_HOURS)
    seen = state_token(group)

    save_setting(settings.AUTO_CLOSE_HOURS, 48, actor=admin)
    db.session.commit()

    with pytest.raises(SettingConflictError):
        save_settings(
            {settings.REOPEN_WINDOW_DAYS: 10}, actor=admin, base_token=seen, group=group
        )

    db.session.rollback()
    assert value_of(settings.REOPEN_WINDOW_DAYS) == 30


def test_a_change_outside_the_group_does_not_conflict(admin):
    group = (settings.REOPEN_WINDOW_DAYS,)
    seen = state_token(group)
    save_setting(settings.AUTO_CLOSE_HOURS, 48, actor=admin)
    db.session.commit()

    saved = save_settings(
        {settings.REOPEN_WINDOW_DAYS: 10}, actor=admin, base_token=seen, group=group
    )

    assert saved == [settings.REOPEN_WINDOW_DAYS]


@pytest.mark.parametrize("setting", INT_SETTINGS, ids=lambda s: s.key)
def test_every_setting_has_an_upper_bound_that_is_enforced(admin, setting):
    assert setting.maximum is not None

    with pytest.raises(SettingRuleError, match=setting.key):
        save_setting(setting, setting.maximum + 1, actor=admin)
