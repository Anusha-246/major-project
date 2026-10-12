import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "banking-behaviour-shift-demo-key"
    )

    DATABASE_PATH = os.path.join(
        BASE_DIR, "database", "banking.db"
    )

    MODEL_DIR = os.path.join(BASE_DIR, "models")
    DATASET_DIR = os.path.join(BASE_DIR, "dataset")
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

    MAX_CONTENT_LENGTH = 80 * 1024 * 1024

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    SESSION_PERMANENT = False
    N_CUSTOMERS = 10000
    N_BRANCHES = 80
    N_MONTHS = 12
    N_TRANSACTIONS = 200000

    RANDOM_STATE = 42