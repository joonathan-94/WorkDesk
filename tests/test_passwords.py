from argon2 import Type

from src.workdesk.security import (
    hash_password,
    password_needs_rehash,
    passwords,
    verify_password,
)
from src.workdesk.security.passwords import build_password_hasher


def test_hash_password_uses_argon2id():
    password = "WorkDeskTest123!"

    password_hash = hash_password(password)

    assert password_hash != password
    assert password_hash.startswith("$argon2id$")


def test_verify_password_accepts_correct_password():
    password = "WorkDeskTest123!"
    password_hash = hash_password(password)

    assert verify_password(password_hash, password) is True


def test_verify_password_rejects_wrong_password():
    password_hash = hash_password("WorkDeskTest123!")

    assert (
        verify_password(
            password_hash,
            "ContraseñaIncorrecta123!",
        )
        is False
    )


def test_new_password_hash_does_not_need_rehash():
    password_hash = hash_password("WorkDeskTest123!")

    assert password_needs_rehash(password_hash) is False


def test_the_production_hasher_meets_the_owasp_minimum():
    """OWASP (Password Storage Cheat Sheet) pide para Argon2id al menos 19 MiB de memoria y
    2 pasadas. WorkDesk usa 64 MiB y 3 pasadas (`security/passwords.py`). Esta prueba mira
    el hasher de producción, no el de la suite (que es barato a propósito, ver
    `tests/conftest.py`): así abaratar los tests nunca puede abaratar la producción."""
    production = build_password_hasher()

    assert production.type is Type.ID
    assert production.memory_cost >= 19 * 1024
    assert production.time_cost >= 2
    assert production.parallelism >= 1
    assert (production.time_cost, production.memory_cost, production.parallelism) == (
        passwords.TIME_COST,
        passwords.MEMORY_COST_KIB,
        passwords.PARALLELISM,
    )


def test_the_suite_still_verifies_with_real_argon2id():
    # El hasher de la suite es más barato, pero es Argon2id de verdad: el login de los
    # tests recorre el mismo código que en producción.
    assert passwords.password_hasher.type is Type.ID
    assert hash_password("WorkDeskTest123!").startswith("$argon2id$")


def test_a_hash_with_other_parameters_is_rehashed_by_production():
    # Si los parámetros de producción cambian, los hashes antiguos se recalculan al iniciar
    # sesión: un hash de la suite (más barato) le parece antiguo a producción.
    assert build_password_hasher().check_needs_rehash(hash_password("WorkDeskTest123!"))
