-- 077 — Versioned cover letter edits per match (Professional+ editor)

CREATE TABLE cover_letter_versions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    match_id uuid REFERENCES matches(id) ON DELETE CASCADE,
    content_md text NOT NULL,
    version_number int NOT NULL,
    parent_version_id uuid REFERENCES cover_letter_versions(id) ON DELETE SET NULL,
    generated_by text NOT NULL CHECK (generated_by IN ('ai', 'user_edit')),
    created_at timestamptz DEFAULT NOW(),
    UNIQUE (user_id, match_id, version_number)
);

CREATE INDEX idx_cover_letter_user_match
    ON cover_letter_versions (user_id, match_id, version_number DESC);

ALTER TABLE cover_letter_versions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS cover_letter_versions_self ON cover_letter_versions;
CREATE POLICY cover_letter_versions_self ON cover_letter_versions
    FOR ALL
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

COMMENT ON TABLE cover_letter_versions IS
    'Per-match cover letter versions: AI drafts and user edits (Professional+ editor).';
