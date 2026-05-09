"""Tier-gate tests for POST /api/v1/cover-letter/generate.

Locks in the fix for the regression where super_standard subscribers
(K500/mo, the highest tier) were being 403'd at the gate even though
they pay more than Professional users who were allowed through.

These tests stop at the tier-gate boundary and assert the next gate is
reached. We deliberately do NOT exercise CV/job lookup or LLM generation
— those are unrelated to the slice and would require heavier mocks.
"""
from unittest.mock import MagicMock

from tests.conftest import FakeSupabaseQuery


class _SingleQuery(FakeSupabaseQuery):
    """Like FakeSupabaseQuery but .single().execute() returns a single dict."""

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
    """get_current_user looks up users table for id/phone/role."""
    fake_supabase.set_table(
        "users",
        FakeSupabaseQuery(
            data=[{"id": "test-user-id", "phone": "+260971234567", "role": role}]
        ),
    )


def _seed_subscription(fake_supabase, tier):
    fake_supabase.set_table(
        "subscriptions",
        _SingleQuery(
            data=[{"tier": tier, "status": "active"}]
        ),
    )


class TestCoverLetterTierGate:
    def test_free_tier_blocked(self, client, auth_headers, fake_supabase):
        """Free users get 403 with the upgrade message."""
        _seed_user(fake_supabase)
        _seed_subscription(fake_supabase, "free")

        resp = client.post(
            "/api/v1/cover-letter/generate",
            headers=auth_headers,
            json={"job_id": "job-1", "tone": "formal"},
        )
        assert resp.status_code == 403
        assert "Professional" in resp.json()["detail"]

    def test_starter_tier_blocked(self, client, auth_headers, fake_supabase):
        """Starter (K125/mo) is below the cover-letter tier — also 403."""
        _seed_user(fake_supabase)
        _seed_subscription(fake_supabase, "starter")

        resp = client.post(
            "/api/v1/cover-letter/generate",
            headers=auth_headers,
            json={"job_id": "job-1", "tone": "formal"},
        )
        assert resp.status_code == 403

    def test_professional_passes_gate(
        self, client, auth_headers, fake_supabase
    ):
        """Professional clears the tier gate; next failure is missing CV (422)."""
        _seed_user(fake_supabase)
        _seed_subscription(fake_supabase, "professional")
        # cvs lookup returns no rows → 422 "Upload a CV first"
        fake_supabase.set_table("cvs", FakeSupabaseQuery(data=[]))

        resp = client.post(
            "/api/v1/cover-letter/generate",
            headers=auth_headers,
            json={"job_id": "job-1", "tone": "formal"},
        )
        # Did NOT 403 on the tier gate.
        assert resp.status_code != 403
        assert resp.status_code == 422

    def test_super_standard_passes_gate(
        self, client, auth_headers, fake_supabase
    ):
        """super_standard (K500/mo) MUST clear the tier gate. Regression fix."""
        _seed_user(fake_supabase)
        _seed_subscription(fake_supabase, "super_standard")
        fake_supabase.set_table("cvs", FakeSupabaseQuery(data=[]))

        resp = client.post(
            "/api/v1/cover-letter/generate",
            headers=auth_headers,
            json={"job_id": "job-1", "tone": "formal"},
        )
        # The regression: this used to 403. Must now pass the gate.
        assert resp.status_code != 403
        assert resp.status_code == 422
