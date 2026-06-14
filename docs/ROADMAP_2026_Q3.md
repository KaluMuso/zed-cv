# ZedApply Q3 2026 Roadmap

**Status:** Draft — 2026-06-14 — pending product sign-off from Kaluba.

This document captures the five workstreams scoped during the 2026-06-14 planning session. Each section has rationale, schema, endpoints, frontend touch-points, and a phased ship plan. Treat this as the source of truth for PRs N1..N5 (referenced from individual PR descriptions).

---

## 1. Tenders feature completion (PR N1..N4)

### Current state (master @ 2026-06-14)

Already in place:
- `public.tenders` and `public.tender_embeddings` tables (migrations from PR #329)
- `public.business_profiles` table (referenced by `/tenders/matches`)
- `POST /api/v1/tenders/ingest` — bulk insert with dedup by (procuring_entity, title, closing_date) + embedding generation
- `GET /api/v1/tenders/matches` — semantic search via `match_tenders` RPC
- Frontend dashboard widget (per PR #329 commit messages)
- `TenderCreate` schema with eight fields

What's missing for the product to feel complete:
- Public list + detail endpoints (currently only matches are reachable)
- Business profile CRUD (no UI for users to fill in `company_name`, `industry_tags`, etc.)
- Tender-specific authenticity fields (procuring entity verification, doc attachments)
- Tender-specific pricing tier (B2B pricing — businesses pay more than job seekers)
- Tender-specific boosters (urgent bid prep, doc review, expert consultation)
- Scraper sources (ZPPA, GRZ portals)
- WhatsApp digest for new matching tenders

### Schema expansion

Add to `public.tenders`:

```sql
ALTER TABLE public.tenders
  ADD COLUMN reference_number TEXT,            -- ZPPA reference / IFT number
  ADD COLUMN sector TEXT,                       -- Construction, ICT, Health, etc.
  ADD COLUMN scope_of_work TEXT,                -- Detailed scope (separate from short description)
  ADD COLUMN eligibility_criteria TEXT,         -- Who can bid
  ADD COLUMN evaluation_criteria TEXT,          -- How bids are scored
  ADD COLUMN bid_security_amount_ngwee BIGINT,  -- Bond / bid security required (in ngwee)
  ADD COLUMN bid_security_currency TEXT DEFAULT 'ZMW',
  ADD COLUMN document_fee_ngwee BIGINT,         -- Cost to access tender docs
  ADD COLUMN estimated_value_min_ngwee BIGINT,  -- Estimated contract value range (min)
  ADD COLUMN estimated_value_max_ngwee BIGINT,  -- Estimated contract value range (max)
  ADD COLUMN pre_bid_meeting_at TIMESTAMPTZ,    -- Pre-bid clarification meeting
  ADD COLUMN opening_date TIMESTAMPTZ,          -- Bid opening (after closing_date)
  ADD COLUMN contact_name TEXT,                 -- Procurement officer name
  ADD COLUMN contact_email TEXT,                -- Procurement officer email
  ADD COLUMN contact_phone TEXT,                -- Procurement officer phone
  ADD COLUMN document_urls JSONB,               -- Array of {name, url, size_bytes}
  ADD COLUMN tender_type TEXT,                  -- Open, Selective, Restricted, etc.
  ADD COLUMN funding_source TEXT,               -- GRZ, World Bank, AfDB, etc.

  -- Authenticity verification (the explicit ask from Kaluba)
  ADD COLUMN authenticity_status TEXT DEFAULT 'unverified',  -- unverified, verified, suspicious, fraudulent
  ADD COLUMN authenticity_verified_at TIMESTAMPTZ,
  ADD COLUMN authenticity_verified_by_user_id UUID REFERENCES public.users(id),
  ADD COLUMN authenticity_notes TEXT,                         -- Admin notes on verification
  ADD COLUMN procuring_entity_verified BOOLEAN DEFAULT FALSE; -- PPP registration confirmed?

CREATE INDEX idx_tenders_authenticity_status ON public.tenders(authenticity_status);
CREATE INDEX idx_tenders_closing_date ON public.tenders(closing_date);
CREATE INDEX idx_tenders_sector ON public.tenders(sector);
```

### New endpoints (PR N1)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/api/v1/tenders` | Public | Paginated list, filterable by `sector`, `province`, `closing_date_range`, `authenticity_status` |
| `GET` | `/api/v1/tenders/{id}` | Public | Detail view of a single tender (only returns `authenticity_status='verified'` for non-admins) |
| `GET` | `/api/v1/business-profile` | User | Read own business profile |
| `PUT` | `/api/v1/business-profile` | User | Create or update own business profile |
| `POST` | `/api/v1/admin/tenders/{id}/verify` | Admin | Mark authenticity_status = verified |
| `POST` | `/api/v1/admin/tenders/{id}/flag` | Admin | Mark authenticity_status = suspicious/fraudulent |

### Pricing — separate tier from job-seeker plans (PR N2)

Job pricing is consumer-priced (K125/month Starter). Tender users are businesses competing for contracts — they have budget. Different SKUs:

| Tier | Monthly (ZMW) | Annual (ZMW) | Matches/month | Notes |
|---|---:|---:|---|---|
| **Tender Watcher** (free) | 0 | — | 3 | Read public tender list, see 3 matched per month, no docs |
| **Tender Pro** | 500 | 5,000 (30% off) | Unlimited | Full match feed, document downloads, WhatsApp digest |
| **Tender Plus** | 1,500 | 15,000 | Unlimited + alerts | Custom keyword alerts, daily WhatsApp digest, save lists |
| **Tender Elite** | 5,000 | 50,000 | Unlimited + concierge | Phone support, custom matches, early access to new sources |

Rationale: K500/mo = US$20/mo, which is in line with what procurement intel services charge globally (Tenders.com.zm charges K600 in the same range). The K1,500 and K5,000 tiers monetise businesses who would otherwise pay a full-time admin to monitor tenders.

Schema change:

```sql
INSERT INTO public.tier_config (tier, display_name, price_ngwee, matches_limit, sort_order, billing_period_days, product)
VALUES
  ('tender_watcher', 'Tender Watcher', 0, 3, 10, 30, 'tenders'),
  ('tender_pro', 'Tender Pro', 50000, 99999, 11, 30, 'tenders'),
  ('tender_pro', 'Tender Pro (Annual)', 500000, 99999, 11, 365, 'tenders'),
  ('tender_plus', 'Tender Plus', 150000, 99999, 12, 30, 'tenders'),
  ('tender_plus', 'Tender Plus (Annual)', 1500000, 99999, 12, 365, 'tenders'),
  ('tender_elite', 'Tender Elite', 500000, 99999, 13, 30, 'tenders'),
  ('tender_elite', 'Tender Elite (Annual)', 5000000, 99999, 13, 365, 'tenders');

-- New `product` column on tier_config disambiguates "jobs" vs "tenders" SKUs
-- so a user can hold both subscriptions independently.
ALTER TABLE public.tier_config ADD COLUMN product TEXT DEFAULT 'jobs';
UPDATE public.tier_config SET product = 'jobs' WHERE product IS NULL;
ALTER TABLE public.tier_config ALTER COLUMN product SET NOT NULL;
```

### Tender-specific boosters (PR N3)

Job boosters (re-match, CV tailor, cover letter) don't translate. Tender users need different one-time products:

| Booster | Price (ZMW) | What it does |
|---|---:|---|
| **Urgent bid prep** | 1,000 | LLM generates a starting bid proposal from the tender requirements + user's company profile (~2-3 page doc) |
| **Doc review** | 750 | Upload a draft bid, get LLM critique highlighting weak areas, missing requirements, scoring vulnerabilities |
| **Expert consultation** | 5,000 | 30-min Zoom with a Zambian procurement consultant (humans, scheduled via Calendly) |
| **Bid security calculator** | 250 | Computes likely bid security amount based on similar past tenders |
| **Competitor intel** | 500 | Pulls list of likely bidders for this tender from historical award data |

Each maps to a `booster_sku` row with `product='tenders'`. Backend uses existing booster purchase rails. The Expert Consultation booster differs in that it returns a Calendly link instead of an immediate AI result.

### Frontend pages (PR N4)

- `/tenders` — public paginated list with filters (sector, province, closing-soon, value range, authenticity-verified-only). Mirrors `/jobs` layout for consistency.
- `/tenders/[id]` — detail page with: scope, requirements, eligibility, evaluation criteria, bid security, documents (link if Tender Pro+), procurement officer contact (link if Tender Pro+), authenticity badge.
- `/tenders/match` — authenticated user dashboard showing matched tenders. Free tier sees 3 with cards blurred ("Upgrade to see all matches"). Pro+ sees all.
- `/business-profile` — setup wizard for `business_profiles`: company name, registration number, sector, industry tags, operating provinces, company bio, logo upload (see §2).
- `/pricing/tenders` — separate pricing page for tender SKUs (NOT mixed with /pricing for jobs).
- Admin: `/admin/tenders` (similar to `/admin/jobs/review`) for the authenticity verification queue.

### Scraper sources (PR N5)

n8n workflow `ZedApply - Tender Scraper Every 24h`:

1. **ZPPA** (zppa.org.zm) — the central Zambia Public Procurement Authority feed. Highest authority. Worth investing in a robust parser.
2. **Government Gazette** — published weekly. Some tenders published here only.
3. **PMRC / Ministry websites** — Ministry of Finance, MoH, MoE all publish their own RFPs.
4. **Donor portals** — UN Global Marketplace (UNGM), World Bank, AfDB. Filter for "Zambia" geographic tag.
5. **Print → scan ingest** — accept PDFs forwarded via WhatsApp (Slice F extension to tenders).

Each source has its own n8n workflow. All POST to `/api/v1/tenders/ingest` with the same JSON contract.

### Authenticity verification flow (PR N6)

For every ingested tender, set `authenticity_status='unverified'`. Public `GET /tenders` returns only `verified` rows by default; admin override flag returns unverified too. Admin queue at `/admin/tenders` shows unverified rows; admin clicks one of:

- **Verify** — `authenticity_status='verified'`. Tender visible to all.
- **Flag suspicious** — `authenticity_status='suspicious'`. Stays hidden from public; admin notes saved.
- **Mark fraudulent** — `authenticity_status='fraudulent'`. Permanently hidden. Used for known scam tenders.

PPP (Public Procurement Practitioner) check: the admin verifies that the procuring_entity has a current ZPPA registration. This is a manual step today; could automate with a ZPPA registration scraper later. Stored in `procuring_entity_verified`.

---

## 2. Profile and company images (PR S)

### User profile photo

- New column `users.profile_image_url TEXT`
- New endpoint `POST /api/v1/profile/avatar` — multipart upload, stored in Supabase Storage bucket `user-avatars` (public read, authenticated write, RLS so only owner can replace).
- Frontend: `/profile` page gains an avatar widget with crop (use `react-easy-crop` library). Square aspect ratio, 512x512 max after crop.
- "Remove photo" button sets `profile_image_url=NULL`.

### Company logo

- New column `users.business_profile_id` references `business_profiles.id`.
- `business_profiles.logo_url TEXT`
- Same upload flow as user avatar but separate bucket `company-logos`.
- Used in tender bid proposals, on `/business-profile` page, on admin tender list.

### CV integration

- `cv_generations.include_avatar BOOLEAN DEFAULT FALSE` — opt-in per CV.
- When `True`, the PDF renderer (see §3) places a 80x80 circular crop in the top-right of the header. Square crop already enforced at upload.
- Toggle: "Include my photo on this CV" on `/profile/cv-builder` and `/matches/{id}/tailor-cv` modal.
- Default OFF — Zambian CV conventions don't require photos and some employers actively prefer no photo for unbiased review.

### Storage cost

Supabase Storage is $0.021/GB/mo. At 512KB avg per avatar × 10K users = ~5GB → $0.10/mo. Negligible.

---

## 3. Multiple CV templates (PR T)

Today: one template (free-form markdown). Users get the same look regardless of role / industry.

### Five proposed templates

| Template | Audience | Layout |
|---|---|---|
| **Classic** | Traditional roles (government, banking, NGO) | 1-column, serif typography, "References available on request" line. Today's default. |
| **Modern** | Tech, marketing, startup roles | 2-column. Left rail = contact + skills + languages. Right = experience + education. Sans-serif. Subtle color accent. |
| **Compact** | Senior candidates with 10+ years experience | Dense single-column. Smaller font. Pushes 1.5 pages of content into 1 page. |
| **Executive** | C-suite, board roles | Spacious 1-column. Larger heading typography. Highlights "Career Summary" prominently. Conservative color. |
| **Creative** | Marketing, design, media | Bold typography. Accent color block on header. Photo slot. Skills visualised as bars. |

### Schema

```sql
ALTER TABLE public.cv_generations
  ADD COLUMN template TEXT DEFAULT 'classic';

-- Constraint: template must be one of the 5 known values
ALTER TABLE public.cv_generations
  ADD CONSTRAINT cv_template_check
  CHECK (template IN ('classic', 'modern', 'compact', 'executive', 'creative'));
```

### Implementation

The LLM still emits the same `CVSections` structure. The template only changes the PDF rendering. New `cv_renderer.py` service with five render functions, one per template. PDF generated via `reportlab` (already a backend dep for boosters) or `weasyprint` (HTML→PDF, easier to style).

Recommend `weasyprint` — write 5 HTML+CSS templates in `apps/backend/app/services/cv_templates/`, render via Jinja2, convert via weasyprint. Lower maintenance vs reportlab layout code.

### Frontend

- CV builder page gets a template picker (5 thumbnail previews).
- Default = Classic.
- Selected template persists per CV generation row.
- Download PDF button respects the selected template.

---

## 4. Student / internship onboarding (PR U)

### Why

Students are a HUGE untapped audience in Zambia. They:
- Have no work experience (current CV builder assumes you do)
- Look for internships (current matcher tuned for full-time)
- Have lower spending power but high WhatsApp engagement
- Convert into full users after graduation (a 3-year LTV)

### Schema

```sql
ALTER TABLE public.users
  ADD COLUMN is_student BOOLEAN DEFAULT FALSE,
  ADD COLUMN expected_graduation_date DATE,
  ADD COLUMN study_field TEXT,                  -- "Computer Science", "Accounting", etc.
  ADD COLUMN study_institution TEXT,            -- "University of Zambia", etc.
  ADD COLUMN year_of_study INT;                 -- 1, 2, 3, 4, postgrad
```

### Signup flow change

Add a step after OTP verify: "Are you currently a student?" → if Yes, show student-specific fields. If No, skip.

### Internship-focused matching

- New `employment_type` filter pre-checked for student accounts: `internship,part_time,temporary,full_time`.
- Matching algorithm gives a small bonus (5-10 points) to internship-tagged jobs when `is_student=true`.
- Free-tier students get 14 matches/month instead of 3 (subsidise their experience).

### Student-specific CV template

The Modern template (§3) becomes the default for student accounts but with these tweaks:
- Education section FIRST, not after experience
- "Projects" section enabled by default
- "Extracurricular Activities" section enabled
- "Skills" section emphasises coursework
- "Work Experience" optional, can be empty

### Cover letter prompt enhancement

Student-context cover letter prompt:
- Lead with academic interest in the field
- Reference relevant coursework and projects
- Cite extracurriculars / leadership (Student Union, sports, debate)
- Acknowledge lack of professional experience but pitch transferable skills

### Pricing

Students get a 50% discount on Starter (K62.50/mo) and Professional (K125/mo). Verified by `expected_graduation_date` not yet passed. No discount on Super Standard.

---

## 5. CV / cover letter quality round 2 (PR V)

### Diagnosis

PR #324 improved prompts (tone, anti-clichés). User reports output still feels generic. Next dials to turn:

### 5.1 Premium model for tailored generation

Add new Settings field:

```python
class Settings(BaseSettings):
    llm_model: str = "google/gemini-2.0-flash-001"             # current default
    llm_model_premium: str = "google/gemini-2.5-pro"            # NEW
```

Use `llm_model_premium` for:
- `generate_tailored_cv_for_match` (the per-match tailored CV)
- `generate_cover_letter` (cover letter generation)

Keep `llm_model` (Flash) for:
- `analyze_cv` (scoring)
- `generate_cv` (initial CV from raw resume — generic, not match-specific)
- Job ingest enrichment

Cost: Gemini 2.5 Pro is ~3x more expensive than Flash 2.0 but for premium tailored CV it's worth it. Estimated +$0.10 per tailored CV.

### 5.2 Tone selector

Frontend adds tone dropdown on `/matches/{id}/tailor-cv`: `Professional` (default), `Confident`, `Warm`. Prompt picks per-tone instructions:

```python
TONE_GUIDANCE = {
    "professional": "Formal Zambian business prose. Conservative tone.",
    "confident": "Assertive language. Lead with measurable wins. Strong verbs.",
    "warm": "Approachable, conversational tone while maintaining professionalism.",
}
```

### 5.3 Company research step

Before generation, do a `web_fetch` on the company's main website (if `apply_url` or `source_url` has a parseable company domain). Extract 2-3 key facts:
- Recent product launches
- Mission statement / company values
- Notable clients or partnerships

Inject into the cover letter prompt: "Demonstrate knowledge of the company by referencing the following facts: [...]"

Skip if `apply_url` is an aggregator (LinkedIn, indeed, etc.) — can't reliably resolve the company website.

### 5.4 Few-shot examples in prompt

Add 2 hand-curated "ideal" examples to `MATCH_TAILOR_SYSTEM_PROMPT`. Each example shows: input (master CV + job description) → output (tailored CV). LLMs mimic patterns from few-shot examples better than abstract instructions.

### 5.5 LLM-as-judge review pass

After initial generation, send the output back to LLM with a critique prompt:

> "Rate this CV section-by-section on professionalism, specificity, and impact (1-5 each). Flag any section scoring below 4."

If any section flagged, regenerate that section specifically with the critique in the user prompt. Adds one extra LLM call per CV but yields measurable quality jumps.

### Cost

Combined: Premium model + LLM-as-judge ≈ 4x current cost. For tailored CV at est. $0.025 each → $0.10 per CV. Fine for paid tiers; gate behind Starter+.

---

## Sequencing

Suggested ship order over 3-4 weeks:

| Week | Workstream | PRs |
|---|---|---|
| **1** | Tenders MVP (list, detail, business profile CRUD, basic scraper) | PR N1, N4 (partial), N5 partial |
| **2** | Tenders monetisation + authenticity | PR N2 (pricing), N3 (boosters), N6 (verify flow) |
| **3** | Profile images + CV templates | PR S, PR T |
| **4** | Students + CV quality round 2 | PR U, PR V |

PR L (foreign filter widening), PR M (single-URL ingest), PR O (review queue dismiss/edit), PR R (this batch's tender code-review fixes) ship in parallel as small standalone PRs.

---

## Open product questions for Kaluba

1. **Tender pricing**: are the K500/K1,500/K5,000 tiers right for the Zambian market? I anchored against current Zambian competitors but you have better local intuition.
2. **Authenticity gating**: should `authenticity_status='unverified'` tenders be visible to anyone, or strictly hidden until admin verifies? My default says hide-until-verified. Trade-off: better trust but slower scaling.
3. **Student verification**: do we trust the self-reported `is_student` flag, or require something (.ac.zm email, student ID upload)? Self-report scales but is gameable for the 50% discount.
4. **CV templates**: are the 5 templates the right cut, or do you want fewer (3?) or more (8?)?
5. **Photo on CV default**: I'm proposing OFF by default per Zambian convention. Confirm or flip?

Ping me with answers and I'll start shipping PR N1 (tenders list/detail endpoints).
