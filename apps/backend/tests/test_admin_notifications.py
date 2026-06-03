"""Tests for POST /api/v1/admin/notifications."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import FakeSupabaseQuery

INGEST_HEADERS = {"INGEST_API_KEY": "test-ingest-key"}


class TierFilterUsersQuery(FakeSupabaseQuery):
    """Returns user ids, optionally filtered by subscription_tier."""

    def __init__(self, users: list[dict]):
        super().__init__(data=users)
        self._users = users
        self._filters: dict[str, str] = {}
        self._range: tuple[int, int] | None = None

    def select(self, *a, **kw):
        return self

    def eq(self, col, val):
        if col:
            self._filters[str(col)] = str(val)
        return self

    def range(self, start, end):
        self._range = (int(start), int(end))
        return self

    def execute(self):
        rows = list(self._users)
        tier = self._filters.get("subscription_tier")
        if tier:
            rows = [r for r in rows if r.get("subscription_tier") == tier]
        if self._range is not None:
            start, end = self._range
            rows = rows[start : end + 1]
        result = type("R", (), {})()
        result.data = rows
        result.count = len(rows)
        return result


class RecordingInsertQuery(FakeSupabaseQuery):
    """Records insert payloads and returns generated ids."""

    def __init__(self, *, return_id: str = "campaign-uuid-1"):
        super().__init__()
        self.inserted: list[dict | list] = []
        self.updated: list[dict] = []
        self._return_id = return_id
        self._filters: dict[str, str] = {}

    def insert(self, data):
        self.inserted.append(data)
        return self

    def update(self, data):
        self.updated.append(data)
        return self

    def select(self, *a, **kw):
        return self

    def eq(self, col, val):
        if col:
            self._filters[str(col)] = str(val)
        return self

    def in_(self, *a, **kw):
        return self

    def lte(self, *a):
        return self

    def limit(self, *a):
        return self

    def execute(self):
        result = type("R", (), {})()
        if self.inserted:
            last = self.inserted[-1]
            if isinstance(last, dict):
                row = {**last, "id": self._return_id}
                result.data = [row]
            elif isinstance(last, list):
                result.data = last
            else:
                result.data = []
        elif self._filters.get("id") == "campaign-uuid-1":
            result.data = [
                {
                    "id": "campaign-uuid-1",
                    "title": "Hello",
                    "body": "World",
                    "url": "/matches",
                    "status": "pending",
                }
            ]
        else:
            result.data = []
        return result


def _seed_users(fake_supabase):
    users = [
        {"id": "user-free-1", "subscription_tier": "free"},
        {"id": "user-free-2", "subscription_tier": "free"},
        {"id": "user-starter-1", "subscription_tier": "starter"},
    ]
    fake_supabase.set_table("users", TierFilterUsersQuery(users))
    return users


class TestAdminNotificationsAuth:
    def test_rejects_missing_admin_key(self, client, fake_supabase):
        resp = client.post(
            "/api/v1/admin/notifications",
            json={
                "title": "Test",
                "body": "Body",
                "target_audience": "all",
            },
        )
        assert resp.status_code == 401

    def test_rejects_invalid_admin_key(self, client, fake_supabase):
        resp = client.post(
            "/api/v1/admin/notifications",
            headers={"INGEST_API_KEY": "wrong-key"},
            json={
                "title": "Test",
                "body": "Body",
                "target_audience": "all",
            },
        )
        assert resp.status_code == 401


class TestAdminNotificationsTierFilter:
    @patch(
        "app.services.admin_notifications.vapid_configured",
        return_value=False,
    )
    @patch(
        "app.services.admin_notifications.deliver_campaign",
        new_callable=AsyncMock,
    )
    def test_all_users_targets_everyone(
        self, mock_deliver, _vapid, client, fake_supabase
    ):
        _seed_users(fake_supabase)
        campaigns = RecordingInsertQuery(return_id="camp-all")
        recipients = RecordingInsertQuery()
        fake_supabase.set_table("admin_notification_campaigns", campaigns)
        fake_supabase.set_table("admin_notification_recipients", recipients)

        resp = client.post(
            "/api/v1/admin/notifications",
            headers=INGEST_HEADERS,
            json={
                "title": "Platform update",
                "body": "We shipped a new feature.",
                "target_audience": "all",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["recipients_queued"] == 3
        assert body["target_audience"] == "all"
        assert body["target_tier"] is None
        recipient_rows = recipients.inserted[-1]
        assert isinstance(recipient_rows, list)
        assert {r["user_id"] for r in recipient_rows} == {
            "user-free-1",
            "user-free-2",
            "user-starter-1",
        }
        mock_deliver.assert_not_called()

    @patch(
        "app.services.admin_notifications.vapid_configured",
        return_value=False,
    )
    def test_tier_filter_only_matching_users(self, _vapid, client, fake_supabase):
        _seed_users(fake_supabase)
        campaigns = RecordingInsertQuery(return_id="camp-starter")
        recipients = RecordingInsertQuery()
        fake_supabase.set_table("admin_notification_campaigns", campaigns)
        fake_supabase.set_table("admin_notification_recipients", recipients)

        resp = client.post(
            "/api/v1/admin/notifications",
            headers=INGEST_HEADERS,
            json={
                "title": "Starter perk",
                "body": "Exclusive for Starter plans.",
                "target_audience": "tier",
                "target_tier": "starter",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["recipients_queued"] == 1
        assert body["target_tier"] == "starter"
        recipient_rows = recipients.inserted[-1]
        assert [r["user_id"] for r in recipient_rows] == ["user-starter-1"]
        assert campaigns.inserted[0]["target_tier"] == "starter"

    def test_tier_audience_requires_target_tier(self, client, fake_supabase):
        resp = client.post(
            "/api/v1/admin/notifications",
            headers=INGEST_HEADERS,
            json={
                "title": "Missing tier",
                "body": "Should fail validation",
                "target_audience": "tier",
            },
        )
        assert resp.status_code == 422


class TestAdminNotificationsSchedule:
    @patch(
        "app.services.admin_notifications.vapid_configured",
        return_value=True,
    )
    @patch(
        "app.services.admin_notifications.deliver_campaign",
        new_callable=AsyncMock,
        return_value={"sent": 2, "failed": 0},
    )
    def test_immediate_send_invokes_delivery(
        self, mock_deliver, _vapid, client, fake_supabase
    ):
        _seed_users(fake_supabase)
        fake_supabase.set_table(
            "admin_notification_campaigns", RecordingInsertQuery()
        )
        fake_supabase.set_table(
            "admin_notification_recipients", RecordingInsertQuery()
        )

        resp = client.post(
            "/api/v1/admin/notifications",
            headers=INGEST_HEADERS,
            json={
                "title": "Now",
                "body": "Immediate",
                "target_audience": "all",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "completed"
        mock_deliver.assert_awaited_once()

    @patch(
        "app.services.admin_notifications.deliver_campaign",
        new_callable=AsyncMock,
    )
    def test_future_schedule_skips_immediate_delivery(
        self, mock_deliver, client, fake_supabase
    ):
        _seed_users(fake_supabase)
        fake_supabase.set_table(
            "admin_notification_campaigns", RecordingInsertQuery()
        )
        fake_supabase.set_table(
            "admin_notification_recipients", RecordingInsertQuery()
        )
        future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

        resp = client.post(
            "/api/v1/admin/notifications",
            headers=INGEST_HEADERS,
            json={
                "title": "Later",
                "body": "Scheduled",
                "target_audience": "all",
                "scheduled_at": future,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "scheduled"
        mock_deliver.assert_not_called()


class _InboxInsertQuery(FakeSupabaseQuery):
    def __init__(self):
        super().__init__()
        self.inserted: list[dict] = []

    def insert(self, data):
        if isinstance(data, dict):
            self.inserted.append(data)
        return self


class TestDeliverCampaignInbox:
    @pytest.mark.asyncio
    @patch("app.services.admin_notifications.vapid_configured", return_value=True)
    @patch(
        "app.services.admin_notifications.send_payload_to_user",
        new_callable=AsyncMock,
        return_value=1,
    )
    async def test_successful_push_writes_admin_broadcast_inbox_row(
        self, _send, _vapid, fake_supabase
    ):
        from app.core.config import get_settings
        from app.services.admin_notifications import deliver_campaign

        campaign_id = "camp-inbox-1"
        fake_supabase.set_table(
            "admin_notification_campaigns",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": campaign_id,
                        "title": "Hello",
                        "body": "World",
                        "url": "/jobs",
                        "status": "pending",
                    }
                ]
            ),
        )
        fake_supabase.set_table(
            "admin_notification_recipients",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "rec-1",
                        "user_id": "user-free-1",
                        "campaign_id": campaign_id,
                        "status": "pending",
                    }
                ]
            ),
        )
        inbox = _InboxInsertQuery()
        fake_supabase.set_table("notifications", inbox)

        counts = await deliver_campaign(
            campaign_id, fake_supabase, settings=get_settings()
        )
        assert counts["sent"] == 1
        assert len(inbox.inserted) == 1
        row = inbox.inserted[0]
        assert row["user_id"] == "user-free-1"
        assert row["type"] == "admin_broadcast"
        assert row["payload"]["title"] == "Hello"
        assert row["payload"]["campaign_id"] == campaign_id
