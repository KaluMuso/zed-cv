"""Track 4e: description extraction, deadlines, activation, admin review, apply UX."""
from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.services.description_body_extractor import (
    extract_apply_from_description,
    merge_description_extraction,
)
from app.services.job_activation import compute_review_state, can_publish_after_admin_edit
from app.services.job_deadline_extractor import (
    extract_deadline_from_text_regex,
    parse_closing_date,
)


def test_description_email_extractor_finds_recruitment_email():
    text = (
        "Abattoir Supervisor role. Send CV to recruitments@mikameats.com "
        "before 30 June 2026."
    )
    result = extract_apply_from_description(text)
    assert result.apply_email == "recruitments@mikameats.com"
    assert result.apply_source == "description_email"


def test_description_email_extractor_skips_generic_info_email():
    text = "Contact info@company.com or careers@company.com for applications."
    result = extract_apply_from_description(text)
    assert result.apply_email == "careers@company.com"


def test_description_url_extractor_skips_zedapply_hosts():
    text = "Apply at https://jobs.example.com/apply and https://zedapply.com/jobs/1"
    result = extract_apply_from_description(text)
    assert result.apply_url == "https://jobs.example.com/apply"
    assert result.apply_source == "description_url"


def test_merge_description_extraction_does_not_overwrite_existing():
    row = {"apply_url": "https://existing.test/apply", "apply_email": "keep@test.com"}
    merge_description_extraction(
        row,
        "Other email hr@other.com and https://other.com/jobs",
    )
    assert row["apply_url"] == "https://existing.test/apply"
    assert row["apply_email"] == "keep@test.com"


def test_deadline_extractor_finds_iso_date():
    assert extract_deadline_from_text_regex("Apply by 2026-06-15 end of day") == date(
        2026, 6, 15
    )


def test_deadline_extractor_finds_natural_language_date():
    assert parse_closing_date("2026-12-01") == date(2026, 12, 1)


@pytest.mark.asyncio
async def test_deadline_extractor_llm_returns_iso():
    from app.services import job_deadline_extractor as mod

    mock_resp = MagicMock()
    mock_resp.choices = [
        MagicMock(message=MagicMock(content='{"closing_date": "2026-08-20"}'))
    ]
    with patch.object(mod, "_client") as mock_client:
        mock_client.return_value.chat.completions.create = MagicMock(return_value=mock_resp)
        with patch.object(mod.get_settings(), "openrouter_api_key", "test-key"):
            result = await mod.extract_closing_date_llm(
                "Submission deadline: 20 August 2026",
                title="Analyst",
                company="ACME",
            )
    assert result == date(2026, 8, 20)


def test_job_activation_inactive_when_no_apply_path():
    state = compute_review_state(
        apply_url=None,
        apply_email=None,
        closing_date="2026-06-30",
    )
    assert state.is_active is False
    assert state.is_review_required is True
    assert state.review_reason == "no_apply_path"


def test_job_activation_requires_review_when_no_deadline():
    state = compute_review_state(
        apply_url="https://co.test/apply",
        apply_email=None,
        closing_date=None,
    )
    assert state.is_active is True
    assert state.is_review_required is True
    assert state.review_reason == "no_deadline"


def test_can_publish_after_admin_edit():
    assert can_publish_after_admin_edit(
        "https://x.test/a", "hr@test.com", "2026-07-01"
    )
    assert not can_publish_after_admin_edit("https://x.test/a", None, None)


class MemoryQuery:
    def __init__(self, store, table):
        self.store = store
        self.table = table
        self._filters: list = []
        self._order = None
        self._range = None
        self.count = None

    def select(self, *args, **kwargs):
        self.count = "exact" if kwargs.get("count") else None
        return self

    def eq(self, col, val):
        self._filters.append(("eq", col, val))
        return self

    def is_(self, col, val):
        self._filters.append(("is", col, val))
        return self

    def order(self, col, desc=False):
        self._order = (col, desc)
        return self

    def range(self, start, end):
        self._range = (start, end)
        return self

    def execute(self):
        rows = list(self.store.rows(self.table))
        for kind, col, val in self._filters:
            if kind == "eq":
                rows = [r for r in rows if r.get(col) == val]
            elif kind == "is" and val == "null":
                rows = [r for r in rows if r.get(col) is None]
        if self._order:
            col, desc = self._order
            rows.sort(key=lambda r: r.get(col) or "", reverse=desc)
        if self._range:
            rows = rows[self._range[0] : self._range[1] + 1]
        result = MagicMock()
        result.data = rows
        result.count = len(self.store.tables.get(self.table, []))
        return result

    def update(self, patch):
        self._patch = patch
        return self

    def single(self):
        return self


