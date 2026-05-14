"""Tests for the data-subject-rights endpoints (task #63).

Covers:
- export bundle shape (presence of every promised section + exclusion
  of internal columns like cvs.embedding)
- DELETE confirmation flow (mismatched phone → 400, exact phone → 200)
- 1/hour per-user rate limit on /export
- idempotency of DELETE (second call after the row is gone → 200 with
  already_deleted=true)
- subscriptions + payments NOT hard-deleted (the storage anonymisation
  comes from the FK ON DELETE SET NULL added in migration 018 — at the
  unit level we assert the route does not issue a DELETE against
  subscriptions or payments).
"""
import json
from unittest.mock import MagicMock

import pytest

from tests.conftest import FakeSupabase, FakeSupabaseQuery


# ──────────────────────────── helpers ────────────────────────────


def _seed_full_user(fake_supabase: FakeSupabase, *, user_id: str, phone: str) -> None:
    """Seed a realistic user row + one of each downstream record so the
    export bundle covers every section."""
    fake_supabase.set_table(
        "users",
        FakeSupabaseQuery(
            data=[
                {
                    "id": user_id,
                    "phone": phone,
                    "full_name": "Test User",
                    "email": "test@example.com",
                    "location": "Lusaka",
                    "years_experience": 3,
                    "subscription_tier": "free",
                    "whatsapp_alerts": True,
                    "email_notifications_enabled": True,
                    "language": "en",
                    "is_active": True,
                    "created_at": "2026-01-01T00:00:00Z",
                }
            ]
        ),
    )
    fake_supabase.set_table(
        "subscriptions",
        FakeSupabaseQuery(
            data=[
                {
                    "id": "sub-1",
                    "user_id": user_id,
                    "tier": "free",
                    "status": "active",
                    "current_period_start": "2026-01-01T00:00:00Z",
                    "matches_used": 0,
                    "matches_limit": 10,
                    "created_at": "2026-01-01T00:00:00Z",
                }
            ]
        ),
    )
    fake_supabase.set_table(
        "payments",
        FakeSupabaseQuery(
            data=[
                {
                    "id": "pay-1",
                    "user_id": user_id,
                    "amount": 25000,
                    "currency": "ZMW",
                    "payment_method": "mtn_money",
                    "provider": "dpo_pay",
                    "provider_ref": "ref-xyz",
                    "status": "completed",
                    "created_at": "2026-01-15T00:00:00Z",
                }
            ]
        ),
    )
    fake_supabase.set_table(
        "cvs",
        FakeSupabaseQuery(
            data=[
                {
                    "id": "cv-1",
                    "file_type": "pdf",
                    "raw_text": "raw cv text",
                    "parsed_data": {"name": "Test User", "skills": ["python"]},
                    "parsing_confidence": 0.9,
                    "is_primary": True,
                    "created_at": "2026-02-01T00:00:00Z",
                    # If the route SELECT widens, embedding must NOT
                    # appear in the export. Seed it so a regression
                    # (e.g. select("*")) would surface it.
                    "embedding": [0.1] * 768,
                }
            ]
        ),
    )
    fake_supabase.set_table(
        "cv_generations",
        FakeSupabaseQuery(
            data=[
                {
                    "id": "gen-1",
                    "job_title": "Software Engineer",
                    "company": "Acme",
                    "content": "Tailored CV content",
                    "word_count": 350,
                    "metadata": {"source_cv_id": "cv-1"},
                    "created_at": "2026-03-01T00:00:00Z",
                }
            ]
        ),
    )
    fake_supabase.set_table(
        "matches",
        FakeSupabaseQuery(
            data=[
                {
                    "id": "match-1",
                    "job_id": "job-1",
                    "cv_id": "cv-1",
                    "score": 82.5,
                    "vector_score": 0.85,
                    "skill_score": 0.7,
                    "bonus_score": 0.1,
                    "matched_skills": ["python"],
                    "missing_skills": ["go"],
                    "explanation": "Good vector fit, partial skill overlap.",
                    "status": "new",
                    "created_at": "2026-03-05T00:00:00Z",
                }
            ]
        ),
    )
    fake_supabase.set_table(
        "jobs",
        FakeSupabaseQuery(
            data=[
                {
                    "id": "job-1",
                    "title": "Senior Software Engineer",
                    "company": "Acme Corp",
                    "location": "Lusaka",
                    "description": "We need a Python developer.",
                    "requirements": ["python", "fastapi"],
                    "salary_min": 50000,
                    "salary_max": 80000,
                    "apply_url": "https://example.com/apply",
                    "apply_email": None,
                    "source": "manual",
                    "source_url": None,
                    "closing_date": "2026-04-01",
                    "posted_at": "2026-02-15T00:00:00Z",
                }
            ]
        ),
    )
    fake_supabase.set_table(
        "user_skills",
        FakeSupabaseQuery(
            data=[
                {
                    "proficiency": "advanced",
                    "source": "cv_parse",
                    "skills": {"name": "python"},
                }
            ]
        ),
    )


