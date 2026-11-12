import pytest

from src.workdesk import create_app
from src.workdesk.security import (
    MAX_LENGTH,
    MIN_LENGTH_FLOOR,
    PasswordPolicyError,
    generate_temporary_password,
    hash_password,
    validate_password_policy,
)

MIN_LENGTH = 12
AMBIGUOUS_CHARACTERS = set("0Oo1lI")


@pytest.mark.parametrize("length", [MIN_LENGTH, 40, MAX_LENGTH])
def test_accepts_passwords_within_the_allowed_length(length):
    validate_password_policy("a" * length, min_length=MIN_LENGTH)


@pytest.mark.parametrize("length", [0, 1, MIN_LENGTH - 1])
def test_rejects_passwords_shorter_than_the_minimum(length):
    with pytest.raises(PasswordPolicyError, match="al menos 12"):
        validate_password_policy("a" * length, min_length=MIN_LENGTH)


def test_rejects_passwords_longer_than_the_maximum():
    with pytest.raises(PasswordPolicyError, match="superar"):
        validate_password_policy(
            "a" * (MAX_LENGTH + 1),
            min_length=MIN_LENGTH,
        )


def test_error_message_uses_the_configured_minimum():
    with pytest.raises(PasswordPolicyError, match="al menos 14"):
        validate_password_policy("a" * 12, min_length=14)


def test_rejects_passwords_made_only_of_spaces():
    with pytest.raises(PasswordPolicyError, match="solo por espacios"):
        validate_password_policy(" " * 20, min_length=MIN_LENGTH)


def test_does_not_trim_surrounding_spaces():
    # Los espacios forman parte de la contraseña: cuentan para la longitud.
    validate_password_policy("  frase segura  ", min_length=MIN_LENGTH)


def test_length_is_measured_in_characters_not_bytes():
    validate_password_policy("ñ" * MIN_LENGTH, min_length=MIN_LENGTH)


def test_does_not_require_character_composition():
    validate_password_policy("solominusculas", min_length=MIN_LENGTH)


def test_rejects_new_password_equal_to_the_current_one():
    current_password = "ContraseñaActual123"

    with pytest.raises(PasswordPolicyError, match="distinta de la actual"):
        validate_password_policy(
            current_password,
            min_length=MIN_LENGTH,
            current_hash=hash_password(current_password),
        )


def test_accepts_new_password_different_from_the_current_one():
    validate_password_policy(
        "OtraContraseña456",
        min_length=MIN_LENGTH,
        current_hash=hash_password("ContraseñaActual123"),
    )


def test_temporary_password_has_default_length_of_16():
    assert len(generate_temporary_password(MIN_LENGTH)) == 16


def test_temporary_password_respects_a_larger_minimum():
    assert len(generate_temporary_password(20)) == 20


def test_temporary_password_never_exceeds_the_maximum():
    assert len(generate_temporary_password(500)) == MAX_LENGTH


def test_temporary_password_has_no_ambiguous_characters():
    for _ in range(200):
        password = generate_temporary_password(MIN_LENGTH)

        assert password.isalnum()
        assert not AMBIGUOUS_CHARACTERS & set(password)


def test_temporary_passwords_are_different_each_time():
    passwords = {generate_temporary_password(MIN_LENGTH) for _ in range(50)}

    assert len(passwords) == 50


def test_temporary_password_satisfies_the_policy():
    validate_password_policy(
        generate_temporary_password(MIN_LENGTH),
        min_length=MIN_LENGTH,
    )


def build_config(**overrides):
    return {
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        **overrides,
    }


@pytest.mark.parametrize(
    "invalid_value",
    [0, MIN_LENGTH_FLOOR - 1, MAX_LENGTH + 1],
)
def test_app_rejects_min_length_outside_the_allowed_range(invalid_value):
    with pytest.raises(RuntimeError, match="PASSWORD_MIN_LENGTH"):
        create_app(build_config(PASSWORD_MIN_LENGTH=invalid_value))


@pytest.mark.parametrize("valid_value", [MIN_LENGTH_FLOOR, 12, MAX_LENGTH])
def test_app_accepts_min_length_within_the_allowed_range(valid_value):
    app = create_app(build_config(PASSWORD_MIN_LENGTH=valid_value))

    assert app.config["PASSWORD_MIN_LENGTH"] == valid_value
