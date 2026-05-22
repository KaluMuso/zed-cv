-- 046_create_skills_dictionary.sql
--
-- Admin skill canonicalization: map messy scraper strings (e.g. "ms excel")
-- to curated display names (e.g. "Microsoft Excel") before job ingest links
-- skills via the existing resolver.
--
-- Idempotent: IF NOT EXISTS on tables and indexes.

BEGIN;

CREATE TABLE IF NOT EXISTS canonical_skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw_skill_mappings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    raw_name VARCHAR(200) UNIQUE NOT NULL,
    canonical_id UUID REFERENCES canonical_skills(id) ON DELETE SET NULL,
    occurrences INT NOT NULL DEFAULT 1 CHECK (occurrences >= 1)
);

CREATE INDEX IF NOT EXISTS idx_raw_skill_mappings_pending
    ON raw_skill_mappings(occurrences DESC)
    WHERE canonical_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_raw_skill_mappings_canonical_id
    ON raw_skill_mappings(canonical_id)
    WHERE canonical_id IS NOT NULL;

COMMENT ON TABLE canonical_skills IS
    'Curated skill display names for admin merges (Admin Console).';
COMMENT ON TABLE raw_skill_mappings IS
    'Raw scraper skill strings; canonical_id NULL = pending admin review.';

COMMIT;
