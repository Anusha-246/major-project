from flask import Blueprint, flash, redirect, render_template, request, url_for

from routes.auth import login_required
from services.dataset_service import dataset_stats, load_demo, validate_and_ingest

dataset_bp = Blueprint("dataset", __name__)


@dataset_bp.route("/dataset", methods=["GET", "POST"])
@login_required
def manage():
    report = None
    if request.method == "POST":
        action = request.form.get("action")
        if action == "demo":
            summary = load_demo()
            flash("Demo dataset loaded and models retrained.", "success")
            report = {"kind": "retrain", "summary": summary}
        elif action == "upload":
            files = {
                "customers": request.files.get("customers_csv"),
                "branches": request.files.get("branches_csv"),
                "transactions": request.files.get("transactions_csv"),
                "customer_behaviour": request.files.get("behaviour_csv"),
                "customer_engagement": request.files.get("engagement_csv"),
            }
            report = validate_and_ingest(files, retrain=request.form.get("retrain") == "on")
            if report.get("ok"):
                flash("Dataset ingested successfully.", "success")
            else:
                flash(report.get("error", "Upload failed."), "danger")
    return render_template("dataset.html", stats=dataset_stats(), report=report)
