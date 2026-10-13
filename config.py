
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    DATABASE_PATH = os.path.join(
        BASE_DIR, "database", "banking.db"
    )

    MODEL_DIR = os.path.join(BASE_DIR, "models")
    DATASET_DIR = os.path.join(BASE_DIR, "dataset")
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

    # Email / SMTP settings
    MAIL_SERVER = os.environ.get(
        "MAIL_SERVER", "smtp.gmail.com"
    )
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USE_TLS = (
        os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    )
    MAIL_USE_SSL = (
        os.environ.get("MAIL_USE_SSL", "false").lower() == "true"
    )

    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = (
        os.environ.get("MAIL_DEFAULT_SENDER") or MAIL_USERNAME
    )

    # Password-reset links expire after 30 minutes
    PASSWORD_RESET_MAX_AGE_SECONDS = 1800

    MAX_CONTENT_LENGTH = 80 * 1024 * 1024

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = (
        os.environ.get("SESSION_COOKIE_SECURE", "false").lower()
        == "true"
    )
    SESSION_PERMANENT = False

    N_CUSTOMERS = 10000
    N_BRANCHES = 80
    N_MONTHS = 12
    N_TRANSACTIONS = 200000

    RANDOM_STATE = 42
