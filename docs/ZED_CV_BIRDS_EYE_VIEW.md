# Zed CV — Complete Project Birds-Eye View

> Last updated: 2026-05-09
> Owner: Kaluba Prosper Musonda (convergeozambia@gmail.com)
> Repo: https://github.com/KaluMuso/zed-cv (private, branch: master)

---

## 1. What Is Zed CV?

Zed CV is an AI-powered job matching SaaS for Zambian professionals. Users upload their CV, the system parses it with AI, generates vector embeddings, and matches them against scraped/posted jobs using cosine similarity + skill overlap + location bonuses. Notifications go out via WhatsApp (primary) and email (secondary). Payment is via MTN MoMo / Airtel Money through DPO Pay (Lenco initiation live, webhook handler still missing).

**Live URLs:**
- Frontend: https://www.zedapply.com (Vercel, project: prj_Hp6wJwdSO7XVGjy5n1UGJBnrsAmr) - Domain recently changed from zedcv.vergeo.company
- Backend API: https://zedcv-api.vergeo.company (OCI free-tier Ubuntu, Docker)
- Supabase project: chnesgmcuxyhwhzomdov
- WhatsApp number: +260761359005 (WAHA)

### Production state as of 2026-05-09

The platform is **deployed but not yet in active use**. Verified via Supabase: **1 user, 1 CV uploaded, 12 jobs ingested, 0 matches ever generated**. Treat the "What Has Been Built" inventory in §8 as code-shipped, not as user-validated. The matching pipeline, payment flow, and WhatsApp bot have not been exercised against real-world load — surfaces flagged in §10 (DPO webhook hardening, Lenco webhook handler, `payment_method` CHECK constraint, tier-limit drift) will likely fail the moment a paying user appears.

---

## 2. Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Next.js 14 PWA │────▶│  FastAPI Backend  │────▶│  Supabase PG    │
│  (Vercel)       │     │  (OCI Docker)     │     │  + pgvector     │
└─────────────────┘     └──────┬───┬────────┘     └─────────────────┘
                               │   │
                    ┌──────────┘   └──────────┐
                    ▼                          ▼
             ┌─────────────┐          ┌──────────────┐
             │  WAHA        │          │  OpenRouter   │
             │  (WhatsApp)  │          │  (Gemini 2.0) │
             └─────────────┘          └──────────────┘
                                              │
                    ┌─────────────────────────┤
                    ▼                         ▼
             ┌─────────────┐          ┌──────────────┐
             │  Resend      │          │  Gemini       │
             │  (Email)     │          │  (Embeddings) │
             └─────────────┘          └──────────────┘

