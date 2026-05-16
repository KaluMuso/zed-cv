"""Tests for the legal-docs API (task #62).

Covers:
- public GET returns 404 when no row exists (frontend uses that as a
  fallback signal)
- admin GET returns an empty doc on first-open (so the editor doesn't
  see an error on a slug that's never been saved)
- admin PATCH upserts the row + sanitises rendered HTML
- slug whitelist is enforced
- non-admin callers get 403 on both admin paths
- the markdown→HTML pipeline strips dangerous tags (XSS defence at the
  storage boundary)
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from jose import jwt

from app.api.v1.legal import _render_and_sanitise
from tests.conftest import FakeSupabaseQuery


def _admin_token() -> str:
    """A JWT whose sub matches a row we seed in the users table with
    role=superadmin. require_admin reads role off the DB row, so we
    have to seed both."""
    import os
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": "admin-user-id",
            "phone": "+260971111111",
            "exp": now + timedelta(hours=24),
            "iat": now,
        },
        os.environ["JWT_SECRET"],
        algorithm="HS256",
    )


def _seed_admin(fake_supabase) -> None:
    """Seed the users table so require_admin's role lookup succeeds."""
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


# ─────────────────────────── sanitiser ───────────────────────────


class TestSanitiser:
    """Pin the trust-boundary policy of _render_and_sanitise. These are
    the cases that, if regressed, would let a stored XSS land in
    legal_docs.content_html."""

    def test_renders_basic_markdown(self):
        html = _render_and_sanitise("# Heading\n\nParagraph **bold** word.")
        assert "<h1>" in html and "</h1>" in html
        assert "<strong>bold</strong>" in html

    def test_strips_script_tag_from_markdown(self):
        """Markdown allows inline HTML. A <script> typed into the source
        must NOT survive the sanitiser. bleach correctly strips the
        <script> TAG; the inner text remains as a harmless text node
        (which is preferable to losing user content silently)."""
        html = _render_and_sanitise(
            "Hello <script>alert(1)</script> world"
        )
        # The executable tag itself must be gone — that's the security
        # contract. The text inside becomes inert.
        assert "<script" not in html
        assert "</script" not in html
        # And the harmless "hello" + "world" framing survives.
        assert "Hello" in html and "world" in html

    def test_strips_event_handler_attributes(self):
        html = _render_and_sanitise(
            'Click <a href="https://ok.com" onclick="alert(1)">here</a>'
        )
        assert "onclick" not in html
        assert "https://ok.com" in html

    def test_rejects_javascript_url_in_link(self):
        html = _render_and_sanitise('[click](javascript:alert(1))')
        # bleach drops the unsafe href; the link text survives.
        assert "javascript:" not in html

    def test_keeps_mailto_links(self):
        """The privacy page links to support email. mailto: stays in the
        allowed-protocols list."""
        html = _render_and_sanitise(
            "[Email us](mailto:convergeozambia@gmail.com)"
        )
        assert "mailto:convergeozambia@gmail.com" in html

    def test_strips_iframe(self):
        html = _render_and_sanitise(
            '<iframe src="https://evil.com"></iframe>'
        )
        assert "<iframe" not in html

    def test_preserves_lists(self):
        html = _render_and_sanitise("- one\n- two\n- three")
        assert "<ul>" in html
        assert html.count("<li>") == 3


# ────────────────────────── public GET ──────────────────────────


class TestPublicGet:
    def test_404_when_no_row(self, client, fake_supabase):
        """Empty table → 404 so the frontend renders the inline fallback."""
        fake_supabase.set_table("legal_docs", FakeSupabaseQuery(data=[]))
        resp = client.get("/api/v1/legal/privacy")
        assert resp.status_code == 404

    def test_returns_row_when_present(self, client, fake_supabase):
        fake_supabase.set_table(
            "legal_docs",
            FakeSupabaseQuery(
                data=[
                    {
                        "slug": "privacy",
                        "version": "1.1",
                        "content_md": "# Updated",
                        "content_html": "<h1>Updated</h1>",
                        "last_modified_by": None,
                        "last_modified_at": "2026-05-15T12:00:00Z",
                    }
                ]
            ),
        )
        resp = client.get("/api/v1/legal/privacy")
        assert resp.status_code == 200
        body = resp.json()
        assert body["version"] == "1.1"
        assert body["content_md"] == "# Updated"
        assert "<h1>" in body["content_html"]

    def test_unknown_slug_404s(self, client, fake_supabase):
        resp = client.get("/api/v1/legal/not-a-real-slug")
        assert resp.status_code == 404
        assert "Unknown legal slug" in resp.json()["detail"]


# ────────────────────────── admin auth ──────────────────────────


