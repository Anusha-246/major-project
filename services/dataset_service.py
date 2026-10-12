"""CSV upload validation, demo reload, and SQLite ingest."""
from __future__ import annotations

import os

import pandas as pd

from config import Config
from database.db import get_connection, query_one
from ml.train import load_core_frames, train_and_score
from scripts.initialize import load_frames, reset_database

REQUIRED = {
    "customers": [
        "customer_id",
        "full_name",
        "age",
        "gender",
        "city",
        "region",
        "branch_id",
        "account_type",
        "masked_account",
        "account_open_date",
        "tenure_months",
        "products_count",
        "credit_score",
        "occupation",
        "income_band",
        "satisfaction_score",
        "complaint_count",
        "service_request_count",
        "churn_label",
    ],
    "branches": ["branch_id", "branch_name", "region", "city", "manager_name", "opened_year", "staff_count"],
    "customer_behaviour": [
        "customer_id",
        "month_index",
        "month_label",
        "txn_frequency",
        "txn_amount",
        "deposits",
        "withdrawals",
        "atm_usage",
        "mobile_usage",
        "internet_usage",
        "card_usage",
        "avg_balance",
        "digital_engagement",
        "complaints",
        "service_activity",
    ],
    "customer_engagement": [
        "customer_id",
        "mobile_logins",
        "internet_logins",
        "app_sessions",
        "last_login_days",
        "nps_score",
        "product_usage_score",
        "digital_active",
    ],
    "transactions": ["txn_id", "customer_id", "branch_id", "txn_date", "txn_type", "channel", "amount"],
}

FORBIDDEN_TOKENS = ["cvv", "pin", "password", "card_number", "pan", "ifsc_secret"]


def dataset_stats() -> dict:
    def _count(table):
        row = query_one(f"SELECT COUNT(*) AS n FROM {table}")
        return row["n"] if row else 0

    try:
        return {
            "customers": _count("customers"),
            "branches": _count("branches"),
            "transactions": _count("transactions"),
            "behaviour": _count("customer_behaviour"),
            "engagement": _count("customer_engagement"),
            "predictions": _count("churn_predictions"),
        }
    except Exception:
        return {
            "customers": 0,
            "branches": 0,
            "transactions": 0,
            "behaviour": 0,
            "engagement": 0,
            "predictions": 0,
        }


def load_demo():
    from scripts.initialize import initialize_project

    return initialize_project()


def _save_upload(file_storage, name: str):
    if not file_storage or not file_storage.filename:
        return None
    os.makedirs(Config.UPLOAD_DIR, exist_ok=True)
    path = os.path.join(Config.UPLOAD_DIR, f"{name}.csv")
    file_storage.save(path)
    return path


def _validate_frame(name: str, df: pd.DataFrame) -> dict:
    issues = []
    cols_lower = [c.lower() for c in df.columns]
    for token in FORBIDDEN_TOKENS:
        if any(token in c for c in cols_lower):
            issues.append(f"Forbidden sensitive column pattern detected: {token}")
    missing_cols = [c for c in REQUIRED[name] if c not in df.columns]
    extra = [c for c in df.columns if c not in REQUIRED[name]]
    missing_values = int(df[REQUIRED[name]].isna().sum().sum()) if not missing_cols else int(df.isna().sum().sum())
    dupes = int(df.duplicated().sum())
    if name in ("customers", "branches", "transactions"):
        key = REQUIRED[name][0]
        if key in df.columns:
            dupes += int(df[key].duplicated().sum())
    return {
        "name": name,
        "rows": int(len(df)),
        "columns": list(df.columns),
        "missing_columns": missing_cols,
        "extra_columns": extra,
        "missing_values": missing_values,
        "duplicates": dupes,
        "issues": issues,
        "ok": not missing_cols and not issues,
    }


def validate_and_ingest(files: dict, retrain: bool = True) -> dict:
    frames = {}
    reports = []
    for key, storage in files.items():
        path = _save_upload(storage, key)
        if not path:
            continue
        df = pd.read_csv(path)
        report = _validate_frame(key, df)
        reports.append(report)
        if report["ok"]:
            frames[key] = df[REQUIRED[key]]
    if "customers" not in frames or "branches" not in frames or "customer_behaviour" not in frames:
        return {
            "ok": False,
            "error": "customers, branches, and behaviour CSVs are required.",
            "reports": reports,
        }
    months = frames["customer_behaviour"]["month_index"]
    if months.min() > 9 or months.max() < 10:
        return {
            "ok": False,
            "error": "customer_behaviour must include historical months (1-9) and recent months (10-12).",
            "reports": reports,
        }
    if "customer_engagement" not in frames:
        cust = frames["customers"]
        frames["customer_engagement"] = pd.DataFrame(
            {
                "customer_id": cust["customer_id"],
                "mobile_logins": 10,
                "internet_logins": 6,
                "app_sessions": 12,
                "last_login_days": 14,
                "nps_score": 60,
                "product_usage_score": 40,
                "digital_active": 1,
            }
        )
        reports.append({"name": "customer_engagement", "note": "Filled with defaults", "ok": True})
    if "transactions" not in frames:
        frames["transactions"] = pd.DataFrame(columns=REQUIRED["transactions"])

    reset_database()
    conn = get_connection()
    create_admin(conn)
    load_frames(conn, frames)
    conn.commit()
    conn.close()
    summary = None
    if retrain:
        customers, behaviour, engagement, branches = load_core_frames()
        summary = train_and_score(customers, behaviour, engagement, branches)
    return {"ok": True, "reports": reports, "summary": summary, "stats": dataset_stats()}


dataset_stats = dataset_stats
load_demo = load_demo
validate_and_ingest = validate_and_ingest
dataset_stats = dataset_stats
load_demo = load_demo
validate_and_ingest = validate_and_ingest
