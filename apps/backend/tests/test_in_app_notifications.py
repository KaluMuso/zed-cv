"""GET /notifications and PATCH /notifications/{id}/read."""
from datetime import datetime, timezone
from unittest.mock import MagicMock

from tests.conftest import FakeSupabaseQuery

NOTIF_ID = "11111111-2222-3333-4444-555555556666"
OTHER_USER = "other-user-id"


class _NotificationsQuery(FakeSupabaseQuery):
    def __init__(self, rows=None, unread_count=0):
        super().__init__(data=list(rows or []))
        self._unread_count = unread_count
        self._filters: dict[str, object] = {}
        self._is_null_col: str | None = None
        self._count_exact = False

    def select(self, *args, **kwargs):
        self._filters = {}
        self._is_null_col = None
        self._count_exact = kwargs.get("count") == "exact"
        return self

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def is_(self, col, val):
        if val == "null":
            self._is_null_col = col
        return self

    def order(self, *_a, **_kw):
        return self

    def limit(self, *_a):
        return self

    def update(self, data):
        self._pending_update = data
        return self

    def _filtered_rows(self):
        rows = list(self._data)
        for col, val in self._filters.items():
            rows = [r for r in rows if r.get(col) == val]
        if self._is_null_col:
            rows = [r for r in rows if r.get(self._is_null_col) is None]
        return rows

    def execute(self):
        rows = self._filtered_rows()
        pending = getattr(self, "_pending_update", None)
        if pending is not None:
            for row in self._data:
                if all(row.get(k) == v for k, v in self._filters.items()):
                    row.update(pending)
            rows = self._filtered_rows()
            self._pending_update = None
        result = MagicMock()
        if self._count_exact:
            result.count = self._unread_count
            result.data = rows
        else:
            result.data = rows
            result.count = self._unread_count
        return result


def _seed_notifications(fake_supabase, *, user_id: str = "test-user-id"):
    now = datetime.now(timezone.utc).isoformat()
    fake_supabase.set_table(
        "notifications",
        _NotificationsQuery(
            rows=[
                {
                    "id": NOTIF_ID,
                    "user_id": user_id,
                    "type": "web_push",
                    "payload": {
                        "title": "Strong match: Engineer",
                        "body": "92% match",
                        "url": "/matches/m1",
                    },
                    "read_at": None,
                    "created_at": now,
                },
                {
                    "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                    "user_id": user_id,
                    "type": "invoice",
                    "payload": {
                        "title": "Invoice ZED-ABC",
                        "body": "Starter — K125",
                        "url": "/settings/billing",
                    },
                    "read_at": now,
                    "created_at": now,
                },
            ],
            unread_count=1,
        ),
    )


class TestInAppNotifications:
    def test_list_notifications(self, client, auth_headers, fake_supabase):
        _seed_notifications(fake_supabase)
        resp = client.get("/api/v1/notifications", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["unread_count"] == 1
        assert len(body["items"]) == 2
        assert body["items"][0]["type"] == "web_push"
        assert body["items"][0]["payload"]["title"] == "Strong match: Engineer"

    def test_mark_read(self, client, auth_headers, fake_supabase):
        _seed_notifications(fake_supabase)
        resp = client.patch(
            f"/api/v1/notifications/{NOTIF_ID}/read",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["notification"]["id"] == NOTIF_ID
        assert body["notification"]["read_at"] is not None

    def test_mark_read_not_found(self, client, auth_headers, fake_supabase):
        _seed_notifications(fake_supabase)
        resp = client.patch(
            "/api/v1/notifications/00000000-0000-0000-0000-000000000099/read",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_mark_read_idor(self, client, auth_headers, fake_supabase):
        now = datetime.now(timezone.utc).isoformat()
        fake_supabase.set_table(
            "notifications",
            _NotificationsQuery(
                rows=[
                    {
                        "id": NOTIF_ID,
                        "user_id": OTHER_USER,
                        "type": "admin_broadcast",
                        "payload": {"title": "Hello", "body": "", "url": "/"},
                        "read_at": None,
                        "created_at": now,
                    }
                ],
                unread_count=1,
            ),
        )
        resp = client.patch(
            f"/api/v1/notifications/{NOTIF_ID}/read",
            headers=auth_headers,
        )
        assert resp.status_code == 404
