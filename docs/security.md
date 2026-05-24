# Zed CV — Security Notes

## SECURITY DEFINER hardening 2026-05-24

Supabase Database Linter flagged **SECURITY DEFINER** functions callable by the `anon` role. Anyone with the public anon key could invoke these RPCs over PostgREST (`/rest/v1/rpc/<name>`) without authentication. Because these functions run as the owner (bypassing RLS), that exposure is high severity.

Migration: `infra/supabase/migrations/063_revoke_security_definer_anon.sql`

### Functions hardened

| Function | Why it was dangerous | Revoked from | Who can still call it |
| --- | --- | --- | --- |
| `activate_subscription_after_payment(...)` | Upgrades user tier and extends billing after payment — bypasses webhook verification if called directly | `anon`, `authenticated`, `PUBLIC` | `service_role` only (FastAPI DPO/Lenco webhooks via `app/services/subscription_billing.py`) |
| `admin_stats()` | Returns platform-wide user, job, match, and revenue aggregates | `anon`, `authenticated`, `PUBLIC` | `service_role` only (`GET /api/v1/admin/stats` with `require_admin` + service key in `get_supabase`) |
| `admin_export_companies()` | Exports all companies, contact fields, and job counts | `anon`, `authenticated`, `PUBLIC` | `service_role` only (`GET /api/v1/admin/export/companies.csv` with `require_admin`) |
| `downgrade_expired_subscriptions()` | Batch-cancels paid tiers and sets users to `free` | `anon`, `authenticated`, `PUBLIC` | `service_role` only (n8n daily cron `infra/n8n/subscription_expiry_daily.json` with `SUPABASE_SERVICE_ROLE_KEY`) |
| `schema_guard_rls()` | Reads `pg_class` RLS flags for audited tables (ops introspection) | `anon`, `authenticated`, `PUBLIC` | `service_role` only (`apps/backend/scripts/production_readiness_audit.py`) |

### Legitimate call paths (unchanged)

- **Payments:** Webhooks in `apps/backend/app/api/v1/webhooks.py` call `activate_subscription_after_payment()` through the Python helper; they do not rely on browser/anon PostgREST access.
- **Admin:** `apps/backend/app/api/v1/admin.py` and `admin_companies_export.py` use `Depends(require_admin)` on the router and invoke RPCs with `settings.supabase_key` (documented as service_role in `app/core/config.py`).
- **Cron:** Subscription expiry uses the service role key in n8n headers, not the anon key.
- **Frontend:** No `.rpc('…')` usage for any of the five functions under `apps/frontend/src/`.

### Apply

Run the migration in Supabase SQL Editor or your usual migration pipeline. After apply, verify in SQL:

```sql
SELECT p.proname, r.rolname, has_function_privilege(r.oid, p.oid, 'EXECUTE') AS can_execute
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
CROSS JOIN pg_roles r
WHERE n.nspname = 'public'
  AND p.proname IN (
      'activate_subscription_after_payment',
      'admin_stats',
      'admin_export_companies',
      'downgrade_expired_subscriptions',
      'schema_guard_rls'
  )
  AND r.rolname IN ('anon', 'authenticated', 'service_role')
ORDER BY 1, 2;
```

Expect `can_execute = false` for `anon` and `authenticated`, and `true` for `service_role` only.
