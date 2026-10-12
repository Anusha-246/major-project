from functools import wraps


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
@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        username = (request.form.get("username") or "").strip()
        official_email = (request.form.get("official_email") or "").strip()

        user = query_one(
            """
            SELECT
                users.id,
                users.username,
                banks.official_email
            FROM users
            JOIN banks ON users.bank_id = banks.id
            WHERE users.username = ?
              AND banks.official_email = ?
            """,
            (username, official_email)
        )

        if not user:
            flash(
                "Username and official email do not match.",
                "danger"
            )
            return render_template("forgot_password.html")

        session["reset_user_id"] = user["id"]

        return redirect(url_for("auth.reset_password"))

    return render_template("forgot_password.html")
@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():

    if not session.get("reset_user_id"):
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":

        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("reset_password.html")

        if len(password) < 8:
            flash(
                "Password must contain at least 8 characters.",
                "danger"
            )
            return render_template("reset_password.html")

        execute(
            """
            UPDATE users
            SET password_hash = ?
            WHERE id = ?
            """,
            (
                generate_password_hash(password),
                session["reset_user_id"]
            )
        )

        session.pop("reset_user_id", None)

        flash(
            "Password reset successful. Please sign in with your new password.",
            "success"
        )

        return redirect(url_for("auth.login"))

    return render_template("reset_password.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))