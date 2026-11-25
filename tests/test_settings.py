"""La definición única de los parámetros numéricos (`settings.py`).

Antes, el nombre, el valor por defecto y el rango de cada parámetro estaban repartidos entre
`config.py` y seis funciones de validación de `create_app`. Ahora hay una sola lista, y estas
pruebas impiden que vuelva a haber dos: un parámetro numérico nuevo sin definición, o una
definición que `Config` ignora, hace fallar la suite.
"""

import re
from pathlib import Path

import pytest

from src.workdesk import settings
from src.workdesk.config import Config
from src.workdesk.settings import (
    ALL_SETTINGS,
    BOOL_SETTINGS,
    INT_SETTINGS,
    BoolSetting,
    IntSetting,
    validate_settings,
)

ROOT = Path(__file__).resolve().parents[1]

# Lo único numérico de `Config` que no es un parámetro administrable: el tamaño de los logs.
NOT_ADMINISTRABLE = {"LOG_MAX_BYTES", "LOG_BACKUP_COUNT"}


def _valid_config() -> dict:
    return {setting.key: setting.default for setting in ALL_SETTINGS}


def test_every_numeric_setting_of_config_is_defined_in_settings():
    numeric = {
        name
        for name, value in vars(Config).items()
        if name.isupper() and isinstance(value, int) and not isinstance(value, bool)
    }

    assert numeric - NOT_ADMINISTRABLE == {setting.key for setting in INT_SETTINGS}


def test_there_are_no_two_definitions_of_the_same_key():
    keys = [setting.key for setting in ALL_SETTINGS]

    assert len(keys) == len(set(keys))


def test_the_listed_settings_are_all_the_ones_defined_in_the_module():
    defined = {
        value
        for value in vars(settings).values()
        if isinstance(value, IntSetting | BoolSetting)
    }

    assert defined == set(ALL_SETTINGS)


def test_every_switch_of_config_is_defined_in_settings():
    switches = {
        name
        for name, value in vars(Config).items()
        if isinstance(value, bool) and name.endswith("_ENABLED")
    }

    assert switches == {setting.key for setting in BOOL_SETTINGS}


def test_every_default_is_valid_by_its_own_rule():
    assert validate_settings(_valid_config()) is None


@pytest.mark.parametrize("setting", INT_SETTINGS, ids=lambda s: s.key)
def test_each_setting_rejects_a_value_below_its_minimum(setting):
    config = _valid_config()
    config[setting.key] = setting.minimum - 1

    with pytest.raises(RuntimeError, match=setting.key):
        validate_settings(config)


@pytest.mark.parametrize("setting", INT_SETTINGS, ids=lambda s: s.key)
def test_each_setting_rejects_something_that_is_not_an_integer(setting):
    for wrong in ("10", 1.5, None, True):
        config = _valid_config()
        config[setting.key] = wrong

        with pytest.raises(RuntimeError, match=setting.key):
            validate_settings(config)


def test_the_password_length_is_bounded_on_both_sides():
    for wrong in (7, 129):
        config = _valid_config()
        config["PASSWORD_MIN_LENGTH"] = wrong

        with pytest.raises(RuntimeError, match="entre 8 y 128"):
            validate_settings(config)


def test_zero_turns_off_the_high_workload_mark_but_nothing_else_accepts_it():
    config = _valid_config()
    config["WORKLOAD_HIGH_ACTIVE_TICKETS"] = 0
    validate_settings(config)

    for setting in INT_SETTINGS:
        if setting.key == "WORKLOAD_HIGH_ACTIVE_TICKETS":
            continue

        config = _valid_config()
        config[setting.key] = 0

        with pytest.raises(RuntimeError, match=setting.key):
            validate_settings(config)


