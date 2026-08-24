from flask import Blueprint, render_template

from routes.auth import login_required
from services.analytics import branch_detail, branch_overview, region_overview

branches_bp = Blueprint("branches", __name__)


@branches_bp.route("/branches")
@login_required
def list_branches():
    return render_template("branches.html", branches=branch_overview(), regions=region_overview())


@branches_bp.route("/branches/<branch_id>")
@login_required
def detail(branch_id):
    payload = branch_detail(branch_id)
    return render_template("branch_detail.html", **payload)
