# AI_CONTEXT.md — Zed CV Platform
# READ THIS FILE BEFORE MAKING ANY CHANGES TO THIS CODEBASE

## Project Overview
Zed CV is an AI-powered job matching SaaS for Zambia. It scrapes/ingests job listings, stores them in a vector database, matches them against user CVs using hybrid scoring, generates tailored CVs/cover letters, and delivers results via WhatsApp and a web dashboard.

## Architecture Constraints (NON-NEGOTIABLE)
- **Budget**: $100 total, ~$20-30/month operating cost
- **Developer**: Solo, AI-assisted (Claude Code, Gemini CLI, Cursor)
- **No fabrication**: Never invent APIs, endpoints, or libraries that don't exist
- **Contract-first**: All API endpoints defined in `docs/openapi.yaml` BEFORE implementation

## Tech Stack (DO NOT CHANGE WITHOUT UPDATING THIS FILE)
| Layer | Technology | Hosting | Tier |
|-------|-----------|---------|------|
| Database | Supabase (PostgreSQL + pgvector) | Supabase Cloud | Free |
| Backend | FastAPI (Python 3.11+) | Oracle Cloud Always Free | Free |
| Frontend | Next.js 14 (App Router, TypeScript) | Vercel | Free |
| Automation | n8n | Oracle Cloud Always Free | Free |
| WhatsApp | WAHA (self-hosted Docker) | Oracle Cloud Always Free | Free |
| Embeddings | OpenAI text-embedding-3-small | OpenAI API | ~$2/mo |
| LLM (parsing) | Claude Haiku / Gemini Flash | API | ~$5-15/mo |
| Payments | DPO Pay | DPO Pay API | Per-txn |
| Currency | ZMW (Zambian Kwacha) | — | — |

## Database (Supabase)
- Uses `pgvector` extension for embedding storage (1536 dimensions)
- Heartbeat cron via n8n every 6 hours to prevent free tier pausing
- All migrations in `infra/supabase/migrations/`
- RPC functions for matching queries (avoid N+1 from application layer)

## Matching Algorithm
```
final_score = (vector_similarity * 0.6) + (skill_overlap * 0.3) + (bonus_signals * 0.1)
```
- **vector_similarity** (60%): cosine similarity between CV embedding and job embedding
- **skill_overlap** (30%): |intersection(user_skills, job_skills)| / |job_skills|
- **bonus_signals** (10%): location match, experience range, recency, job quality score
- LLM explanation generated ONLY for matches with score > 70

## Job Quality Score (0-100)
- Company name present: +15
- Apply email/link present: +20
- Description > 200 chars: +10
- Salary range included: +10
- Verified source: +25
- Closing date present: +10
- Location specified: +10

## Skills Normalization
All skills are lowercased and mapped through aliases before comparison:
- "js" → "javascript", "ts" → "typescript"
- "ms word" → "microsoft office", "ppt" → "powerpoint"
- Aliases stored in `packages/utils/src/skills-aliases.ts`

## Pricing Tiers (ZMW)
| Tier | Price | Matches/Month | Features |
|------|-------|---------------|----------|
| Mwana (Free) | K0 | 5 | Basic matching, WhatsApp alerts |
| Mwezi | K79/mo (~$4) | 25 | CV generation, priority matching |
| Bwino | K199/mo (~$10) | Unlimited | Cover letters, career coaching |

## API Conventions
- All endpoints prefixed with `/api/v1/`
- Auth via Supabase JWT (passed as Bearer token)
- Request/response validated by Pydantic (backend) and Zod (frontend)
- Error responses follow RFC 7807 Problem Details format
- All monetary values in ZMW as integers (ngwee, like cents)

## File Structure
```
zed-cv/
├── AI_CONTEXT.md          ← YOU ARE HERE
├── apps/
│   ├── backend/           ← FastAPI application
│   │   ├── app/
│   │   │   ├── api/v1/    ← Route handlers
│   │   │   ├── core/      ← Config, security, dependencies
│   │   │   ├── models/    ← SQLAlchemy/Supabase models
│   │   │   ├── schemas/   ← Pydantic schemas
│   │   │   ├── services/  ← Business logic
│   │   │   └── workers/   ← Background tasks
│   │   ├── requirements.txt
│   │   └── main.py
│   └── frontend/          ← Next.js 14 application
│       ├── src/app/       ← App Router pages
│       ├── src/components/
│       ├── src/lib/       ← API client, utils
│       └── package.json
├── packages/
│   ├── types/             ← Shared TypeScript types (generated from OpenAPI)
│   └── utils/             ← Shared utilities (skills aliases, scoring)
├── infra/
│   ├── supabase/migrations/ ← SQL migration files
│   ├── n8n/               ← n8n workflow JSON exports
│   └── waha/              ← WAHA Docker config
└── docs/
    └── openapi.yaml       ← API contract (source of truth)
```

## Development Rules for AI Assistants
1. **Read this file first** before any code generation task
2. **Never modify the OpenAPI spec** without updating both backend schemas AND frontend types
3. **Never add a new dependency** without checking it exists and has >1000 weekly downloads
4. **Never store secrets in code** — use environment variables via `.env` (not committed)
5. **Never use `any` type** in TypeScript — use `unknown` and narrow
6. **All database changes** must be new migration files, never edit existing ones
7. **Test edge cases**: empty CV, job with no skills, expired jobs, network failures
8. **Zambia-specific**: Phone numbers start with +260, currency is ZMW, mobile money is primary payment
9. **Keep files under 300 lines** — split into modules if growing beyond that
10. **Commit messages**: `type(scope): description` — e.g., `feat(matching): add skill normalization`

## Environment Variables Required
```
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=        # For Claude Haiku
DPO_PAY_COMPANY_TOKEN=
DPO_PAY_SERVICE_TYPE=
WAHA_API_URL=http://localhost:3000
WAHA_API_KEY=
JWT_SECRET=
```

## Critical Warnings
- ⚠️ Supabase free tier pauses after 7 days inactivity — n8n heartbeat is MANDATORY
- ⚠️ Oracle Cloud free tier: ARM Ampere A1 (4 OCPU, 24GB RAM shared across all VMs)
- ⚠️ No Zambian job site has public APIs — ingestion starts manual, then semi-automated
- ⚠️ WAHA requires persistent Docker container — monitor for disconnections
- ⚠️ DPO Pay webhooks must be verified with signature check
- ⚠️ User CVs contain PII — encrypt at rest, never log full content
