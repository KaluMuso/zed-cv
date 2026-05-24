# n8n workflows and environments

n8n runs **only on production** today. Job scraping, match crons, Supabase heartbeat, subscription expiry, and admin alert workflows all call **`https://api.zedapply.com`** (or the internal Docker hostname `http://backend:8000` on the OCI compose network).

## Production layout

- Compose path on OCI: `~/n8n-docker/`
- Workflow exports: [infra/n8n/](../infra/n8n/)
- Container: `zedcv-n8n` (see [infra/waha/docker-compose.yml](../infra/waha/docker-compose.yml) or production compose)

Environment inside n8n uses **production** `SUPABASE_URL` and `SUPABASE_KEY` from `~/n8n-docker/.env`.

## Staging

**Staging does not run n8n.** The checked-in [infra/staging/docker-compose.yml](../infra/staging/docker-compose.yml) includes backend + WAHA only.

Implications:

- Do not point n8n nodes at `staging-api.zedapply.com` unless you are deliberately testing a one-off workflow copy.
- Staging job data comes from `scripts/seed_staging.py`, not scrapers.
- The Supabase **heartbeat** workflow must stay on production — it prevents the free-tier project from pausing.

## Editing workflows

1. Open n8n UI on OCI (port `5678`, firewall-restricted).
2. Export JSON back to `infra/n8n/<workflow>.json` when stable.
3. PR changes through `develop` → `master` like application code.

## Related

- [staging.md](./staging.md)
- [AGENTS.md](../AGENTS.md) — invariant: 6-hour Supabase heartbeat
