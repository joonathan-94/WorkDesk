from src.workdesk.security import (
    hash_password,
    password_needs_rehash,
    verify_password,
)


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