# ─────────────────────────── export tests ───────────────────────────


class TestExportBundleShape:
    """The bundle must include every promised section and NOTHING the
    user shouldn't see (e.g. cvs.embedding)."""

    def test_export_includes_all_sections(self, client, fake_supabase, auth_headers):
        _seed_full_user(fake_supabase, user_id="test-user-id", phone="+260971234567")
        resp = client.get("/api/v1/me/export", headers=auth_headers)
        assert resp.status_code == 200

        # Streamed JSON download — Content-Disposition + dated filename.
        cd = resp.headers["content-disposition"]
        assert "attachment" in cd
        assert "zedcv-data-export-" in cd
        assert cd.endswith('.json"')
        assert resp.headers["content-type"].startswith("application/json")
        assert resp.headers["cache-control"] == "no-store"

        bundle = json.loads(resp.text)
        # Every promised top-level key must be present.
        for key in [
            "export_format_version",
            "exported_at",
            "data_controller",
            "rights_basis",
            "profile",
            "preferences",
            "subscriptions",
            "payments",
            "cvs",
            "cv_generations",
            "matches",
            "user_skills",
        ]:
            assert key in bundle, f"export bundle missing {key!r}"

        # Profile + preferences shape
        assert bundle["profile"]["id"] == "test-user-id"
        assert bundle["profile"]["phone"] == "+260971234567"
        assert bundle["preferences"]["whatsapp_alerts"] is True
        assert bundle["preferences"]["language"] == "en"

        # Subscription + payment history surfaced as lists
        assert len(bundle["subscriptions"]) == 1
        assert len(bundle["payments"]) == 1
        assert bundle["payments"][0]["amount"] == 25000

        # CV generations + user_skills carry their content
        assert bundle["cv_generations"][0]["job_title"] == "Software Engineer"
        assert bundle["user_skills"][0]["name"] == "python"

    def test_export_excludes_cv_embedding(
        self, client, fake_supabase, auth_headers, monkeypatch
    ):
        """cvs.embedding is internal — the route must request an explicit
        column allowlist that excludes it. (FakeSupabaseQuery.select() is
        a no-op so the resulting payload can't be asserted; we assert the
        column list the route sent to the DB, which is where production
        Supabase does the actual filtering.)"""
        _seed_full_user(fake_supabase, user_id="test-user-id", phone="+260971234567")

        cvs_select_args: list[str] = []
        original_table = fake_supabase.table

        def _spying_table(name: str):
            q = original_table(name)
            if name == "cvs":
                real_select = q.select

                def _select(*args, **kwargs):
                    cvs_select_args.extend(args)
                    return real_select(*args, **kwargs)

                q.select = _select  # type: ignore[method-assign]
            return q

        monkeypatch.setattr(fake_supabase, "table", _spying_table)

        resp = client.get("/api/v1/me/export", headers=auth_headers)
        assert resp.status_code == 200

        # The route must NOT use SELECT * on cvs (would surface embedding),
        # and the explicit column list must NOT mention embedding.
        assert cvs_select_args, "Route must call .select() on cvs at least once"
        for arg in cvs_select_args:
            assert arg != "*", (
                "cvs export must use an explicit column allowlist, not '*'"
            )
            assert "embedding" not in arg, (
                "cvs.embedding must NOT be in the export column list — it "
                "is internal vector data."
            )

    def test_export_attaches_job_snapshot_to_each_match(
        self, client, fake_supabase, auth_headers
    ):
        _seed_full_user(fake_supabase, user_id="test-user-id", phone="+260971234567")
        resp = client.get("/api/v1/me/export", headers=auth_headers)
        bundle = json.loads(resp.text)

        assert len(bundle["matches"]) == 1
        match = bundle["matches"][0]
        snap = match.get("job_snapshot")
        assert snap is not None, "Every match should carry a job_snapshot"
        assert snap["title"] == "Senior Software Engineer"
        assert snap["company"] == "Acme Corp"
        # Internal columns like `embedding` must not appear here either.
        assert "embedding" not in snap

    def test_export_404s_when_user_row_missing(
        self, client, fake_supabase, auth_headers
    ):
        # Valid JWT, but the user row is gone — export should 404, not
        # 500 or empty-bundle.
        fake_supabase.set_table("users", FakeSupabaseQuery(data=[]))
        resp = client.get("/api/v1/me/export", headers=auth_headers)
        assert resp.status_code == 404


