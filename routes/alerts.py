from flask import Blueprint, redirect, render_template, request, url_for

from database.db import execute, query_all
from routes.auth import login_required

alerts_bp = Blueprint("alerts", __name__)


@alerts_bp.route("/alerts")
@login_required
def list_alerts():
    severity = request.args.get("severity", "")
    sql = "SELECT * FROM alerts"
    params = []
    if severity:
        sql += " WHERE severity = ?"
        params.append(severity)
    sql += " ORDER BY id DESC LIMIT 800"
    rows = query_all(sql, params)
    return render_template("alerts.html", alerts=rows, severity=severity)


@alerts_bp.route("/alerts/<int:alert_id>/read")
@login_required
def mark_read(alert_id):
    execute("UPDATE alerts SET is_read = 1 WHERE id = ?", (alert_id,))
    return redirect(url_for("alerts.list_alerts"))
