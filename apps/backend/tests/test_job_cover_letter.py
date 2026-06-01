"""Tests for POST /api/v1/jobs/{job_id}/generate-cover-letter."""
from unittest.mock import AsyncMock, MagicMock, patch

from tests.conftest import FakeSupabaseQuery


class _SingleQuery(FakeSupabaseQuery):
    def single(self):
        self._single = True
        return self

    def execute(self):
        result = MagicMock()
        if getattr(self, "_single", False) and self._data:
            result.data = (
                self._data[0] if isinstance(self._data, list) else self._data
            )
        else:
            result.data = self._data
        result.count = getattr(self, "_count", None)
        return result


def _seed_user(fake_supabase, role="user"):
    fake_supabase.set_table(
        "users",
        FakeSupabaseQuery(
            data=[{"id": "test-user-id", "phone": "+260971234567", "role": role}]
        ),
    )


def _seed_subscription(fake_supabase, tier):
    fake_supabase.set_table(
        "subscriptions",
        _SingleQuery(data=[{"tier": tier, "status": "active"}]),
    )


class TestJobCoverLetterEndpoint:
    def test_free_tier_blocked(self, client, auth_headers, fake_supabase):
        _seed_user(fake_supabase)
        _seed_subscription(fake_supabase, "free")

        resp = client.post(
            "/api/v1/jobs/job-1/generate-cover-letter",
            headers=auth_headers,
        )
        assert resp.status_code == 403
        assert "Professional" in resp.json()["detail"]

    def test_professional_missing_cv(self, client, auth_headers, fake_supabase):
        _seed_user(fake_supabase)
        _seed_subscription(fake_supabase, "professional")
        fake_supabase.set_table("cvs", FakeSupabaseQuery(data=[]))

        resp = client.post(
            "/api/v1/jobs/job-1/generate-cover-letter",
            headers=auth_headers,
        )
        assert resp.status_code == 422

    @patch(
        "app.api.v1.job_cover_letter.generate_cover_letter",
        new_callable=AsyncMock,
    )
    def test_success_stores_document(
        self, mock_generate, client, auth_headers, fake_supabase
    ):
        _seed_user(fake_supabase)
        _seed_subscription(fake_supabase, "professional")
        fake_supabase.set_table(
            "cvs",
            FakeSupabaseQuery(
                data=[{"raw_text": "Experienced accountant with SAP skills."}]
            ),
        )
        fake_supabase.set_table(
            "jobs",
            FakeSupabaseQuery(
                data=[
                    {
                        "title": "Finance Manager",
                        "company": "Zed Bank",
                        "description": "Need SAP and IFRS experience.",
                    }
                ]
            ),
        )
        fake_supabase.set_table(
            "generated_documents",
            FakeSupabaseQuery(data=[]),
        )
        mock_generate.return_value = {
            "letter": "Dear Hiring Manager,\n\nI am applying...",
            "word_count": 220,
            "tone": "formal",
        }

        resp = client.post(
            "/api/v1/jobs/job-1/generate-cover-letter",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["word_count"] == 220
        assert "Dear Hiring Manager" in body["content"]
        assert body["document_id"]
        mock_generate.assert_awaited_once()
