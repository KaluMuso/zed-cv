"""Pin the v2 weighted scoring formula in migration 060."""
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "infra"
    / "supabase"
    / "migrations"
    / "060_match_jobs_v2_weighted.sql"
)


def test_migration_060_exists():
    assert MIGRATION_PATH.exists(), f"Migration 060 missing at {MIGRATION_PATH}"


def test_migration_060_semantic_component_scaled_to_50():
    sql = MIGRATION_PATH.read_text()
    assert "(1 - (j.embedding <=> v_user_embedding)) * 50" in sql


def test_migration_060_skills_required_only_scaled_to_20():
    sql = MIGRATION_PATH.read_text()
    assert "is_required = true" in sql
    assert "* 20" in sql


def test_migration_060_experience_contributes_to_sum():
    sql = MIGRATION_PATH.read_text()
    assert "compute_experience_score(" in sql
    assert "* 15" in sql
    assert "experience_max_years" in sql


def test_migration_060_location_remote_hybrid():
    sql = MIGRATION_PATH.read_text()
    assert "work_arrangement" in sql
    assert "'remote', 'hybrid'" in sql


def test_migration_060_recency_decays_over_30_days():
    sql = MIGRATION_PATH.read_text()
    assert "/ 86400.0 / 30.0" in sql
    assert "posted_at" in sql


def test_migration_060_hard_floor_35():
    sql = MIGRATION_PATH.read_text()
    assert ">= 35" in sql


def test_migration_060_additive_final_score():
    sql = MIGRATION_PATH.read_text()
    assert "js.sem_score + js.sk_score + js.exp_score + js.loc_score + js.rec_score" in sql


def test_match_v2_floor_35_excludes_low_score():
    sql = MIGRATION_PATH.read_text()
    ranked_idx = sql.find("ranked AS")
    assert ranked_idx >= 0
    assert ">= 35" in sql[ranked_idx : ranked_idx + 800]


def test_match_v2_experience_match_contributes():
    sql = MIGRATION_PATH.read_text()
    assert "exp_score" in sql
    assert "js.exp_score" in sql


def test_match_v2_recency_decays_over_30_days():
    sql = MIGRATION_PATH.read_text()
    assert "rec_score" in sql
    assert "LEAST(" in sql


def test_migration_060_adds_match_columns():
    sql = MIGRATION_PATH.read_text()
    assert "location_score REAL" in sql
    assert "recency_score REAL" in sql


def test_migration_060_preserves_rpc_signature():
    sql = MIGRATION_PATH.read_text()
    assert "p_user_id    UUID" in sql
    assert "p_min_score  REAL    DEFAULT 50.0" in sql
    assert "p_limit      INTEGER DEFAULT 50" in sql


def test_migration_060_drops_function_first():
    sql = MIGRATION_PATH.read_text()
    drop_idx = sql.find("DROP FUNCTION IF EXISTS public.match_jobs_for_user")
    create_idx = sql.find("CREATE FUNCTION public.match_jobs_for_user")
    assert drop_idx >= 0 and create_idx > drop_idx
