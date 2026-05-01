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
