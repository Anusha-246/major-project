from flask import Blueprint, make_response, render_template, request

from routes.auth import login_required
from services.reports import build_report

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/reports")
@login_required
def index():
    kind = request.args.get("kind", "churn")
    report = build_report(kind)
    return render_template("reports.html", kind=kind, report=report)


@reports_bp.route("/reports/export")
@login_required
def export():
    kind = request.args.get("kind", "churn")
    report = build_report(kind)
    lines = [report["title"], ""]
    lines.append(",".join(report["columns"]))
    for row in report["rows"]:
        lines.append(",".join(str(row.get(c, "")) for c in report["columns"]))
    body = "\n".join(lines)
    resp = make_response(body)
    resp.headers["Content-Type"] = "text/csv"
    resp.headers["Content-Disposition"] = f"attachment; filename={kind}_report.csv"
    return resp
