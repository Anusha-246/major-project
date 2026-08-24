"""Dashboard and customer/branch analytics queries."""
from __future__ import annotations

import json

from database.db import query_all, query_one


def dashboard_payload() -> dict:
    kpis = query_one(
        """
        SELECT
            (SELECT COUNT(*) FROM customers) AS total_customers,
            (SELECT COUNT(*) FROM churn_predictions WHERE risk_level IN ('High','Critical')) AS at_risk,
            (SELECT COUNT(*) FROM churn_predictions WHERE prediction = 1) AS predicted_churners,
            (SELECT COUNT(*) FROM behaviour_deviations WHERE classification != 'Normal') AS behaviour_shifts,
            (SELECT COUNT(*) FROM behaviour_deviations WHERE classification = 'Critical Shift') AS critical_customers,
            (SELECT AVG(probability) FROM churn_predictions) AS avg_churn,
            (SELECT SUM(value_at_risk) FROM customer_value) AS value_at_risk
        """
    )
    churn_trend = query_all(
        """
        SELECT substr(cb.month_label, 1, 7) AS month,
               AVG(CASE WHEN c.churn_label = 1 THEN 1.0 ELSE 0.0 END) AS observed,
               AVG(p.probability) AS predicted
        FROM customer_behaviour cb
        JOIN customers c ON c.customer_id = cb.customer_id
        JOIN churn_predictions p ON p.customer_id = cb.customer_id
        GROUP BY cb.month_label
        ORDER BY cb.month_label
        """
    )
    shift_trend = query_all(
        """
        SELECT classification AS label, COUNT(*) AS n
        FROM behaviour_deviations
        GROUP BY classification
        """
    )
    risk_dist = query_all(
        """
        SELECT risk_level AS label, COUNT(*) AS n
        FROM churn_predictions
        GROUP BY risk_level
        """
    )
    branch_churn = query_all(
        """
        SELECT b.branch_name AS label,
               AVG(p.probability) AS churn_prob,
               AVG(CASE WHEN c.churn_label = 1 THEN 1.0 ELSE 0.0 END) AS churn_rate
        FROM customers c
        JOIN branches b ON b.branch_id = c.branch_id
        JOIN churn_predictions p ON p.customer_id = c.customer_id
        GROUP BY b.branch_id
        ORDER BY churn_rate DESC
        LIMIT 12
        """
    )
    reasons = query_all(
        """
        SELECT shap_top FROM churn_predictions WHERE prediction = 1 LIMIT 800
        """
    )
    reason_counts = {}
    for row in reasons:
        try:
            items = json.loads(row["shap_top"] or "[]")
        except json.JSONDecodeError:
            items = []
        if items:
            top = items[0]["feature"]
            reason_counts[top] = reason_counts.get(top, 0) + 1
    top_reasons = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)[:8]
    value_bins = query_all(
        """
        SELECT CASE
            WHEN predicted_future_value < 20000 THEN 'Under 20k'
            WHEN predicted_future_value < 50000 THEN '20k-50k'
            WHEN predicted_future_value < 100000 THEN '50k-100k'
            WHEN predicted_future_value < 200000 THEN '100k-200k'
            ELSE '200k+'
        END AS label,
        COUNT(*) AS n
        FROM customer_value
        GROUP BY label
        """
    )
    segments = query_all(
        """
        SELECT segment_name AS label, COUNT(*) AS n
        FROM customer_segments
        GROUP BY segment_name
        """
    )
    return {
        "kpis": kpis,
        "churn_trend": churn_trend,
        "shift_trend": shift_trend,
        "risk_dist": risk_dist,
        "branch_churn": branch_churn,
        "top_reasons": top_reasons,
        "value_bins": value_bins,
        "segments": segments,
    }


