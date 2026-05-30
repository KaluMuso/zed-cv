"""Tests for subscription renewal reminder service."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.services.renewal_reminder import run_renewal_reminder_emails


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *_a, **_k):
        return self

    def neq(self, *_a, **_k):
        return self

    def execute(self):
        class _R:
            data = self._rows

        return _R()


class _FakeSupabase:
    def __init__(self, rows):
        self._rows = rows

    def table(self, name):
        assert name == "users"
        return _FakeQuery(self._rows)


@pytest.mark.asyncio
async def test_renewal_reminder_sends_within_window():
    renew_at = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    sb = _FakeSupabase(
        [
            {
                "id": "u1",
                "email": "user@example.com",
                "full_name": "Jane Doe",
                "subscription_tier": "starter",
                "subscription_renews_at": renew_at,
                "subscription_expires_at": None,
                "email_notifications_enabled": True,
            }
        ]
    )
    with patch(
        "app.services.renewal_reminder.send_renewal_reminder_email",
        new_callable=AsyncMock,
        return_value=True,
    ) as send_mock:
        stats = await run_renewal_reminder_emails(sb)
    assert stats == {"sent": 1, "skipped": 0, "failed": 0}
    send_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_renewal_reminder_skips_outside_window():
    renew_at = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    sb = _FakeSupabase(
        [
            {
                "id": "u1",
                "email": "user@example.com",
                "full_name": "Jane",
                "subscription_tier": "starter",
                "subscription_renews_at": renew_at,
                "subscription_expires_at": None,
                "email_notifications_enabled": True,
            }
        ]
    )
    with patch(
        "app.services.renewal_reminder.send_renewal_reminder_email",
        new_callable=AsyncMock,
    ) as send_mock:
        stats = await run_renewal_reminder_emails(sb)
    assert stats["sent"] == 0
    assert stats["skipped"] == 1
    send_mock.assert_not_awaited()
