import os

from dotenv import load_dotenv

load_dotenv()


def get_bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


class Config:
    APP_NAME = "WorkDesk"
    APP_ENV = os.getenv("APP_ENV", "development")
    APP_TIMEZONE = os.getenv("APP_TIMEZONE", "America/Santiago")

    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")

    LOGIN_MAX_FAILED_ATTEMPTS = int(
        os.getenv("LOGIN_MAX_FAILED_ATTEMPTS", "5")
    )

    LOGIN_LOCK_MINUTES = int(
        os.getenv("LOGIN_LOCK_MINUTES", "15")
    )

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = get_bool_env(
        "SESSION_COOKIE_SECURE",
        default=False,
    )