"""Downloadable analytical reports."""
from __future__ import annotations

import json

from database.db import query_all


def build_report(kind: str) -> dict:
    kind = (kind or "churn").lower()
    if kind == "behaviour":
        rows = query_all(
            """
            SELECT c.customer_id, c.full_name, c.branch_id, d.shift_score, d.anomaly_score,
                   d.classification, d.deviating_attributes
            FROM behaviour_deviations d
            JOIN customers c ON c.customer_id = d.customer_id
            ORDER BY d.shift_score DESC
            LIMIT 500
            """
        )
        return {
            "title": "Behaviour Shift Report",
            "columns": ["customer_id", "full_name", "branch_id", "shift_score", "anomaly_score", "classification", "deviating_attributes"],
            "rows": rows,
            "summary": f"{len(rows)} highest behaviour-shift customers.",
        }
    if kind == "value":
        rows = query_all(
            """
            SELECT c.customer_id, c.full_name, v.current_value, v.predicted_future_value,
                   v.value_at_risk, v.is_high_value, p.probability
            FROM customer_value v
            JOIN customers c ON c.customer_id = v.customer_id
            JOIN churn_predictions p ON p.customer_id = c.customer_id
            ORDER BY v.value_at_risk DESC
            LIMIT 500
            """
        )
        return {
            "title": "Customer Value Report",
            "columns": ["customer_id", "full_name", "current_value", "predicted_future_value", "value_at_risk", "is_high_value", "probability"],
            "rows": rows,
            "summary": "Customers ranked by predicted value at risk.",
        }
    if kind == "branch":
        rows = query_all(
            """
            SELECT b.branch_id, b.branch_name, b.region, COUNT(c.customer_id) AS customers,
                   AVG(CASE WHEN c.churn_label = 1 THEN 1.0 ELSE 0.0 END) AS churn_rate,
                   AVG(d.shift_score) AS avg_shift, SUM(v.value_at_risk) AS value_at_risk
            FROM branches b
            JOIN customers c ON c.branch_id = b.branch_id
            JOIN behaviour_deviations d ON d.customer_id = c.customer_id
            JOIN customer_value v ON v.customer_id = c.customer_id
            GROUP BY b.branch_id
            ORDER BY churn_rate DESC
            """
        )
        return {
            "title": "Branch Analysis Report",
            "columns": ["branch_id", "branch_name", "region", "customers", "churn_rate", "avg_shift", "value_at_risk"],
            "rows": rows,
            "summary": "Branch comparison of churn, behaviour shift, and value at risk.",
        }
    if kind == "highrisk":
        rows = query_all(
            """
            SELECT c.customer_id, c.full_name, c.branch_id, p.probability, p.risk_level,
                   d.classification, v.is_high_value, v.value_at_risk
            FROM churn_predictions p
            JOIN customers c ON c.customer_id = p.customer_id
            JOIN behaviour_deviations d ON d.customer_id = c.customer_id
            JOIN customer_value v ON v.customer_id = c.customer_id
            WHERE p.risk_level IN ('High','Critical')
            ORDER BY p.probability DESC
            LIMIT 500
            """
        )
        return {
            "title": "High-Risk Customer Report",
            "columns": ["customer_id", "full_name", "branch_id", "probability", "risk_level", "classification", "is_high_value", "value_at_risk"],
            "rows": rows,
            "summary": "Customers with high or critical predicted churn risk.",
        }
    if kind == "retention":
        rows = query_all(
            """
            SELECT r.customer_id, c.full_name, r.priority, r.strategy_title, r.rationale, v.value_at_risk
            FROM retention_strategies r
            JOIN customers c ON c.customer_id = r.customer_id
            JOIN customer_value v ON v.customer_id = r.customer_id
            ORDER BY v.value_at_risk DESC
            LIMIT 400
            """
        )
        return {
            "title": "Retention Strategy Report",
            "columns": ["customer_id", "full_name", "priority", "strategy_title", "rationale", "value_at_risk"],
            "rows": rows,
            "summary": "Personalized retention actions prioritized by value at risk.",
        }
    if kind == "models":
        raw = query_all("SELECT model_type, model_name, metrics_json, is_best FROM model_metrics")
        rows = []
        for item in raw:
            metrics = json.loads(item["metrics_json"])
            flat = {"model_type": item["model_type"], "model_name": item["model_name"], "is_best": item["is_best"]}
            flat.update({k: v for k, v in metrics.items() if not isinstance(v, (dict, list))})
            rows.append(flat)
        cols = sorted({k for row in rows for k in row.keys()})
        return {
            "title": "Model Evaluation Report",
            "columns": cols,
            "rows": rows,
            "summary": "Accuracy, precision, recall, F1, ROC-AUC, PR-AUC for churn; MAE/RMSE/R2 for value; silhouette for K-Means.",
        }
    rows = query_all(
        """
        SELECT c.customer_id, c.full_name, c.branch_id, p.probability, p.prediction, p.risk_level,
               c.churn_label, d.shift_score
        FROM churn_predictions p
        JOIN customers c ON c.customer_id = p.customer_id
        JOIN behaviour_deviations d ON d.customer_id = c.customer_id
        ORDER BY p.probability DESC
        LIMIT 500
        """
    )
    return {
        "title": "Churn Report",
        "columns": ["customer_id", "full_name", "branch_id", "probability", "prediction", "risk_level", "churn_label", "shift_score"],
        "rows": rows,
        "summary": "Predicted churn probability and observed labels.",
    }
