"""Create SQLite database, load synthetic data, and train models."""
from __future__ import annotations

import os
import sqlite3




from config import Config
from database.db import get_connection, init_schema
from ml.data_generator import generate_all
from ml.train import train_and_score


def reset_database():
    """Create the schema and clear generated data without deleting accounts."""
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)

    conn = get_connection()

    tables = (
        "alerts",
        "model_metrics",
        "retention_strategies",
        "customer_segments",
        "customer_value",
        "churn_predictions",
        "behaviour_deviations",
        "customer_engagement",
        "transactions",
        "customer_behaviour",
        "customers",
        "branches",
    )

    try:
        init_schema(conn)

        for table in tables:
            conn.execute(f"DELETE FROM {table}")

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def _insert_df(conn, table, df, columns):
    placeholders = ",".join(["?"] * len(columns))
    cols = ",".join(columns)
    conn.executemany(
        f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",
        df[columns].itertuples(index=False, name=None),
    )


def load_frames(conn, frames: dict):
    _insert_df(
        conn,
        "branches",
        frames["branches"],
        ["branch_id", "branch_name", "region", "city", "manager_name", "opened_year", "staff_count"],
    )
    _insert_df(
        conn,
        "customers",
        frames["customers"],
        [
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
    )
    _insert_df(
        conn,
        "customer_behaviour",
        frames["customer_behaviour"],
        [
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
    )
    _insert_df(
        conn,
        "customer_engagement",
        frames["customer_engagement"],
        [
            "customer_id",
            "mobile_logins",
            "internet_logins",
            "app_sessions",
            "last_login_days",
            "nps_score",
            "product_usage_score",
            "digital_active",
        ],
    )
    _insert_df(
        conn,
        "transactions",
        frames["transactions"],
        ["txn_id", "customer_id", "branch_id", "txn_date", "txn_type", "channel", "amount"],
    )


def initialize_project(regenerate: bool = True):
    print("Creating SQLite database...")
    reset_database()
    conn = get_connection()
    print("Generating synthetic banking data (demo only)...")
    frames = generate_all()
    print(
        f"Loaded {len(frames['customers'])} customers, {len(frames['branches'])} branches, "
        f"{len(frames['transactions'])} transactions."
    )
    load_frames(conn, frames)
    conn.commit()
    conn.close()
    print("Training ML models (this can take a few minutes)...")
    from ml.train import load_core_frames

    customers, behaviour, engagement, branches = load_core_frames()
    summary = train_and_score(customers, behaviour, engagement, branches)
    print("Best churn model:", summary["best_churn_model"])
    print("Value model R2:", summary["value_model"]["r2"])
    print("K-Means silhouette:", summary["kmeans"]["silhouette"])
    print("Done. Database:", Config.DATABASE_PATH)
    return summary


if __name__ == "__main__":
    initialize_project()
