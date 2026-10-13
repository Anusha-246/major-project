from functools import wraps

from itsdangerous import (
    URLSafeTimedSerializer,
    BadSignature,
    SignatureExpired,
)
from flask import current_app
from services.email_service import send_email



from flask import Blueprint, flash, redirect, render_template, request, session, url_for
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
        official_email = (request.form.get("official_email") or "").strip()
        admin_name = (request.form.get("admin_name") or "").strip()
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""

        # Check required fields
        if not all([
            bank_name,
            bank_id,
            official_email,
            admin_name,
            username,
            password,
            confirm_password
        ]):
            flash("Please fill in all fields.", "danger")
            return render_template("register.html")

        # Check password
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "danger")
            return render_template("register.html")

        # Check whether bank ID already exists
        existing_bank = query_one(
            "SELECT id FROM banks WHERE bank_id = ?",
            (bank_id,)
        )

        if existing_bank:
            flash("Bank ID is already registered.", "danger")
            return render_template("register.html")

        # Check official email
        existing_email = query_one(
            "SELECT id FROM banks WHERE official_email = ?",
            (official_email,)
        )

        if existing_email:
            flash("Official email is already registered.", "danger")
            return render_template("register.html")

        # Check username
        existing_user = query_one(
            "SELECT id FROM users WHERE username = ?",
            (username,)
        )

        if existing_user:
            flash("Username is already taken.", "danger")
            return render_template("register.html")

        try:
            # Create bank
            execute(
                """
                INSERT INTO banks
                (bank_name, bank_id, official_email, status, created_at)
                VALUES (?, ?, ?, 'Approved', ?)
                """,
                (
                    bank_name,
                    bank_id,
                    official_email,
                    __import__("datetime").datetime.utcnow().isoformat() + "Z"
                )
            )

            # Get newly created bank
            bank = query_one(
                "SELECT id FROM banks WHERE bank_id = ?",
                (bank_id,)
            )

            # Create administrator account
            execute(
                """
                INSERT INTO users
                (bank_id, admin_name, username, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, 'admin', ?)
                """,
                (
                    bank["id"],
                    admin_name,
                    username,
                    generate_password_hash(password),
                    __import__("datetime").datetime.utcnow().isoformat() + "Z"
                )
            )

            flash(
                "Bank registration successful. You can now sign in as administrator.",
                "success"
            )
            return redirect(url_for("auth.login"))

        except Exception:
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

def make_reset_serializer():
    return URLSafeTimedSerializer(
        current_app.config["SECRET_KEY"]
    )


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("official_email") or "").strip()

        user = query_one(
            """
            SELECT users.id, users.admin_name, banks.official_email
            FROM users
            JOIN banks ON users.bank_id = banks.id
            WHERE users.username = ?
              AND LOWER(banks.official_email) = LOWER(?)
            """,
            (username, email),
        )

        # Do not reveal whether an account exists.
        if user:
            token = make_reset_serializer().dumps(
                {"user_id": user["id"]},
                salt="banking-password-reset",
            )

            reset_url = url_for(
                "auth.reset_password",
                token=token,
                _external=True,
            )

            sent = send_email(
                user["official_email"],
                "Password reset request",
                (
                    f"Hello {user['admin_name']},\n\n"
                    "Use this link to reset your password. "
                    "It expires in 30 minutes:\n\n"
                    f"{reset_url}\n\n"
                    "If you did not request this, ignore this email."
                ),
            )

            if not sent:
                current_app.logger.error(
                    "Could not send password reset email."
                )

        flash(
            "If the details match, a reset link will be sent to "
            "the registered email address.",
            "info",
        )
        return redirect(url_for("auth.login"))

    return render_template("forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    try:
        data = make_reset_serializer().loads(
            token,
            salt="banking-password-reset",
            max_age=current_app.config[
                "PASSWORD_RESET_MAX_AGE_SECONDS"
            ],
        )
        user_id = int(data["user_id"])

    except SignatureExpired:
        flash("The reset link has expired. Request a new one.", "warning")
        return redirect(url_for("auth.forgot_password"))

    except (BadSignature, KeyError, TypeError, ValueError):
        flash("Invalid reset link. Request a new one.", "danger")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("reset_password.html")

        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "danger")
            return render_template("reset_password.html")

        user = query_one(
            "SELECT id FROM users WHERE id = ?",
            (user_id,),
        )

        if not user:
            flash("Account not found. Request a new reset link.", "danger")
            return redirect(url_for("auth.forgot_password"))

        execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (generate_password_hash(password), user_id),
        )

        flash(
            "Password reset successful. Please sign in with your new password.",
            "success",
        )
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))