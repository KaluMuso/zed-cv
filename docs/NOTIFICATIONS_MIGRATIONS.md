# Notifications migration train

Linear Supabase migration sequence for in-app notifications, admin broadcast
campaigns, and related admin stats. **Do not apply to production from this
document alone** — run each file in order via your normal migration process
(Supabase CLI / dashboard / ops runbook).

## Supersedes

| PR | Branch | Status |
| --- | --- | --- |
| #248 | `cursor/user-notifications-dropdown-9e6a` | Superseded by migration train PR |
| #249 | `cursor/admin-notifications-push-9e6a` | Superseded by migration train PR |
| #256 | `cursor/admin-review-queue-overview-9e6a` | Stats portion superseded (`102_*`); other UI changes land separately |

## Apply order (master baseline through 103)

| # | File | Purpose |
| --- | --- | --- |
| 099 | `099_match_dismiss_note.sql` | Optional dismiss note on matches |
| 100 | `100_in_app_notifications.sql` | `notifications` inbox + RLS (types: `web_push`, `tier_expiry`, `invoice`, `admin_broadcast`) |
| 101 | `101_admin_broadcast_notifications.sql` | `admin_notification_campaigns` + `admin_notification_recipients` |
| 102 | `102_admin_stats_jobs_active_public.sql` | `admin_stats()` with review counters + `jobs_active_public` |
| 103 | `103_zambia_skill_aliases_fix.sql` | Idempotent repair for `098_zambia_skill_aliases` |

### Removed duplicate (do not apply)

- **`099_admin_stats_job_review_counts.sql`** — dropped; its `admin_stats()` changes are fully included in `102_admin_stats_jobs_active_public.sql`.

### Renumbered from conflicting PRs

| Old name (PR branch) | New name |
| --- | --- |
| `100_admin_broadcast_notifications.sql` (#249) | `101_admin_broadcast_notifications.sql` |
| `101_admin_stats_jobs_active_public.sql` (#256) | `102_admin_stats_jobs_active_public.sql` |
| `102_zambia_skill_aliases_fix.sql` (#256) | `103_zambia_skill_aliases_fix.sql` |

## Schema model

### User inbox (`notifications` — migration 100)

Single table for navbar dropdown / `GET /api/v1/notifications`:

| `type` | Source |
| --- | --- |
| `web_push` | High-match push, test push (`web_push.py`) |
| `tier_expiry` | Renewal reminder (`renewal_reminder.py`) |
| `invoice` | Payment receipt email path (`email.py`) |
| `admin_broadcast` | Admin campaign delivery (`admin_notifications.py`) |

Distinct from **`user_notifications`** (migration 050): digest dedup only
(`job_id` + `channel`), not the in-app inbox.

### Admin campaigns (migration 101)

- `admin_notification_campaigns` — compose + schedule metadata
- `admin_notification_recipients` — per-user Web Push delivery status

On successful push delivery, the backend inserts an `admin_broadcast` row into
`notifications` so users see the same title/body/url in the inbox.

## Production apply checklist (human)

1. Confirm current ledger: highest applied migration before this train.
2. If `099_match_dismiss_note` not applied, apply `099` first.
3. Apply `100` → `101` → `102` → `103` in order.
4. If `099_admin_stats_job_review_counts` was partially applied in a broken
   deploy, **skip** it; `102` replaces that function definition entirely.
5. Smoke:
   - `GET /api/v1/notifications` (authenticated user)
   - `POST /api/v1/admin/notifications` (admin + ingest key)
   - Admin overview stats include `jobs_need_review` and `jobs_active_public`

## Backend references

- `apps/backend/app/services/in_app_notifications.py`
- `apps/backend/app/services/admin_notifications.py`
- `apps/backend/app/api/v1/notifications.py`
- `apps/backend/app/api/v1/admin_notifications.py`
