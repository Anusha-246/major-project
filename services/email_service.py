
from flask import current_app
from flask_mail import Mail, Message

mail = Mail()


def init_email(app):
    """Initialize email support for the Flask application."""
    mail.init_app(app)


def send_email(to, subject, body):
    """Send a plain-text email and report whether it succeeded."""
    if not to:
        return False

    if not current_app.config.get("MAIL_USERNAME") or not current_app.config.get("MAIL_PASSWORD"):
        current_app.logger.error(
            "Email settings are missing. Configure your local .env file."
        )
        return False

    try:
        message = Message(
            subject=subject,
            recipients=[to],
            body=body,
            sender=current_app.config.get("MAIL_DEFAULT_SENDER"),
        )
        mail.send(message)
        return True
    except Exception:
        current_app.logger.exception("Email delivery failed")
        return False
