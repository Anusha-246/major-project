from flask import current_app
from flask_mail import Mail, Message

mail = Mail()


def init_email(app):
    app.config["MAIL_SERVER"] = current_app.config.get(
        "MAIL_SERVER", "smtp.gmail.com"
    )
    mail.init_app(app)


def send_email(to, subject, body):
    if not to:
        return False

    try:
        message = Message(
            subject=subject,
            recipients=[to],
            body=body,
        )
        mail.send(message)
        return True
    except Exception:
        current_app.logger.exception("Email delivery failed")
        return False