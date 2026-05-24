# Disaster recovery — ZedApply

**RPO target:** 24 hours (nightly `pg_dump` to OCI Object Storage at 02:30 CAT).  
**RTO target:** 4 hours for full API + DB restore (manual runbook).

## Contacts

| Role | Action |
|------|--------|
| Kaluba | Decision maker, Lenco/Resend account owner, backup env secrets |
| Supabase support | Project pause, connection limits, extension issues |

---

## 1. Automated backups (OCI)

Nightly backups run on the **OCI VM** (`~/n8n-docker` / `~/zedcv` host), not inside Docker.

| Item | Value |
|------|--------|
| Script | `scripts/backup_database.sh` |
| Schedule | 02:30 CAT daily (`30 0 * * *` UTC) — see `infra/cron/backup.cron` |
| Bucket | `zedapply-backups` (OCI Object Storage) |
| Object name | `zedapply_YYYY-MM-DD_HH-MM.sql.gz.enc` |
| Retention | 30 daily + 12 monthly (1st-of-month snapshots) |
| Log | `/var/log/zedapply-backup.log` |

### 1.1 One-time OCI setup

1. **Install tools** on the VM: `postgresql-client`, `oci-cli`, `jq`, `openssl`.
2. **OCI CLI auth** (pick one):
   - **Instance principal** (recommended on OCI compute): add the VM to a dynamic group with `OBJECT_STORAGE_OBJECT` manage on compartment; set `OCI_CLI_AUTH=instance_principal` in `/etc/zedapply/backup.env`.
   - **API key config file**: `oci setup config` as `ubuntu`, default `~/.oci/config`; ensure the user can `oci os object put` to `zedapply-backups`.
3. **Create bucket** `zedapply-backups` in the same region as the VM (e.g. `af-johannesburg-1`).
4. **Secrets file**:
   ```bash
   sudo mkdir -p /etc/zedapply
   sudo cp scripts/backup.env.example /etc/zedapply/backup.env
   sudo chmod 600 /etc/zedapply/backup.env
   sudo chown root:root /etc/zedapply/backup.env
   # Edit: SUPABASE_DB_URL, BACKUP_ENCRYPTION_KEY, optional OCI_CLI_AUTH
   ```
5. **Install cron**:
   ```bash
   sudo cp infra/cron/backup.cron /etc/cron.d/zedapply-backup
   sudo chmod 644 /etc/cron.d/zedapply-backup
   sudo chmod +x scripts/backup_database.sh scripts/restore_database.sh scripts/test_backup_restore.sh
   ```

### 1.2 Manual backup (verification)

```bash
sudo BACKUP_ENV_FILE=/etc/zedapply/backup.env ./scripts/backup_database.sh
oci os object list --bucket-name zedapply-backups --prefix zedapply_ | head
tail -20 /var/log/zedapply-backup.log
```

### 1.3 Restore from OCI backup

**Use a new Supabase project or a throwaway local Postgres first.** Do not point at production until you intend to overwrite it.

```bash
# Example: local throwaway DB
createdb test_restore
export BACKUP_ENCRYPTION_KEY='...'   # same key as backup time
./scripts/restore_database.sh zedapply_2026-05-25_02-30.sql.gz.enc postgres://localhost:5432/test_restore
```

When prompted, type **`YES`** (all caps) to confirm.

**Production cutover after restore:**

1. Create a **new** Supabase project **or** restore into a dedicated recovery project.
2. Run `restore_database.sh` with the latest `zedapply_*.sql.gz.enc` object name.
3. Update OCI `apps/backend/.env` and n8n `.env`: `SUPABASE_URL`, `SUPABASE_KEY` (service role).
4. Apply any migrations **newer** than the dump only if the backup predates schema changes (`infra/supabase/migrations/`).
5. Re-embed if `EMBEDDING_MODEL` changed since backup: `POST /api/v1/admin/re-embed?target=all`.
6. Smoke: health, OTP, `/matches`, `production_readiness_audit.py`.

### 1.4 Weekly test-restore (optional)

`scripts/test_backup_restore.sh` runs **Sunday 03:30 CAT** (`30 1 * * 0` UTC) when `STAGING_SUPABASE_DB_URL` is set in `/etc/zedapply/backup.env`. It restores the latest object to staging and runs `SELECT COUNT(*) FROM public.users`. On failure it WhatsApps Kaluba via WAHA (`ADMIN_ALERT_PHONE`, `WAHA_API_URL`, `WAHA_API_KEY`).

**TODO:** Provision a disposable Supabase staging project and set `STAGING_SUPABASE_DB_URL` before enabling this cron line in production.

---

## 2. Supabase dashboard backups (secondary)

Free tier has **no** PITR. Pro tier adds dashboard backups — treat OCI dumps as **primary** DR for free tier.

If you upgrade to Pro, keep OCI dumps as an independent copy (ransomware / operator error protection).

---

## 3. OCI backend + WAHA + n8n

```bash
cd /home/ubuntu/zedcv && git pull origin master
cd ~/n8n-docker
docker compose build --no-cache zedcv-backend
docker compose up -d --force-recreate zedcv-backend
# WAHA: if health.waha != ok, POST /api/v1/admin/waha/bootstrap-session
```

Session files: `/home/ubuntu/n8n-docker/waha_data/sessions` — back up before OS reinstall.

---

## 4. Vercel (frontend)

Redeploy from `master` without build cache. Verify `NEXT_PUBLIC_API_URL` points at live API.

---

## 5. Verification checklist

- [ ] `/api/v1/health` → `status: healthy`, `waha: ok`
- [ ] OTP to test phone succeeds
- [ ] `/matches` returns results for a user with CV + jobs
- [ ] Lenco test payment (small amount) upgrades tier
- [ ] `production_readiness_audit.py` — zero red
- [ ] Latest object visible in `zedapply-backups` after manual backup

---

## 6. Environment variables (secrets checklist)

Populate on the OCI VM in `/etc/zedapply/backup.env`:

| Variable | Required | Notes |
|----------|----------|--------|
| `SUPABASE_DB_URL` | Yes | Direct Postgres URI (not pooler) for `pg_dump` |
| `BACKUP_ENCRYPTION_KEY` | Yes | `openssl rand -base64 32` — store in password manager |
| `OCI_BACKUP_BUCKET` | No | Default `zedapply-backups` |
| `OCI_CLI_AUTH` | No | Set to `instance_principal` on OCI compute |
| `STAGING_SUPABASE_DB_URL` | For test-restore | Disposable staging project only |
| `WAHA_API_URL` / `WAHA_API_KEY` | For alerts | Same as n8n-docker stack |
| `ADMIN_ALERT_PHONE` | For alerts | Default `+260761359005` |

---

## 7. Post-incident

Log timeline in a GitHub issue; add a guard or test if root cause was schema drift, missing backup, or wrong `SUPABASE_DB_URL` after restore.
