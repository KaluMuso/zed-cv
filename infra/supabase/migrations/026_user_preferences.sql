-- 026_user_preferences.sql
--
-- Phase 2 Initiative #4 — CV Generator data capture.
--
-- Creates the user_preferences table that backs the rewritten Preferences
-- tab + the /cv/upload auto-populate path. The existing `users` table
-- already carries location and years_experience; we deliberately don't
-- duplicate those here.
--
-- ZMW ngwee invariant (AGENTS.md): salary_min/salary_max are integers in
-- ngwee (1 ZMW = 100 ngwee). NULL = "not specified". Frontend formats
-- to K-amounts for display. salary_min < salary_max is enforced in the
-- API layer (not as a CHECK) so a user typing salary_max first and
-- salary_min after doesn't get a constraint-violation 422 mid-edit.
--
-- RLS: every column is per-user; the policy below scopes every row to
-- auth.uid() so a misconfigured PostgREST select can't leak between
-- users.

BEGIN;

CREATE TABLE IF NOT EXISTS user_preferences (
  user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,

  -- Group 1: Target roles (multi-value).
  -- Free-form strings rather than skill_id FKs because target roles
  -- ("Software Engineer", "Operations Manager") are job-title-shaped,
  -- not always represented in the skills catalogue. Auto-populate
  -- writes inferred roles here; the user can override freely.
  target_roles TEXT[] DEFAULT '{}',
  target_roles_source TEXT
    CHECK (target_roles_source IN ('user_provided', 'cv_inferred', 'mixed'))
    DEFAULT 'user_provided',

  -- Group 2: Salary expectations (ZMW ngwee per AGENTS.md invariant).
  -- Nullable so a user can leave them blank. salary_currency is kept
  -- for forward-compat with international relocations even though every
  -- in-country listing is ZMW today.
  salary_min INTEGER,
  salary_max INTEGER,
  salary_currency TEXT DEFAULT 'ZMW',
  salary_frequency TEXT
    CHECK (salary_frequency IN ('monthly', 'annual', 'hourly', 'daily')),

  -- Group 3: Work arrangement + relocation.
  preferred_work_arrangement TEXT
    CHECK (preferred_work_arrangement IN ('remote', 'hybrid', 'onsite', 'any')),
  willing_to_relocate BOOLEAN DEFAULT FALSE,
  acceptable_regions TEXT[] DEFAULT '{}',

  -- Group 4: Languages + industry experience.
  -- JSONB rather than two extra normalised tables: cardinality is small
  -- (max 8 each, enforced in the API), the shape is read in one shot
  -- on the Preferences tab, and we'd never query by individual entries
  -- relationally. Keeping it as JSONB avoids two more migrations.
  languages JSONB DEFAULT '[]'::jsonb,
  industries JSONB DEFAULT '[]'::jsonb,

  -- Group 5: Extensible free-form key/value bag.
  -- Schema intentionally open — consumers must treat unknown keys
  -- gracefully. The UI exposes "Add custom field" so users with
  -- recruiter-style asks (notice period, preferred start date, etc.)
  -- can record them without a schema change.
  extras JSONB DEFAULT '{}'::jsonb,

  -- Metadata. We track auto-populated separately from manually-updated
  -- so the auto-populate path can avoid clobbering user edits:
  -- - auto_populated_at is set whenever the /cv/upload hook fills a
  --   previously-empty field.
  -- - manually_updated_at is set whenever the PATCH endpoint runs.
  -- The auto-populate service consults these to decide whether to
  -- overwrite a field on re-upload (it never overwrites manual edits).
  auto_populated_at TIMESTAMPTZ,
  manually_updated_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- GIN indexes for the two array columns. Used by the /matches query
-- when filtering candidates by target_roles overlap or by region.
CREATE INDEX IF NOT EXISTS idx_user_preferences_target_roles_gin
  ON user_preferences USING gin (target_roles);
CREATE INDEX IF NOT EXISTS idx_user_preferences_acceptable_regions_gin
  ON user_preferences USING gin (acceptable_regions);

-- RLS: users can read+write only their own row.
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS user_preferences_self ON user_preferences;
CREATE POLICY user_preferences_self ON user_preferences
  FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

COMMENT ON TABLE user_preferences IS
  'Per-user job-search preferences. Backs /api/v1/preferences and the '
  'Preferences tab. One row per user; auto-created on first GET if absent.';

COMMENT ON COLUMN user_preferences.target_roles IS
  'User-stated job titles they want to match against, e.g. {"Software '
  'Engineer", "Data Analyst"}. Capped at 10 entries in the API layer.';

COMMENT ON COLUMN user_preferences.target_roles_source IS
  '''user_provided'' = entirely manual. ''cv_inferred'' = filled by the '
  'CV upload auto-populate path. ''mixed'' = user edited an auto-populated '
  'value.';

COMMENT ON COLUMN user_preferences.salary_min IS
  'Lower bound of preferred salary, in ZMW ngwee (1 ZMW = 100 ngwee). '
  'NULL = unspecified. The salary_min < salary_max invariant is enforced '
  'in the API, not as a CHECK, so a user partial-update doesn''t 422.';

COMMENT ON COLUMN user_preferences.acceptable_regions IS
  'Provinces/regions the user is open to working in, e.g. {"Lusaka", '
  '"Copperbelt", "International"}. Capped at 6 entries in the API.';

COMMENT ON COLUMN user_preferences.languages IS
  'JSONB array of {language: string, proficiency: '
  '"native"|"fluent"|"intermediate"|"basic"}. Example: '
  '[{"language": "English", "proficiency": "native"}, '
  '{"language": "Bemba", "proficiency": "fluent"}]. Capped at 8 entries '
  'in the API.';

COMMENT ON COLUMN user_preferences.industries IS
  'JSONB array of {industry: string, years_experience: int}. Example: '
  '[{"industry": "Agriculture", "years_experience": 6}, '
  '{"industry": "Government", "years_experience": 2}]. Capped at 8 entries.';

COMMENT ON COLUMN user_preferences.extras IS
  'Free-form JSONB for any additional user-provided info. Schema is '
  'intentionally open; consumers should treat unknown keys gracefully.';

COMMENT ON COLUMN user_preferences.auto_populated_at IS
  'Last time the /cv/upload hook filled at least one empty field on '
  'this row. NULL until the first CV-driven population.';

COMMENT ON COLUMN user_preferences.manually_updated_at IS
  'Last time the user PATCH''d this row. NULL until first manual edit. '
  'Auto-populate consults this to avoid clobbering manual entries on '
  'CV re-upload.';

COMMIT;
