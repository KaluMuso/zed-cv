"""Deep-link enrichment must recompute review queue flags."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.deep_link_jobs import enrich_job_row
from app.services.deep_link_parsers import EnrichmentResult


@pytest.mark.asyncio
async def test_enrich_job_row_clears_review_when_apply_and_deadline_present():
    fake = MagicMock()
    table = MagicMock()
    fake.table.return_value = table
    chain = table.update.return_value
    chain.eq.return_value.execute.return_value = MagicMock(data=[{"id": "j1"}])

    row = {
        "apply_url": None,
        "apply_email": None,
        "contact_phone": None,
        "source_url": "https://employer.example/jobs/1",
        "enrichment_attempted_at": None,
        "closing_date": "2026-12-01",
        "is_review_required": True,
        "review_reason": "no_apply_path",
    }

    with patch(
        "app.services.deep_link_enricher.enrich_from_source_url",
        new_callable=AsyncMock,
        return_value=EnrichmentResult(
            apply_email="jobs@employer.example",
            apply_source="enriched",
        ),
    ):
        updated = await enrich_job_row(fake, "j1", row)

    assert updated is True
    patch_body = table.update.call_args[0][0]
    assert patch_body["apply_email"] == "jobs@employer.example"
    assert patch_body["is_review_required"] is False
    assert patch_body.get("review_reason") is None
