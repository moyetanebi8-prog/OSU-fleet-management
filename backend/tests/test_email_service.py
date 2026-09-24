"""
These tests exercise the REAL app/services/email_service.send_email
function - unlike every other test file, which gets a fake via the
autouse `_stub_email_sending` fixture in conftest.py. Defining a fixture
with that exact same name here overrides it for this file only (standard
pytest fixture-resolution behavior: the closest-scope definition wins),
so these tests see the actual function, not the stub.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services import email_service


@pytest.fixture(autouse=True)
def _stub_email_sending():
    """Overrides conftest.py's autouse stub - a no-op so these tests see
    the real email_service.send_email."""
    yield


def test_send_email_raises_when_smtp_not_configured():
    """Empty SMTP_HOST (the default, and this test environment's actual
    state - no real mail server is configured here) must raise a clear,
    distinct error - never silently pretend to succeed."""
    with patch.object(email_service.settings, "SMTP_HOST", ""):
        with pytest.raises(email_service.EmailNotConfiguredError):
            email_service.send_email(to_email="someone@example.com", subject="Hi", body="Test")


def test_send_email_uses_smtp_correctly_when_configured():
    """Verifies the actual SMTP call shape (host, port, starttls, login,
    message fields) without touching a real network - smtplib.SMTP itself
    is mocked, since no real mail server exists in this environment. This
    confirms the code is CORRECT; actually reaching a real mail server is
    something only you can verify, on your own machine, with real
    credentials (see the README's honesty note on this)."""
    with patch.object(email_service.settings, "SMTP_HOST", "smtp.example.com"), patch.object(
        email_service.settings, "SMTP_PORT", 587
    ), patch.object(email_service.settings, "SMTP_USERNAME", "apikey"), patch.object(
        email_service.settings, "SMTP_PASSWORD", "secret"
    ), patch.object(
        email_service.settings, "SMTP_USE_TLS", True
    ), patch.object(
        email_service.settings, "SMTP_FROM_EMAIL", "no-reply@fleetco.test"
    ), patch.object(
        email_service.settings, "SMTP_FROM_NAME", "Fleet Co"
    ):
        mock_smtp_instance = MagicMock()
        mock_smtp_context = MagicMock()
        mock_smtp_context.__enter__.return_value = mock_smtp_instance
        mock_smtp_context.__exit__.return_value = False

        with patch("smtplib.SMTP", return_value=mock_smtp_context) as mock_smtp_class:
            email_service.send_email(
                to_email="driver@example.com", subject="Trip assigned", body="You're driving trip #5."
            )

        mock_smtp_class.assert_called_once_with("smtp.example.com", 587, timeout=10)
        mock_smtp_instance.starttls.assert_called_once()
        mock_smtp_instance.login.assert_called_once_with("apikey", "secret")

        assert mock_smtp_instance.send_message.call_count == 1
        sent_message = mock_smtp_instance.send_message.call_args[0][0]
        assert sent_message["To"] == "driver@example.com"
        assert sent_message["Subject"] == "Trip assigned"
        assert "Fleet Co" in sent_message["From"]
        assert "no-reply@fleetco.test" in sent_message["From"]


def test_send_email_skips_login_when_no_username_configured():
    """Some SMTP relays (e.g. an internal company mail server) don't
    require auth at all - login() should only be called if a username was
    actually configured."""
    with patch.object(email_service.settings, "SMTP_HOST", "internal-mail.example.com"), patch.object(
        email_service.settings, "SMTP_USERNAME", ""
    ), patch.object(email_service.settings, "SMTP_USE_TLS", False):
        mock_smtp_instance = MagicMock()
        mock_smtp_context = MagicMock()
        mock_smtp_context.__enter__.return_value = mock_smtp_instance
        mock_smtp_context.__exit__.return_value = False

        with patch("smtplib.SMTP", return_value=mock_smtp_context):
            email_service.send_email(to_email="x@example.com", subject="Hi", body="Test")

        mock_smtp_instance.login.assert_not_called()
        mock_smtp_instance.starttls.assert_not_called()
