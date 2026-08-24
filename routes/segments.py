from flask import Blueprint, render_template

from database.db import query_all
from routes.auth import login_required

segments_bp = Blueprint("segments", __name__)


@segments_bp.route("/segments")
@login_required
def page():
    rows = query_all(
        """
        SELECT s.segment_name,
               COUNT(*) AS customers,
               AVG(p.probability) AS avg_churn,
               AVG(b.shift_score) AS avg_shift,
               AVG(v.predicted_future_value) AS avg_future_value,
               SUM(v.value_at_risk) AS value_at_risk
        FROM customer_segments s
        JOIN churn_predictions p ON p.customer_id = s.customer_id
        JOIN behaviour_deviations b ON b.customer_id = s.customer_id
        JOIN customer_value v ON v.customer_id = s.customer_id
        GROUP BY s.segment_name
        ORDER BY customers DESC
        """
    )
    return render_template("segments.html", segments=rows)


@segments_bp.route("/retention")
@login_required
def retention():
    rows = query_all(
        """
        SELECT r.*, c.full_name, c.branch_id, p.probability, p.risk_level, v.is_high_value, v.value_at_risk
        FROM retention_strategies r
        JOIN customers c ON c.customer_id = r.customer_id
        JOIN churn_predictions p ON p.customer_id = r.customer_id
        JOIN customer_value v ON v.customer_id = r.customer_id
        WHERE r.priority LIKE 'P1%' OR r.priority LIKE 'P2%'
        ORDER BY v.value_at_risk DESC
        LIMIT 250
        """
    )
    return render_template("retention.html", rows=rows)
