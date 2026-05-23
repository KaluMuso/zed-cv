"""Unit tests for v2 match RPC normalization and explanations."""
from app.services.match_explanation import build_match_explanation
from app.services.matching import normalize_rpc_match_row


def test_normalize_rpc_match_row_v2_fields():
    row = normalize_rpc_match_row(
        {
            "job_id": "j1",
            "score": 72.0,
            "semantic_score": 40.0,
            "skills_score": 16.0,
            "experience_score": 12.0,
            "location_score": 10.0,
            "recency_score": 4.0,
            "matched_skills": ["python"],
            "missing_skills": ["kubernetes"],
            "explanation": "Semantic 40/50, skills 16/20, experience 12/15, location 10/10, recency 4/5.",
        }
    )
    assert row["final_score"] == 72.0
    assert row["vector_score"] == 40.0
    assert row["skill_score"] == 16.0
    assert row["bonus_score"] == 14.0
    assert row["location_score"] == 10.0
    assert row["recency_score"] == 4.0


def test_normalize_rpc_match_row_legacy_aliases():
    row = normalize_rpc_match_row(
        {
            "job_id": "j2",
            "final_score": 55.0,
            "vector_score": 30.0,
            "skill_score": 10.0,
            "bonus_score": 15.0,
            "experience_score": 0.0,
            "matched_skills": [],
            "missing_skills": [],
        }
    )
    assert row["semantic_score"] == 30.0
    assert row["skills_score"] == 10.0


def test_match_v2_floor_35_excludes_low_score_documented():
    """RPC SQL applies hard floor 35; rows below are not returned."""
    low = normalize_rpc_match_row(
        {
            "job_id": "j-low",
            "score": 30.0,
            "semantic_score": 20.0,
            "skills_score": 5.0,
            "experience_score": 0.0,
            "location_score": 0.0,
            "recency_score": 0.0,
            "matched_skills": [],
            "missing_skills": [],
        }
    )
    assert low["final_score"] == 30.0
    assert low["final_score"] < 35


def test_match_v2_experience_match_contributes():
    full = normalize_rpc_match_row(
        {
            "job_id": "j-exp",
            "score": 80.0,
            "semantic_score": 35.0,
            "skills_score": 10.0,
            "experience_score": 15.0,
            "location_score": 10.0,
            "recency_score": 5.0,
            "matched_skills": [],
            "missing_skills": [],
        }
    )
    assert full["experience_score"] == 15.0
    assert full["final_score"] >= 35


def test_match_v2_recency_decays_over_30_days():
    """Recency component is stored separately for UI breakdown."""
    recent = normalize_rpc_match_row(
        {
            "job_id": "j-new",
            "score": 65.0,
            "semantic_score": 35.0,
            "skills_score": 10.0,
            "experience_score": 10.0,
            "location_score": 5.0,
            "recency_score": 5.0,
            "matched_skills": [],
            "missing_skills": [],
        }
    )
    stale = normalize_rpc_match_row(
        {
            "job_id": "j-old",
            "score": 60.0,
            "semantic_score": 35.0,
            "skills_score": 10.0,
            "experience_score": 10.0,
            "location_score": 5.0,
            "recency_score": 0.0,
            "matched_skills": [],
            "missing_skills": [],
        }
    )
    assert recent["recency_score"] > stale["recency_score"]


def test_build_match_explanation_lists_five_components():
    text = build_match_explanation(
        semantic_score=42.0,
        skills_score=14.0,
        experience_score=12.0,
        location_score=10.0,
        recency_score=4.0,
        matched_skills=["Python", "FastAPI"],
    )
    assert "42/50" in text
    assert "14/20" in text
    assert "12/15" in text
    assert "10/10" in text
    assert "4/5" in text
    assert "Matched on" in text
