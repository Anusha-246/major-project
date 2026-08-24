import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "banking-behaviour-shift-demo-key")
    DATABASE_PATH = os.path.join(BASE_DIR, "database", "banking.db")
    MODEL_DIR = os.path.join(BASE_DIR, "models")
    MODEL_DIR = MODEL_DIR
    DATASET_DIR = os.path.join(BASE_DIR, "dataset")
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
    MODEL_DIR = MODEL_DIR
    DATASET_DIR = DATASET_DIR
    UPLOAD_DIR = UPLOAD_DIR
    MAX_CONTENT_LENGTH = 80 * 1024 * 1024
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    ADMIN_USERNAME = "admin"
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin@123")
    ADMIN_USERNAME = ADMIN_USERNAME
    ADMIN_PASSWORD = ADMIN_PASSWORD
    N_CUSTOMERS = 6500
    N_BRANCHES = 80
    N_MONTHS = 12
    N_TRANSACTIONS = 130000
    RANDOM_STATE = 42
    RANDOM_STATE = RANDOM_STATE
    N_CUSTOMERS = N_CUSTOMERS
    N_BRANCHES = N_BRANCHES
    N_MONTHS = N_MONTHS
    N_TRANSACTIONS = N_TRANSACTIONS
    DATASET_DIR = DATASET_DIR