def customer_list(q, risk, shift, segment, sort, page, page_size=20):
    where = ["1=1"]
    params = []
    if q:
        where.append("(c.customer_id LIKE ? OR c.full_name LIKE ? OR c.city LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like, like])
    if risk:
        where.append("p.risk_level = ?")
        params.append(risk)
    if shift:
        where.append("d.classification = ?")
        params.append(shift)
    if segment:
        where.append("s.segment_name = ?")
        params.append(segment)
    order = {
        "churn_desc": "p.probability DESC",
        "shift_desc": "d.shift_score DESC",
        "value_desc": "v.predicted_future_value DESC",
        "name": "c.full_name",
    }.get(sort, "p.probability DESC")
    where_sql = " AND ".join(where)
    total = query_one(
        f"""
        SELECT COUNT(*) AS n
        FROM customers c
        JOIN churn_predictions p ON p.customer_id = c.customer_id
        JOIN behaviour_deviations d ON d.customer_id = c.customer_id
        JOIN customer_value v ON v.customer_id = c.customer_id
        JOIN customer_segments s ON s.customer_id = c.customer_id
        WHERE {where_sql}
        """,
        params,
    )["n"]
    offset = (page - 1) * page_size
    rows = query_all(
        f"""
        SELECT c.customer_id, c.full_name, c.city, c.branch_id, c.account_type,
               p.probability, p.prediction, p.risk_level,
               d.shift_score, d.classification,
               v.current_value, v.predicted_future_value, v.value_at_risk, v.is_high_value,
               s.segment_name
        FROM customers c
        JOIN churn_predictions p ON p.customer_id = c.customer_id
        JOIN behaviour_deviations d ON d.customer_id = c.customer_id
        JOIN customer_value v ON v.customer_id = c.customer_id
        JOIN customer_segments s ON s.customer_id = c.customer_id
        WHERE {where_sql}
        ORDER BY {order}
        LIMIT ? OFFSET ?
        """,
        params + [page_size, offset],
    )
    segments = query_all("SELECT DISTINCT segment_name FROM customer_segments ORDER BY segment_name")
    pages = max((total + page_size - 1) // page_size, 1)
    return {
        "rows": rows,
        "total": total,
        "page": page,
        "pages": pages,
        "q": q,
        "risk": risk,
        "shift": shift,
        "segment": segment,
        "sort": sort,
        "segments": segments,
        "error": None,
    }


def customer_360(customer_id: str):
    customer = query_one(
        """
        SELECT c.*,
               e.mobile_logins, e.internet_logins, e.app_sessions, e.last_login_days,
               e.nps_score, e.product_usage_score, e.digital_active,
               p.probability, p.prediction, p.risk_level, p.model_name, p.shap_top,
               d.shift_score, d.anomaly_score, d.classification, d.deviating_attributes, d.attribute_details,
               v.current_value, v.predicted_future_value, v.value_at_risk, v.is_high_value,
               s.segment_name, r.priority, r.strategy_title, r.actions, r.rationale,
               b.branch_name, b.region AS branch_region
        FROM customers c
        JOIN customer_engagement e ON e.customer_id = c.customer_id
        JOIN churn_predictions p ON p.customer_id = c.customer_id
        JOIN behaviour_deviations d ON d.customer_id = c.customer_id
        JOIN customer_value v ON v.customer_id = c.customer_id
        JOIN customer_segments s ON s.customer_id = c.customer_id
        JOIN retention_strategies r ON r.customer_id = c.customer_id
        JOIN branches b ON b.branch_id = c.branch_id
        WHERE c.customer_id = ?
        """,
        (customer_id,),
    )
    if not customer:
        return None
    history = query_all(
        "SELECT * FROM customer_behaviour WHERE customer_id = ? ORDER BY month_index",
        (customer_id,),
    )
    txns = query_all(
        "SELECT * FROM transactions WHERE customer_id = ? ORDER BY txn_date DESC LIMIT 40",
        (customer_id,),
    )
    shap_top = json.loads(customer["shap_top"] or "[]")
    actions = json.loads(customer["actions"] or "[]")
    details = json.loads(customer["attribute_details"] or "{}")
    deviating = json.loads(customer["deviating_attributes"] or "[]")
    return {
        "c": customer,
        "history": history,
        "txns": txns,
        "shap_top": shap_top,
        "actions": actions,
        "details": details,
        "deviating": deviating,
    }


def branch_overview():
    return query_all(
        """
        SELECT b.*,
               COUNT(c.customer_id) AS total_customers,
               AVG(CASE WHEN c.churn_label = 1 THEN 1.0 ELSE 0.0 END) AS churn_rate,
               SUM(CASE WHEN p.risk_level IN ('High','Critical') THEN 1 ELSE 0 END) AS high_risk,
               AVG(d.shift_score) AS avg_shift,
               SUM(CASE WHEN d.classification != 'Normal' THEN 1 ELSE 0 END) AS shifts,
               SUM(v.value_at_risk) AS value_at_risk
        FROM branches b
        LEFT JOIN customers c ON c.branch_id = b.branch_id
        LEFT JOIN churn_predictions p ON p.customer_id = c.customer_id
        LEFT JOIN behaviour_deviations d ON d.customer_id = c.customer_id
        LEFT JOIN customer_value v ON v.customer_id = c.customer_id
        GROUP BY b.branch_id
        ORDER BY churn_rate DESC
        """
    )


def region_overview():
    return query_all(
        """
        SELECT b.region,
               COUNT(c.customer_id) AS total_customers,
               AVG(CASE WHEN c.churn_label = 1 THEN 1.0 ELSE 0.0 END) AS churn_rate,
               AVG(d.shift_score) AS avg_shift,
               SUM(v.value_at_risk) AS value_at_risk
        FROM branches b
        JOIN customers c ON c.branch_id = b.branch_id
        JOIN behaviour_deviations d ON d.customer_id = c.customer_id
        JOIN customer_value v ON v.customer_id = c.customer_id
        GROUP BY b.region
        ORDER BY churn_rate DESC
        """
    )


def branch_detail(branch_id: str):
    branch = query_one("SELECT * FROM branches WHERE branch_id = ?", (branch_id,))
    stats = query_one(
        """
        SELECT COUNT(*) AS total_customers,
               AVG(CASE WHEN c.churn_label = 1 THEN 1.0 ELSE 0.0 END) AS churn_rate,
               SUM(CASE WHEN p.prediction = 1 THEN 1 ELSE 0 END) AS predicted_churners,
               SUM(CASE WHEN d.classification = 'Critical Shift' THEN 1 ELSE 0 END) AS critical_shifts,
               SUM(v.value_at_risk) AS value_at_risk
        FROM customers c
        JOIN churn_predictions p ON p.customer_id = c.customer_id
        JOIN behaviour_deviations d ON d.customer_id = c.customer_id
        JOIN customer_value v ON v.customer_id = c.customer_id
        WHERE c.branch_id = ?
        """,
        (branch_id,),
    )
    customers = query_all(
        """
        SELECT c.customer_id, c.full_name, p.probability, p.risk_level, d.shift_score, d.classification,
               v.value_at_risk, v.is_high_value
        FROM customers c
        JOIN churn_predictions p ON p.customer_id = c.customer_id
        JOIN behaviour_deviations d ON d.customer_id = c.customer_id
        JOIN customer_value v ON v.customer_id = c.customer_id
        WHERE c.branch_id = ?
        ORDER BY p.probability DESC
        LIMIT 80
        """,
        (branch_id,),
    )
    alerts = query_all(
        "SELECT * FROM alerts WHERE branch_id = ? ORDER BY id DESC LIMIT 20",
        (branch_id,),
    )
    return {"branch": branch, "stats": stats, "customers": customers, "alerts": alerts}
