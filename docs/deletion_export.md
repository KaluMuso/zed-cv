# Account deletion, data export, and consent log (Bucket 9)

ZDPA 2021 rights implemented: **right to erasure** (scheduled deletion with grace period) and **right to portability** (ZIP export with signed URL).

## Prerequisites

- **Sensitive-action OTP** (`app/services/otp.py`): `delete_account` and `export_data` require a fresh OTP even when `X-Device-Token` would skip login OTP (Bucket 8.5 contract).
- Migration **`064_deletion_export_consent.sql`**: `data_deletion_requests`, `data_export_requests`, `consent_log`, `deletion_safety_allowlist`, and `users.deleted_at`.

## API (under `/api/v1/users`)

| Method | Path | Body | Notes |
|--------|------|------|-------|
| POST | `/me/delete-request` | `{ "otp_code": "123456" }` | Schedules erasure `now + 7 days` |
| POST | `/me/delete-cancel/{request_id}` | — | Only while `status=pending` |
| POST | `/me/export-request` | `{ "otp_code": "123456" }` | Queues ZIP; background `generate_export` |
| GET | `/me/export-status/{request_id}` | — | Poll until `ready` + `download_url` |
| POST | `/me/consent` | `{ "consent_type", "granted" }` | Service-role insert into `consent_log` |

Legacy **`DELETE /api/v1/me`** and **`GET /api/v1/me/export`** (immediate JSON) remain for backward compatibility; new UI uses the routes above.

## Deletion execution order (`execute_deletion`)

1. **Safety allowlist** — if `users.phone` is in `deletion_safety_allowlist`, mark `failed` / `safety_allowlist`. **No DELETE runs before this check.**
2. Supabase Storage — remove `documents` bucket paths under `cvs/{user_id}/`
3. **Anonymise** `users` row — `phone`, `email`, `full_name` → NULL; set `deleted_at`, `is_active=false`. **Never DROP `users`.**
4. **Hard-delete** (by `user_id`): `user_skills`, `cvs`, `matches`, `cv_generations`, `generated_documents` (incl. cover letters), `application_outcomes`, `user_preferences`, `interview_sessions`, `aptitude_scores`, `saved_jobs`, `cv_upload_queue`, `otp_codes` (by phone), `trusted_devices` (if table exists), Bwana transcripts in `ai_cache` (`cache_type=bwana_chat`, matched on `result.user_id`).
5. **Anonymise** (set `user_id` NULL): `payments`, `consent_log`, `subscriptions`
6. Write counts to `data_deletion_requests.artifacts`; `status=completed`

### `bwana_chat_history`

There is **no** `bwana_chat_history` table. Bwana conversation state lives in **`ai_cache`** with `cache_type = bwana_chat`. Deletion removes those rows by `result.user_id`.

## Export bundle

ZIP at `exports/{user_id}/{request_id}.zip` in the `documents` bucket:

- `profile.json` — full bundle (profile, CVs metadata, matches, payments, etc.)
- `cvs/*` — raw files from storage when `file_url` is present
- `matches.csv`
- `consent_log.json`

Signed URL TTL: **7 days** (`download_expires_at`).

## Safety allowlist (manual, post-merge)

Do **not** seed phones in migration. After deploy:

```sql
INSERT INTO deletion_safety_allowlist (phone, reason)
VALUES ('+260YOURPHONE', 'founder'), ('+260WIFEPHONE', 'family-test-account');
```

## Verification (staging)

1. Synthetic user `+260911000099`
2. `POST /users/me/delete-request` with valid OTP → `pending`, `scheduled_at ≈ now + 7d`
3. `UPDATE data_deletion_requests SET scheduled_at = NOW() - INTERVAL '1 hour' WHERE id = …`
4. Call `execute_deletion(request_id)` (admin/cron — not yet wired to n8n; invoke from shell or future job)
5. Confirm hard-deleted child tables empty; `users` row exists with nulled PII and `deleted_at` set

## Frontend

- `/settings/account` — delete + export with OTP modal
- `/settings/privacy` — consent toggles → `POST /me/consent`