class MemoryTableUpdate:
    def __init__(self, store, table, patch):
        self.store = store
        self.table = table
        self.patch = patch
        self._id = None

    def eq(self, col, val):
        self._id = val
        return self

    def execute(self):
        for row in self.store.rows(self.table):
            if row.get("id") == self._id:
                row.update(self.patch)
                result = MagicMock()
                result.data = [row]
                return result
        result = MagicMock()
        result.data = []
        return result


class MemorySupabase:
    def __init__(self, tables=None):
        self.tables = tables or {}

    def rows(self, table):
        return self.tables.setdefault(table, [])

    def table(self, table):
        q = MemoryQuery(self, table)

        def _update(patch):
            return MemoryTableUpdate(self, table, patch)

        q.update = _update
        return q


def test_admin_review_endpoint_lists_only_pending(client: TestClient, admin_headers: dict, fake_supabase):
    from tests.conftest import FakeSupabaseQuery
    from app.core.deps import get_supabase, require_admin
    from main import app

    fake_supabase.set_table(
        "users",
        FakeSupabaseQuery(
            data=[{"id": "admin-user-id", "phone": "+260971111111", "role": "admin"}]
        ),
    )
    fake_supabase.set_table(
        "jobs",
        FakeSupabaseQuery(
            data=[
                {
                    "id": "pending-1",
                    "title": "NOCAD Role",
                    "company": "NOCAD",
                    "source": "scraper",
                    "source_url": "https://example.com/j1",
                    "review_reason": "no_apply_path",
                    "admin_review_reason": None,
                    "created_at": "2026-05-20T10:00:00Z",
                }
            ],
            count=1,
        ),
    )
    app.dependency_overrides[require_admin] = lambda: {
        "id": "admin-user-id",
        "role": "admin",
    }
    with patch("app.api.v1.admin_review_jobs.get_supabase", return_value=fake_supabase):
        res = client.get("/api/v1/admin/review-jobs", headers=admin_headers)
    app.dependency_overrides.pop(require_admin, None)
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert len(body["jobs"]) == 1
    assert body["jobs"][0]["id"] == "pending-1"
    assert "no_apply_path" in body["jobs"][0]["reasons"]


def test_admin_review_overview_returns_counts(client: TestClient, admin_headers: dict, fake_supabase):
    from tests.conftest import FakeSupabaseQuery
    from app.core.deps import require_admin
    from main import app

    fake_supabase.set_table(
        "jobs",
        FakeSupabaseQuery(data=[], count=42),
    )
    app.dependency_overrides[require_admin] = lambda: {
        "id": "admin-user-id",
        "role": "admin",
    }
    with patch("app.api.v1.admin_review_jobs.get_supabase", return_value=fake_supabase):
        res = client.get("/api/v1/admin/review-jobs/overview", headers=admin_headers)
    app.dependency_overrides.pop(require_admin, None)
    assert res.status_code == 200
    body = res.json()
    assert body["need_review"] == 42
    assert "active_public" in body
    assert "dismiss_expired_eligible" in body


@pytest.mark.asyncio
async def test_admin_review_edit_promotes_to_active():
    from app.api.v1.admin_review_jobs import update_review_job
    from app.schemas.admin import AdminJobReviewUpdate

    job_id = "job-review-1"
    supabase = MemorySupabase(
        {
            "jobs": [
                {
                    "id": job_id,
                    "apply_url": None,
                    "apply_email": None,
                    "closing_date": None,
                    "review_reason": "both",
                    "is_review_required": True,
                    "is_active": False,
                }
            ]
        }
    )

    class JobSelectQuery(MemoryQuery):
        def single(self):
            return self

        def execute(self):
            rows = [r for r in self.store.rows(self.table) if r.get("id") == job_id]
            result = MagicMock()
            result.data = rows[0] if rows else None
            return result

    def table(name):
        if name == "jobs":
            q = JobSelectQuery(supabase, name)

            def _update(patch):
                return MemoryTableUpdate(supabase, name, patch)

            q.update = _update
            return q
        return MemoryQuery(supabase, name)

    supabase.table = table

    with patch("app.api.v1.admin_review_jobs.get_supabase", return_value=supabase):
        out = await update_review_job(
            job_id,
            AdminJobReviewUpdate(
                apply_email="hr@company.com",
                closing_date=date(2026, 9, 1),
            ),
            current_user={"id": "admin-user-id"},
            supabase=supabase,
        )
    assert out["is_active"] is True
    assert out["is_review_required"] is False
    updated = supabase.rows("jobs")[0]
    assert updated["apply_email"] == "hr@company.com"
    assert updated["is_active"] is True
