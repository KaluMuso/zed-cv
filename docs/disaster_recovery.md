# Disaster recovery — ZedApply

**RPO target:** 24 hours (Supabase daily backup on Pro).  
**RTO target:** 4 hours for full API + DB restore.

## Contacts

| Role | Action |
|------|--------|
| Kaluba | Decision maker, Lenco/Resend account owner |
| Supabase support | Backup/restore, project pause |

## 1. Supabase (database)

1. Confirm backups: Dashboard → **Database** → **Backups** (enable Pro if disabled).
2. **Restore:** create a **new** project or preview branch from backup snapshot; do not overwrite prod in place without a maintenance window.
3. Update OCI `.env`: `SUPABASE_URL`, `SUPABASE_KEY` (service role) to the restored project if switching.
4. Run pending migrations only if the restore is *older* than prod schema.
5. Smoke: `curl https://api.zedcv.com/api/v1/health` and `python scripts/production_readiness_audit.py`.

## 2. OCI backend + WAHA + n8n

```bash
cd /home/ubuntu/zedcv && git pull origin master
cd ~/n8n-docker
docker compose build --no-cache zedcv-backend
docker compose up -d --force-recreate zedcv-backend
# WAHA: if health.waha != ok, POST /api/v1/admin/waha/bootstrap-session
```

Session files live at `/home/ubuntu/n8n-docker/waha_data/sessions` — back up this directory before OS reinstall.

## 3. Vercel (frontend)

Redeploy from `master` without build cache. Verify `NEXT_PUBLIC_API_URL` points at live API.

## 4. Verification checklist

- [ ] `/api/v1/health` → `status: healthy`, `waha: ok`
- [ ] OTP to test phone succeeds
- [ ] `/matches` returns results for a user with CV + jobs
- [ ] Lenco test payment (small amount) upgrades tier
- [ ] `production_readiness_audit.py` — zero red

## 5. Post-incident

Log timeline in GitHub issue; add regression test or guard if the root cause was code/schema drift.
