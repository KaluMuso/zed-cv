# Production promotion checklist

Copy this section into the **`develop` → `master`** PR description and check each item before merge.

## PR metadata

- **Source branch:** `develop`
- **Target branch:** `master`
- **Staging preview:** https://preview.zedapply.com
- **Staging API:** https://staging-api.zedapply.com/api/v1/health

## Database and schema

- [ ] Every new migration in this release was applied to **staging Supabase** in numeric order (`001` … latest).
- [ ] `059_audit_idempotent.sql` (or latest audit migration) passes on staging SQL editor.
- [ ] `python scripts/production_audit.py --env staging` reports no **red** checks (yellow acceptable for unpaired WAHA).
- [ ] Production migration filenames were reviewed for **prefix collisions** (no duplicate `NNN_` numbers).

## Staging functional smoke test

- [ ] `preview.zedapply.com` loads marketing/login UI (staging Supabase + staging API env vars).
- [ ] Login with synthetic staging user `+260971000001` (OTP flow or test bypass per team process).
- [ ] **Matches** page shows **synthetic** jobs only (not production data).
- [ ] Bwana chat sends a test message without errors (no spam to real user phones).
- [ ] No new **Sentry** issues on project `zedapply-staging` in the last 24 hours.

## Backend health

- [ ] `GET https://staging-api.zedapply.com/api/v1/health` → `200`, overall status acceptable.
- [ ] `GET https://staging-api.zedapply.com/api/v1/health/ready` → `200` when dependencies configured.

## Integrations (if touched in this release)

- [ ] **WAHA:** tested against **staging** WAHA only; no OTP/digest sent to real production users.
- [ ] **Lenco:** sandbox payment flow re-tested on staging (never live keys on staging).
- [ ] **Email:** staging uses separate Resend key/domain or outbound email disabled.
- [ ] **n8n:** unchanged workflows still target **production** API only ([n8n.md](./n8n.md)).

## CI and contract

- [ ] All required GitHub checks green on the `develop` → `master` PR.
- [ ] OpenAPI ↔ TypeScript guard passed (`scripts/ci_openapi_ts_guard.py`).
- [ ] No production URL or production Supabase project ref in staging env configuration (grep diff).

## Post-merge (production)

- [ ] Vercel production deployment succeeded for `master`.
- [ ] OCI production backend recreated if `requirements.txt` or `.env` changed (`docker compose build` + `up -d --force-recreate`).
- [ ] `python scripts/production_audit.py --env production` green on OCI.
- [ ] `GET https://api.zedapply.com/api/v1/health` verified.

## Sign-off

- [ ] Reviewed by: __________________  Date: __________
