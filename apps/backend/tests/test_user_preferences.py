"""GET/PATCH /api/v1/users/me/preferences — dashboard settings."""
from unittest.mock import MagicMock

from tests.conftest import FakeSupabaseQuery


class _SettingsQuery(FakeSupabaseQuery):
    """Tracks user settings updates and merges them into the stored row."""

    def __init__(self, data=None, count=None):
        super().__init__(data=data, count=count)
        self.update_calls: list[dict] = []

    def single(self):
        self._single = True
        return self

    def update(self, data):
        self.update_calls.append(data)
        if self._data and isinstance(self._data, list):
            self._data[0] = {**self._data[0], **data}
        return self

    def execute(self):
        result = MagicMock()
        if getattr(self, "_single", False) and self._data:
            row = self._data[0] if isinstance(self._data, list) else self._data
            result.data = row
        else:
            result.data = self._data
        result.count = self._count
        return result


def _seed_users(fake_supabase):
    fake_supabase.set_table(
        "users",
        _SettingsQuery(
            data=[
                {
                    "id": "test-user-id",
                    "phone": "+260971234567",
                    "whatsapp_number": None,
                    "location": "Lusaka",
                    "currency": "ZMW",
                    "alert_frequency": "daily",
                    "whatsapp_verified": True,
                    "preferred_notification_channel": "email",
                    "subscription_tier": "free",
                }
            ]
        ),
    )


class TestUserDashboardPreferences:
    def test_get_preferences_returns_effective_whatsapp(
        self, client, auth_headers, fake_supabase
    ):
        _seed_users(fake_supabase)
        resp = client.get("/api/v1/users/me/preferences", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["whatsapp_number"] == "+260971234567"
        assert body["location"] == "Lusaka"
        assert body["currency"] == "ZMW"
        assert body["alert_frequency"] == "daily"
        assert body["whatsapp_verified"] is True
        assert body["preferred_notification_channel"] == "email"
        assert body["whatsapp_digest_available"] is False

    def test_patch_whatsapp_channel_requires_paid_tier(
        self, client, auth_headers, fake_supabase
    ):
        _seed_users(fake_supabase)
        resp = client.patch(
            "/api/v1/users/me/preferences",
            headers=auth_headers,
            json={"preferred_notification_channel": "whatsapp"},
        )
        assert resp.status_code == 403

    def test_patch_location_and_currency(self, client, auth_headers, fake_supabase):
        _seed_users(fake_supabase)
        resp = client.patch(
            "/api/v1/users/me/preferences",
            headers=auth_headers,
            json={"location": "Kitwe", "currency": "USD", "alert_frequency": "weekly"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["location"] == "Kitwe"
        assert body["currency"] == "USD"
        assert body["alert_frequency"] == "weekly"

    def test_patch_whatsapp_number_clears_verified(
        self, client, auth_headers, fake_supabase
    ):
        _seed_users(fake_supabase)
        resp = client.patch(
            "/api/v1/users/me/preferences",
            headers=auth_headers,
            json={"whatsapp_number": "+260961234567"},
        )
        assert resp.status_code == 200
        assert resp.json()["whatsapp_number"] == "+260961234567"
        assert resp.json()["whatsapp_verified"] is False
        users_q = fake_supabase._tables["users"]
        assert users_q.update_calls[-1]["whatsapp_verified"] is False

    def test_patch_invalid_whatsapp_is_422(self, client, auth_headers, fake_supabase):
        _seed_users(fake_supabase)
        resp = client.patch(
            "/api/v1/users/me/preferences",
            headers=auth_headers,
            json={"whatsapp_number": "+14155552671"},
        )
        assert resp.status_code == 422

    def test_patch_empty_body_is_422(self, client, auth_headers, fake_supabase):
        _seed_users(fake_supabase)
        resp = client.patch(
            "/api/v1/users/me/preferences",
            headers=auth_headers,
            json={},
        )
        assert resp.status_code == 422

    def test_get_requires_auth(self, client):
        resp = client.get("/api/v1/users/me/preferences")
        assert resp.status_code in (401, 403)
