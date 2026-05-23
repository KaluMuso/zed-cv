"""Pin migration 046 deep-scrape enrichment columns."""
from pathlib import Path

MIGRATION_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "infra"
    / "supabase"
    / "migrations"
    / "046_jobs_deep_scrape_enrichment.sql"
)


def _sql() -> str:
    return MIGRATION_PATH.read_text()


def test_migration_045_exists():
    assert MIGRATION_PATH.exists()


def test_migration_045_adds_expected_columns():
    sql = _sql()
    for col in (
        "source_platform",
        "original_source_url",
        "contact_email",
        "contact_phone",
        "contact_whatsapp",
        "is_enriched",
    ):
        assert col in sql, f"missing column {col!r} in migration 045"


def test_migration_045_uses_idempotent_add_column():
    assert "ADD COLUMN IF NOT EXISTS" in _sql()
