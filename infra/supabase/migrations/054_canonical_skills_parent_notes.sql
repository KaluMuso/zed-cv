-- 054_canonical_skills_parent_notes.sql
-- Optional grouping (parent_skill) and admin notes on curated dictionary rows.

BEGIN;

ALTER TABLE canonical_skills
    ADD COLUMN IF NOT EXISTS parent_skill VARCHAR(200),
    ADD COLUMN IF NOT EXISTS notes TEXT;

COMMENT ON COLUMN canonical_skills.parent_skill IS
    'Optional umbrella label (e.g. Microsoft Office for Excel/Word).';
COMMENT ON COLUMN canonical_skills.notes IS
    'Optional admin context (e.g. expansion for acronyms).';

COMMIT;
