"""Admin companies CSV export and Zambian phone extraction."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from jose import jwt

from app.services.description_body_extractor import (
    extract_phone_from_description,
    normalize_zambian_phone,
)
from tests.conftest import FakeSupabaseQuery


def _user_token(sub: str = "test-user-id") -> str:
    import os

    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": sub,
            "phone": "+260971234567",
            "exp": now + timedelta(hours=24),
            "iat": now,
        },
        os.environ["JWT_SECRET"],
        algorithm="HS256",
    )


def _admin_token() -> str:
    return _user_token("admin-user-id")


def _seed_admin(fake_supabase) -> None:
    fake_supabase.set_table(
        "users",
        FakeSupabaseQuery(
            data=[
                {
                    "id": "admin-user-id",
                    "phone": "+260971111111",
                    "role": "superadmin",
                }
            ]
        ),
    )


def _seed_regular_user(fake_supabase) -> None:
    fake_supabase.set_table(
        "users",
        FakeSupabaseQuery(
            data=[
                {
                    "id": "test-user-id",
                    "phone": "+260971234567",
                    "role": "user",
                }
            ]
        ),
    )


class _CompaniesExportRpc:
    def __init__(self, rows: list[dict]):
        self._rows = rows

    def execute(self):
        result = MagicMock()
        result.data = self._rows
        return result


def test_companies_csv_export_admin_only_403_for_user(client, fake_supabase):
    _seed_regular_user(fake_supabase)
    res = client.get(
        "/api/v1/admin/export/companies.csv",
        headers={"Authorization": f"Bearer {_user_token()}"},
    )
    assert res.status_code == 403


def test_companies_csv_export_returns_csv_with_correct_columns(client, fake_supabase):
    _seed_admin(fake_supabase)
    posted = "2026-05-01T12:00:00+00:00"
    rows = [
        {
            "company": "ACME Ltd",
            "primary_apply_email": "hr@acme.test",
            "primary_apply_url": "https://acme.test/jobs",
            "primary_phone": "+260971234567",
            "total_jobs": 3,
            "active_jobs": 2,
            "review_required_jobs": 1,
            "latest_posted_at": posted,
            "source_url_sample": "https://example.com/job/1",
        }
    ]

    def rpc(name, args=None, **kw):
        if name == "admin_export_companies":
            return _CompaniesExportRpc(rows)
        return FakeSupabaseQuery(data=[])

    fake_supabase.rpc = rpc

    res = client.get(
        "/api/v1/admin/export/companies.csv",
        headers={"Authorization": f"Bearer {_admin_token()}"},
    )
    assert res.status_code == 200
    assert "text/csv" in res.headers.get("content-type", "")
    assert 'filename="companies.csv"' in res.headers.get("content-disposition", "")

    lines = res.text.strip().split("\n")
    assert lines[0] == (
        "company,primary_apply_email,primary_apply_url,primary_phone,"
        "total_jobs,active_jobs,review_required_jobs,latest_posted_at,"
        "source_url_sample"
    )
    assert lines[1].startswith("ACME Ltd,hr@acme.test,https://acme.test/jobs,+260971234567,3,2,1,")


def test_phone_extractor_finds_local_zambian_numbers():
    assert normalize_zambian_phone("0971234567") == "+260971234567"
    assert normalize_zambian_phone("+260 97 123 4567") == "+260971234567"
    assert normalize_zambian_phone("+260971234567") == "+260971234567"

    text = "Call 097-123-4567 or WhatsApp +260 96 111 2233 for details."
    assert extract_phone_from_description(text) == "+260971234567"

    assert extract_phone_from_description("No phone here, email only hr@test.com") is None
