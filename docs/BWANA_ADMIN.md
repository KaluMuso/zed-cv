# Bwana admin configuration

Admin UI: **https://www.zedapply.com/admin/bwana** (requires admin or superadmin JWT).

## What you can edit

| Field | Purpose |
| --- | --- |
| `support_email` | Shown to users + receives escalation emails (Resend) |
| `support_phone` | Public +260 E.164 line in contact replies |
| `escalation_whatsapp_phone` | WAHA destination for human / unsatisfied escalations |
| `escalation_sla_hours` | Substituted as `{sla}` in reply templates |
| Reply templates | `{email}`, `{phone}`, `{sla}`, `{operator}`, `{chatbot_name}`, `{ticket_id}` |
| `faq_intents_json` | Admin-editable FAQ array (see below) |
| `public_knowledge_extra` | Max 2000 chars appended to Bwana system prompt (no secrets) |
| `enable_email_escalation` | When true, escalations also email `support_email` |
| `enable_user_escalation_ack` | When true and the user has an email on file, send acknowledgement via Resend |
| `user_escalation_ack_template` | Email body for user ack; supports `{ticket_id}`, `{operator}`, `{sla}`, `{email}`, `{phone}` |

Do **not** store API keys, ingest secrets, or scraper credentials in this table.

## API

- `GET /api/v1/admin/bwana/config`
- `PATCH /api/v1/admin/bwana/config`
- `GET /api/v1/admin/bwana/config/preview` — truncated assembled system prompt
- `GET /api/v1/admin/bwana/analytics?days=7` — message counts, escalation rate, top FAQ intents
- `POST /api/v1/admin/bwana/test-escalation` — one WAHA ping to escalation phone

Public (no auth): `GET /api/v1/bwana/public-config` — email, phone, SLA (no escalation WhatsApp).

## Apply migration

```bash
# Supabase SQL editor or CLI
psql "$DATABASE_URL" -f infra/supabase/migrations/092_bwana_platform_config.sql
psql "$DATABASE_URL" -f infra/supabase/migrations/093_bwana_phase2_faq_analytics_tickets.sql
```

### Custom FAQ JSON example

```json
[
  {
    "intent_id": "refund_policy",
    "enabled": true,
    "triggers": ["refund policy", "money back"],
    "response": "See /legal/refund for our 7-day refund rules."
  }
]
```

Default seed: `convergeozambia@gmail.com`, `+260761359005` (matches `admin_alert_phone`).

## n8n pipeline

`infra/n8n/bwana_chat_pipeline.json` is optional. On OCI, leave `BWANA_N8N_WEBHOOK_URL` empty to run FAQ + escalation + LLM **in-process** on the backend (recommended). If you re-enable the n8n webhook, the exported workflow mirrors backend FAQ routing (50/20/15/10/5 matching, Starter without tailored CV, unsatisfied/contact-admin paths, chatbot identity in the LLM node). Escalation WAHA still uses `escalation_whatsapp_phone` from DB (falls back to env `ADMIN_ALERT_PHONE` only when the table is missing).

## Smoke checklist

1. "What's your support email?" → configured email in reply
2. "I'm not satisfied" → apology template + WAHA + log row
3. "Talk to human" → human template + WAHA
4. "What is your ingest API key?" → refusal (boundaries)
5. Widget badge shows **Bwana**, not "AI"
