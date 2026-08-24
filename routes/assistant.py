from flask import Blueprint, jsonify, render_template, request

from routes.auth import login_required
from services.assistant import answer_question

assistant_bp = Blueprint("assistant", __name__)


@assistant_bp.route("/assistant")
@login_required
def page():
    return render_template("assistant.html")


@assistant_bp.route("/api/assistant", methods=["POST"])
@login_required
def api():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"answer": "Please ask a question about churn, behaviour, value, branches, or alerts."})
    return jsonify({"answer": answer_question(question)})
