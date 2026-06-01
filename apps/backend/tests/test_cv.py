"""Smoke tests for CV upload routes."""
from io import BytesIO
from unittest.mock import AsyncMock, patch
from tests.conftest import FakeSupabaseQuery


# task #77: every upload test that gets past the Content-Type allowlist
# must short-circuit the libmagic sniff to a matching MIME, because the
# test bytes (e.g. b"fake-pdf-content") aren't real PDF/JPG/etc. Tests
# that specifically exercise the sniff (renamed-EXE, MIME mismatch)
# patch this with their own return value.
def _mime_for_pdf(_bytes):
    return "application/pdf"


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

    def test_upload_renamed_executable_rejected(
        self, client, auth_headers
    ):
        """task #77: a .exe renamed to .pdf must be rejected at the sniff
        step with a 400. Critical — without this, the previous header-
        only check would happily store an arbitrary binary as if it were
        a PDF and feed it to the parsing pipeline."""
        # MZ header = "This is a DOS/Windows executable". libmagic
        # identifies these as application/x-dosexec on Linux and
        # application/x-msdownload on some macOS builds. Either way,
        # NOT application/pdf, so verification should fail.
        exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00\x04" + (b"\x00" * 200)

        with patch(
            "app.api.v1.cv._sniff_mime",
            return_value="application/x-dosexec",
        ):
            resp = client.post(
                "/api/v1/cv/upload",
                headers=auth_headers,
                files={"file": ("malware.pdf", exe_bytes, "application/pdf")},
            )

        assert resp.status_code == 400, resp.text
        detail = resp.json()["detail"].lower()
        # User-facing error must name BOTH what we saw and what was
        # claimed so the user understands why their "pdf" was rejected.
        assert "application/x-dosexec" in detail
        assert "pdf" in detail
        # Defence-in-depth phrasing — flags that the file looks like
        # it was renamed, not just that the type was wrong.
        assert "renamed" in detail

    def test_upload_zip_disguised_as_pdf_rejected(
        self, client, auth_headers
    ):
        """A real .zip with a .pdf extension must also be rejected — the
        sniffer maps zip to application/zip, which is in the docx
        whitelist but NOT in the pdf whitelist."""
        with patch(
            "app.api.v1.cv._sniff_mime",
            return_value="application/zip",
        ):
            resp = client.post(
                "/api/v1/cv/upload",
                headers=auth_headers,
                files={
                    "file": (
                        "archive.pdf",
                        b"PK\x03\x04" + b"\x00" * 100,
                        "application/pdf",
                    )
                },
            )
        assert resp.status_code == 400
        assert "application/zip" in resp.json()["detail"]

    @patch("app.api.v1.cv._sniff_mime", side_effect=_mime_for_pdf)
    @patch("app.api.v1.cv.resolve_skill_ids", new_callable=AsyncMock)
    @patch("app.api.v1.cv.generate_embedding", new_callable=AsyncMock)
    @patch("app.api.v1.cv.parse_cv_with_llm", new_callable=AsyncMock)
    @patch("app.api.v1.cv.extract_text_from_file", new_callable=AsyncMock)
    def test_upload_success(
        self,
        mock_extract,
        mock_parse,
        mock_embed,
        mock_resolve,
        mock_sniff,
        client,
        auth_headers,
        fake_supabase,
    ):
        """Successful upload extracts skills and returns result."""
        # Migration 024+ routes skills through the hybrid resolver. Stub
        # it so this test stays focused on the upload happy-path; the
        # resolver itself is covered by test_skill_resolver.
        mock_resolve.return_value = ["sk-python", "sk-fastapi", "sk-pg"]
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

    @patch("app.api.v1.cv._sniff_mime", side_effect=_mime_for_pdf)
    @patch("app.api.v1.cv.resolve_skill_ids", new_callable=AsyncMock)
    @patch("app.api.v1.cv.generate_embedding", new_callable=AsyncMock)
    @patch("app.api.v1.cv.parse_cv_with_llm", new_callable=AsyncMock)
    @patch("app.api.v1.cv.extract_text_from_file", new_callable=AsyncMock)
    def test_upload_skips_llm_calls_on_cache_hit(
        self,
        mock_extract,
        mock_parse,
        mock_embed,
        mock_resolve,
        mock_sniff,
        client,
        auth_headers,
        fake_supabase,
    ):
        """When ai_cache has a result for this text hash, upload skips
        the Gemini call entirely. This is the cost-saving contract -
        a re-uploaded CV must not double-spend on AI calls."""
        mock_resolve.return_value = ["sk-cached"]
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

    @patch("app.api.v1.cv._sniff_mime", side_effect=_mime_for_pdf)
    @patch("app.api.v1.cv.extract_text_from_file", new_callable=AsyncMock)
    def test_upload_image_scanned_pdf_rejected(
        self,
        mock_extract,
        mock_sniff,
        client,
        auth_headers,
    ):
        """Scanned PDFs with no extractable text return a structured 422."""
        mock_extract.return_value = "   \n  "

        resp = client.post(
            "/api/v1/cv/upload",
            headers=auth_headers,
            files={"file": ("scan.pdf", b"fake-pdf-content", "application/pdf")},
        )

        assert resp.status_code == 422, resp.text
        body = resp.json()
        assert body["detail"] == "image_scanned_pdf"
        assert "scanned image" in body["user_message"].lower()
