-- 020 — legal_docs table for admin-editable legal pages (task #62)
--
-- Backs the WYSIWYG editor that lets the operator update /legal/privacy,
-- /legal/terms and /legal/cookies without a code deploy. The renderers
-- in apps/frontend/src/app/legal/<slug>/page.tsx now fetch this table
-- first (via the public /api/v1/legal/{slug} endpoint) and fall back to
-- the inline _content.ts constants if no row exists — that way the
-- legal pages keep working today, and the moment the admin clicks
-- Save on a slug for the first time, the DB row takes over.
--
-- One row per slug. We replace-in-place rather than versioning per
-- edit; `version` is the document's own version string ("1.0", "1.1",
-- etc.) maintained by the editor, mirroring what _content.ts already
-- exposes via the VERSION constant.

BEGIN;

CREATE TABLE IF NOT EXISTS legal_docs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    -- "privacy" | "terms" | "cookies". Lower-case, no trailing slash —
    -- matches the route segment in /legal/<slug>/page.tsx.
    slug VARCHAR(32) UNIQUE NOT NULL,
    -- Display version string ("1.0", "1.1"…). Free text rather than
    -- semver-typed because legal docs version by stakeholder decision,
    -- not by code change. Empty string allowed at create time.
    version VARCHAR(32) NOT NULL DEFAULT '',
    -- Source of truth — markdown the operator types in the editor.
    content_md TEXT NOT NULL,
    -- Server-rendered + sanitised HTML, written at save time. Cached
    -- on the row so the public /legal page renderer doesn't have to
    -- re-render markdown on every request. AI-safety: this column
    -- never contains anything that hasn't been through the backend
    -- sanitiser at /admin/legal/<slug> PATCH time.
    content_html TEXT NOT NULL,
    -- Who last edited. References users(id) ON DELETE SET NULL so the
    -- legal_docs row survives an operator off-boarding (the
    -- editorial history is what matters; the link to the now-deleted
    -- user becomes NULL).
    last_modified_by UUID REFERENCES users(id) ON DELETE SET NULL,
    last_modified_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS legal_docs_slug_idx ON legal_docs(slug);

COMMIT;

COMMENT ON TABLE legal_docs IS
    'Admin-editable source for /legal/<slug> pages. One row per slug. content_html is sanitised at write time.';
