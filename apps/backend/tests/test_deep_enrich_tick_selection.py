"""Unit tests for deep-enrich tick candidate selection."""
from __future__ import annotations

from app.services.deep_enrich import filter_deep_enrich_candidates


def _row(
    *,
    job_id: str = "j1",
    is_active: bool = True,
    is_review_required: bool = False,
    source_url: str | None = "https://jobwebzambia.com/jobs/accountant-acme/",
    deep_enriched_at: str | None = None,
    created_at: str = "2026-06-01T10:00:00Z",
) -> dict:
    return {
        "id": job_id,
        "is_active": is_active,
        "is_review_required": is_review_required,
        "source_url": source_url,
        "apply_url": None,
        "deep_enriched_at": deep_enriched_at,
        "created_at": created_at,
    }


def test_filter_includes_review_queue_row_with_source_url():
    rows = [
        _row(
            job_id="review",
            is_active=False,
            is_review_required=True,
            source_url="https://www.gozambiajobs.com/jobs/123-slug",
        ),
    ]
    out = filter_deep_enrich_candidates(rows, limit=10)
    assert len(out) == 1
    assert out[0]["id"] == "review"


def test_filter_skips_already_enriched_after_create():
    rows = [
        _row(
            deep_enriched_at="2026-06-01T12:00:00Z",
            created_at="2026-06-01T10:00:00Z",
        ),
    ]
    assert filter_deep_enrich_candidates(rows, limit=10) == []


def test_filter_skips_missing_fetchable_url():
    rows = [
        _row(source_url="https://jobwebzambia.com/"),
        _row(source_url=None),
    ]
    assert filter_deep_enrich_candidates(rows, limit=10) == []


def test_filter_respects_limit():
    rows = [
        _row(job_id=f"j{i}", source_url=f"https://jobwebzambia.com/jobs/role-{i}/")
        for i in range(5)
    ]
    out = filter_deep_enrich_candidates(rows, limit=2)
    assert len(out) == 2
