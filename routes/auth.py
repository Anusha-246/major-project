from datetime import datetime, timezone
from functools import wraps

from flask import (
    Blueprint, current_app, flash, redirect, render_template,
    request, session, url_for
)
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import query_one, execute
from services.email_service import send_email

auth_bp = Blueprint("auth", __name__)


def _reset_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


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
        official_email = (request.form.get("official_email") or "").strip()
        admin_name = (request.form.get("admin_name") or "").strip()
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""

        if not all([bank_name, bank_id, official_email, admin_name, username, password, confirm_password]):
            flash("Please fill in all fields.", "danger")
            return render_template("register.html")
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")
        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "danger")
            return render_template("register.html")
        if query_one("SELECT id FROM banks WHERE bank_id = ?", (bank_id,)):
            flash("Bank ID is already registered.", "danger")
            return render_template("register.html")
        if query_one("SELECT id FROM banks WHERE official_email = ?", (official_email,)):
            flash("Official email is already registered.", "danger")
            return render_template("register.html")
        if query_one("SELECT id FROM users WHERE username = ?", (username,)):
            flash("Username is already taken.", "danger")
            return render_template("register.html")

        try:
            created_at = datetime.now(timezone.utc).isoformat()
            execute(
                """
                INSERT INTO banks
                (bank_name, bank_id, official_email, status, created_at)
                VALUES (?, ?, ?, 'Approved', ?)
                """,
                (bank_name, bank_id, official_email, created_at),
            )
            bank = query_one("SELECT id FROM banks WHERE bank_id = ?", (bank_id,))
            execute(
                """
                INSERT INTO users
                (bank_id, admin_name, username, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, 'admin', ?)
                """,
                (bank["id"], admin_name, username, generate_password_hash(password), created_at),
            )

            email_sent = send_email(
                official_email,
                "Banking Behaviour Shift Intelligence - Registration",
                (
                    f"Hello {admin_name},\n\n"
                    f"The administrator account for {bank_name} was registered successfully.\n"
                    f"Username: {username}\n\n"
                    "If you did not request this registration, please contact your system administrator."
                ),
            )
            if email_sent:
                flash("Registration successful. A confirmation email has been sent. You can now sign in.", "success")
            else:
                flash("Registration successful. Email confirmation could not be sent; check your local SMTP settings.", "warning")
            return redirect(url_for("auth.login"))
        except Exception:
            current_app.logger.exception("Bank registration failed")
            flash("Registration failed. Please check the application log and try again.", "danger")

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        user = query_one(
            """
            SELECT users.id, users.bank_id, users.admin_name, users.username,
                   users.password_hash, users.role, banks.bank_name, banks.status
            FROM users
            JOIN banks ON users.bank_id = banks.id
            WHERE users.username = ?
            """,
            (username,),
        )

        if user and check_password_hash(user["password_hash"], password):
            if user["status"] != "Approved":
                flash("Your bank organization is not approved for access.", "warning")
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
        official_email = (request.form.get("official_email") or "").strip()
        user = query_one(
            """
            SELECT users.id, users.username, users.admin_name, banks.official_email
            FROM users
            JOIN banks ON users.bank_id = banks.id
            WHERE users.username = ? AND LOWER(banks.official_email) = LOWER(?)
            """,
            (username, official_email),
        )

        # Keep the same response whether the account exists or not.
        if user:
            token = _reset_serializer().dumps(
                {"user_id": user["id"]},
                salt="banking-password-reset",
            )
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            sent = send_email(
                user["official_email"],
                "Password reset request",
                (
                    f"Hello {user['admin_name']},\n\n"
                    "A password reset was requested for your administrator account. "
                    "Use the link below within 30 minutes to choose a new password:\n\n"
                    f"{reset_url}\n\n"
                    "If you did not request this, ignore this email. Your current password will remain unchanged."
                ),
            )
            if not sent:
                current_app.logger.error("Password-reset email could not be delivered for user id %s", user["id"])

        flash("If the username and official email match, a password-reset link will be sent to that email address.", "info")
        return redirect(url_for("auth.login"))
    return render_template("forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    try:
        payload = _reset_serializer().loads(
            token,
            salt="banking-password-reset",
            max_age=current_app.config["PASSWORD_RESET_MAX_AGE_SECONDS"],
        )
        user_id = int(payload["user_id"])
    except SignatureExpired:
        flash("This password-reset link has expired. Please request a new one.", "warning")
        return redirect(url_for("auth.forgot_password"))
    except (BadSignature, KeyError, TypeError, ValueError):
        flash("This password-reset link is invalid. Please request a new one.", "danger")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("reset_password.html")
        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "danger")
            return render_template("reset_password.html")

        user = query_one("SELECT id FROM users WHERE id = ?", (user_id,))
        if not user:
            flash("This account could not be found. Please request a new reset link.", "danger")
            return redirect(url_for("auth.forgot_password"))

        execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (generate_password_hash(password), user_id),
        )
        flash("Password reset successful. Please sign in with your new password.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