class TestAdminAuth:
    def test_admin_get_requires_auth(self, client):
        resp = client.get("/api/v1/admin/legal/privacy")
        assert resp.status_code in (401, 403)

    def test_admin_patch_requires_auth(self, client):
        resp = client.patch(
            "/api/v1/admin/legal/privacy",
            json={"version": "1.0", "content_md": "# Hi"},
        )
        assert resp.status_code in (401, 403)

    def test_non_admin_cannot_read(self, client, auth_headers, fake_supabase):
        """A valid user JWT but role=user gets 403."""
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
        resp = client.get("/api/v1/admin/legal/privacy", headers=auth_headers)
        assert resp.status_code == 403


# ────────────────────────── admin GET ──────────────────────────


class TestAdminGet:
    def test_returns_empty_doc_on_first_open(self, client, fake_supabase):
        """No row yet → 200 with empty fields so the editor opens cleanly."""
        _seed_admin(fake_supabase)
        fake_supabase.set_table("legal_docs", FakeSupabaseQuery(data=[]))

        resp = client.get(
            "/api/v1/admin/legal/privacy",
            headers={"Authorization": f"Bearer {_admin_token()}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["slug"] == "privacy"
        assert body["content_md"] == ""
        assert body["content_html"] == ""
        assert body["version"] == ""

    def test_returns_row_when_present(self, client, fake_supabase):
        _seed_admin(fake_supabase)
        fake_supabase.set_table(
            "legal_docs",
            FakeSupabaseQuery(
                data=[
                    {
                        "slug": "terms",
                        "version": "2.0",
                        "content_md": "# Terms",
                        "content_html": "<h1>Terms</h1>",
                        "last_modified_by": "admin-user-id",
                        "last_modified_at": "2026-05-15T10:00:00Z",
                    }
                ]
            ),
        )
        resp = client.get(
            "/api/v1/admin/legal/terms",
            headers={"Authorization": f"Bearer {_admin_token()}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["version"] == "2.0"
        assert body["last_modified_by"] == "admin-user-id"


# ──────────────────────── admin PATCH ────────────────────────


class TestAdminPatch:
    def test_upsert_sanitises_html(self, client, fake_supabase, monkeypatch):
        """The render+sanitise pipeline strips dangerous content BEFORE
        the upsert call. We capture the upsert payload to confirm what
        actually lands in storage."""
        _seed_admin(fake_supabase)

        # Spy on the upsert call to grab the payload the route builds.
        seen: dict = {}
        legal_docs_query = FakeSupabaseQuery(
            data=[
                {
                    "slug": "privacy",
                    "version": "1.1",
                    "content_md": "# Title",
                    "content_html": "<h1>Title</h1>",
                    "last_modified_by": "admin-user-id",
                    "last_modified_at": "2026-05-15T12:00:00Z",
                }
            ]
        )
        original_upsert = legal_docs_query.upsert

        def _spy_upsert(payload, **kw):
            seen["payload"] = payload
            return original_upsert(payload, **kw)

        legal_docs_query.upsert = _spy_upsert  # type: ignore[method-assign]
        fake_supabase.set_table("legal_docs", legal_docs_query)

        resp = client.patch(
            "/api/v1/admin/legal/privacy",
            headers={"Authorization": f"Bearer {_admin_token()}"},
            json={
                "version": "1.1",
                # The hostile fragments must NOT appear in the stored HTML.
                "content_md": (
                    "# Title\n\n"
                    "Hello <script>alert(1)</script> world. "
                    'Visit [evil](javascript:alert(2)).'
                ),
            },
        )
        assert resp.status_code == 200, resp.text

        stored = seen["payload"]
        # Source markdown is stored as-is (user's editable source). HTML
        # is the sanitised render.
        assert "<script" not in stored["content_html"]
        assert "javascript:" not in stored["content_html"]
        assert "<h1>" in stored["content_html"]
        # Slug + last_modified_by are stamped by the route, NOT taken
        # from the client body. Pinning this so a future refactor can't
        # accept client-supplied slug overrides.
        assert stored["slug"] == "privacy"
        assert stored["last_modified_by"] == "admin-user-id"

    def test_patch_rejects_unknown_slug(self, client, fake_supabase):
        _seed_admin(fake_supabase)
        resp = client.patch(
            "/api/v1/admin/legal/not-a-slug",
            headers={"Authorization": f"Bearer {_admin_token()}"},
            json={"version": "1.0", "content_md": "# Hi"},
        )
        assert resp.status_code == 404

    def test_patch_validates_body(self, client, fake_supabase):
        """content_md is required and bounded — empty / too-large bodies 422."""
        _seed_admin(fake_supabase)
        # Empty content
        r1 = client.patch(
            "/api/v1/admin/legal/privacy",
            headers={"Authorization": f"Bearer {_admin_token()}"},
            json={"version": "1.0", "content_md": ""},
        )
        assert r1.status_code == 422

        # Too large (cap is 100k chars)
        r2 = client.patch(
            "/api/v1/admin/legal/privacy",
            headers={"Authorization": f"Bearer {_admin_token()}"},
            json={"version": "1.0", "content_md": "x" * 100_001},
        )
        assert r2.status_code == 422
