"""Tests for POST /cv/build-from-scratch."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def auth_headers():
    from app.core.deps import get_current_user_id
    from main import app

    app.dependency_overrides[get_current_user_id] = lambda: "wizard-user"
    yield {"Authorization": "Bearer test-token"}
    app.dependency_overrides.pop(get_current_user_id, None)


@patch("app.api.v1.cv.render_cv_pdf")
def test_build_from_scratch_returns_signed_url(mock_render, client: TestClient, auth_headers):
    mock_render.return_value = (b"%PDF-fake-content", 42)

    mock_storage = MagicMock()
    mock_storage.upload.return_value = {"path": "ok"}
    mock_storage.create_signed_url.return_value = {
        "signedURL": "https://example.com/signed.pdf",
    }

    mock_supabase = MagicMock()

    class FakeQuery:
        def __init__(self, data=None):
            self._data = data or []

        def select(self, *a, **kw):
            return self

        def eq(self, *a, **kw):
            return self

        def limit(self, *a, **kw):
            return self

        def update(self, *a, **kw):
            return self

        def insert(self, data):
            row = {**data, "id": data.get("id", "new-cv-id")}
            self._data = [row]
            return self

        def execute(self):
            return MagicMock(data=self._data)

    cvs_query = FakeQuery([])
    mock_supabase.table.side_effect = lambda name: cvs_query if name == "cvs" else FakeQuery()
    mock_supabase.storage.from_.return_value = mock_storage

    from app.core.deps import get_supabase
    from main import app

    app.dependency_overrides[get_supabase] = lambda: mock_supabase

    body = {
        "summary": "Experienced professional.",
        "basics": {
            "full_name": "Test User",
            "phone": "+260971234567",
            "email": "test@example.com",
            "location": "Lusaka",
            "headline": "Engineer",
        },
        "experience": [],
        "education": [],
        "skills": ["Python"],
        "style": {"template": "modern", "accent_color": "#0E5C3A", "show_summary": True},
    }

    res = client.post("/api/v1/cv/build-from-scratch", json=body, headers=auth_headers)
    app.dependency_overrides.pop(get_supabase, None)

    assert res.status_code == 200
    data = res.json()
    assert data["pdf_url"] == "https://example.com/signed.pdf"
    assert data["render_time_ms"] == 42
    assert "cv_id" in data
