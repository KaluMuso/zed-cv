-- 013_drop_widened_check_constraints.sql
--
-- Purpose:
--   Migration 011's own comment named this slice as the next step:
--   "dropping these constraints and validating at the application layer
--   (Pydantic enum at the input boundary, one place to add new values).
--   For now we just widen — that refactor is a separate slice."
--
--   This is that slice.
--
-- What this drops (the "hot" CHECKs that have been widened 3+ times):
--   - users.subscription_tier (widened in 003, 005, 010)
--   - subscriptions.tier (widened in 003, 005, 010)
--   - ai_cache.cache_type (widened in 004, 005, 011)
--   - cv_upload_queue.status (new in 012, on the same trajectory)
--
-- What this DOES NOT drop (and why):
--   - quality_score, score range CHECKs — these guard against data
--     corruption (negative scores, >100 percentages) that no app-layer
--     validation can recover from for existing rows. Different class.
--   - file_type, proficiency, language, role, matches.status,
--     payments.status, subscriptions.status, payment_method,
--     doc_type, jobs.source — stable enum CHECKs that haven't required
--     widening since they were added. No recurring tax = no need to drop.
--
-- Deploy order (important):
--   1. App-layer enums + write-site validation deploys FIRST.
--   2. THIS migration applies.
--   3. Without step 1, there's a window where invalid values could
--      land in the DB unchecked. The corresponding Pydantic enums
--      (CacheType, QueueStatus) plus the existing SubscriptionTier
--      cover the four columns we're dropping CHECKs on.
--
-- Rollback:
--   If a bug allows bad data to land, re-create the constraint via a
--   follow-up migration with `ADD CONSTRAINT ... CHECK (col IN (...))`.
--   Existing valid rows pass; new invalid rows fail.
--
-- Idempotency: DROP CONSTRAINT IF EXISTS, safe to re-run.

BEGIN;

ALTER TABLE public.users
    DROP CONSTRAINT IF EXISTS users_subscription_tier_check;

ALTER TABLE public.subscriptions
    DROP CONSTRAINT IF EXISTS subscriptions_tier_check;

ALTER TABLE public.ai_cache
    DROP CONSTRAINT IF EXISTS ai_cache_cache_type_check;

ALTER TABLE public.cv_upload_queue
    DROP CONSTRAINT IF EXISTS cv_upload_queue_status_check;

COMMIT;
