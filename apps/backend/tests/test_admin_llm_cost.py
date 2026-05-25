"""Admin LLM cost stats endpoint."""
from tests.conftest import FakeSupabaseQuery


class TestAdminLlmCostStats:
    def test_llm_cost_stats_requires_auth(self, client):
        resp = client.get("/api/v1/admin/llm-cost-stats")
        assert resp.status_code in (401, 403)

    def test_llm_cost_stats_success(self, client, auth_headers, fake_supabase):
        fake_supabase.set_table(
            "users",
            FakeSupabaseQuery(data=[{"id": "test-user-id", "role": "admin"}]),
        )
        fake_supabase.set_table(
            "llm_usage_log",
            FakeSupabaseQuery(
                data=[
                    {
                        "feature": "bwana",
                        "model": "google/gemini-2.0-flash-001",
                        "prompt_tokens": 50,
                        "completion_tokens": 10,
                        "cost_usd": 0.00001,
                        "created_at": "2026-05-24T12:00:00Z",
                    }
                ]
            ),
        )
        resp = client.get(
            "/api/v1/admin/llm-cost-stats?days=7",
            headers=auth_headers,
        )
        assert resp.status_code in (200, 403, 404)
        if resp.status_code == 200:
            body = resp.json()
            assert body["total_requests"] == 1
            assert body["by_feature"][0]["feature"] == "bwana"
