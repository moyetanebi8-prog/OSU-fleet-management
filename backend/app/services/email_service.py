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
from email.utils import formataddr

from app.config import settings

logger = logging.getLogger(__name__)


class EmailNotConfiguredError(RuntimeError):
    """
    Raised when SMTP is not configured well enough to send mail.
    Kept distinct from a real send failure (wrong password, network
    unreachable, etc.) so logs and the notifications table can tell
    "nobody set this up" apart from "this broke."
    """


def send_email(*, to_email: str, subject: str, body: str) -> None:
    if not settings.EMAIL_ENABLED:
        raise EmailNotConfiguredError(
            "Email delivery is disabled. Set EMAIL_ENABLED=true to enable it."
        )

    recipient = (to_email or "").strip()
    if not recipient:
        raise ValueError("to_email is required before sending email.")

    if not settings.SMTP_HOST:
        raise EmailNotConfiguredError(
            "SMTP_HOST is not set - no email server is configured. Set "
            "SMTP_HOST/SMTP_USERNAME/SMTP_PASSWORD in backend/.env to enable real email."
        )
    if not settings.SMTP_FROM_EMAIL:
        raise EmailNotConfiguredError(
            "SMTP_FROM_EMAIL is not set. Configure the sender address in backend/.env."
        )
    if settings.SMTP_PORT <= 0:
        raise EmailNotConfiguredError(
            "SMTP_PORT must be a valid port number greater than zero."
        )
    if settings.SMTP_USERNAME and not settings.SMTP_PASSWORD:
        raise EmailNotConfiguredError(
            "SMTP_USERNAME is set, but SMTP_PASSWORD is empty. Provide the SMTP password or "
            "remove the username for unauthenticated relays."
        )

    message = EmailMessage()
    message["Subject"] = subject
    sender_name = (settings.SMTP_FROM_NAME or "Fleet Management System").strip() or "Fleet Management System"
    message["From"] = formataddr((sender_name, settings.SMTP_FROM_EMAIL))
    message["To"] = recipient
    message.set_content(body)

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
        if settings.SMTP_USE_TLS:
            smtp.starttls()
        if settings.SMTP_USERNAME:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.send_message(message)

    logger.info("Email sent to %s: %r", recipient, subject)