def test_the_heartbeat_must_be_shorter_than_the_lock_duration():
    config = _valid_config()
    config["EDIT_LOCK_HEARTBEAT_SECONDS"] = config["EDIT_LOCK_TTL_SECONDS"]

    with pytest.raises(RuntimeError, match="EDIT_LOCK_HEARTBEAT_SECONDS debe ser menor"):
        validate_settings(config)


def test_every_problem_is_reported_at_once():
    config = _valid_config()
    config["SESSION_IDLE_MINUTES"] = 0
    config["REOPEN_WINDOW_DAYS"] = -1
    config["UPLOAD_MAX_BYTES"] = "grande"

    with pytest.raises(RuntimeError) as error:
        validate_settings(config)

    message = str(error.value)

    assert "SESSION_IDLE_MINUTES" in message
    assert "REOPEN_WINDOW_DAYS" in message
    assert "UPLOAD_MAX_BYTES" in message


def test_the_environment_is_the_initial_value(monkeypatch):
    setting = IntSetting("AUTO_CLOSE_HOURS", "cierre.auto_cierre_horas", 24)

    monkeypatch.delenv("AUTO_CLOSE_HOURS", raising=False)
    assert setting.from_environment() == 24

    monkeypatch.setenv("AUTO_CLOSE_HOURS", "48")
    assert setting.from_environment() == 48

    # Una variable vacía (típica de un `.env` a medio rellenar) equivale a no definirla.
    monkeypatch.setenv("AUTO_CLOSE_HOURS", "  ")
    assert setting.from_environment() == 24


def test_an_environment_value_that_is_not_a_number_says_which_one(monkeypatch):
    monkeypatch.setenv("AUTO_CLOSE_HOURS", "veinticuatro")

    with pytest.raises(RuntimeError, match="AUTO_CLOSE_HOURS debe ser un entero"):
        IntSetting("AUTO_CLOSE_HOURS", "cierre.auto_cierre_horas", 24).from_environment()


def test_every_setting_has_its_own_well_formed_table_key():
    keys = [setting.table_key for setting in ALL_SETTINGS]

    assert len(keys) == len(set(keys))
    assert all(re.fullmatch(r"[a-z]+\.[a-z_]+", key) for key in keys), keys


def test_the_data_model_document_names_every_table_key():
    # `docs/09` (sección 26.1) es donde se leen los nombres de la tabla `configuracion`: si
    # un parámetro cambia de clave o aparece uno nuevo, el documento debe decirlo.
    document = (ROOT / "docs" / "09_modelo_de_datos.md").read_text(encoding="utf-8")

    missing = [s.table_key for s in ALL_SETTINGS if s.table_key not in document]

    assert not missing, f"docs/09 no menciona: {missing}"


@pytest.mark.parametrize("setting", INT_SETTINGS, ids=lambda s: s.key)
def test_each_setting_rejects_a_value_above_its_maximum(setting):
    config = _valid_config()
    config[setting.key] = setting.maximum + 1

    with pytest.raises(RuntimeError, match=setting.key):
        validate_settings(config)


@pytest.mark.parametrize("setting", BOOL_SETTINGS, ids=lambda s: s.key)
def test_each_switch_rejects_something_that_is_not_a_boolean(setting):
    for wrong in ("true", 1, None):
        config = _valid_config()
        config[setting.key] = wrong

        with pytest.raises(RuntimeError, match=setting.key):
            validate_settings(config)


def test_a_switch_reads_the_usual_spellings_from_the_environment(monkeypatch):
    setting = BoolSetting("SLA_ENABLED", "sla.habilitado", True)

    for raw, expected in (("false", False), (" NO ", False), ("0", False), ("on", True)):
        monkeypatch.setenv("SLA_ENABLED", raw)
        assert setting.from_environment() is expected

    monkeypatch.setenv("SLA_ENABLED", "")
    assert setting.from_environment() is True

    monkeypatch.setenv("SLA_ENABLED", "quizás")
    with pytest.raises(RuntimeError, match="SLA_ENABLED"):
        setting.from_environment()
