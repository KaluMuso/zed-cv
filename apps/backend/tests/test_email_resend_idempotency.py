"""Resend SDK v2 idempotency options shape (ZEDCV-BACKEND-17)."""
from unittest.mock import patch

from app.services import email as email_mod


@patch("app.services.email.resend.Emails.send")
@patch("app.services.email._api_ready", return_value=True)
def test_send_uses_options_dict_for_idempotency(mock_ready, mock_send):
    email_mod._send(
        "user@example.com",
        "Subject",
        "<p>Hi</p>",
        idempotency_key="welcome-email/user-1",
    )
    mock_send.assert_called_once_with(
        {
            "from": email_mod.get_settings().resend_from_email,
            "to": ["user@example.com"],
            "subject": "Subject",
            "html": "<p>Hi</p>",
        },
        {"idempotency_key": "welcome-email/user-1"},
    )
