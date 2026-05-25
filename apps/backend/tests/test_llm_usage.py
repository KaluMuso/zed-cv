"""LLM usage logging and admin cost aggregation."""
from unittest.mock import MagicMock

from app.api.v1.admin import _aggregate_llm_cost_rows
from app.services.llm import (
    estimate_gemini_embed_cost_usd,
    estimate_openrouter_cost_usd,
    extract_usage_from_completion,
    record_openrouter_completion,
    LlmLogContext,
    FEATURE_BWANA,
)
from tests.conftest import FakeSupabaseQuery


class TestLlmCostEstimates:
    def test_openrouter_gemini_flash_pricing(self):
        cost = estimate_openrouter_cost_usd(
            "google/gemini-2.0-flash-001",
            prompt_tokens=1_000_000,
            completion_tokens=0,
        )
        assert abs(cost - 0.10) < 1e-6

    def test_gemini_embed_pricing(self):
        cost = estimate_gemini_embed_cost_usd("gemini-embedding-001", 1_000_000)
        assert abs(cost - 0.15) < 1e-6


class TestExtractUsage:
    def test_reads_openai_style_usage(self):
        response = MagicMock()
        response.usage.prompt_tokens = 100
        response.usage.completion_tokens = 50
        response.id = "gen-abc"
        prompt, completion, req_id = extract_usage_from_completion(response)
        assert prompt == 100
        assert completion == 50
        assert req_id == "gen-abc"


class TestRecordLlmUsage:
    def test_inserts_row_via_supabase(self, fake_supabase):
        fake_supabase.set_table("llm_usage_log", FakeSupabaseQuery())
        response = MagicMock()
        response.usage.prompt_tokens = 10
        response.usage.completion_tokens = 5
        response.id = "req-1"

        record_openrouter_completion(
            response,
            model="google/gemini-2.0-flash-001",
            context=LlmLogContext(
                feature=FEATURE_BWANA,
                route="POST /api/v1/bwana/chat",
                user_id="user-1",
            ),
            supabase=fake_supabase,
        )

        table = fake_supabase._tables.get("llm_usage_log")
        assert table is not None
        assert len(table._data) == 1
        row = table._data[0]
        assert row["feature"] == FEATURE_BWANA
        assert row["model"] == "google/gemini-2.0-flash-001"
        assert row["prompt_tokens"] == 10
        assert row["completion_tokens"] == 5
        assert float(row["cost_usd"]) > 0


class TestAdminLlmCostAggregation:
    def test_rollup_by_feature_and_model(self):
        rows = [
            {
                "feature": "bwana",
                "model": "google/gemini-2.0-flash-001",
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "cost_usd": 0.00002,
                "created_at": "2026-05-24T10:00:00Z",
            },
            {
                "feature": "cv_parsing",
                "model": "google/gemini-2.0-flash-001",
                "prompt_tokens": 500,
                "completion_tokens": 100,
                "cost_usd": 0.00009,
                "created_at": "2026-05-24T11:00:00Z",
            },
        ]
        stats = _aggregate_llm_cost_rows(rows, days=7)
        assert stats.total_requests == 2
        assert len(stats.by_model) == 1
        assert len(stats.by_feature) == 2
        assert stats.daily[0].date == "2026-05-24"
