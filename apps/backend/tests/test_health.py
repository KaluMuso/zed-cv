"""Smoke tests for health endpoint."""
from unittest.mock import AsyncMock, patch


class TestHealth:
    @patch("main.check_waha_health", new_callable=AsyncMock)
    def test_health_ok(self, mock_waha, client, fake_supabase):
        mock_waha.return_value = True
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] in ("healthy", "degraded", "unhealthy")
        assert "version" in body

    def test_health_no_auth_required(self, client):
        """Health endpoint should be accessible without auth."""
        resp = client.get("/api/v1/health")
        # Should not return 401
        assert resp.status_code != 401
