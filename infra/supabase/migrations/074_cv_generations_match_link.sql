-- 074 — Link cv_generations to a specific match for per-role tailored CVs.
-- source distinguishes user-initiated /cv/generate from match-tailored output.

ALTER TABLE cv_generations
    ADD COLUMN IF NOT EXISTS match_id UUID REFERENCES matches(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS source TEXT;

ALTER TABLE cv_generations
    DROP CONSTRAINT IF EXISTS cv_generations_source_check;

ALTER TABLE cv_generations
    ADD CONSTRAINT cv_generations_source_check
    CHECK (source IS NULL OR source IN ('user_input', 'match_tailored'));

CREATE UNIQUE INDEX IF NOT EXISTS idx_cv_generations_user_match_tailored
    ON cv_generations(user_id, match_id)
    WHERE source = 'match_tailored' AND match_id IS NOT NULL;

COMMENT ON COLUMN cv_generations.match_id IS
    'When source=match_tailored, the match row this CV was tailored for.';
COMMENT ON COLUMN cv_generations.source IS
    'user_input = POST /cv/generate; match_tailored = POST /matches/{id}/tailor-cv';
