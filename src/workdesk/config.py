import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    APP_NAME = "WorkDesk"
    APP_ENV = os.getenv("APP_ENV", "development")
    APP_TIMEZONE = os.getenv("APP_TIMEZONE", "America/Santiago")
    SECRET_KEY = os.getenv("SECRET_KEY")