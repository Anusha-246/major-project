from flask import current_app
from flask_mail import Mail, Message

mail = Mail()


def init_email(app):
    """Attach Flask-Mail to the application using Config/environment settings."""
    mail.init_app(app)


def send_email(to, subject, body):
    """Send a plain-text email. Return False and log details if SMTP fails."""
    if not to:
        current_app.logger.warning("Email not sent because recipient is empty.")
        return False

    if not current_app.config.get("MAIL_USERNAME") or not current_app.config.get("MAIL_PASSWORD"):
        current_app.logger.error(
            "Email not sent: configure MAIL_USERNAME and MAIL_PASSWORD in your local .env file."
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
