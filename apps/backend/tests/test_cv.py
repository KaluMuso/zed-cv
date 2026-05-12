"""Smoke tests for CV upload routes."""
from io import BytesIO
from unittest.mock import AsyncMock, patch
from tests.conftest import FakeSupabaseQuery


class TestCVUpload:
    def test_upload_unauthenticated(self, client):
        """CV upload requires auth."""
        resp = client.post(
            "/api/v1/cv/upload",
            files={"file": ("test.pdf", b"fake-pdf", "application/pdf")},
        )
        assert resp.status_code in (401, 403)

    def test_upload_invalid_type(self, client, auth_headers):
        """Rejects unsupported file types."""
        resp = client.post(
            "/api/v1/cv/upload",
            headers=auth_headers,
            files={"file": ("test.txt", b"hello", "text/plain")},
        )
        assert resp.status_code == 422

    @patch("app.api.v1.cv.generate_embedding", new_callable=AsyncMock)
    @patch("app.api.v1.cv.parse_cv_with_llm", new_callable=AsyncMock)
    @patch("app.api.v1.cv.extract_text_from_file", new_callable=AsyncMock)
    def test_upload_success(
        self,
        mock_extract,
        mock_parse,
        mock_embed,
        client,
        auth_headers,
        fake_supabase,
    ):
        """Successful upload extracts skills and returns result."""
        mock_extract.return_value = "John Doe\nPython Developer\n5 years experience in Python, FastAPI, PostgreSQL"
        mock_parse.return_value = {
            "full_name": "John Doe",
            "skills": ["python", "fastapi", "postgresql"],
            "experience_summary": "5 years backend development",
            "confidence": 0.85,
        }
        mock_embed.return_value = [0.1] * 1536

        fake_supabase.set_table(
            "cvs",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "cv-001",
                        "user_id": "test-user-id",
                        "file_url": "cvs/test/test.pdf",
                    }
                ]
            ),
        )
        fake_supabase.set_table("skills", FakeSupabaseQuery(data=[]))
        fake_supabase.set_table("user_skills", FakeSupabaseQuery(data=[]))

        resp = client.post(
            "/api/v1/cv/upload",
            headers=auth_headers,
            files={
                "file": ("resume.pdf", b"fake-pdf-content", "application/pdf")
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "cv_id" in body
        assert "parsed_skills" in body

    @patch("app.api.v1.cv.generate_embedding", new_callable=AsyncMock)
    @patch("app.api.v1.cv.parse_cv_with_llm", new_callable=AsyncMock)
    @patch("app.api.v1.cv.extract_text_from_file", new_callable=AsyncMock)
    def test_upload_skips_llm_calls_on_cache_hit(
        self,
        mock_extract,
        mock_parse,
        mock_embed,
        client,
        auth_headers,
        fake_supabase,
    ):
        """When ai_cache has a result for this text hash, upload skips
        the Gemini call entirely. This is the cost-saving contract -
        a re-uploaded CV must not double-spend on AI calls."""
        mock_extract.return_value = (
            "John Doe\nPython Developer\n5 years experience in Python, FastAPI, PostgreSQL"
        )
        # FakeSupabaseQuery ignores the eq() filter and returns whatever
        # data we set, so any ai_cache lookup will hit this row - both
        # for the parse-cache and the embed-cache lookups.
        fake_supabase.set_table(
            "ai_cache",
            FakeSupabaseQuery(
                data=[
                    {
                        "result": {
                            "full_name": "Cached Person",
                            "skills": ["cached-skill"],
                            "experience_summary": "from cache",
                            "confidence": 0.99,
                        }
                    }
                ]
            ),
        )
        fake_supabase.set_table(
            "cvs",
            FakeSupabaseQuery(
                data=[{"id": "cv-cached", "user_id": "test-user-id", "file_url": "x"}]
            ),
        )
        fake_supabase.set_table("skills", FakeSupabaseQuery(data=[]))
        fake_supabase.set_table("user_skills", FakeSupabaseQuery(data=[]))

        resp = client.post(
            "/api/v1/cv/upload",
            headers=auth_headers,
            files={"file": ("resume.pdf", b"x" * 100, "application/pdf")},
        )
        assert resp.status_code == 200
        # Critical: cache hit short-circuited the LLM call.
        mock_parse.assert_not_called()
        mock_embed.assert_not_called()
