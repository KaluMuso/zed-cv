# ZedApply operations runbook

Day-2 operations for production and staging. For first-time deploy steps, see [DEPLOY.md](../DEPLOY.md).

---

## Production quick reference

| Item | Value |
| --- | --- |
| Frontend | https://zedapply.com (Vercel, branch `master`) |
| API | https://api.zedapply.com |
| Compose | `~/n8n-docker/` on OCI |
| Supabase | `chnesgmcuxyhwhzomdov` |
| Audit | `python scripts/production_audit.py --env production` |

### Production deploy (backend)

```bash
cd ~/n8n-docker
git pull   # or rsync new image context
docker compose build zedcv-backend
docker compose up -d --force-recreate zedcv-backend
```

After `.env` changes, use `up -d --force-recreate` — **`docker compose restart` does not reload `.env`** (see AGENTS.md §3.5).

### Production health

```bash
curl -sS https://api.zedapply.com/api/v1/health | jq
curl -sS https://api.zedapply.com/api/v1/health/ready | jq
```

---

## Staging quick reference

| Item | Value |
| --- | --- |
| Frontend | https://preview.zedapply.com (Vercel `develop`) |
| API | https://staging-api.zedapply.com |
| Compose | `~/n8n-docker-staging/` |
| Supabase | Separate project — see [staging.md](./staging.md) |
| Audit | `python scripts/production_audit.py --env staging` |
| Seed | `python scripts/seed_staging.py` |

Full setup: [staging.md](./staging.md). Branch flow: [branching.md](./branching.md).

---

## Staging recovery (nuke and rebuild)

Use when the staging compose stack is corrupt, `.env` was wrong, or WAHA volumes need reset. **Does not touch production** (`~/n8n-docker`).

### 1. Stop and remove staging containers

```bash
cd ~/n8n-docker-staging
docker compose down
```

### 2. Optional — wipe staging volumes only

```bash
rm -rf ~/n8n-docker-staging/data/waha/*
# Do NOT delete ~/n8n-docker/data — that is production WAHA
```

### 3. Refresh compose template from repo

```bash
cp /path/to/zed-cv/infra/staging/docker-compose.yml ~/n8n-docker-staging/
# Ensure .env exists (from infra/staging/.env.example)
```

### 4. Rebuild and start

```bash
cd ~/n8n-docker-staging
docker compose build backend
docker compose up -d
docker compose logs -f zedcv-backend-staging
```

### 5. Verify reverse proxy

Confirm Caddy/Nginx still routes `staging-api.zedapply.com` → `127.0.0.1:8001` ([infra/staging/Caddyfile.snippet](../infra/staging/Caddyfile.snippet)).

```bash
curl -sS https://staging-api.zedapply.com/api/v1/health | jq
```

### 6. Reset staging database (optional)

If schema drifted or bad data was imported:

1. In Supabase staging dashboard: reset database **or** re-run migrations on a fresh project.
2. Re-apply `infra/supabase/migrations/*.sql` in order.
3. Re-seed: `python scripts/seed_staging.py` with `STAGING_SUPABASE_*` env vars.

Never run seed against production URLs (script refuses project ref `chnesgmcuxyhwhzomdov`).

### 7. Vercel preview

If `preview.zedapply.com` shows production data, fix **Preview** environment variables in Vercel — not Production. See [staging.md](./staging.md).

---

## Common failures

| Symptom | Likely cause | Action |
| --- | --- | --- |
| Browser “CORS” on staging login | Backend 500 | `curl -i` staging API; read `docker compose logs zedcv-backend-staging` |
| Staging shows prod jobs | Wrong Supabase URL on Vercel Preview | Update Preview env vars |
| OTP sent to real users from staging | Staging WAHA paired to prod session | Use `default-staging`, burner phone, or keep unpaired |
| n8n hit staging API | Misconfigured workflow URL | n8n is prod-only — [n8n.md](./n8n.md) |

---

## Related

- [promotion_checklist.md](./promotion_checklist.md)
- [production_cutover.md](./production_cutover.md)
- [disaster_recovery.md](./disaster_recovery.md)
