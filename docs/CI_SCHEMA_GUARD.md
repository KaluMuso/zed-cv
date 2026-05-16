# CI drift-detection guards

Three static checks live under `scripts/` and run on every PR via
`.github/workflows/schema_guard.yml`. They exist to catch contract
drift that has historically slipped past code review and only surfaced
in production — usually as a uvicorn 500 that strips CORS headers and
reaches the browser as a misleading "CORS error".

| Guard | What it compares | Catches |
|---|---|---|
| `ci_schema_guard.py`        | Backend `supabase.table().select/insert/upsert/update` references vs. the live Postgres schema | PR #23 (`cv_generations.word_count` referenced before the column shipped) |
| `ci_openapi_ts_guard.py`    | TS interfaces used as `apiFetch<…>` response types vs. `docs/openapi.yaml` | PR #24 (`skills_extracted` in TS, `parsed_skills` in OpenAPI → upload toast showed "0 skills") |
| `ci_compose_env_guard.py`   | `${VAR}` references in `infra/*/docker-compose*.yml` vs. sibling `.env.example` | PR #26 (WAHA started with empty `WHATSAPP_API_KEY` because no `.env.example` documented `WAHA_API_KEY`) |

---

## Running locally

```bash
# All three guards
python scripts/ci_schema_guard.py
python scripts/ci_openapi_ts_guard.py
python scripts/ci_compose_env_guard.py

# JSON-only (what CI consumes)
python scripts/ci_schema_guard.py --json
```

`ci_schema_guard.py` picks a schema source automatically:

- **`SUPABASE_URL` + `SUPABASE_SERVICE_KEY` set** → live mode (queries
  Supabase). Requires that the project ships a `schema_guard_columns`
  RPC (one row per `(table_name, column_name)` in the `public` schema).
- **Otherwise** → derives the schema from `infra/supabase/migrations/`.
  This is the path used for PRs from forks and for local development
  without DB credentials. It handles `CREATE TABLE`, `ALTER TABLE … ADD
  COLUMN [IF NOT EXISTS]`, and chained add-column statements.

Force a mode with `--schema-source {live,migrations,file}`. The `file`
mode reads a JSON dump and is what the tests use.

---

## Interpreting failures

### `schema-guard`

Example:
```
schema-guard: 1 drift(s) detected
  apps/backend/app/api/v1/cv.py:559  .insert('cv_generations')
    -> column 'word_count' column_missing
```

Means: `cv.py:559` writes a `word_count` field via
`supabase.table("cv_generations").insert({...})`, but no migration ever
added `word_count` to that table.

Resolutions, in order of preference:

1. **Add the column via a new migration.** This is almost always the
   right fix — the backend code is the customer-visible behavior; the
   schema is the lagging artifact.
2. **Remove the reference from the code** if the column was a typo or
   leftover from a deleted feature.
3. **Allow-list the entry** in `scripts/ci_schema_guard_allowlist.yml`
   only if the analyzer is genuinely wrong (e.g., the column lives on a
   view exposed under a different name). Include a `reason:` field.

#### Dynamic calls

```
.insert() payload is not a dict literal on table 'jobs'
```

means the analyzer couldn't see the column set statically — the
payload is a variable (`supabase.table("jobs").insert(body)`) and the
guard can't trace its keys without running the program. These are
**warn-only**; the guard never fails on them. Use `--show-dynamics` to
include them in human output.

### `openapi-ts-guard`

Example:
```
openapi-ts-guard: 1 drift(s) detected
  apps/frontend/src/lib/api.ts:512  interface CVUploadResult
    -> schema CVUploadResponse is missing field 'skills_extracted'
```

Means: `CVUploadResult` (matched to `CVUploadResponse` in the OpenAPI
spec) declares a field the spec doesn't document. Frontend will read a
key the backend doesn't emit — i.e., always `undefined`.

Resolutions:

1. **Rename the TS field** to match what OpenAPI / backend actually
   send. This is what PR #24 did.
2. **Add the field to the OpenAPI schema** if the backend really does
   emit it (then update the Pydantic response model and any related
   migration). The OpenAPI spec is the contract.
3. **Allow-list** the field in
   `scripts/ci_openapi_ts_guard_allowlist.yml` if the field lives only
   on a 202-branch response or other non-200 status that the OpenAPI
   schema intentionally omits.

#### Matching heuristics

The guard finds the OpenAPI counterpart of a TS interface in this
order:

1. `// @openapi SchemaName` comment immediately above the interface.
   This is the **preferred** form — it's explicit, survives renames,
   and reads naturally.
2. Exact name match (`CVGenerationDetail` ↔ `CVGenerationDetail`).
3. Suffix swap: `*Result` ↔ `*Response`, `*ListResponse` ↔ `*List`.
4. Fallback: TS interface logged as unmapped (warn-only). Run with
   `--fail-on-unmapped` to escalate.

### `compose-env-guard`

Example:
```
compose-env-guard: drift detected
  infra/production/docker-compose.prod.yml
    ⚠ missing from infra/production/.env.example:
        - WAHA_NEW_FLAG
```

Means: `docker-compose.prod.yml` references `${WAHA_NEW_FLAG}` for
substitution at `docker-compose up` time, but no operator-facing
`.env.example` documents the variable — so a fresh `cp .env.example
.env` produces an empty value and the service starts silently
mis-configured. Add the variable to the sibling `.env.example` with a
comment explaining what to fill in.

Suspicious-secret hits (long hex strings, `sk-`-prefixed values, JWT
shapes) print as `(warn)` and never fail the build — they exist to
nudge a human to look before merge, not to gate on regex false
positives.

---

## Allow-list shape

### `scripts/ci_schema_guard_allowlist.yml`

```yaml
ignore:
  - table: cvs
    column: legacy_field
    reason: kept for migration backfill; row reads only
  - file: apps/backend/app/services/foo.py
    line: 42
    reason: dynamic table from per-tenant config dict
```

Any combination of `table | column | file | line | method` works; all
declared fields must match. Always include a `reason:`.

### `scripts/ci_openapi_ts_guard_allowlist.yml`

```yaml
ignore:
  - interface: CVUploadResult
    field: queued
    reason: 202-branch field; OpenAPI documents the 200 sync schema only.

unmapped_ok:
  - OTPResponse  # endpoint emits {message: string}; not yet in spec
```

`ignore` silences individual (interface, field) pairs. `unmapped_ok`
silences the "no matching schema in OpenAPI" warning for TS interfaces
whose endpoint shape simply isn't documented yet — preferring to add a
proper schema is always cleaner.

---

## Adding a new check

Each guard exposes a `check(...)` function that returns a list of
drift records. To add (say) a Pydantic ↔ OpenAPI check, follow the
same pattern: pure-Python AST/regex extraction, a structured drift
type, JSON output for CI, and a small fixture-driven test in
`scripts/tests/`.

When adding a new guard, also append it to
`.github/workflows/schema_guard.yml` so it runs on every PR.