┌──────────────────┐
│  n8n             │──── Job scraping (every 12h) ──▶ POST /api/v1/jobs (auth-gated)
│  (OCI Docker)    │──── Daily digest workflow
└──────────────────┘
```

**Server Infrastructure (OCI):**
- Docker Compose at `~/n8n-docker/docker-compose.yml`
- Services: Caddy (reverse proxy), n8n, WAHA, zedcv-backend
- Caddy handles TLS + routing for zedcv-api.vergeo.company

---

## 3. Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Frontend | Next.js 14 App Router, React 18, Tailwind CSS 3.4, TypeScript | PWA with service worker, mobile tab bar |
| Backend | FastAPI 0.111, Python 3.11+, Pydantic 2.7 | Async, Docker container |
| Database | Supabase PostgreSQL 15 + pgvector | Vector embeddings (768d), RLS enabled |
| AI - LLM | OpenRouter → google/gemini-2.0-flash-001 | CV parsing, matching explanations, CV generation |
| AI - Embeddings | Google Gemini text-embedding-004 (768d) | CV + job embeddings (via Gemini API) |
| AI - OCR | Anthropic Claude (fallback for image CVs) | Via anthropic SDK |
| WhatsApp | WAHA (devlikeapro) | OTP, notifications, bot commands |
| Email | Resend | Welcome, match digest, job alerts, interview notifications |
| Payments | DPO Pay (live) + Lenco (initiation live, webhook handler missing) | MTN MoMo, Airtel Money, card |
| Scraping | n8n → Gemini AI → POST /api/v1/jobs | JobSearchZM.com, Go Zambia Jobs, every 12h |
| Hosting | Vercel (frontend), OCI free tier (backend/infra) | Docker Compose |

---

## 4. Database Schema (16 tables)

**Core tables:**
- `users` — phone, full_name, email, location, years_experience, subscription_tier, welcome_email_sent, email_notifications_enabled
- `otp_codes` — phone, code, expires_at, verified, attempts
- `cvs` — user_id, file_url, raw_text, parsed_data (JSONB), embedding (VECTOR 768), is_primary
- `jobs` — title, company, location, description, requirements, salary_min/max, apply_url, source, embedding, quality_score, closing_date
- `matches` — user_id, job_id, cv_id, score, vector_score, skill_score, bonus_score, matched_skills, missing_skills, status
- `subscriptions` — user_id, tier, status, matches_used, matches_limit, current_period_start/end

**Supporting tables:**
- `skills` (39 seed skills), `skill_aliases` (15 aliases), `user_skills`, `job_skills`
- `job_fingerprints` — dedup for scraper
- `payments` — amount, currency (ZMW), payment_method, provider, provider_ref, status
- `ai_cache` — cache_key, cache_type, result (JSONB), model, tokens_used
- `generated_documents` — doc_type (cv/cover_letter), content
- `whatsapp_sessions` — session_state FSM for WhatsApp bot
- `application_outcomes` — outcome tracking (applied/interview/offer/rejected)
- `cv_generations` — tracks CV generation usage per user

**Key RPC functions:**
- `match_jobs_for_user(user_id, limit, min_score)` — pgvector cosine similarity + skill overlap + bonus scoring
- `calculate_job_quality(job_id)` — auto-scores job listing quality (0-100)
- `deactivate_expired_jobs()` — cron-callable cleanup

---

## 5. API Endpoints (37 across 10 route files)

### Auth (2)
- `POST /api/v1/auth/otp/request` — Send OTP via WhatsApp
- `POST /api/v1/auth/otp/verify` — Verify OTP, return JWT tokens

### Profile (8)
- `GET /api/v1/profile` — Current user profile
- `PATCH /api/v1/profile` — Update profile fields (name, email, location, years_experience)
- `DELETE /api/v1/profile` — Delete account
- `GET /api/v1/profile/preferences` — Notification preferences
- `PATCH /api/v1/profile/preferences` — Update preferences (email/WhatsApp toggles)
- `GET /api/v1/profile/skills` — User's skill list
- `POST /api/v1/profile/skills` — Add skill
- `PATCH /api/v1/profile/skills/{name}` — Update skill (e.g., proficiency)
- `DELETE /api/v1/profile/skills/{name}` — Remove skill

### CV (3)
- `POST /api/v1/cv/upload` — Upload CV file (PDF/DOCX/JPG/PNG, max 5MB)
- `POST /api/v1/cv/analyze` — AI analysis of primary CV with scores
- `POST /api/v1/cv/generate` — Generate tailored CV for job title (tier-gated)

### Cover Letter (1)
- `POST /api/v1/cover-letter/generate` — Generate cover letter for a job (tier-gated; see §10 — currently blocked for super_standard)

### Interview Prep (1)
- `POST /api/v1/interview-prep/generate` — Generate interview prep kit (Super Standard tier)

### Jobs (3)
- `GET /api/v1/jobs` — List jobs (public, filterable)
- `GET /api/v1/jobs/{id}` — Get single job (public)
- `POST /api/v1/jobs` — Create job (auth required, rate-limited 10/min). Used by both n8n scraper and admin job creation. No dedicated `/ingest` route exists.

### Matches (2)
- `GET /api/v1/matches` — List user's matches (min_score, limit)
- `POST /api/v1/matches/trigger` — Trigger AI matching (background task)

### Subscription (2)
- `GET /api/v1/subscription` — Current subscription details
- `POST /api/v1/subscription/pay` — Initiate payment (DPO Pay or Lenco)

### Webhooks (2)
- `POST /api/v1/webhooks/whatsapp` — WAHA incoming messages
- `POST /api/v1/webhooks/dpo` — DPO Pay payment callbacks (no idempotency / signature check — see §10)

### Admin (12)
- `GET /api/v1/admin/stats` — Dashboard statistics
- `GET /api/v1/admin/users` — List users
- `PATCH /api/v1/admin/users/{user_id}/role` — Change user role
- `GET /api/v1/admin/jobs` — List jobs
- `POST /api/v1/admin/jobs` — Create job
- `PATCH /api/v1/admin/jobs/{job_id}` — Update job
- `DELETE /api/v1/admin/jobs/{job_id}` — Delete job
- `POST /api/v1/admin/jobs/bulk-deactivate` — Bulk deactivate jobs
- `GET /api/v1/admin/payments` — List payments
- `GET /api/v1/admin/matches` — List matches
- `GET /api/v1/admin/subscriptions` — List subscriptions
- `PATCH /api/v1/admin/subscriptions/{user_id}` — Update subscription

---

## 6. Frontend Pages (14)

| Route | Description |
|-------|-------------|
| `/` | Landing page with hero, features, stats, CTA |
| `/auth` | Phone + OTP login (redirects if authenticated) |
| `/jobs` | Job browse with filters, search, drawer detail view |
| `/matches` | Match dashboard with score rings, explanations |
| `/profile` | User profile with CV upload, CV Generator, CV Analysis tabs |
| `/pricing` | 4-tier pricing cards + comparison table + FAQ + payment modal |
| `/admin` | Admin dashboard (jobs CRUD, users, stats) |
| `/about` | About page |
| `/contact` | Contact page |
| `/blog` | Blog page |
| `/careers` | Careers page |
| `/terms` | Terms of service |
| `/privacy` | Privacy policy |
| `/cookies` | Cookie policy |

---

## 7. Subscription Tiers (Current Live State)

| Tier | Price | Matches/Month | Key Features |
|------|-------|---------------|--------------|
| Free | K0 | 10 | WhatsApp alerts, basic CV analysis, job browsing |
| Starter | K125/mo | 50 | AI tailored CVs, priority matching, score breakdowns |
| Professional | K250/mo | 125 | Cover letters, CV rewriting per role, priority support |
| Super Standard | K500/mo | Unlimited | Everything + interview prep notes |

**Note:** The Super Standard tier was added by Claude Code during deployment. The original plan had 3 tiers. The 4-tier model is better for revenue capture.

---

## 8. What Has Been Built (Completed)

### Core Platform
- [x] Phone + WhatsApp OTP authentication
- [x] CV upload (PDF, DOCX, JPG, PNG) with AI parsing
- [x] Vector embedding generation (Gemini text-embedding-004, 768d)
- [x] AI job matching (pgvector cosine similarity + skill overlap + bonuses)
- [x] Match scoring with explanations
- [x] Job browsing with filters (location, search, pagination)
- [x] 4-tier subscription system (free/starter/professional/super_standard)
- [x] DPO Pay payment integration (MTN MoMo, Airtel Money)
- [x] WhatsApp bot (OTP, match summaries, subscription info, help)
- [x] Email notifications via Resend (welcome, match digest, job alerts, interview)
- [x] Admin dashboard (stats, job CRUD, user management)
- [x] Superadmin auto-promotion
- [x] Job scraping via n8n (JobSearchZM.com, Go Zambia Jobs, 12-hour cycle)
- [x] Bulk job ingest endpoint with dedup via fingerprints
- [x] CV generation (tailored CV for specific job, tier-gated)
- [x] CV analysis (AI scoring with improvement recommendations)
- [x] Cover letter generation endpoint
- [x] Interview prep generation endpoint (Super Standard tier)
- [x] Profile management endpoints (PATCH /profile, /profile/preferences, /profile/skills CRUD)
- [x] Rate limiting via slowapi across auth, cv, cover_letter, interview_prep, jobs, matches, subscription routes

### Frontend/UX
- [x] Full redesign with custom design system (green + copper palette)
- [x] Responsive layout (mobile-first)
- [x] PWA manifest, service worker, app icons
- [x] Mobile bottom tab bar
- [x] Splash screen
- [x] Dark/light theme toggle
- [x] Scroll animations
- [x] Error boundaries
- [x] SEO meta tags
- [x] Static pages (about, contact, terms, privacy, cookies, blog, careers)

### Infrastructure
- [x] Docker Compose deployment (Caddy + n8n + WAHA + backend)
- [x] Vercel frontend deployment with custom domain
- [x] OCI free-tier server setup
- [x] n8n workflows (job scraping, daily digest, heartbeat)
- [x] GitHub Actions CI (`.github/workflows/ci.yml`) — backend tests, frontend build, backend Docker build on push to master
- [x] Vercel auto-deploy for frontend on push to master

---

## 9. Full Roadmap (Phase 2–5)

### Phase 2: Platform Hardening + Employer Side (Target: 4-6 weeks)

**Goal:** Make the platform robust enough for paying users and open the employer revenue stream.

**2A — Application Tracking (Professional+ feature)**
- [ ] Add `applications` table: user_id, match_id, job_id, status (applied/screening/interview/offer/rejected/no_response), applied_at, updated_at, notes
- [ ] `POST /api/v1/applications` — Mark a match as "applied"
- [ ] `GET /api/v1/applications` — List user's applications with status timeline
- [ ] `PATCH /api/v1/applications/{id}` — Update status (user self-reports or employer updates)
- [ ] Frontend: Application tracker page with Kanban-style columns or timeline view
- [ ] WhatsApp: "applied" command to mark application status
- [ ] Tier gate: Free/Starter can apply but can't track. Professional+ get full tracker with reminders.

**2B — Employer Portal**
- [ ] New `employers` table: id, company_name, email, phone, logo_url, verified, plan, created_at
- [ ] New `employer_users` table: employer_id, user_id, role (owner/admin/recruiter)
- [ ] Employer auth flow: Email + OTP (separate from job seeker phone auth)
- [ ] `POST /api/v1/employer/jobs` — Post a job (K500/listing or included in plan)
- [ ] `GET /api/v1/employer/candidates` — Browse matched CVs for their jobs (K2,500/20 CVs)
- [ ] `POST /api/v1/employer/accept` — "Accept for Interview" → triggers WhatsApp + email notification to candidate
- [ ] Employer dashboard: Posted jobs, candidate pipeline, billing
- [ ] Pricing tiers:
  - Pay-per-use: K500/job listing + K2,500/20 CV views
  - Agency plan: K15,000/mo — unlimited listings, 100 CV views/mo, priority placement
- [ ] Scraped jobs remain free (no employer account behind them) — these drive job seeker engagement
- [ ] Revenue tracking: employer_payments table, monthly invoicing

**2C — Admin Panel v2 (Role-Based)**
- [ ] Role system: superadmin, admin, moderator, employer_admin
- [ ] `roles` table + `user_roles` join table (users can have multiple roles)
- [ ] Role-based middleware: check role on every admin endpoint
- [ ] Admin dashboard sections:
  - **Overview:** Active users, jobs, matches, revenue (all roles)
  - **Job Management:** CRUD, approve/reject scraped jobs, feature jobs (admin+)
  - **User Management:** View profiles, adjust tiers, ban/suspend (admin+)
  - **Employer Management:** Approve employers, view billing, manage plans (admin+)
  - **Content Management:** Blog posts, FAQs, static pages (moderator+)
  - **System Config:** Tier limits, pricing, feature flags (superadmin only)
  - **Analytics:** Revenue, conversion funnels, scraper health (admin+)

**2D — Foundation Fixes**
- [ ] `PATCH /api/v1/profile` — Standalone profile update endpoint
- [ ] `PATCH /api/v1/profile/preferences` — Email notification toggle, WhatsApp preferences
- [ ] Email preferences toggle in frontend profile page
- [ ] Lenco payment integration (when API is ready)
- [ ] Fix stale CHECK constraints in database (update to include free/starter/professional/super_standard)
- [ ] Add Sentry error tracking (free tier)
- [ ] E2E tests for critical flows: signup → CV upload → match → apply
- [ ] OpenAPI spec update to match all current endpoints

**Phase 2 Revenue Impact:**
- Job seeker subscriptions: K125-K500/mo × users
- Employer job postings: K500/listing
- Employer CV access: K2,500/20 CVs
- Agency plans: K15,000/mo

---

### Phase 3: Value-Add Features (Target: 6-10 weeks after Phase 2)

**Goal:** Increase retention, justify tier pricing, and create new revenue streams.

**3A — Skills Gap Analysis**
- [ ] For each match, show: "You have 7/10 required skills. You're missing: Docker, Kubernetes, AWS"
- [ ] Per-skill recommendations: link to courses on Udemy, Coursera, YouTube
- [ ] Zambian local content creators: partner with local training providers for featured courses
- [ ] Revenue model: Affiliate commissions from Udemy/Coursera (5-15% per enrollment), featured listing fees from local creators (K500-K2,000/mo)
- [ ] `skills_gap` computed field on match results
- [ ] `/api/v1/skills/recommendations` endpoint — returns courses for missing skills
- [ ] Frontend: Skills gap visualization on match detail page
- [ ] Tier gate: Free sees the gap, Starter+ gets course recommendations

**3B — Interview Prep AI**
- [ ] `POST /api/v1/interview/prep` — Takes job_id + user's CV, generates:
  - 10 likely interview questions (behavioral + technical)
  - Model answers tailored to user's experience
  - Company research brief (scraped from web)
  - Salary negotiation tips for the role/location
- [ ] Chat-based practice mode: User answers questions, AI gives feedback
- [ ] WhatsApp integration: "prep me for [company]" command
- [ ] Output as downloadable PDF (interview prep kit)
- [ ] Tier gate: Super Standard only (key differentiator for K500 tier)

**3C — Salary Insights**
- [ ] `salary_data` table: role, location, min, median, max, sample_size, source, updated_at
- [ ] Data sources: scrape salary info from job listings, manual input from verified employers, user self-reports (anonymous)
- [ ] `GET /api/v1/salary?role=accountant&location=lusaka` — Returns salary range
- [ ] Frontend: Salary explorer page with charts (bar chart by role, map by location)
- [ ] Show salary context on job listings: "This salary is above/below average for this role in Lusaka"
- [ ] Tier gate: Free sees ranges, Starter+ sees detailed breakdowns

**3D — Referral Program**
- [ ] `referrals` table: referrer_id, referred_id, code, status (pending/completed/rewarded), created_at
- [ ] Each user gets a unique referral code/link
- [ ] Rewards: Refer 3 friends → 1 free month of Starter. Refer 10 → 1 free month of Professional.
- [ ] Referral dashboard in profile page: track invites, see rewards
- [ ] WhatsApp: Share referral link via WhatsApp command
- [ ] Anti-abuse: Referred user must upload a CV and trigger at least 1 match to count

**3E — Weekly Email Digest (Automated)**
- [ ] n8n scheduled task: Every Monday 8am CAT
- [ ] For each user with email_notifications_enabled=true:
  - Fetch top 5 new matches since last digest
  - Fetch any new jobs matching their skills
  - Include application status updates
- [ ] Use `send_match_digest_email()` from email service
- [ ] Unsubscribe link in every email
- [ ] Track open rates via Resend analytics

**Phase 3 Revenue Impact:**
- Course affiliate commissions: K50-500/enrollment
- Featured course listings: K500-2,000/mo per provider
- Interview prep as Super Standard differentiator → drives upgrades
- Referral program → organic growth, lower CAC

---

### Phase 4: Mobile + Analytics (Target: 3-4 months after Phase 3)

**Goal:** Capture the 80%+ of Zambian users who are mobile-first, and build data-driven decision making.

**4A — React Native Mobile App**
- [ ] Android first (>90% of Zambian smartphone users), iOS second
- [ ] Shares the same FastAPI backend — no new API needed if Phase 2-3 endpoints are solid
- [ ] Core screens: Login, Job browse, Matches, Profile, Application tracker
- [ ] Push notifications via Firebase Cloud Messaging (replace/supplement WhatsApp for in-app users)
- [ ] Offline mode: Cache last-viewed matches and job listings
- [ ] Camera integration: Take photo of printed CV → upload → parse
- [ ] App store: Google Play Store (K0 to publish with Google Play Console, ~$25 one-time)
- [ ] Distribution: Also as APK download from website (many Zambian users sideload)

**4B — Advanced Analytics Dashboard (Internal)**
- [ ] Admin analytics page with:
  - User funnel: Signup → CV upload → First match → First application → Paid conversion
  - Revenue metrics: MRR, churn rate, ARPU, LTV by tier
  - Scraper health: Jobs ingested/day, duplicates, source breakdown
  - Matching performance: Average match score, matches per user, time-to-first-match
  - Employer metrics: Jobs posted, CVs viewed, interviews initiated
- [ ] Data export: CSV download for all metrics
- [ ] Alerts: n8n workflow to notify admin when key metrics drop (e.g., scraper returns 0 jobs)

**4C — AI Model Optimization**
- [ ] Evaluate fine-tuning Gemini for Zambian CV parsing (local terminology, qualification names)
- [ ] Multi-language CV support: Bemba, Nyanja, Tonga (at minimum detect and handle gracefully)
- [ ] Better skill extraction: Industry-specific skill taxonomies (mining, agriculture, banking)
- [ ] Matching algorithm v2: Incorporate application outcomes as training signal (did matched users actually get hired?)
- [ ] A/B test matching weights: Is 60/30/10 (vector/skill/bonus) optimal?

**Phase 4 Revenue Impact:**
- Mobile app → larger addressable market (most Zambians won't use a desktop site daily)
- Push notifications → higher engagement → more matches consumed → more upgrades
- Better AI → better matches → higher satisfaction → lower churn

---

### Phase 5: Scale + Global (Target: 6-12 months after Phase 4)

**Goal:** Expand beyond Zambia, build network effects, become the LinkedIn for emerging markets.

**5A — Multi-Country Expansion**
- [ ] Country-specific job sources: Zimbabwe (JobZimbabwe), Malawi, Tanzania, Kenya
- [ ] Multi-currency support: ZMW, USD, ZWD, MWK, TZS, KES
- [ ] Localized pricing: Different tier prices per country (PPP-adjusted)
- [ ] Country-specific skills and qualifications
- [ ] Regulatory compliance: Data residency considerations per country

**5B — Network Effects**
- [ ] Employer self-serve portal: No manual approval needed (with identity verification)
- [ ] Job seeker profiles visible to employers (opt-in): Employers search candidates, not just respond to applications
- [ ] Company reviews: Job seekers rate employers (Glassdoor-lite)
- [ ] Skill assessments: Short quizzes to verify claimed skills → badges on profile
- [ ] Community features: Forums or Q&A for job seekers by industry

**5C — API & Partnerships**
- [ ] Public API for job boards to pull listings from Zed CV
- [ ] Partnership with universities: Integrate with career services offices
- [ ] Government partnerships: Ministry of Labour job data feed
- [ ] HR software integrations: ATS (Greenhouse, Lever) two-way sync for employers

**5D — Revenue Diversification**
- [ ] Premium employer analytics: Which skills are most in-demand? Salary benchmarking reports.
- [ ] Recruitment Process Outsourcing (RPO): Full-service hiring for enterprise clients
- [ ] Training partnerships: Co-branded courses with local institutions
- [ ] White-label: License the matching engine to other job platforms

**Phase 5 Revenue Impact:**
- Multi-country = 10x addressable market
- Self-serve employer portal = scalable revenue without sales team
- API/partnerships = B2B revenue stream
- Network effects = defensible moat

---

### Success Metrics by Phase

| Phase | Key Metric | Target |
|-------|-----------|--------|
| 2 | First paying employer | 1 employer posting within 30 days of launch |
| 2 | Job seeker paid conversions | 5% of active users on Starter+ |
| 3 | Retention (30-day) | 40%+ monthly active users returning |
| 3 | Referral viral coefficient | 0.3+ (each user brings 0.3 new users) |
| 4 | Mobile app installs | 1,000 in first month |
| 4 | Match-to-application rate | 20%+ of matches result in applications |
| 5 | Multi-country users | Active users in 3+ countries |
| 5 | Employer self-serve rate | 80%+ of employer signups without manual intervention |

---

## 10. Known Issues & Technical Debt

### Critical
1. **Database CHECK constraints are stale** — `001_initial_schema.sql` still has `CHECK (tier IN ('mwana', 'mwezi', 'bwino'))` on both `users.subscription_tier` and `subscriptions.tier`. Claude Code handled this via migration 006, but the initial schema file is misleading for anyone reading it.
2. **DPO webhook is unprotected** — `POST /api/v1/webhooks/dpo` has no idempotency key, no replay protection, and no signature verification. A duplicate or forged callback can grant arbitrary tier upgrades or double-credit a payment.
3. **Lenco initiation is live but the webhook handler does not exist** — `services/lenco.py` and `subscription.py:74-118` initiate Lenco payments, but there is no `POST /api/v1/webhooks/lenco` route. Any Lenco payment that completes evaporates: subscription is never activated, no payment row is reconciled.
4. **`payments.payment_method` CHECK constraint rejects real values** — The constraint does not include `'card'` or any `'lenco_*'` value, so any DPO card payment or Lenco payment fails to insert into `payments`. Payment records silently drop.
5. **RLS bypassed** — Backend uses `supabase_service_key` (service role), so RLS policies are bypassed. This is standard for server-side access but means RLS is only effective for direct Supabase client access (which we don't currently use from frontend).
6. **Payment webhook maps tiers by price** — If prices change, the DPO webhook tier mapping breaks.

### High
7. **Tier-limit constants diverge across the codebase** — `subscription.py`, `admin.py`, the Pydantic schemas, and the frontend all hardcode their own copies of per-tier match limits and feature gates. Changing a limit in one place silently de-syncs the others.
8. **Cover letter generation blocked for `super_standard` tier** — The tier-gate check in `cover_letter.py` excludes super_standard, so the highest-paying tier cannot use a feature the pricing table promises.
9. **`POST /api/v1/jobs` is open to any authenticated user** — Any logged-in user can create job listings. Used by n8n (acceptable) and admin (acceptable) but no role check, so any free-tier user can pollute the job board.
10. **OTP `attempts` counter is never incremented and `/auth/otp/verify` has no rate limit** — The `otp_codes.attempts` column exists but is never written, and `/verify` has no slowapi decorator. OTPs are brute-forceable in practice.
11. **LLM CV-parser output is stored without Pydantic validation** — `cv_parser.py` writes the raw model JSON straight into `cvs.parsed_data`. A malformed or hallucinated structure can break every downstream consumer (matching, analysis, generation).
12. **`ai_cache` not consulted by `cv_parser` or `embedding` services** — The cache table exists and is wired for some calls, but CV parsing and embedding generation always hit the model. Direct cost burn on every retry/re-upload.
13. **CV filename used as storage path without sanitization** — User-controlled filename flows into Supabase Storage path on upload. Path traversal / collision / overwrite risk against other users' files.

### Moderate
14. **~~Embedding model mismatch risk~~** — RESOLVED by migration 007 (2026-05-09): source migrations now declare `vector(768)` matching the live Gemini `text-embedding-004` model and prod schema. Originally: source migrations declared `vector(1536)` (OpenAI sizing) while prod and the backend's `embedding_dimensions` config had been switched to 768 (Gemini), so a fresh-clone deploy would have silently failed at INSERT. Changing embedding models again would still require re-embedding all CVs and jobs.
15. **No database migrations strategy** — Migrations are ad-hoc SQL files run manually. No Alembic or migration runner.
16. **Test coverage gaps** — Tests exist but mock heavily. No integration tests against real Supabase.
17. **WhatsApp session state** — FSM is basic, no timeout handling for stale sessions.

### Low
18. **AI cache has no eviction** — `ai_cache` table grows unbounded. Need TTL cleanup.
19. **No error tracking** — No Sentry or equivalent. Errors only visible in Docker logs.
20. **No API versioning strategy** — All routes under `/api/v1` but no plan for v2.
21. **PWA needs audit** — Service worker and manifest deployed but functionality not verified.

---

## 11. Environment Variables (Backend)

```env
# Core
SUPABASE_URL=https://chnesgmcuxyhwhzomdov.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_KEY=...
JWT_SECRET=...

