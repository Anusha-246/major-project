from flask import Blueprint, abort, render_template, request

from database.db import query_all, query_one
from routes.auth import login_required
from services.analytics import customer_360, customer_list

customers_bp = Blueprint("customers", __name__)


@customers_bp.route("/customers")
@login_required
def list_customers():
    q = request.args.get("q", "").strip()
    risk = request.args.get("risk", "")
    shift = request.args.get("shift", "")
    segment = request.args.get("segment", "")
    sort = request.args.get("sort", "churn_desc")
    page = max(int(request.args.get("page", 1)), 1)
    data = customer_list(q, risk, shift, segment, sort, page)
    return render_template("customers.html", **data)


@customers_bp.route("/customers/<customer_id>")
@login_required
def detail(customer_id):
    payload = customer_360(customer_id)
    if not payload:
        abort(404)
    return render_template("customer_detail.html", **payload)
