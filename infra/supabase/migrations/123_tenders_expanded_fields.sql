-- Migration: 123_tenders_expanded_fields.sql
-- Description: Expand tenders table with full posting metadata + authenticity verification.
-- Roadmap: docs/ROADMAP_2026_Q3.md §1
-- Companion to PR N1 (tender list/detail endpoints + business profile CRUD).

BEGIN;

-- ── 1. Add Reference / Classification Fields ──
ALTER TABLE public.tenders
  ADD COLUMN IF NOT EXISTS reference_number TEXT,            -- ZPPA reference / IFT number
  ADD COLUMN IF NOT EXISTS sector TEXT,                       -- Construction, ICT, Health, Agriculture, etc.
  ADD COLUMN IF NOT EXISTS tender_type TEXT,                  -- Open, Selective, Restricted, RFP, etc.
  ADD COLUMN IF NOT EXISTS funding_source TEXT;               -- GRZ, World Bank, AfDB, USAID, EU, etc.

-- ── 2. Add Content Fields ──
ALTER TABLE public.tenders
  ADD COLUMN IF NOT EXISTS scope_of_work TEXT,                -- Detailed scope (longer than `description`)
  ADD COLUMN IF NOT EXISTS eligibility_criteria TEXT,         -- Who can bid (NRC, PPP reg, etc.)
  ADD COLUMN IF NOT EXISTS evaluation_criteria TEXT;          -- How bids are scored

-- ── 3. Add Financial Fields ──
ALTER TABLE public.tenders
  ADD COLUMN IF NOT EXISTS bid_security_amount_ngwee BIGINT,  -- Bid bond required (in ngwee, 1 ZMW = 100)
  ADD COLUMN IF NOT EXISTS bid_security_currency TEXT DEFAULT 'ZMW',
  ADD COLUMN IF NOT EXISTS document_fee_ngwee BIGINT,         -- Cost to access tender docs
  ADD COLUMN IF NOT EXISTS estimated_value_min_ngwee BIGINT,  -- Contract value range — lower bound
  ADD COLUMN IF NOT EXISTS estimated_value_max_ngwee BIGINT;  -- Contract value range — upper bound

-- ── 4. Add Date Fields ──
ALTER TABLE public.tenders
  ADD COLUMN IF NOT EXISTS pre_bid_meeting_at TIMESTAMPTZ,    -- Pre-bid clarification meeting
  ADD COLUMN IF NOT EXISTS opening_date TIMESTAMPTZ;          -- Bid opening (after closing_date)

-- ── 5. Add Contact Fields ──
-- Procurement officer contact, for paid-tier users to follow up directly.
ALTER TABLE public.tenders
  ADD COLUMN IF NOT EXISTS contact_name TEXT,
  ADD COLUMN IF NOT EXISTS contact_email TEXT,
  ADD COLUMN IF NOT EXISTS contact_phone TEXT;

-- ── 6. Add Document Attachments ──
-- JSONB array of {name, url, size_bytes}. Public can see filenames; only
-- paid-tier users get the download URLs (enforced at API layer).
ALTER TABLE public.tenders
  ADD COLUMN IF NOT EXISTS document_urls JSONB DEFAULT '[]'::JSONB;

-- ── 7. Add Authenticity Verification Fields ──
-- Hybrid trust model:
--   • Free tier users (Tender Watcher) see only 'verified' tenders
--   • Paid tier users (Tender Pro+) also see 'unverified' WITH a clear
--     "Pending admin verification" badge in the frontend
--   • 'suspicious' and 'fraudulent' are hidden from everyone (admin only)
-- Default for new rows is 'unverified' so the admin team can backlog-verify.

DO $$ BEGIN
    CREATE TYPE tender_authenticity_status AS ENUM (
        'unverified',  -- Default, pending admin review
        'verified',    -- Admin confirmed legitimate, listed publicly
        'suspicious',  -- Admin flagged for further review, hidden from non-admins
        'fraudulent'   -- Confirmed scam tender, hidden from non-admins (kept for audit)
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

ALTER TABLE public.tenders
  ADD COLUMN IF NOT EXISTS authenticity_status tender_authenticity_status DEFAULT 'unverified' NOT NULL,
  ADD COLUMN IF NOT EXISTS authenticity_verified_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS authenticity_verified_by_user_id UUID REFERENCES public.users(id),
  ADD COLUMN IF NOT EXISTS authenticity_notes TEXT,
  ADD COLUMN IF NOT EXISTS procuring_entity_verified BOOLEAN DEFAULT FALSE;

-- ── 8. Indices for New Filterable Columns ──
CREATE INDEX IF NOT EXISTS idx_tenders_authenticity_status ON public.tenders(authenticity_status);
CREATE INDEX IF NOT EXISTS idx_tenders_sector ON public.tenders(sector) WHERE sector IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tenders_closing_date ON public.tenders(closing_date) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_tenders_tender_type ON public.tenders(tender_type) WHERE tender_type IS NOT NULL;

-- ── 9. Update Public RLS Policy ──
-- Migration 122 allowed any is_active=true tender to be readable. PR N1
-- tightens this so the public can't read suspicious/fraudulent rows.
-- API layer enforces the free-vs-paid hybrid model on top of this.
DROP POLICY IF EXISTS tenders_select_public ON public.tenders;
CREATE POLICY tenders_select_public ON public.tenders
    FOR SELECT TO public
    USING (
        is_active = true
        AND authenticity_status NOT IN ('suspicious', 'fraudulent')
    );

-- Admins can read everything (used by /admin/tenders queue).
DROP POLICY IF EXISTS tenders_select_admin ON public.tenders;
CREATE POLICY tenders_select_admin ON public.tenders
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.users u
            WHERE u.id = auth.uid()
              AND u.role IN ('admin', 'superadmin')
        )
    );


COMMIT;