class TestExportRateLimit:
    """The endpoint is decorated with @limiter.limit('1/hour', key_func=
    _per_user_key). We re-enable the limiter for this test to confirm
    the second call within the window 429s."""

    def test_second_call_within_hour_is_429(
        self, client, fake_supabase, auth_headers, monkeypatch
    ):
        from app.core.rate_limit import limiter

        _seed_full_user(fake_supabase, user_id="test-user-id", phone="+260971234567")

        # Test client uses limiter.enabled = False (set in conftest). Flip
        # it back on for this test; reset after.
        prev = limiter.enabled
        limiter.enabled = True
        # Clear any state from prior tests in this process so the bucket
        # starts empty for this user.
        try:
            limiter.reset()
        except Exception:
            pass
        try:
            r1 = client.get("/api/v1/me/export", headers=auth_headers)
            assert r1.status_code == 200, r1.text

            r2 = client.get("/api/v1/me/export", headers=auth_headers)
            assert r2.status_code == 429, (
                f"Second call within the hour should be rate-limited, "
                f"got {r2.status_code}: {r2.text}"
            )
        finally:
            limiter.enabled = prev
            try:
                limiter.reset()
            except Exception:
                pass


# ─────────────────────────── delete tests ───────────────────────────


class TestDeleteAccount:
    """DELETE /api/v1/me — phone confirmation flow + idempotency."""

    def test_delete_requires_matching_phone(self, client, fake_supabase, auth_headers):
        _seed_full_user(fake_supabase, user_id="test-user-id", phone="+260971234567")
        resp = client.request(
            "DELETE",
            "/api/v1/me",
            headers=auth_headers,
            json={"confirm_phone": "+260970000000"},
        )
        assert resp.status_code == 400
        assert "match" in resp.json()["detail"].lower()

    def test_delete_with_matching_phone_succeeds(
        self, client, fake_supabase, auth_headers
    ):
        _seed_full_user(fake_supabase, user_id="test-user-id", phone="+260971234567")
        # Capture storage interactions to confirm the CV bucket was swept.
        storage = MagicMock()
        bucket = MagicMock()
        bucket.list.return_value = [{"name": "old-cv.pdf"}, {"name": "newer.pdf"}]
        bucket.remove.return_value = None
        storage.from_.return_value = bucket
        fake_supabase.storage = storage

        resp = client.request(
            "DELETE",
            "/api/v1/me",
            headers=auth_headers,
            json={"confirm_phone": "+260971234567"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body == {
            "deleted": True,
            "already_deleted": False,
            "user_id": "test-user-id",
        }

        # Storage purge actually ran with the right bucket + scoped paths.
        bucket.list.assert_called_once_with("cvs/test-user-id")
        bucket.remove.assert_called_once_with(
            ["cvs/test-user-id/old-cv.pdf", "cvs/test-user-id/newer.pdf"]
        )

    def test_delete_byte_exact_compare_rejects_close_match(
        self, client, fake_supabase, auth_headers
    ):
        """A trailing space, lowercase, or alt-encoding must NOT pass —
        the route uses hmac.compare_digest on raw bytes."""
        _seed_full_user(fake_supabase, user_id="test-user-id", phone="+260971234567")
        for variant in ["+260971234567 ", " +260971234567", "260971234567"]:
            resp = client.request(
                "DELETE",
                "/api/v1/me",
                headers=auth_headers,
                json={"confirm_phone": variant},
            )
            assert resp.status_code == 400, (
                f"Variant {variant!r} should NOT pass the confirmation"
            )

    def test_delete_is_idempotent_when_user_already_gone(
        self, client, fake_supabase, auth_headers
    ):
        # Valid JWT but the row no longer exists in the DB.
        fake_supabase.set_table("users", FakeSupabaseQuery(data=[]))
        resp = client.request(
            "DELETE",
            "/api/v1/me",
            headers=auth_headers,
            json={"confirm_phone": "+260971234567"},
        )
        assert resp.status_code == 200
        assert resp.json() == {
            "deleted": False,
            "already_deleted": True,
            "user_id": None,
        }

    def test_delete_requires_confirm_phone_field(
        self, client, fake_supabase, auth_headers
    ):
        _seed_full_user(fake_supabase, user_id="test-user-id", phone="+260971234567")
        # Missing the field entirely → 422 (pydantic) not 400 (mismatch).
        resp = client.request(
            "DELETE", "/api/v1/me", headers=auth_headers, json={}
        )
        assert resp.status_code == 422

    def test_delete_does_not_hard_delete_subscriptions_or_payments(
        self, client, fake_supabase, auth_headers, monkeypatch
    ):
        """The retention guarantee is FK-driven (ON DELETE SET NULL in
        migration 018), not application-side. As a defence-in-depth
        contract we ALSO assert the route does not issue a DELETE
        against subscriptions or payments — a refactor that flips that
        would silently break the 7-year tax-retention promise.

        Implemented by recording every `(table_name, op)` the route
        triggers on the fake client.
        """
        _seed_full_user(fake_supabase, user_id="test-user-id", phone="+260971234567")

        deletes_against: list[str] = []
        original_table = fake_supabase.table

        def _spying_table(name: str):
            q = original_table(name)
            real_delete = q.delete

            def _delete(*a, **kw):
                deletes_against.append(name)
                return real_delete(*a, **kw)

            q.delete = _delete  # type: ignore[method-assign]
            return q

        monkeypatch.setattr(fake_supabase, "table", _spying_table)

        resp = client.request(
            "DELETE",
            "/api/v1/me",
            headers=auth_headers,
            json={"confirm_phone": "+260971234567"},
        )
        assert resp.status_code == 200

        # The route must delete users (cascade does the rest) and the
        # phone-keyed otp_codes sweep. It must NOT directly delete
        # subscriptions or payments.
        assert "users" in deletes_against
        assert "subscriptions" not in deletes_against, (
            "Subscriptions must be retained (anonymised) for tax compliance"
        )
        assert "payments" not in deletes_against, (
            "Payments must be retained (anonymised) for tax compliance"
        )
