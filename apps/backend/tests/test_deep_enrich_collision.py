import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.deep_enrich import run_deep_enrich_tick, DeepEnrichRole

@pytest.mark.asyncio
async def test_deep_enrich_continues_past_dedupe_collision():
    # Setup candidate jobs
    job1 = {
        "id": "job-1",
        "title": "Software Developer",
        "company": "Company A",
        "description": "Original description A",
        "source_url": "https://example.com/job1",
        "is_active": True,
        "deep_enriched_at": None,
        "created_at": "2026-06-01T00:00:00Z",
    }
    job2 = {
        "id": "job-2",
        "title": "Data Scientist",
        "company": "Company B",
        "description": "Original description B",
        "source_url": "https://example.com/job2",
        "is_active": True,
        "deep_enriched_at": None,
        "created_at": "2026-06-01T00:00:00Z",
    }

    # Mock supabase client
    supabase = MagicMock()
    query_mock = MagicMock()
    supabase.table.return_value = query_mock
    query_mock.select.return_value = query_mock
    query_mock.order.return_value = query_mock
    query_mock.limit.return_value = query_mock
    query_mock.or_.return_value = query_mock
    
    # We want query chain calls to return query_mock
    query_mock.eq.return_value = query_mock
    
    # run_deep_enrich_tick calls supabase.table("jobs").select(...).execute()
    # to fetch candidates. Let's return our two jobs first, then subsequent executes
    # will be controlled by mock_execute.
    candidates_returned = False
    last_update_payload = {}

    def mock_update(payload):
        nonlocal last_update_payload
        last_update_payload = payload
        return query_mock

    query_mock.update.side_effect = mock_update

    def mock_execute():
        nonlocal candidates_returned
        if not candidates_returned:
            candidates_returned = True
            return MagicMock(data=[job1, job2])
        
        # Subsequent executes are for the updates inside enrichment
        mock_exec_res = MagicMock()
        if last_update_payload.get("title") == "Software Developer":
            raise Exception("duplicate key value violates unique constraint 'idx_jobs_dedupe_key_active'")
        mock_exec_res.data = []
        return mock_exec_res

    query_mock.execute.side_effect = mock_execute

    # Let's mock LLM responses
    role1 = DeepEnrichRole(
        title="Software Developer",
        description_md="Description A enriched",
        skills_required=["python"],
        requirements=["degree"],
    )
    role2 = DeepEnrichRole(
        title="Data Scientist",
        description_md="Description B enriched",
        skills_required=["r"],
        requirements=["masters"],
    )

    with (
        patch("app.services.deep_enrich.fetch_source_page", AsyncMock(return_value=(200, "page content"))),
        patch("app.services.deep_enrich.extract_page_text_for_description", return_value="some text " * 10),
        patch("app.services.deep_enrich._call_deep_enrich_llm", AsyncMock(side_effect=[[role1], [role2]])),
        patch("app.services.deep_enrich.generate_embedding", AsyncMock(return_value=[0.1]*768)),
        patch("app.services.deep_enrich._attach_job_skills", AsyncMock()),
        patch("app.services.deep_enrich._log_enrich"),
    ):
        result = await run_deep_enrich_tick(supabase, limit=2, inter_job_delay_sec=0)

    # Verify that the tick processed both candidates and returned
    assert result.attempted == 2
    assert result.skipped == 1  # job1 skipped due to dedupe collision
    assert result.enriched == 1  # job2 successfully enriched
    assert len(result.results) == 2
    assert result.results[0].outcome == "skipped"
    assert result.results[0].detail == "dedupe collision on update"
    assert result.results[1].outcome == "enriched"
