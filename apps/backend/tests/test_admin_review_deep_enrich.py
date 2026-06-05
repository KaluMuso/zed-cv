"""Admin review-queue deep-enrich tick endpoint."""
from unittest.mock import AsyncMock, patch

from app.core.deps import require_admin
from app.services.deep_enrich import DeepEnrichJobResult, DeepEnrichTickResult
from main import app


class TestAdminReviewDeepEnrichTick:
    @patch(
        "app.api.v1.admin_review_jobs.run_deep_enrich_tick",
        new_callable=AsyncMock,
        return_value=DeepEnrichTickResult(
            enriched=1,
            attempted=1,
            results=[
                DeepEnrichJobResult(
                    job_id="j1",
                    title="Sales Intern",
                    outcome="enriched",
                    detail="https://example.com/listing",
                    review_cleared=True,
                ),
            ],
        ),
    )
    def test_admin_deep_enrich_tick_returns_per_job_results(
        self, mock_tick, client, admin_headers
    ):
        app.dependency_overrides[require_admin] = lambda: {
            "id": "admin-user-id",
            "role": "admin",
        }
        try:
            resp = client.post(
                "/api/v1/admin/review-jobs/deep-enrich-tick?limit=5&dry_run=false",
                headers=admin_headers,
            )
        finally:
            app.dependency_overrides.pop(require_admin, None)

        assert resp.status_code == 200
        body = resp.json()
        assert body["enriched"] == 1
        assert body["results"][0]["review_cleared"] is True
        mock_tick.assert_awaited_once()
        assert mock_tick.await_args.kwargs["dry_run"] is False
