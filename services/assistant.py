"""Rule-based banking analytics assistant grounded in SQLite results."""
from __future__ import annotations

from database.db import query_all, query_one


def answer_question(question: str) -> str:
    q = question.lower()

    if any(k in q for k in ["hello", "hi ", "help"]):
        return (
            "I am the banking intelligence assistant. Ask about churn, behaviour shifts, "
            "customer value, high-risk customers, branch performance, retention, or alerts."
        )

    if "alert" in q:
        rows = query_all(
            "SELECT severity, alert_type, COUNT(*) AS n FROM alerts GROUP BY severity, alert_type ORDER BY n DESC"
        )
        if not rows:
            return "There are no alerts in the database."
        parts = [f"{r['n']} {r['severity']} alerts for {r['alert_type']}" for r in rows[:8]]
        return "Current alert summary: " + "; ".join(parts) + "."

    if "branch" in q and ("worst" in q or "high churn" in q or "performance" in q or "spike" in q):
        rows = query_all(
            """
            SELECT b.branch_name, b.region,
                   AVG(CASE WHEN c.churn_label = 1 THEN 1.0 ELSE 0.0 END) AS churn_rate,
                   SUM(v.value_at_risk) AS var
            FROM branches b
            JOIN customers c ON c.branch_id = b.branch_id
            JOIN customer_value v ON v.customer_id = c.customer_id
            GROUP BY b.branch_id
            ORDER BY churn_rate DESC
            LIMIT 5
            """
        )
        lines = [
            f"{r['branch_name']} ({r['region']}) churn {r['churn_rate']:.0%}, value at risk ₹{r['var']:,.0f}"
            for r in rows
        ]
        return "Highest-churn branches: " + "; ".join(lines) + "."

    if "region" in q:
        rows = query_all(
            """
            SELECT b.region,
                   AVG(CASE WHEN c.churn_label = 1 THEN 1.0 ELSE 0.0 END) AS churn_rate
            FROM branches b JOIN customers c ON c.branch_id = b.branch_id
            GROUP BY b.region ORDER BY churn_rate DESC
            """
        )
        return "Regional churn: " + ", ".join(f"{r['region']} {r['churn_rate']:.0%}" for r in rows) + "."

    if "retention" in q or "strategy" in q:
        rows = query_all(
            """
            SELECT r.strategy_title, COUNT(*) AS n
            FROM retention_strategies r
            JOIN churn_predictions p ON p.customer_id = r.customer_id
            WHERE p.probability >= 0.45
            GROUP BY r.strategy_title
            ORDER BY n DESC
            """
        )
        return "Top retention plays for at-risk customers: " + "; ".join(
            f"{r['strategy_title']} ({r['n']} customers)" for r in rows[:6]
        ) + "."

    if "high-value" in q or "high value" in q or "value at risk" in q or "customer value" in q:
        k = query_one(
            """
            SELECT SUM(value_at_risk) AS var,
                   SUM(CASE WHEN is_high_value = 1 THEN 1 ELSE 0 END) AS hv,
                   SUM(CASE WHEN is_high_value = 1 AND customer_id IN
                        (SELECT customer_id FROM churn_predictions WHERE probability >= 0.45) THEN 1 ELSE 0 END) AS hv_risk
            FROM customer_value
            """
        )
        return (
            f"Total customer value at risk is ₹{k['var']:,.0f}. "
            f"There are {k['hv']} high-value customers, of whom {k['hv_risk']} are also high churn-risk."
        )

    if "behaviour" in q or "shift" in q or "anomaly" in q:
        k = query_one(
            """
            SELECT
              SUM(CASE WHEN classification = 'Normal' THEN 1 ELSE 0 END) AS normal,
              SUM(CASE WHEN classification = 'Mild Shift' THEN 1 ELSE 0 END) AS mild,
              SUM(CASE WHEN classification = 'Significant Shift' THEN 1 ELSE 0 END) AS sig,
              SUM(CASE WHEN classification = 'Critical Shift' THEN 1 ELSE 0 END) AS crit,
              AVG(shift_score) AS avg_shift
            FROM behaviour_deviations
            """
        )
        return (
            f"Average behaviour-shift score is {k['avg_shift']:.1f}. "
            f"Classification: {k['normal']} normal, {k['mild']} mild, {k['sig']} significant, {k['crit']} critical. "
            "Shifts are computed from historical vs recent activity across transactions, deposits, "
            "withdrawals, ATM, mobile, internet, card, balance, digital engagement, complaints, and service activity."
        )

    if "reason" in q or "shap" in q or "factor" in q:
        return (
            "Individual churn reasons come from SHAP values on the XGBoost model. "
            "Typical adverse drivers in this demo are behaviour shift score, recent transaction drop, "
            "low digital engagement, complaints, last-login recency, and satisfaction. "
            "Open any customer profile to see positive vs negative feature impact."
        )

    if "model" in q or "accuracy" in q or "xgboost" in q or "evaluate" in q:
        rows = query_all("SELECT model_name, metrics_json, is_best FROM model_metrics WHERE model_type = 'churn'")
        import json

        parts = []
        for r in rows:
            m = json.loads(r["metrics_json"])
            tag = " (best ROC-AUC)" if r["is_best"] else ""
            parts.append(
                f"{r['model_name']}{tag}: accuracy {m['accuracy']:.2%}, recall {m['recall']:.2%}, ROC-AUC {m['roc_auc']:.3f}"
            )
        return "Churn model comparison: " + "; ".join(parts) + "."

    if "high-risk" in q or "high risk" in q or "churn" in q:
        k = query_one(
            """
            SELECT COUNT(*) AS n,
                   AVG(probability) AS avg_p,
                   SUM(prediction) AS pred
            FROM churn_predictions
            """
        )
        top = query_all(
            """
            SELECT c.customer_id, c.full_name, p.probability, d.shift_score
            FROM churn_predictions p
            JOIN customers c ON c.customer_id = p.customer_id
            JOIN behaviour_deviations d ON d.customer_id = c.customer_id
            ORDER BY p.probability DESC LIMIT 5
            """
        )
        names = ", ".join(f"{t['full_name']} ({t['probability']:.0%})" for t in top)
        return (
            f"Average churn probability is {k['avg_p']:.0%} with {k['pred']} predicted churners. "
            f"Highest-risk customers: {names}."
        )

    k = query_one(
        """
        SELECT (SELECT COUNT(*) FROM customers) AS customers,
               (SELECT COUNT(*) FROM branches) AS branches,
               (SELECT COUNT(*) FROM transactions) AS txns,
               (SELECT AVG(probability) FROM churn_predictions) AS avg_p
        """
    )
    return (
        f"The demo bank book has {k['customers']} customers across {k['branches']} branches "
        f"and {k['txns']} transactions. Average predicted churn is {k['avg_p']:.0%}. "
        "Ask about churn, behaviour shifts, value at risk, branches, retention, or alerts."
    )
