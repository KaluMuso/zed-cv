"""Pin the 60/30/10 scoring formula in migration 046."""
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "infra"
    / "supabase"
    / "migrations"
    / "046_match_jobs_60_30_10_scoring.sql"
)


def test_migration_046_exists():
    assert MIGRATION_PATH.exists(), f"Migration 046 missing at {MIGRATION_PATH}"


def test_migration_046_semantic_component_scaled_to_60():
    sql = MIGRATION_PATH.read_text()
    assert "(1 - (j.embedding <=> v_user_embedding)) * 60" in sql


def test_migration_046_skills_component_scaled_to_30():
    sql = MIGRATION_PATH.read_text()
    assert "* 30" in sql
    assert "job_skills" in sql


def test_migration_046_bonus_location_and_salary():
    sql = MIGRATION_PATH.read_text()
    assert "remote" in sql.lower()
    assert "v_salary_min" in sql
    assert "THEN 5" in sql


def test_migration_046_additive_final_score():
    sql = MIGRATION_PATH.read_text()
    assert "js.v_score + js.s_score + js.b_score" in sql
    assert "js.v_score * 0.6 + js.s_score * 0.3" not in sql


def test_migration_046_preserves_rpc_signature():
    sql = MIGRATION_PATH.read_text()
    assert "p_user_id    UUID" in sql
    assert "p_min_score  REAL    DEFAULT 50.0" in sql
    assert "p_limit      INTEGER DEFAULT 20" in sql


def test_migration_046_drops_function_first():
    sql = MIGRATION_PATH.read_text()
    drop_idx = sql.find("DROP FUNCTION IF EXISTS public.match_jobs_for_user")
    create_idx = sql.find("CREATE FUNCTION public.match_jobs_for_user")
    assert drop_idx >= 0
    assert create_idx >= 0
    assert drop_idx < create_idx


def test_migration_046_keeps_review_and_expired_filters():
    sql = MIGRATION_PATH.read_text()
    assert "is_review_required" in sql
    assert "j.closing_date IS NULL OR j.closing_date >= CURRENT_DATE" in sql
