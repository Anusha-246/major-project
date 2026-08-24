from flask import Blueprint, render_template

from routes.auth import login_required
from services.analytics import dashboard_payload

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    payload = dashboard_payload()
    return render_template("dashboard.html", **payload)
