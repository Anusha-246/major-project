"""Personalized retention strategies and operational alerts."""
from __future__ import annotations

import json
from datetime import datetime

import pandas as pd


def _priority(row) -> str:
    if row["is_high_value"] == 1 and row["churn_probability"] >= 0.45:
        return "P1 - High Value At Risk"
    if row["churn_probability"] >= 0.70 or row["shift_score"] >= 75:
        return "P1 - Critical"
    if row["churn_probability"] >= 0.45 or row["shift_score"] >= 55:
        return "P2 - High"
    if row["churn_probability"] >= 0.25 or row["shift_score"] >= 30:
        return "P3 - Watch"
    return "P4 - Stable"


def _strategy(row) -> tuple[str, list[str], str]:
    reasons = []
    if row["shift_score"] >= 55:
        reasons.append("material behaviour shift")
    if row["complaint_count"] >= 2:
        reasons.append("complaint history")
    if row["last_login_days"] >= 21:
        reasons.append("digital inactivity")
    if row["satisfaction_score"] < 3:
        reasons.append("low satisfaction")
    if row["products_count"] <= 2:
        reasons.append("thin product holding")
    reason_text = ", ".join(reasons) if reasons else "standard relationship risk"

    if row["is_high_value"] == 1 and row["churn_probability"] >= 0.45:
        title = "Priority wealth retention desk"
        actions = [
            "Assign a relationship manager within 24 hours",
            "Offer a personalized rate or fee waiver on the primary product",
            "Schedule a portfolio review covering deposits, cards, and digital usage",
            "Follow up on open complaints with a same-day callback",
        ]
    elif row["shift_score"] >= 75:
        title = "Critical behaviour recovery journey"
        actions = [
            "Trigger an outbound call to confirm life-event or dissatisfaction",
            "Restore digital engagement with a guided app reactivation offer",
            "Review recent ATM/withdrawal spikes for service or fraud friction",
            "Provide a 90-day loyalty bonus on recurring deposits",
        ]
    elif row["complaint_count"] >= 2:
        title = "Service recovery and apology path"
        actions = [
            "Close open service requests with a documented resolution",
            "Issue a goodwill benefit proportional to complaint severity",
            "Survey satisfaction after resolution",
        ]
    elif row["last_login_days"] >= 21:
        title = "Digital re-engagement campaign"
        actions = [
            "Send a secure mobile banking reactivation reminder",
            "Offer assisted onboarding for internet banking",
            "Highlight bill-pay and transfer convenience features",
        ]
    elif row["products_count"] <= 2 and row["predicted_future_value"] > 0:
        title = "Cross-sell to deepen the relationship"
        actions = [
            "Recommend a suitable second product based on income band",
            "Bundle a debit card plus auto-savings goal",
            "Track uptake over the next two statement cycles",
        ]
    else:
        title = "Standard nurture and monitoring"
        actions = [
            "Keep the customer on quarterly review",
            "Monitor behaviour-shift score monthly",
            "Promote low-friction digital features",
        ]
    rationale = (
        f"Churn probability {row['churn_probability']:.0%}, behaviour shift {row['shift_score']:.0f}, "
        f"segment {row['segment_name']}, drivers: {reason_text}."
    )
    return title, actions, rationale


def build_retention_and_alerts(feat: pd.DataFrame, branches: pd.DataFrame):
    ret_rows = []
    for row in feat.to_dict("records"):
        title, actions, rationale = _strategy(row)
        ret_rows.append(
            (
                row["customer_id"],
                _priority(row),
                title,
                json.dumps(actions),
                rationale,
            )
        )
    retention_df = pd.DataFrame(
        ret_rows, columns=["customer_id", "priority", "strategy_title", "actions", "rationale"]
    )

    now = datetime.utcnow().isoformat() + "Z"
    alerts = []
    crit = feat[feat["shift_score"] >= 75]
    for row in crit.itertuples():
        alerts.append(
            (
                "Critical behaviour shift",
                "Critical",
                row.customer_id,
                row.branch_id,
                f"{row.customer_id} shows a critical behaviour shift (score {row.shift_score:.1f}).",
                now,
            )
        )
    high_churn = feat[feat["churn_probability"] >= 0.70]
    for row in high_churn.head(400).itertuples():
        alerts.append(
            (
                "High churn probability",
                "High",
                row.customer_id,
                row.branch_id,
                f"{row.customer_id} has churn probability {row.churn_probability:.0%}.",
                now,
            )
        )
    hvar = feat[(feat["is_high_value"] == 1) & (feat["churn_probability"] >= 0.45)]
    for row in hvar.itertuples():
        alerts.append(
            (
                "High-value customer at risk",
                "Critical",
                row.customer_id,
                row.branch_id,
                f"High-value customer {row.customer_id} is at risk; value at risk ₹{row.value_at_risk:,.0f}.",
                now,
            )
        )
    top_var = feat.nlargest(80, "value_at_risk")
    for row in top_var.itertuples():
        alerts.append(
            (
                "High customer value at risk",
                "High",
                row.customer_id,
                row.branch_id,
                f"Customer {row.customer_id} has estimated value at risk ₹{row.value_at_risk:,.0f}.",
                now,
            )
        )

    branch_churn = feat.groupby("branch_id").agg(
        customers=("customer_id", "count"),
        churners=("churn_label", "sum"),
        pred=("churn_probability", "mean"),
    )
    branch_churn["rate"] = branch_churn["churners"] / branch_churn["customers"]
    spike = branch_churn[branch_churn["rate"] >= max(0.28, branch_churn["rate"].quantile(0.90))]
    bmap = branches.set_index("branch_id")["branch_name"].to_dict()
    for bid, row in spike.iterrows():
        alerts.append(
            (
                "Branch churn spike",
                "High",
                None,
                bid,
                f"{bmap.get(bid, bid)} churn rate is {row['rate']:.0%} across {int(row['customers'])} customers.",
                now,
            )
        )
    alerts_df = pd.DataFrame(
        alerts, columns=["alert_type", "severity", "customer_id", "branch_id", "message", "created_at"]
    )
    return retention_df, alerts_df
