"""Tests for deep-enrich pipeline (mocked LLM + Supabase)."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import APIStatusError

from app.services.deep_enrich import (
    DeepEnrichRole,
    _role_to_job_patch,
    enrich_job_deep,
)
from app.services.job_quality import parent_listing_signature


@pytest.fixture
def parent_row():
    return {
        "id": "parent-1",
        "title": "Bricklayers, Carpenters, Plumbers",
        "company": "BuildCo",
        "location": "Lusaka",
        "description": "Multi role listing",
        "source_url": "https://employer.example/jobs/multi",
        "apply_url": None,
        "apply_email": None,
        "contact_phone": None,
        "source": "scraper",
        "posted_at": "2026-05-01T00:00:00Z",
        "closing_date": None,
        "created_at": "2026-05-01T00:00:00Z",
        "salary_min": None,
        "salary_max": None,
        "is_active": True,
    }


def test_parent_listing_signature_stable():
    assert parent_listing_signature("A", "B") == parent_listing_signature("A", "B")
    assert parent_listing_signature("A", "B") != parent_listing_signature("A", "C")


def test_role_to_job_patch_includes_html():
    role = DeepEnrichRole.model_validate(
        {
            "title": "Bricklayer",
            "description_md": "## Responsibilities\n\n- Lay bricks",
            "skills_required": ["masonry", "safety", "tools", "teamwork", "reading"],
            "requirements": ["Grade 12"],
        }
    )
    parent = {"company": "BuildCo", "source": "scraper", "source_url": "https://x"}
    patch = _role_to_job_patch(role, parent, parent_sig="abc")
    assert patch["title"] == "Bricklayer"
    assert patch.get("description_html")
    assert patch.get("section_html")


@pytest.mark.asyncio
async def test_enrich_split_deactivates_parent(parent_row):
    supabase = MagicMock()
    table = MagicMock()
    supabase.table.return_value = table
    table.select.return_value = table
    table.eq.return_value = table
    table.limit.return_value = table
    table.update.return_value = table
    table.insert.return_value = table
    table.execute.return_value = MagicMock(data=[{"id": "child-1"}])

    roles = [
        DeepEnrichRole.model_validate(
            {
                "title": "Bricklayer",
                "description_md": "## Role\n\nBrick work " * 5,
                "skills_required": ["a", "b", "c", "d", "e"],
            }
        ),
        DeepEnrichRole.model_validate(
            {
                "title": "Carpenter",
                "description_md": "## Role\n\nWood work " * 5,
                "skills_required": ["a", "b", "c", "d", "e"],
            }
        ),
    ]

    with (
        patch(
            "app.services.deep_enrich.fetch_source_page",
            new_callable=AsyncMock,
            return_value=(200, "<html><body>jobs</body></html>"),
        ),
        patch(
            "app.services.deep_enrich.extract_page_text_for_description",
            return_value="Bricklayer and Carpenter needed in Lusaka " * 10,
        ),
        patch(
            "app.services.deep_enrich._call_deep_enrich_llm",
            new_callable=AsyncMock,
            return_value=roles,
        ),
        patch(
            "app.services.deep_enrich.generate_embedding",
            new_callable=AsyncMock,
            return_value=[0.1] * 768,
        ),
        patch(
            "app.services.deep_enrich._attach_job_skills",
            new_callable=AsyncMock,
        ),
        patch(
            "app.services.deep_enrich._insert_child_job",
            new_callable=AsyncMock,
            side_effect=["child-1", "child-2"],
        ),
    ):
        mock_llm = MagicMock()
        result = await enrich_job_deep(supabase, parent_row, llm_client=mock_llm)

    assert result.outcome == "split"
    update_calls = [c for c in table.update.call_args_list]
    assert any(
        "split_into_children" in str(c)
        for c in update_calls
    )


@pytest.mark.asyncio
async def test_enrich_openrouter_payment_error_returns_failed(parent_row):
    supabase = MagicMock()
    supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[]
    )
    err = APIStatusError(
        "payment required",
        response=MagicMock(status_code=402),
        body={"error": {"message": "402"}},
    )

    with (
        patch(
            "app.services.deep_enrich.fetch_source_page",
            new_callable=AsyncMock,
            return_value=(200, "<html><body>job</body></html>"),
        ),
        patch(
            "app.services.deep_enrich.extract_page_text_for_description",
            return_value="Engineer role in Lusaka " * 12,
        ),
        patch(
            "app.services.deep_enrich._call_deep_enrich_llm",
            new_callable=AsyncMock,
            side_effect=err,
        ),
    ):
        result = await enrich_job_deep(supabase, parent_row, llm_client=MagicMock())

    assert result.outcome == "failed"
    assert result.detail


@pytest.mark.asyncio
async def test_enrich_no_url_logs_failed(parent_row):
    parent_row["source_url"] = None
    parent_row["apply_url"] = None
    supabase = MagicMock()
    supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[]
    )

    result = await enrich_job_deep(supabase, parent_row)
    assert result.outcome == "failed"
    assert "no source_url" in (result.detail or "")
