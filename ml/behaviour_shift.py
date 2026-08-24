"""Cross-attribute behaviour shift scoring and Isolation Forest anomaly detection."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

ATTRIBUTE_COLS = [
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
]

# Higher weight on activity, balance, and digital drop; complaints rise is inverted
WEIGHTS = {
    "txn_frequency": 1.2,
    "txn_amount": 1.1,
    "deposits": 1.0,
    "withdrawals": 0.8,
    "atm_usage": 0.7,
    "mobile_usage": 1.1,
    "internet_usage": 1.0,
    "card_usage": 0.9,
    "avg_balance": 1.3,
    "digital_engagement": 1.2,
    "complaints": 1.0,
    "service_activity": 0.6,
}


def _pct_dev(hist: pd.Series, recent: pd.Series) -> pd.Series:
    return (recent - hist) / (hist.abs() + 1.0)


def build_shift_table(behaviour: pd.DataFrame) -> pd.DataFrame:
    hist = behaviour[behaviour["month_index"] <= 9].groupby("customer_id")[ATTRIBUTE_COLS].mean()
    recent = behaviour[behaviour["month_index"] >= 10].groupby("customer_id")[ATTRIBUTE_COLS].mean()
    hist, recent = hist.align(recent, join="inner")
    records = []
    for col in ATTRIBUTE_COLS:
        rel = _pct_dev(hist[col], recent[col])
        # Complaints/service: increase is a negative behaviour change
        if col in ("complaints", "service_activity", "withdrawals", "atm_usage"):
            signed = rel  # positive = increase
            adverse = rel.clip(lower=0)
        else:
            signed = rel  # negative = decline
            adverse = (-rel).clip(lower=0)
        records.append(
            pd.DataFrame(
                {
                    "customer_id": hist.index,
                    "attribute": col,
                    "historical": hist[col].values,
                    "recent": recent[col].values,
                    "relative_change": rel.values,
                    "adverse_deviation": adverse.values,
                    "signed_change": signed.values,
                }
            )
        )
    long_df = pd.concat(records, ignore_index=True)
    return long_df, hist, recent


def classify_shift(score: float) -> str:
    if score >= 75:
        return "Critical Shift"
    if score >= 55:
        return "Significant Shift"
    if score >= 30:
        return "Mild Shift"
    return "Normal"


def compute_behaviour_shifts(behaviour: pd.DataFrame, random_state: int = 42) -> pd.DataFrame:
    long_df, hist, recent = build_shift_table(behaviour)
    pivot_adv = long_df.pivot(index="customer_id", columns="attribute", values="adverse_deviation").fillna(0)
    pivot_signed = long_df.pivot(index="customer_id", columns="attribute", values="signed_change").fillna(0)

    weighted = np.zeros(len(pivot_adv))
    wsum = 0.0
    for col in ATTRIBUTE_COLS:
        w = WEIGHTS[col]
        weighted += pivot_adv[col].values * w
        wsum += w
    raw_score = weighted / wsum
    shift_score = np.clip(raw_score * 100.0, 0, 100)

    iso_features = pivot_signed[ATTRIBUTE_COLS].values
    iso = IsolationForest(n_estimators=200, contamination=0.08, random_state=random_state)
    iso.fit(iso_features)
    raw_anom = -iso.score_samples(iso_features)
    anom_min, anom_max = raw_anom.min(), raw_anom.max()
    anomaly_score = (raw_anom - anom_min) / (anom_max - anom_min + 1e-9) * 100

    # Blend isolation forest into final displayed shift score
    blended = np.clip(0.75 * shift_score + 0.25 * anomaly_score, 0, 100)

    rows = []
    for i, cid in enumerate(pivot_adv.index):
        attr_vals = {col: float(pivot_adv.iloc[i][col]) for col in ATTRIBUTE_COLS}
        top = sorted(attr_vals.items(), key=lambda x: x[1], reverse=True)
        deviating = [name for name, val in top if val >= 0.18][:6]
        details = {}
        for col in ATTRIBUTE_COLS:
            details[col] = {
                "historical": round(float(hist.loc[cid, col]), 2),
                "recent": round(float(recent.loc[cid, col]), 2),
                "relative_change": round(float(pivot_signed.loc[cid, col]), 4),
                "adverse_deviation": round(float(pivot_adv.loc[cid, col]), 4),
            }
        rows.append(
            {
                "customer_id": cid,
                "shift_score": round(float(blended[i]), 2),
                "anomaly_score": round(float(anomaly_score[i]), 2),
                "classification": classify_shift(float(blended[i])),
                "deviating_attributes": json.dumps(deviating),
                "attribute_details": json.dumps(details),
            }
        )
    result = pd.DataFrame(rows)
    return result, iso, ATTRIBUTE_COLS
