
"""CSV upload validation, demo reload, and SQLite ingestion."""

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
    "branches": [
        "branch_id",
        "branch_name",
        "region",
        "city",
        "manager_name",
        "opened_year",
        "staff_count",
    ],
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
    "transactions": [
        "txn_id",
        "customer_id",
        "branch_id",
        "txn_date",
        "txn_type",
        "channel",
        "amount",
    ],
}

FORBIDDEN_TOKENS = [
    "cvv",
    "pin",
    "password",
    "card_number",
    "pan",
    "ifsc_secret",
]


def dataset_stats() -> dict:
    """Return record counts for the main application tables."""

    tables = {
        "customers": "customers",
        "branches": "branches",
        "transactions": "transactions",
        "behaviour": "customer_behaviour",
        "engagement": "customer_engagement",
        "predictions": "churn_predictions",
    }

    stats = {}

    for key, table in tables.items():
        try:
            row = query_one(f"SELECT COUNT(*) AS n FROM {table}")
            stats[key] = int(row["n"]) if row else 0
        except Exception:
            stats[key] = 0

    return stats


def load_demo():
    """Regenerate synthetic demo data and retrain the models."""

    from scripts.initialize import initialize_project

    return initialize_project()


def _save_upload(file_storage, name: str):
    """Save an uploaded CSV using a controlled filename."""

    if not file_storage or not file_storage.filename:
        return None

    if name not in REQUIRED:
        raise ValueError(f"Unsupported dataset type: {name}")

    os.makedirs(Config.UPLOAD_DIR, exist_ok=True)

    path = os.path.join(Config.UPLOAD_DIR, f"{name}.csv")
    file_storage.save(path)

    return path


def _validate_frame(name: str, df: pd.DataFrame) -> dict:
    """Validate uploaded CSV columns, sensitive fields, and duplicates."""

    if name not in REQUIRED:
        return {
            "name": name,
            "rows": int(len(df)),
            "columns": list(df.columns),
            "missing_columns": [],
            "extra_columns": list(df.columns),
            "missing_values": 0,
            "duplicates": 0,
            "issues": [f"Unsupported dataset type: {name}"],
            "ok": False,
        }

    issues = []

    # Reject unexpected duplicate column names.
    if df.columns.duplicated().any():
        issues.append("Duplicate column names detected.")

    columns_lower = [str(column).strip().lower() for column in df.columns]

    for token in FORBIDDEN_TOKENS:
        if any(token in column for column in columns_lower):
            issues.append(
                f"Forbidden sensitive column pattern detected: {token}"
            )

    missing_columns = [
        column
        for column in REQUIRED[name]
        if column not in df.columns
    ]

    extra_columns = [
        column
        for column in df.columns
        if column not in REQUIRED[name]
    ]

    if missing_columns:
        missing_values = int(df.isna().sum().sum())
    else:
        missing_values = int(
            df[REQUIRED[name]].isna().sum().sum()
        )

    duplicates = int(df.duplicated().sum())

    # Primary identifiers must be unique for these tables.
    if name in ("customers", "branches", "transactions"):
        key = REQUIRED[name][0]

        if key in df.columns:
            duplicates += int(df[key].duplicated().sum())

    if df.empty:
        issues.append("The uploaded CSV contains no records.")

    if missing_values:
        issues.append(
            f"Missing values detected: {missing_values}."
        )

    if duplicates:
        issues.append(
            f"Duplicate records or identifiers detected: {duplicates}."
        )

    ok = (
        not missing_columns
        and not issues
    )

    return {
        "name": name,
        "rows": int(len(df)),
        "columns": list(df.columns),
        "missing_columns": missing_columns,
        "extra_columns": extra_columns,
        "missing_values": missing_values,
        "duplicates": duplicates,
        "issues": issues,
        "ok": ok,
    }


