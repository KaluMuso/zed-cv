"""Employer portal API — registration, search, consent, RLS-style isolation."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from jose import jwt

from tests.conftest import FakeSupabaseQuery


class FilteringSupabaseQuery(FakeSupabaseQuery):
    """Minimal eq filter for employer isolation tests."""

    def __init__(self, data=None, count=None):
        super().__init__(data, count)
        self._filters: list[tuple[str, object]] = []

    def eq(self, col, val):
        self._filters.append((col, val))
        return self

    def execute(self):
        rows = list(self._data or [])
        for col, val in self._filters:
            rows = [r for r in rows if r.get(col) == val]
        result = super().execute()
        result.data = rows
        result.count = len(rows)
        return result


class StatefulContactRequestsQuery(FakeSupabaseQuery):
    """Tracks inserts/updates for employer consent E2E tests."""

    def __init__(self):
        super().__init__(data=[])
        self._rows: list[dict] = []
        self._pending_update: dict | None = None
        self._pending_id: str | None = None
        self._filters: list[tuple[str, object, str, bool]] = []
        self._negate_next_is = False

    def insert(self, data):
        row = dict(data)
        row.setdefault("id", f"ccr-{len(self._rows) + 1}")
        row.setdefault("created_at", "2026-05-01T00:00:00Z")
        self._rows.append(row)
        self._data = self._rows
        return self

    def update(self, data):
        self._pending_update = dict(data)
        return self

    def eq(self, col, val):
        if self._pending_update is not None:
            self._pending_id = str(val)
        else:
            self._filters.append((col, val, "eq", False))
        return self

    def is_(self, col, val):
        self._filters.append((col, val, "is", self._negate_next_is))
        self._negate_next_is = False
        return self

    @property
    def not_(self):
        self._negate_next_is = True
        return self

    def order(self, *a, **kw):
        return self

    def limit(self, *a):
        return self

    def execute(self):
        if self._pending_update is not None and self._pending_id:
            for row in self._rows:
                if str(row.get("id")) == self._pending_id:
                    row.update(self._pending_update)
                    break
            self._pending_update = None
            self._pending_id = None
            self._data = self._rows
            result = super().execute()
            result.data = self._rows
            return result

        rows = list(self._rows)
        for col, val, op, negate in self._filters:
            if op == "eq":
                rows = [r for r in rows if r.get(col) == val]
            elif op == "is" and val == "null":
                if negate:
                    rows = [r for r in rows if r.get(col) is not None]
                else:
                    rows = [r for r in rows if r.get(col) is None]
        self._filters = []

        result = super().execute()
        result.data = rows
        result.count = len(rows)
        return result


class FilteringUsersQuery(FakeSupabaseQuery):
    """users.eq(...) for consent webhook (phone) and contact list (id)."""

    def __init__(self, data=None):
        super().__init__(data, count=None)
        self._filters: list[tuple[str, object]] = []

    def eq(self, col, val):
        self._filters.append((col, val))
        return self

    def execute(self):
        rows = list(self._data or [])
        for col, val in self._filters:
            rows = [r for r in rows if r.get(col) == val]
        self._filters = []
        result = super().execute()
        result.data = rows
        return result


def _token(user_id: str) -> str:
    import os

    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": user_id,
            "phone": "+260971234567",
            "exp": now + timedelta(hours=1),
            "iat": now,
        },
        os.environ["JWT_SECRET"],
        algorithm="HS256",
    )


def _headers(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(user_id)}"}


@pytest.fixture
def employer_a_setup(fake_supabase):
    fake_supabase.set_table(
        "users",
        FakeSupabaseQuery(
            data=[
                {
                    "id": "owner-a",
                    "phone": "+260971111111",
                    "role": "user",
                    "profile_visible_to_employers": True,
                    "is_active": True,
                },
                {
                    "id": "owner-b",
                    "phone": "+260972222222",
                    "role": "user",
                },
                {
                    "id": "cand-1",
                    "phone": "+260973333333",
                    "email": "cand@example.com",
                    "full_name": "Jane Accountant",
                    "location": "Lusaka",
                    "years_experience": 5,
                    "profile_visible_to_employers": True,
                    "is_active": True,
                },
            ]
        ),
    )
    fake_supabase.set_table("employer_users", FakeSupabaseQuery(data=[]))
    fake_supabase.set_table("employers", FakeSupabaseQuery(data=[]))
    fake_supabase.set_table("employer_subscriptions", FakeSupabaseQuery(data=[]))
    fake_supabase.set_table("candidate_contact_requests", FakeSupabaseQuery(data=[]))
    fake_supabase.set_table(
        "cvs",
        FakeSupabaseQuery(
            data=[
                {
                    "id": "cv-1",
                    "user_id": "cand-1",
                    "is_primary": True,
                    "parsed_data": {
                        "headline": "Senior Accountant",
                        "skills": ["accounting", "excel"],
                    },
                }
            ]
        ),
    )
    fake_supabase.set_table("user_skills", FakeSupabaseQuery(data=[]))
    return fake_supabase


class TestEmployerRegister:
    def test_register_creates_employer_and_owner(self, client, employer_a_setup):
        resp = client.post(
            "/api/v1/employers/register",
            headers=_headers("owner-a"),
            json={
                "company_name": "ABC Personnel",
                "industry": "Recruitment",
                "size_band": "11-50",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["employer"]["company_name"] == "ABC Personnel"


class TestEmployerSearch:
    def test_search_requires_subscription(self, client, employer_a_setup):
        client.post(
            "/api/v1/employers/register",
            headers=_headers("owner-a"),
            json={"company_name": "ABC Personnel"},
        )
        resp = client.get(
            "/api/v1/employers/candidates/search",
            headers=_headers("owner-a"),
            params={"skills": "accountant", "location": "Lusaka"},
        )
        assert resp.status_code == 402

    @patch(
        "app.core.employer_tier_gating.load_active_employer_subscription",
        new_callable=AsyncMock,
    )
    def test_search_returns_anonymized_previews(self, mock_sub, client, employer_a_setup):
        mock_sub.return_value = {
            "id": "sub-1",
            "tier": "pro",
            "status": "active",
            "contacts_used_this_period": 0,
        }
        client.post(
            "/api/v1/employers/register",
            headers=_headers("owner-a"),
            json={"company_name": "ABC Personnel"},
        )
        resp = client.get(
            "/api/v1/employers/candidates/search",
            headers=_headers("owner-a"),
            params={"skills": "accountant", "location": "Lusaka"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        preview = body["results"][0]
        assert "candidate_id" in preview
        assert "phone" not in preview


class TestEmployerConsent:
    @patch(
        "app.services.employer_contact.send_consent_notifications",
        new_callable=AsyncMock,
    )
    @patch(
        "app.core.employer_tier_gating.load_active_employer_subscription",
        new_callable=AsyncMock,
    )
    @patch(
        "app.core.employer_tier_gating.increment_contact_usage",
        new_callable=AsyncMock,
    )
    def test_contact_request_and_yes_reply(
        self, mock_inc, mock_sub, mock_notify, client, employer_a_setup
    ):
        mock_sub.return_value = {
            "id": "sub-1",
            "tier": "lite",
            "status": "active",
            "contacts_used_this_period": 0,
        }
        mock_inc.return_value = 1
        client.post(
            "/api/v1/employers/register",
            headers=_headers("owner-a"),
            json={"company_name": "ABC Personnel"},
        )

        ccr_table = StatefulContactRequestsQuery()
        employer_a_setup.set_table("candidate_contact_requests", ccr_table)
        employer_a_setup.set_table(
            "users",
            FilteringUsersQuery(
                data=[
                    {
                        "id": "owner-a",
                        "phone": "+260971111111",
                        "role": "user",
                        "profile_visible_to_employers": True,
                        "is_active": True,
                    },
                    {
                        "id": "owner-b",
                        "phone": "+260972222222",
                        "role": "user",
                    },
                    {
                        "id": "cand-1",
                        "phone": "+260973333333",
                        "email": "cand@example.com",
                        "full_name": "Jane Accountant",
                        "location": "Lusaka",
                        "years_experience": 5,
                        "profile_visible_to_employers": True,
                        "is_active": True,
                    },
                ]
            ),
        )

        resp = client.post(
            "/api/v1/employers/candidates/cand-1/contact",
            headers=_headers("owner-a"),
            json={
                "message_text": "We have a finance role that may suit you.",
                "channel": "both",
            },
        )
        assert resp.status_code == 200
        mock_notify.assert_awaited_once()
        assert ccr_table._rows[0].get("candidate_consented") is None

        with patch(
            "app.services.whatsapp.send_whatsapp_message",
            new_callable=AsyncMock,
        ):
            wa = client.post(
                "/api/v1/webhooks/whatsapp",
                json={
                    "event": "message",
                    "payload": {
                        "from": "260973333333@c.us",
                        "body": "YES",
                    },
                },
            )
        assert wa.status_code == 200
        assert wa.json().get("employer_consent") is True
        assert ccr_table._rows[0].get("candidate_consented") is True

        contacts = client.get(
            "/api/v1/employers/me/contacts",
            headers=_headers("owner-a"),
        )
        assert contacts.status_code == 200
        body = contacts.json()
        assert body["total"] == 1
        assert body["summary"]["consented"] == 1
        assert body["summary"]["pending"] == 0
        row = body["contacts"][0]
        assert row["status"] == "consented"
        assert row["candidate_phone"] == "+260973333333"
        assert row["candidate_email"] == "cand@example.com"


class TestEmployerIsolation:
    def test_employer_b_cannot_see_a_contacts(self, client, employer_a_setup):
        employer_a_setup.set_table(
            "employer_users",
            FilteringSupabaseQuery(
                data=[
                    {
                        "id": "seat-a",
                        "employer_id": "emp-a",
                        "user_id": "owner-a",
                        "role": "owner",
                        "accepted_at": "2026-01-01T00:00:00Z",
                    },
                    {
                        "id": "seat-b",
                        "employer_id": "emp-b",
                        "user_id": "owner-b",
                        "role": "owner",
                        "accepted_at": "2026-01-01T00:00:00Z",
                    },
                ]
            ),
        )
        employer_a_setup.set_table(
            "employers",
            FakeSupabaseQuery(
                data=[
                    {"id": "emp-a", "company_name": "A Co", "verified": False},
                    {"id": "emp-b", "company_name": "B Co", "verified": False},
                ]
            ),
        )
        employer_a_setup.set_table(
            "candidate_contact_requests",
            FilteringSupabaseQuery(
                data=[
                    {
                        "id": "ccr-1",
                        "employer_id": "emp-a",
                        "candidate_user_id": "cand-1",
                        "initiated_by_user_id": "owner-a",
                        "message_text": "Hi",
                        "channel": "both",
                        "sent_at": "2026-01-01T00:00:00Z",
                        "candidate_consented": True,
                    }
                ]
            ),
        )

        resp = client.get(
            "/api/v1/employers/me/contacts",
            headers=_headers("owner-b"),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["summary"]["total"] == 0
