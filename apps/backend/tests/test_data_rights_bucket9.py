"""Bucket 9 — scheduled deletion, export, consent, safety allowlist."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.core.config import get_settings
from app.services.deletion import execute_deletion, request_deletion
from app.services.otp import hash_otp_code
from tests.conftest import FakeSupabase, FakeSupabaseQuery


class TrackingQuery(FakeSupabaseQuery):
    """Records delete/update side effects for unit tests."""

    def __init__(self, data=None, **kwargs):
        super().__init__(data=data, **kwargs)
        self.delete_calls: list[dict] = []
        self.update_payloads: list[dict] = []

    def delete(self):
        self.delete_calls.append({"table": getattr(self, "_table_name", "")})
        if isinstance(self._data, list):
            self._data.clear()
        return self

    def update(self, data):
        self.update_payloads.append(data)
        if isinstance(self._data, list) and self._data:
            self._data[0] = {**self._data[0], **data}
        elif isinstance(self._data, dict):
            self._data = {**self._data, **data}
        return self


def _seed_user(
    fake_supabase: FakeSupabase,
    *,
    user_id: str = "test-user-id",
    phone: str = "+260911000099",
) -> None:
    fake_supabase.set_table(
        "users",
        FakeSupabaseQuery(
            data=[{
                "id": user_id,
                "phone": phone,
                "email": "test@example.com",
                "full_name": "Synthetic User",
                "deleted_at": None,
            }]
        ),
    )
    fake_supabase.set_table("deletion_safety_allowlist", FakeSupabaseQuery(data=[]))
    fake_supabase.set_table("data_deletion_requests", FakeSupabaseQuery(data=[]))
    for table in (
        "user_skills",
        "cvs",
        "matches",
        "payments",
        "consent_log",
        "subscriptions",
        "otp_codes",
    ):
        fake_supabase.set_table(table, FakeSupabaseQuery(data=[]))


def _seed_valid_otp(fake_supabase: FakeSupabase, phone: str) -> str:
    settings = get_settings()
    code = "123456"
    fake_supabase.set_table(
        "otp_codes",
        FakeSupabaseQuery(
            data=[{
                "id": "otp-1",
                "phone": phone,
                "code": hash_otp_code(code, phone, settings.jwt_secret),
                "verified": False,
                "attempts": 0,
                "expires_at": (
                    datetime.now(timezone.utc) + timedelta(minutes=5)
                ).isoformat(),
            }]
        ),
    )
    return code


class TestDeletionRequest:
    def test_delete_request_schedules_seven_days_out(self, fake_supabase):
        phone = "+260911000099"
        _seed_user(fake_supabase, phone=phone)
        code = _seed_valid_otp(fake_supabase, phone)
        settings = get_settings()

        result = request_deletion(
            "test-user-id",
            otp_code=code,
            supabase=fake_supabase,
            settings=settings,
        )

        assert result["status"] == "pending"
        ddr = fake_supabase._tables["data_deletion_requests"]
        assert ddr._data
        row = ddr._data[-1] if isinstance(ddr._data, list) else ddr._data
        scheduled = datetime.fromisoformat(
            result["scheduled_at"].replace("Z", "+00:00")
        )
        requested = datetime.fromisoformat(
            row["requested_at"].replace("Z", "+00:00")
            if row.get("requested_at")
            else result["scheduled_at"].replace("Z", "+00:00")
        )
        delta = scheduled - requested
        assert 6 <= delta.days <= 7


class TestExecuteDeletion:
    def test_allowlist_blocks_before_any_delete(self, fake_supabase):
        phone = "+260911000099"
        _seed_user(fake_supabase, phone=phone)
        fake_supabase.set_table(
            "deletion_safety_allowlist",
            FakeSupabaseQuery(data=[{"phone": phone, "reason": "founder"}]),
        )
        fake_supabase.set_table(
            "data_deletion_requests",
            FakeSupabaseQuery(
                data=[{
                    "id": "req-1",
                    "user_id": "test-user-id",
                    "status": "pending",
                    "scheduled_at": datetime.now(timezone.utc).isoformat(),
                }]
            ),
        )

        matches_table = TrackingQuery(
            data=[{"id": "m-1", "user_id": "test-user-id"}]
        )
        fake_supabase.set_table("matches", matches_table)

        result = execute_deletion("req-1", fake_supabase)

        assert result["status"] == "failed"
        assert result["failure_reason"] == "safety_allowlist"
        assert not matches_table.delete_calls

    def test_execute_anonymises_user_and_hard_deletes_matches(self, fake_supabase):
        phone = "+260911000099"
        users_q = TrackingQuery(
            data=[{
                "id": "test-user-id",
                "phone": phone,
                "email": "a@b.com",
                "full_name": "Synthetic",
                "deleted_at": None,
            }]
        )
        fake_supabase.set_table("users", users_q)
        fake_supabase.set_table("deletion_safety_allowlist", FakeSupabaseQuery(data=[]))
        fake_supabase.set_table(
            "data_deletion_requests",
            TrackingQuery(
                data=[{
                    "id": "req-2",
                    "user_id": "test-user-id",
                    "status": "pending",
                    "scheduled_at": datetime.now(timezone.utc).isoformat(),
                }]
            ),
        )
        matches_q = TrackingQuery(
            data=[{"id": "m-1", "user_id": "test-user-id"}]
        )
        fake_supabase.set_table("matches", matches_q)
        payments_q = TrackingQuery(
            data=[{"id": "p-1", "user_id": "test-user-id"}]
        )
        fake_supabase.set_table("payments", payments_q)
        for table in (
            "user_skills",
            "cvs",
            "cv_generations",
            "generated_documents",
            "application_outcomes",
            "user_preferences",
            "interview_sessions",
            "aptitude_scores",
            "saved_jobs",
            "cv_upload_queue",
            "otp_codes",
            "consent_log",
            "subscriptions",
            "ai_cache",
        ):
            fake_supabase.set_table(table, TrackingQuery(data=[]))

        storage_mock = MagicMock()
        storage_mock.list.return_value = []
        fake_supabase.storage.from_.return_value = storage_mock

        result = execute_deletion("req-2", fake_supabase)

        assert result["status"] == "completed"
        assert matches_q.delete_calls
        assert payments_q.update_payloads and payments_q.update_payloads[0].get("user_id") is None
        user_updates = [p for p in users_q.update_payloads if p.get("deleted_at")]
        assert user_updates
        assert user_updates[-1]["phone"] is None


class TestDeletionRoutes:
    def test_delete_request_endpoint(self, client, fake_supabase, auth_headers):
        phone = "+260971234567"
        _seed_user(fake_supabase, user_id="test-user-id", phone=phone)
        code = _seed_valid_otp(fake_supabase, phone)

        resp = client.post(
            "/api/v1/users/me/delete-request",
            headers=auth_headers,
            json={"otp_code": code},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "pending"
        assert "scheduled_at" in body
