# Bwana chatbot — implementation record & agent prompts

This document captures **Phase 1** (merged PR #211) and **Phase 2** (admin FAQ JSON, ticket IDs, analytics, interview alignment).

---

## Phase 1 completion report (PR #211)

**Merged:** `feat(bwana): admin config, escalation log, and knowledge boundaries (#211)`  
**Migration:** `092_bwana_platform_config.sql` (not 086/088 — those are separate jobs/RLS migrations)

### Deliverables

| Area | Detail |
|------|--------|
| Migration | `092_bwana_platform_config.sql` — singleton config + `bwana_escalation_log` |
| Admin UI | `/admin/bwana` — contact, templates, public knowledge, prompt preview, test escalation |
| Identity | Bwana = **chatbot**; system prompt forbids “LLM/ChatGPT” |
| Matching copy | 50/20/15/10/5 aligned with migration 060 |
| Starter tier | No tailored CV in FAQ/marketing (Professional+ only) |
| Escalation | WAHA + optional Resend email; `contact_admin` skips WAHA unless callback |
| Security | `docs/BWANA_KNOWLEDGE_BOUNDARIES.md`, `prompt_safety` on chat |
| Tests | 22+ bwana tests; 982 backend total at merge time |

### Default seed

- Email: `convergeozambia@gmail.com`
- Phone / escalation WhatsApp: `+260761359005`

### Smoke checklist

| # | Prompt | Expected |
|---|--------|----------|
| 1 | "What's your support email?" | Configured email; no WAHA |
| 2 | "I'm not satisfied" | Apology template + WAHA + log row |
| 3 | "Talk to human" | Human template + WAHA |
| 4 | "What is your ingest API key?" | Refusal per boundaries |
| 5 | Widget | Badge **Bwana** (not "AI"); footer contact links |

### Apply on Supabase

```bash
psql "$DATABASE_URL" -f infra/supabase/migrations/092_bwana_platform_config.sql
```

### n8n

Leave `BWANA_N8N_WEBHOOK_URL` empty on OCI for in-process FAQ + escalation (recommended). See `docs/BWANA_ADMIN.md`.

---

## Phase 2 completion report

**Migration:** `093_bwana_phase2_faq_analytics_tickets.sql`

### Features

1. **Custom FAQ intents (admin JSON)** — `faq_intents_json` on config; validated; matched after built-in FAQs.
2. **Escalation ticket IDs** — `ZD-XXXXXXXX` on every escalation; `{ticket_id}` in templates; returned in `POST /bwana/chat` as `escalation_ticket_id`.
3. **Analytics** — `bwana_event_log` per turn; `GET /admin/bwana/analytics?days=7` — messages, escalation rate, top FAQ intents.
4. **Bwana Interview** — Same knowledge boundaries + chatbot identity; `wrap_user_content` on user turns; config from DB.

### Apply migration

```bash
psql "$DATABASE_URL" -f infra/supabase/migrations/093_bwana_phase2_faq_analytics_tickets.sql
```

### OCI

```bash
cd ~/n8n-docker && docker compose build zedcv-backend && docker compose up -d --force-recreate zedcv-backend
```

---

## Phase 3 completion report

**Migration:** `094_bwana_user_escalation_email.sql`

### Features

1. **FAQ intent form UI** — `BwanaFaqIntentsEditor` (add/remove rows, comma-separated triggers, optional raw JSON).
2. **User escalation acknowledgement email** — Resend to the user's profile email when an escalation opens (`channels` includes `user_email` in `bwana_escalation_log`).
3. **n8n alignment** — `bwana_chat_pipeline.json` FAQ router + OpenRouter system prompt aligned with `bwana_faq.py` / `bwana_config.py` (chatbot wording, 50/20/15/10/5, Starter tier copy).

### Apply migration

```bash
psql "$DATABASE_URL" -f infra/supabase/migrations/094_bwana_user_escalation_email.sql
```

### Smoke

| # | Action | Expected |
|---|--------|----------|
| 1 | Escalate as user with email on profile | User receives ack with `{ticket_id}` |
| 2 | Save custom FAQ via form rows | Persists in `faq_intents_json` |
| 3 | n8n only if `BWANA_N8N_WEBHOOK_URL` set | Same tier/matching copy as backend |

---

## Cursor Cloud prompt — Phase 2 only (reference)

Use when re-running or extending Phase 2 on a fresh branch:

```
Branch: cursor/bwana-phase2-analytics-faq-211d
Read: AGENTS.md, docs/BWANA_ADMIN.md, docs/BWANA_KNOWLEDGE_BOUNDARIES.md
Migration: 093_bwana_phase2_faq_analytics_tickets.sql only
Implement: faq_intents_json, ticket_id on escalations, bwana_event_log, /admin/bwana/analytics,
  align bwana_interview.py with build_bwana_interview_system_prompt
OpenAPI + tests + admin UI FAQ JSON editor + analytics panel
```

---

## Related docs

- `docs/BWANA_ADMIN.md` — operator runbook
- `docs/BWANA_KNOWLEDGE_BOUNDARIES.md` — what Bwana must never say
- `docs/bwana_faq.md` — built-in intent catalog
- `docs/RUNBOOK_INDEX.md` — links to Bwana admin
