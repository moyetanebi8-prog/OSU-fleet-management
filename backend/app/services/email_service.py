"""
Real SMTP email sending.

Uses Python's standard library (smtplib + email.message) - a plain SMTP
relay covers Gmail (with an app password), SendGrid's SMTP endpoint,
Mailtrap (great for testing without spamming real inboxes), or a company
mail server, without needing a provider-specific SDK.

HONESTY NOTE, stated plainly: this code is real and correct, and will
actually send email once SMTP_HOST/SMTP_USERNAME/SMTP_PASSWORD are set to
real values in backend/.env. It has NOT been executed against a live mail
server in this build environment - there is no SMTP server or credentials
available here to test against, and no network access to reach one even
if there were. Test it end-to-end on your own machine (Mailtrap.io is
free and exists specifically for safely testing this kind of thing)
before relying on it for anything real.
"""

import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)


class EmailNotConfiguredError(RuntimeError):
    """
    Raised when SMTP_HOST is empty - i.e. no mail server has been
    configured at all. Kept distinct from a real send failure (wrong
    password, network unreachable, etc.) so logs and the notifications
    table can tell "nobody set this up" apart from "this broke."
    """


def send_email(*, to_email: str, subject: str, body: str) -> None:
    if not settings.SMTP_HOST:
        raise EmailNotConfiguredError(
            "SMTP_HOST is not set - no email server is configured. Set "
            "SMTP_HOST/SMTP_USERNAME/SMTP_PASSWORD in backend/.env to enable real email."
        )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = to_email
    message.set_content(body)

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
        if settings.SMTP_USE_TLS:
            smtp.starttls()
        if settings.SMTP_USERNAME:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.send_message(message)

    logger.info("Email sent to %s: %r", to_email, subject)