def validate_and_ingest(files: dict, retrain: bool = True) -> dict:
    """Validate uploaded CSV files and load them into SQLite."""

    frames = {}
    reports = []

    if not files:
        return {
            "ok": False,
            "error": "Select the required CSV files before uploading.",
            "reports": [],
        }

    # Validate each uploaded dataset.
    for key, storage in files.items():
        if key not in REQUIRED:
            reports.append(
                {
                    "name": str(key),
                    "ok": False,
                    "issues": [
                        f"Unsupported dataset type: {key}"
                    ],
                }
            )
            continue

        path = _save_upload(storage, key)

        if not path:
            continue

        try:
            df = pd.read_csv(path)
        except (OSError, UnicodeDecodeError, pd.errors.ParserError) as exc:
            reports.append(
                {
                    "name": key,
                    "ok": False,
                    "issues": [f"Unable to read CSV: {exc}"],
                }
            )
            continue

        report = _validate_frame(key, df)
        reports.append(report)

        if report["ok"]:
            frames[key] = df[REQUIRED[key]].copy()

    required_datasets = {
        "customers",
        "branches",
        "customer_behaviour",
    }

    missing_datasets = sorted(required_datasets - set(frames))

    if missing_datasets:
        return {
            "ok": False,
            "error": (
                "Valid CSV files are required for: "
                + ", ".join(missing_datasets)
                + "."
            ),
            "reports": reports,
        }

    # Validate the historical and recent behaviour periods.
    behaviour = frames["customer_behaviour"]

    try:
        behaviour["month_index"] = pd.to_numeric(
            behaviour["month_index"],
            errors="raise",
        )
    except (ValueError, TypeError):
        return {
            "ok": False,
            "error": "month_index must contain numeric month values.",
            "reports": reports,
        }

    if (
        behaviour["month_index"].min() > 9
        or behaviour["month_index"].max() < 10
    ):
        return {
            "ok": False,
            "error": (
                "customer_behaviour must include historical months "
                "(1-9) and recent months (10-12)."
            ),
            "reports": reports,
        }

    if not behaviour["month_index"].between(1, 12).all():
        return {
            "ok": False,
            "error": "month_index values must be between 1 and 12.",
            "reports": reports,
        }

    # Ensure every customer references an uploaded branch.
    branch_ids = set(frames["branches"]["branch_id"])
    customer_branch_ids = set(frames["customers"]["branch_id"])

    unknown_branches = customer_branch_ids - branch_ids

    if unknown_branches:
        return {
            "ok": False,
            "error": (
                "Some customers reference branch IDs that are missing "
                "from the branches CSV."
            ),
            "reports": reports,
        }

    # Ensure behaviour records refer to uploaded customers.
    customer_ids = set(frames["customers"]["customer_id"])
    behaviour_customer_ids = set(behaviour["customer_id"])

    if behaviour_customer_ids - customer_ids:
        return {
            "ok": False,
            "error": (
                "The customer_behaviour CSV contains customer IDs "
                "that are missing from the customers CSV."
            ),
            "reports": reports,
        }

    # Create default engagement values when no engagement CSV is uploaded.
    if "customer_engagement" not in frames:
        customers = frames["customers"]

        frames["customer_engagement"] = pd.DataFrame(
            {
                "customer_id": customers["customer_id"],
                "mobile_logins": 10,
                "internet_logins": 6,
                "app_sessions": 12,
                "last_login_days": 14,
                "nps_score": 60,
                "product_usage_score": 40,
                "digital_active": 1,
            }
        )

        reports.append(
            {
                "name": "customer_engagement",
                "note": "Filled with synthetic default values.",
                "ok": True,
            }
        )

    # Ensure every engagement record references a known customer.
    engagement_ids = set(
        frames["customer_engagement"]["customer_id"]
    )

    if engagement_ids - customer_ids:
        return {
            "ok": False,
            "error": (
                "The customer_engagement CSV contains customer IDs "
                "that are missing from the customers CSV."
            ),
            "reports": reports,
        }

    # Transactions are optional. Use an empty correctly shaped DataFrame.
    if "transactions" not in frames:
        frames["transactions"] = pd.DataFrame(
            columns=REQUIRED["transactions"]
        )

    transaction_customer_ids = set(
        frames["transactions"]["customer_id"]
    )

    if transaction_customer_ids - customer_ids:
        return {
            "ok": False,
            "error": (
                "The transactions CSV contains customer IDs "
                "that are missing from the customers CSV."
            ),
            "reports": reports,
        }

    transaction_branch_ids = set(
        frames["transactions"]["branch_id"]
    )

    if transaction_branch_ids - branch_ids:
        return {
            "ok": False,
            "error": (
                "The transactions CSV contains branch IDs "
                "that are missing from the branches CSV."
            ),
            "reports": reports,
        }

    # WARNING:
    # reset_database() clears generated banking data before loading.
    # Keep the reset function in scripts/initialize.py configured to
    # preserve banks and users if you want to retain registered accounts.
    reset_database()

    conn = get_connection()

    try:
        load_frames(conn, frames)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    summary = None

    if retrain:
        customers, behaviour, engagement, branches = load_core_frames()

        summary = train_and_score(
            customers,
            behaviour,
            engagement,
            branches,
        )

    return {
        "ok": True,
        "reports": reports,
        "summary": summary,
        "stats": dataset_stats(),
    }
