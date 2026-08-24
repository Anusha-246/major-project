import json
import os

from flask import Blueprint, render_template

from config import Config
from database.db import query_all
from routes.auth import login_required

models_bp = Blueprint("models", __name__)


@models_bp.route("/models")
@login_required
def evaluation():
    rows = query_all("SELECT * FROM model_metrics ORDER BY model_type, model_name")
    parsed = []
    for row in rows:
        item = dict(row)
        item["metrics"] = json.loads(row["metrics_json"])
        parsed.append(item)
    shap_global = {}
    path = os.path.join(Config.MODEL_DIR, "metrics.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as handle:
            blob = json.load(handle)
            shap_global = blob.get("shap_global") or {}
    labels = list(shap_global.keys())
    values = list(shap_global.values())
    pairs = sorted(zip(labels, values), key=lambda x: x[1], reverse=True)[:12]
    return render_template(
        "models.html",
        metrics=parsed,
        shap_labels=[p[0] for p in pairs],
        shap_values=[p[1] for p in pairs],
    )
