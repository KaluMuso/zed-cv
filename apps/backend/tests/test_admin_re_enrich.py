from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from .test_admin_jobs import JobsFakeSupabase, jobs_fake, admin_client, auth_headers, _seed_job

@pytest.mark.asyncio
async def test_re_enrich_clears_and_runs(admin_client, auth_headers, jobs_fake):
    # Seed a job with deep_enriched_at set
    job_id = _seed_job(jobs_fake, deep_enriched_at="2026-06-08T12:00:00+00:00")
    
    # Verify it is set initially
    jobs = jobs_fake.tables["jobs"]
    assert jobs[0]["deep_enriched_at"] == "2026-06-08T12:00:00+00:00"

    mock_result = {
        "enriched": True,
        "outcome": "enriched",
        "deep_enriched_at": "2026-06-09T13:00:00+00:00",
        "admin_published": True,
        "description_length": 500,
    }

    # Patch the run_deep_enrich_for_job call
    with patch("app.services.deep_enrich.run_deep_enrich_for_job", AsyncMock(return_value=mock_result)) as mock_enrich:
        r = admin_client.post(
            f"/api/v1/admin/jobs/{job_id}/re-enrich",
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        assert r.json() == mock_result
        
        # Verify the helper was called
        mock_enrich.assert_called_once_with(jobs_fake, job_id)
        
        # Verify that the update to clear deep_enriched_at occurred.
        updates = [w for w in jobs_fake.writes if w["op"] == "update" and w["table"] == "jobs"]
        assert len(updates) >= 1
        assert updates[0]["payload"]["deep_enriched_at"] is None

def test_re_enrich_missing_job_returns_404(admin_client, auth_headers):
    r = admin_client.post(
        "/api/v1/admin/jobs/does-not-exist/re-enrich",
        headers=auth_headers,
    )
    assert r.status_code == 404
