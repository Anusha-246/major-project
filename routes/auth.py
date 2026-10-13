from functools import wraps

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from werkzeug.security import check_password_hash, generate_password_hash
from database.db import query_one, execute

auth_bp = Blueprint("auth", __name__)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):

        if not session.get("user_id"):
            session.clear()
            return redirect(url_for("auth.login"))

        return view(*args, **kwargs)

    return wrapped



@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        bank_name = (request.form.get("bank_name") or "").strip()
        bank_id = (request.form.get("bank_id") or "").strip()
        official_email = (
            request.form.get("official_email") or ""
        ).strip()
        admin_name = (request.form.get("admin_name") or "").strip()
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""

        if not all([
            bank_name, bank_id, official_email,
            admin_name, username, password, confirm_password
        ]):
            flash("Please fill in all fields.", "danger")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        if len(password) < 8:
            flash(
                "Password must contain at least 8 characters.",
                "danger",
            )
            return render_template("register.html")

        if query_one(
            "SELECT id FROM banks WHERE bank_id = ?", (bank_id,)
        ):
            flash("Bank ID is already registered.", "danger")
            return render_template("register.html")

        if query_one(
            "SELECT id FROM banks WHERE official_email = ?",
            (official_email,),
        ):
            flash("Official email is already registered.", "danger")
            return render_template("register.html")

        if query_one(
            "SELECT id FROM users WHERE username = ?", (username,)
        ):
            flash("Username is already taken.", "danger")
            return render_template("register.html")

        try:
            from datetime import datetime, timezone

            created_at = datetime.now(timezone.utc).isoformat()

            execute(
                """
                INSERT INTO banks
                (bank_name, bank_id, official_email, status, created_at)
                VALUES (?, ?, ?, 'Approved', ?)
                """,
                (bank_name, bank_id, official_email, created_at),
            )

            bank = query_one(
                "SELECT id FROM banks WHERE bank_id = ?",
                (bank_id,),
            )

            execute(
                """
                INSERT INTO users
                (bank_id, admin_name, username, password_hash,
                 role, created_at)
                VALUES (?, ?, ?, ?, 'admin', ?)
                """,
                (
                    bank["id"],
                    admin_name,
                    username,
                    generate_password_hash(password),
                    created_at,
                ),
            )

            flash(
                "Bank registration successful. You can now sign in.",
                "success",
            )
            return redirect(url_for("auth.login"))

        except Exception:
            current_app.logger.exception("Bank registration failed")
            flash("Registration failed. Please try again.", "danger")

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        user = query_one(
            """
            SELECT
                users.id,
                users.bank_id,
                users.admin_name,
                users.username,
                users.password_hash,
                users.role,
                banks.bank_name,
                banks.status
            FROM users
            JOIN banks ON users.bank_id = banks.id
            WHERE users.username = ?
            """,
            (username,)
        )

        if user and check_password_hash(user["password_hash"], password):

            if user["status"] != "Approved":
                flash(
                    "Your bank organization is not approved for access.",
                    "warning"
                )
                return render_template("login.html")

            session.clear()
            session.permanent = False

            session["user_id"] = user["id"]
            session["bank_id"] = user["bank_id"]
            session["bank_name"] = user["bank_name"]
            session["admin_name"] = user["admin_name"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            return redirect(url_for("dashboard.index"))

        flash("Invalid administrator credentials.", "danger")

    return render_template("login.html")




@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("official_email") or "").strip()

        user = query_one(
            """
            SELECT users.id
            FROM users
            JOIN banks ON users.bank_id = banks.id
            WHERE users.username = ?
              AND LOWER(banks.official_email) = LOWER(?)
            """,
            (username, email),
        )

        if not user:
            flash(
                "Username or official email is incorrect.",
                "danger",
            )
            return render_template("forgot_password.html")

        # No email is sent. Continue in the current browser session.
        session["reset_user_id"] = user["id"]

        return redirect(url_for("auth.reset_password"))

    return render_template("forgot_password.html")


@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    user_id = session.get("reset_user_id")

    if not user_id:
        flash(
            "Please verify your username and official email first.",
            "warning",
        )
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("reset_password.html")

        if len(password) < 8:
            flash(
                "Password must contain at least 8 characters.",
                "danger",
            )
            return render_template("reset_password.html")

        user = query_one(
            "SELECT id FROM users WHERE id = ?",
            (user_id,),
        )

        if not user:
            session.pop("reset_user_id", None)
            flash("Account not found.", "danger")
            return redirect(url_for("auth.forgot_password"))

        execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (generate_password_hash(password), user_id),
        )

        session.pop("reset_user_id", None)

        flash(
            "Password reset successful. Please sign in.",
            "success",
        )
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))