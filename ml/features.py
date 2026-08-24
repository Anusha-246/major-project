"""Feature assembly for churn, value, and segmentation models."""
from __future__ import annotations

import pandas as pd

CHURN_FEATURES = [
    "age",
    "tenure_months",
    "products_count",
    "credit_score",
    "satisfaction_score",
    "complaint_count",
    "service_request_count",
    "mobile_logins",
    "internet_logins",
    "last_login_days",
    "nps_score",
    "product_usage_score",
    "digital_active",
    "shift_score",
    "anomaly_score",
    "hist_txn_frequency",
    "recent_txn_frequency",
    "hist_avg_balance",
    "recent_avg_balance",
    "hist_digital_engagement",
    "recent_digital_engagement",
    "recent_complaints",
    "gender_code",
    "account_type_code",
    "income_band_code",
]


def _codes(series: pd.Series) -> pd.Series:
    return series.astype("category").cat.codes.astype(int)


def build_feature_frame(
    customers: pd.DataFrame,
    behaviour: pd.DataFrame,
    engagement: pd.DataFrame,
    shifts: pd.DataFrame,
) -> pd.DataFrame:
    hist = behaviour[behaviour["month_index"] <= 9].groupby("customer_id").agg(
        hist_txn_frequency=("txn_frequency", "mean"),
        hist_avg_balance=("avg_balance", "mean"),
        hist_digital_engagement=("digital_engagement", "mean"),
        hist_txn_amount=("txn_amount", "mean"),
    )
    recent = behaviour[behaviour["month_index"] >= 10].groupby("customer_id").agg(
        recent_txn_frequency=("txn_frequency", "mean"),
        recent_avg_balance=("avg_balance", "mean"),
        recent_digital_engagement=("digital_engagement", "mean"),
        recent_txn_amount=("txn_amount", "mean"),
        recent_complaints=("complaints", "mean"),
    )
    df = customers.merge(engagement, on="customer_id").merge(shifts, on="customer_id")
    df = df.merge(hist, on="customer_id").merge(recent, on="customer_id")
    df["gender_code"] = _codes(df["gender"])
    df["account_type_code"] = _codes(df["account_type"])
    df["income_band_code"] = _codes(df["income_band"])
    income_mult = df["income_band"].map({"Low": 0.7, "Medium": 1.0, "High": 1.6, "Premium": 2.4}).fillna(1.0)
    df["current_value"] = (
        df["recent_avg_balance"] * 0.04
        + df["recent_txn_amount"] * 0.12
        + df["products_count"] * 1800
        + df["tenure_months"] * 40
    ) * income_mult
    # Future value target: current value grown or decayed by engagement and churn risk
    growth = (
        0.08
        + 0.04 * (df["digital_active"] == 1).astype(float)
        + 0.03 * (df["satisfaction_score"] - 3) / 2
        - 0.25 * (df["churn_label"] == 1).astype(float)
        - 0.0018 * df["shift_score"]
    )
    df["future_value_target"] = (df["current_value"] * (1 + growth)).clip(lower=200)
    return df


CHURN_FEATURES = CHURN_FEATURES
build_feature_frame = build_feature_frame
