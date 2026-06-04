# Match delivery quota — single source of truth

Zed CV limits how many **unique jobs** a user can receive as delivered matches per billing period. Product UI, enforcement, and admin repair all use the same counter.

## Canonical counter

| Field | Meaning |
| --- | --- |
| `matches.credited_at` | Set when a job is **delivered** into the user's monthly allowance (first time that `job_id` is credited this period). |
| Billing window | Calendar month in **Africa/Lusaka**, converted to UTC for queries (`_delivery_month_start` in `app/services/matching.py`). |
| `matches_used` / `credited_count` | Count of active-status rows with `credited_at >=` period start (`get_credited_match_count`). |
| `matches_limit` | Effective cap from `tier_config` + welcome/referral bonuses (`get_effective_match_limit`). |
| `remaining_quota` | `max(0, matches_limit - matches_used)` (`check_match_quota`). |

**Not used for product quota:** `users.matches_viewed_this_month` and `users.billing_cycle_reset` (UTC calendar reset). Those remain for legacy `verify_tier_access(FEATURE_JOB_MATCHES)` paths elsewhere; they must not drive `/matches` list, refresh, subscription, or dashboard quota display.

## Canonical HTTP routes (product)

Use these for UI and integrations:

| Route | Role |
| --- | --- |
| `GET /api/v1/matches` | **Primary feed** — credited deliveries this Lusaka month; quota block via `build_match_quota_snapshot`. |
| `POST /api/v1/matches/refresh` | Cached nightly batch (or onboarding fallback); same quota block. |
| `GET /api/v1/subscription` | Billing page; `matches_used` from `get_credited_match_count`. |

Frontend: `resolveMatchQuotaDisplay()` in `apps/frontend/src/lib/matchQuota.ts` prefers `matches_used` / `credited_count` / `remaining_quota` from **GET /matches** (or refresh), not `subscription.matches_used` alone. See dashboard audit / PR #239.

## Deprecated live RPC route

| Route | Status |
| --- | --- |
| `GET /api/v1/matches/{user_id}` | **Deprecated** — live `match_jobs_for_user` scores. Quota **enforcement** and response fields now match GET /matches (`assert_match_delivery_quota` + `build_match_quota_snapshot`). Does not increment `matches_viewed_this_month`. |

Prefer `GET /matches` + `POST /matches/refresh` for product. The `{user_id}` path exists for backward compatibility and tests; new clients should not depend on it.

## Code map

| Module | Responsibility |
| --- | --- |
| `app/services/matching.py` | `get_credited_match_count`, `check_match_quota`, `credit_matches_for_cycle`, `fetch_delivered_match_rows` |
| `app/services/match_quota.py` | `build_match_quota_snapshot`, `assert_match_delivery_quota` |
| `app/api/v1/matches.py` | GET /matches, POST /refresh, deprecated GET /{user_id} |
| `app/api/v1/subscription.py` | Subscription payload `matches_used` |
| `app/core/tier_gating.py` | Feature gates (cover letter, interview prep); legacy view counter |

## Admin repair

When delivery and UI disagree: `POST /api/v1/admin/users/{id}/repair-delivery-quota` (see `docs/RUNBOOK_INDEX.md`).

## Smoke checks

1. Same user: `GET /matches` and `GET /subscription` — `matches_used` / `remaining_quota` consistent.
2. Dashboard quota card matches `/matches` header (after refresh).
3. Super Standard with deliveries: not `0 · Unlimited` when `remaining_quota` implies usage (PR #239).
