-- generated_documents was created in 001_initial_schema.sql.
-- This migration adds a dashboard lookup index (idempotent).

CREATE INDEX IF NOT EXISTS idx_generated_documents_user_created
    ON generated_documents (user_id, created_at DESC);

COMMENT ON TABLE generated_documents IS
    'AI-generated CVs and cover letters per user/job; RLS restricts to owner.';
