"""Tier-gate tests for POST /api/v1/cover-letter/generate."""
from tests.conftest import FakeSupabaseQuery


def _seed_user(fake_supabase, role="user", subscription_tier="free"):
    """get_current_user and tier gate read users.subscription_tier."""
    fake_supabase.set_table(
        "users",
        FakeSupabaseQuery(
            data=[
                {
                    "id": "test-user-id",
                    "phone": "+260971234567",
                    "role": role,
                    "subscription_tier": subscription_tier,
                    "matches_viewed_this_month": 0,
                    "billing_cycle_reset": "2099-06-01",
                }
            ]
        ),
    )


class TestCoverLetterTierGate:
    def test_free_tier_blocked(self, client, auth_headers, fake_supabase):
        _seed_user(fake_supabase, subscription_tier="free")

        resp = client.post(
            "/api/v1/cover-letter/generate",
            headers=auth_headers,
            json={"job_id": "job-1", "tone": "formal"},
        )
        assert resp.status_code == 403
        assert "Professional" in resp.json()["detail"]

    def test_starter_tier_blocked(self, client, auth_headers, fake_supabase):
        _seed_user(fake_supabase, subscription_tier="starter")

        resp = client.post(
            "/api/v1/cover-letter/generate",
            headers=auth_headers,
            json={"job_id": "job-1", "tone": "formal"},
        )
        assert resp.status_code == 403

    def test_professional_passes_gate(self, client, auth_headers, fake_supabase):
        _seed_user(fake_supabase, subscription_tier="professional")
        fake_supabase.set_table("cvs", FakeSupabaseQuery(data=[]))

        resp = client.post(
            "/api/v1/cover-letter/generate",
            headers=auth_headers,
            json={"job_id": "job-1", "tone": "formal"},
        )
        assert resp.status_code != 403
        assert resp.status_code == 422

    def test_super_standard_passes_gate(self, client, auth_headers, fake_supabase):
        _seed_user(fake_supabase, subscription_tier="super_standard")
        fake_supabase.set_table("cvs", FakeSupabaseQuery(data=[]))

        resp = client.post(
            "/api/v1/cover-letter/generate",
            headers=auth_headers,
            json={"job_id": "job-1", "tone": "formal"},
        )
        assert resp.status_code != 403
        assert resp.status_code == 422
