from argon2 import Type

from src.workdesk.security import (
    hash_password,
    password_needs_rehash,
    verify_password,
)
from src.workdesk.security.passwords import password_hasher


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
    2 pasadas, o una combinación equivalente. WorkDesk usa los valores por defecto de
    argon2-cffi (64 MiB y 3 pasadas), muy por encima. Esta prueba impide bajarlos sin darse
    cuenta, por ejemplo al abaratar el hash solo para acelerar los tests."""
    assert password_hasher.type is Type.ID
    assert password_hasher.memory_cost >= 19 * 1024
    assert password_hasher.time_cost >= 2
    assert password_hasher.parallelism >= 1
