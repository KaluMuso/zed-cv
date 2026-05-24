# Promotion checklist (develop → master)

Copy this checklist into the body of every `develop → master` PR. Tick each item before merging.

## Pre-merge

- [ ] All migrations in this PR have been applied to staging Supabase and verified (`supabase db push` against staging, then spot-check affected tables)
- [ ] `preview.zedapply.com` smoke test passed:
  - [ ] Login (email + OTP)
  - [ ] View `/matches` — at least one match renders
  - [ ] Send a Bwana (WhatsApp) message — appears in WAHA logs
  - [ ] Open an admin tab — no console errors
- [ ] No new Sentry errors on staging in the last 24h (check `staging-backend` and `staging-frontend` projects)
- [ ] Backend `/v1/health` and `/v1/health/ready` return 200 on staging
- [ ] If this PR contains a **schema change**:
  - [ ] Production migration order verified — no prefix collisions with existing prod migrations
  - [ ] Migration is forward-only OR rollback path is documented in the PR body
  - [ ] Affected RLS policies re-tested on staging
- [ ] If this PR contains a **WAHA-affecting change**:
  - [ ] Tested against staging WAHA instance
  - [ ] Did NOT spam real users (used test phone numbers only)
  - [ ] WAHA session is healthy (`GET /api/sessions` on staging)
- [ ] If this PR contains a **Lenco-affecting change**:
  - [ ] Re-tested sandbox payment flow on staging end-to-end (init → webhook → DB state)
  - [ ] Webhook signature verification confirmed working
  - [ ] Idempotency keys behave correctly on retry

## Merge

- [ ] PR uses a **merge commit** (not squash) — preserves feature commit history in `master`
- [ ] Tag the merge commit: `git tag -a vYYYY.MM.DD -m "release YYYY-MM-DD"` and `git push origin vYYYY.MM.DD`

## Post-merge

- [ ] `zedapply.com` smoke test passed (same steps as staging smoke test above)
- [ ] Backend health endpoints green on production
- [ ] Sentry quiet for 30 minutes after deploy
- [ ] If migration ran: spot-check affected production tables for expected row counts / shape
- [ ] If anything regressed: revert via `revert: ...` PR (see `docs/branching.md` FAQ for the emergency-rollback path)

## Notes

- Production deploys are triggered by merge to `master`. Do not merge outside business hours unless you can monitor for 30 minutes.
- If staging and production drift (e.g. staging has data prod doesn't), call it out in the PR body — some smoke tests may not be apples-to-apples.
