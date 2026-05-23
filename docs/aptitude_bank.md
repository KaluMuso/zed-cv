# Aptitude question bank seeding

Bwana Interview aptitude packs (`numerical`, `verbal`, `abstract`) read from `public.aptitude_question_bank`. Questions are **not** generated per user — they are pre-seeded once via OpenRouter to control cost.

## Prerequisites

- Migration `060_interview_prep.sql` applied on Supabase
- `OPENROUTER_API_KEY` set in `apps/backend/.env` (or container env)
- Backend service role can insert into `aptitude_question_bank` (no RLS policies; service role bypasses RLS)

## Run the seed script

From the repo:

```bash
cd apps/backend && python scripts/seed_aptitude_bank.py
```

Production (OCI docker compose):

```bash
docker compose exec zedcv-backend python /app/scripts/seed_aptitude_bank.py
```

## Idempotency

The script skips any pack that already has **≥ 60** rows. Re-running is safe and will not duplicate banks.

## Verify counts

```sql
SELECT pack, count(*) FROM aptitude_question_bank GROUP BY pack;
```

Expect at least 60 per pack before users take timed tests.

## Model and quality filter

- Model: `google/gemini-2.0-flash-001` via OpenRouter
- Each batch requests JSON with `question_text`, four `options` (`label` + `value`), and `correct_value`
- Rows missing four options or empty text are dropped before insert

## User-facing packs

| Pack | Questions | Time limit |
|------|-----------|------------|
| numerical | 20 (random sample) | 20 minutes |
| verbal | 20 | 20 minutes |
| abstract | 20 | 15 minutes |

Percentiles use a placeholder benchmark (mean 50, stddev 15) until enough real `aptitude_scores` exist to recalibrate.