# AI
OPENAI_API_KEY=...                    # Embeddings
OPENROUTER_API_KEY=...                # LLM (Gemini via OpenRouter)
ANTHROPIC_API_KEY=...                 # OCR fallback

# WhatsApp
WAHA_API_URL=http://waha:3000        # Internal Docker network
WAHA_API_KEY=...

# Payments
DPO_PAY_COMPANY_TOKEN=...
DPO_PAY_SERVICE_TYPE=...

# Email
RESEND_API_KEY=...
RESEND_FROM_EMAIL=Zed CV <notifications@zedcv.vergeo.company>
EMAIL_ENABLED=true

# Scraping
SCRAPER_API_KEY=...                  # Shared with ingest endpoint auth
```

---

## 12. Infrastructure Considerations

### Current Setup (OCI Free Tier)
- **Pros:** Free, sufficient for current scale, Docker Compose simplicity
- **Cons:** Limited CPU/RAM (1 OCPU, 1GB RAM), no auto-scaling, manual deployment

### Potential Upgrades (Evaluate at Scale)
- **RunPod** — For AI inference only (pay-per-use). Worth it when embedding/parsing volume exceeds OCI capacity. Not needed yet.
- **fly.io** — Edge deployment for backend. Benefit: lower latency for Zambian users. Cost: ~$5-10/mo. Consider after 1000+ users.
- **Supabase pgvector** — Current RAG setup is fine. pgvector handles up to ~1M vectors before performance degrades. Alternative: Pinecone or Qdrant when you hit 500K+ vectors.
- **Vercel Edge Functions** — Could replace some backend routes for lower latency. Not worth the migration effort now.

### Recommendation
Stay on OCI + Supabase until you hit 5,000+ active users. At that point, consider:
1. Separating AI inference to RunPod (serverless, pay-per-use)
2. Moving backend to fly.io (auto-scaling, closer to users)
3. Adding Redis for session/cache layer
4. Adding Sentry for error tracking

---

## 13. File Structure Reference

```
zed-cv/
├── apps/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── api/v1/          # 10 route files, 37 endpoints
│   │   │   ├── core/            # config.py, deps.py, rate_limit.py
│   │   │   ├── schemas/         # 6 Pydantic model files
│   │   │   └── services/        # 10 service modules
│   │   ├── tests/               # 8 test files
│   │   ├── main.py              # FastAPI app entry
│   │   ├── requirements.txt
│   │   └── .env.example
│   └── frontend/
│       ├── src/
│       │   ├── app/             # 14 pages (Next.js App Router)
│       │   ├── components/      # 47 .tsx files (across feature/marketing/ui/shared/providers subfolders)
│       │   ├── hooks/           # 3 custom hooks
│       │   └── lib/             # api.ts, auth.tsx
│       ├── public/              # PWA icons, manifest, sw.js
│       ├── package.json
│       └── next.config.js
├── infra/
│   ├── supabase/migrations/     # SQL migration files
│   ├── waha/docker-compose.yml  # Docker setup
│   └── n8n/                     # Workflow JSON files
├── packages/
│   ├── types/                   # Shared TypeScript types
│   └── utils/                   # Skill aliases
├── docs/
│   ├── openapi.yaml             # API spec (covers /profile, /profile/preferences, /profile/skills)
│   ├── CODE_REVIEW_PROMPT.md    # Codebase audit prompt for Claude/Cursor
│   ├── ZED_CV_BIRDS_EYE_VIEW.md # This document
│   └── references/
│       ├── Failure_Modes.pdf
│       └── Tips_to_reduce_LLM_coding_mistakes.pdf
├── CLAUDE.md                    # AI context file
├── AI_CONTEXT.md
├── CURSOR_HANDOFF.md
├── DEPLOY.md
└── README.md
```
