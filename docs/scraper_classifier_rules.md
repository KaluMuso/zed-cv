# WhatsApp scraper classifier rules

Track 4c ingests messages from configured WAHA channels. Before a row reaches
`jobs`, `whatsapp_classifier` decides whether the payload is a **specific job
posting** or noise to discard.

## Decision buckets (ai_cache.metadata)

Each classification write stores:

```json
{
  "classifier_decision": "accepted_as_job | rejected_as_promo | rejected_as_other",
  "llm_response": "<raw JSON from model or null when regex pre-filter fired>",
  "took_ms": 42
}
```

| Value | Meaning |
| --- | --- |
| `accepted_as_job` | LLM returned `is_job: true` with extractable fields |
| `rejected_as_promo` | Regex pre-filter matched an obvious ad (no LLM call) |
| `rejected_as_other` | LLM returned `is_job: false`, or classify parse failed |

Admin dashboard: `GET /api/v1/admin/scraper-stats?days=7`.

## Regex pre-filter (no LLM)

Applied to text bodies and image captions **before** OpenRouter. Patterns live in
`app/services/whatsapp_classifier_prefilter.py`:

| Pattern | Example |
| --- | --- |
| `CV\s*writing` | "Professional CV writing — K50" |
| `CV\s*service` | "CV service available" |
| `take advantage of` + `promotion` | "Take advantage of our promotion today" |
| `inbox us on whats\s*app` | "Inbox us on WhatsApp for tips" |
| `(K\|ZMW)\d{2,4} per (week\|day\|month)` | "K150 per week CV package" |

Rejected pre-filter rows are cached for 30 days like LLM results.

## LLM prompt (is_job=true bar)

`is_job=true` **only** when the message describes a **specific role** at a
**specific employer**, with at least one of:

- Job title
- Company name
- Application instructions (email, URL, phone, office address)

Explicit `is_job=false` categories include CV-writing services, recruitment-agency
promos, motivational posts, paid-group invites, affiliate schemes, unrelated
service sales, mobile-money scams, and bulk promos (`Take advantage of`,
`🎉 Promotion 🎉`, etc.).

**If unsure, lean `is_job=false`** to keep the job board clean.

## Caching

- `ai_cache.cache_type = whatsapp_classify`
- Keys: `wa_classify_text:{model}:{sha256}` / `wa_classify_img:{model}:{sha256}:{caption_hash}`
- TTL: 30 days (`expires_at`)

## Related code

- Classifier: `apps/backend/app/services/whatsapp_classifier.py`
- Pre-filter: `apps/backend/app/services/whatsapp_classifier_prefilter.py`
- Webhook: `apps/backend/app/api/v1/whatsapp_scraper_webhook.py`
- Migration: `infra/supabase/migrations/045_ai_cache_classifier_metadata.sql`
