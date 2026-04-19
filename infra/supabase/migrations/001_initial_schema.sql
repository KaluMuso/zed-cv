-- ============================================================
-- Zed CV — Initial Database Schema
-- Supabase (PostgreSQL 15 + pgvector)
-- ============================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ============================================================
-- USERS & AUTH
-- ============================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone VARCHAR(15) UNIQUE NOT NULL,  -- +260XXXXXXXXX
    full_name VARCHAR(255),
    email VARCHAR(255),
    location VARCHAR(100),
    years_experience INTEGER DEFAULT 0,
    subscription_tier VARCHAR(10) DEFAULT 'mwana' CHECK (subscription_tier IN ('mwana', 'mwezi', 'bwino')),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_phone ON users(phone);

-- OTP verification codes
CREATE TABLE otp_codes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone VARCHAR(15) NOT NULL,
    code VARCHAR(6) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    verified BOOLEAN DEFAULT false,
    attempts INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_otp_phone_active ON otp_codes(phone, verified, expires_at);

-- ============================================================
-- SKILLS
-- ============================================================

-- Canonical skills dictionary
CREATE TABLE skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,       -- normalized lowercase: "javascript"
    category VARCHAR(50),                     -- "programming", "soft_skill", "tool", etc.
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_skills_name ON skills(name);
CREATE INDEX idx_skills_category ON skills(category);

-- Aliases mapping: "js" → skills.id where name = "javascript"
CREATE TABLE skill_aliases (
    alias VARCHAR(100) PRIMARY KEY,          -- "js", "node", "ms word"
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE
);

-- User ↔ Skill junction
CREATE TABLE user_skills (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    proficiency VARCHAR(20) DEFAULT 'intermediate' CHECK (proficiency IN ('beginner', 'intermediate', 'advanced', 'expert')),
    source VARCHAR(20) DEFAULT 'cv_parse' CHECK (source IN ('cv_parse', 'manual', 'assessment')),
    PRIMARY KEY (user_id, skill_id)
);

-- ============================================================
-- CVs
-- ============================================================

CREATE TABLE cvs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_url TEXT NOT NULL,                   -- Supabase Storage path
    file_type VARCHAR(10) NOT NULL CHECK (file_type IN ('pdf', 'docx', 'jpg', 'png')),
    raw_text TEXT,                            -- extracted text
    parsed_data JSONB,                        -- structured parse result
    embedding VECTOR(1536),                   -- OpenAI text-embedding-3-small
    parsing_confidence REAL DEFAULT 0,
    is_primary BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_cvs_user ON cvs(user_id);
CREATE INDEX idx_cvs_primary ON cvs(user_id, is_primary) WHERE is_primary = true;

-- ============================================================
-- JOBS
-- ============================================================

CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    company VARCHAR(255),
    location VARCHAR(100),
    description TEXT NOT NULL,
    requirements TEXT[],
    salary_min INTEGER,                       -- in ZMW ngwee
    salary_max INTEGER,
    apply_url TEXT,
    apply_email VARCHAR(255),
    source VARCHAR(20) NOT NULL CHECK (source IN ('manual', 'scraper', 'ocr', 'partner')),
    source_url TEXT,                          -- original listing URL
    quality_score INTEGER DEFAULT 0 CHECK (quality_score >= 0 AND quality_score <= 100),
    embedding VECTOR(1536),
    closing_date DATE,
    is_active BOOLEAN DEFAULT true,
    posted_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_jobs_active ON jobs(is_active, posted_at DESC);
CREATE INDEX idx_jobs_location ON jobs(location) WHERE is_active = true;
CREATE INDEX idx_jobs_source ON jobs(source);
CREATE INDEX idx_jobs_closing ON jobs(closing_date) WHERE is_active = true;

-- HNSW index for vector similarity search (cosine distance)
CREATE INDEX idx_jobs_embedding ON jobs USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Job ↔ Skill junction
CREATE TABLE job_skills (
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    is_required BOOLEAN DEFAULT true,
    PRIMARY KEY (job_id, skill_id)
);

-- Deduplicate jobs from different sources
CREATE TABLE job_fingerprints (
    fingerprint VARCHAR(64) PRIMARY KEY,     -- SHA256 of normalized title+company+description
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- MATCHING
-- ============================================================

CREATE TABLE matches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    cv_id UUID REFERENCES cvs(id) ON DELETE SET NULL,
    score REAL NOT NULL CHECK (score >= 0 AND score <= 100),
    vector_score REAL DEFAULT 0,
    skill_score REAL DEFAULT 0,
    bonus_score REAL DEFAULT 0,
    matched_skills TEXT[],
    missing_skills TEXT[],
    explanation TEXT,                         -- LLM explanation (only score > 70)
    status VARCHAR(20) DEFAULT 'new' CHECK (status IN ('new', 'viewed', 'applied', 'saved', 'dismissed')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, job_id)
);

CREATE INDEX idx_matches_user_score ON matches(user_id, score DESC);
CREATE INDEX idx_matches_user_status ON matches(user_id, status);

-- ============================================================
-- SUBSCRIPTIONS & PAYMENTS
-- ============================================================

CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tier VARCHAR(10) NOT NULL DEFAULT 'mwana' CHECK (tier IN ('mwana', 'mwezi', 'bwino')),
    status VARCHAR(15) DEFAULT 'active' CHECK (status IN ('active', 'expired', 'cancelled', 'past_due')),
    current_period_start TIMESTAMPTZ DEFAULT NOW(),
    current_period_end TIMESTAMPTZ,
    matches_used INTEGER DEFAULT 0,
    matches_limit INTEGER DEFAULT 5,          -- mwana=5, mwezi=25, bwino=999999
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES subscriptions(id),
    amount INTEGER NOT NULL,                  -- in ZMW ngwee
    currency VARCHAR(3) DEFAULT 'ZMW',
    payment_method VARCHAR(20) NOT NULL CHECK (payment_method IN ('mtn_money', 'airtel_money')),
    provider VARCHAR(20) DEFAULT 'dpo_pay',
    provider_ref VARCHAR(255),                -- DPO transaction token
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed', 'refunded')),
    webhook_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_payments_user ON payments(user_id, created_at DESC);
CREATE INDEX idx_payments_ref ON payments(provider_ref);

-- ============================================================
-- AI CACHE (reduce redundant API calls)
-- ============================================================

CREATE TABLE ai_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cache_key VARCHAR(64) UNIQUE NOT NULL,    -- SHA256 of input
    cache_type VARCHAR(30) NOT NULL CHECK (cache_type IN ('embedding', 'cv_parse', 'cover_letter', 'explanation')),
    input_hash VARCHAR(64) NOT NULL,
    result JSONB NOT NULL,
    model VARCHAR(50),
    tokens_used INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ai_cache_key ON ai_cache(cache_key);
CREATE INDEX idx_ai_cache_expiry ON ai_cache(expires_at) WHERE expires_at IS NOT NULL;

-- ============================================================
-- GENERATED DOCUMENTS (CVs, Cover Letters)
-- ============================================================

CREATE TABLE generated_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id UUID REFERENCES jobs(id) ON DELETE SET NULL,
    doc_type VARCHAR(20) NOT NULL CHECK (doc_type IN ('cv', 'cover_letter')),
    content TEXT NOT NULL,
    file_url TEXT,                            -- Supabase Storage path
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_gen_docs_user ON generated_documents(user_id, doc_type);

-- ============================================================
-- WHATSAPP SESSIONS
-- ============================================================

CREATE TABLE whatsapp_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    phone VARCHAR(15) NOT NULL,
    session_state VARCHAR(30) DEFAULT 'idle' CHECK (session_state IN (
        'idle', 'awaiting_otp', 'onboarding', 'uploading_cv',
        'browsing_matches', 'awaiting_payment', 'settings'
    )),
    context JSONB DEFAULT '{}',              -- conversation state data
    last_message_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_wa_sessions_phone ON whatsapp_sessions(phone);

-- ============================================================
-- ANALYTICS / DATA FLYWHEEL
-- ============================================================

CREATE TABLE application_outcomes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    match_id UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    outcome VARCHAR(20) CHECK (outcome IN ('applied', 'interview', 'offer', 'rejected', 'no_response')),
    reported_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_outcomes_match ON application_outcomes(match_id);

-- ============================================================
-- RPC FUNCTIONS
-- ============================================================

-- Hybrid matching: vector similarity + skill overlap
CREATE OR REPLACE FUNCTION match_jobs_for_user(
    p_user_id UUID,
    p_limit INTEGER DEFAULT 20,
    p_min_score REAL DEFAULT 50
)
RETURNS TABLE (
    job_id UUID,
    title VARCHAR,
    company VARCHAR,
    location VARCHAR,
    vector_score REAL,
    skill_score REAL,
    bonus_score REAL,
    final_score REAL,
    matched_skills TEXT[],
    missing_skills TEXT[]
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_user_embedding VECTOR(1536);
    v_user_skills TEXT[];
    v_user_location VARCHAR;
    v_user_experience INTEGER;
BEGIN
    -- Get user's primary CV embedding
    SELECT c.embedding INTO v_user_embedding
    FROM cvs c
    WHERE c.user_id = p_user_id AND c.is_primary = true
    LIMIT 1;

    IF v_user_embedding IS NULL THEN
        RAISE EXCEPTION 'User has no primary CV with embedding';
    END IF;

    -- Get user's skills as text array
    SELECT ARRAY_AGG(s.name) INTO v_user_skills
    FROM user_skills us
    JOIN skills s ON s.id = us.skill_id
    WHERE us.user_id = p_user_id;

    -- Get user location and experience
    SELECT u.location, u.years_experience
    INTO v_user_location, v_user_experience
    FROM users u WHERE u.id = p_user_id;

    RETURN QUERY
    WITH job_scores AS (
        SELECT
            j.id AS j_id,
            j.title AS j_title,
            j.company AS j_company,
            j.location AS j_location,
            -- Vector similarity (cosine): 0-1 range, scaled to 0-100
            (1 - (j.embedding <=> v_user_embedding)) * 100 AS v_score,
            -- Skill overlap
            COALESCE(
                (SELECT COUNT(*)::REAL FROM job_skills js2
                 JOIN skills s2 ON s2.id = js2.skill_id
                 WHERE js2.job_id = j.id AND s2.name = ANY(v_user_skills))
                /
                NULLIF((SELECT COUNT(*)::REAL FROM job_skills js3 WHERE js3.job_id = j.id), 0)
                * 100,
                0
            ) AS s_score,
            -- Bonus signals
            (
                CASE WHEN j.location = v_user_location THEN 30 ELSE 0 END +
                CASE WHEN j.quality_score > 70 THEN 20 ELSE 0 END +
                CASE WHEN j.closing_date > CURRENT_DATE THEN 20 ELSE 0 END +
                CASE WHEN j.posted_at > NOW() - INTERVAL '7 days' THEN 30 ELSE 0 END
            )::REAL AS b_score,
            -- Matched skills
            ARRAY(
                SELECT s2.name FROM job_skills js2
                JOIN skills s2 ON s2.id = js2.skill_id
                WHERE js2.job_id = j.id AND s2.name = ANY(v_user_skills)
            ) AS m_skills,
            -- Missing skills
            ARRAY(
                SELECT s2.name FROM job_skills js2
                JOIN skills s2 ON s2.id = js2.skill_id
                WHERE js2.job_id = j.id AND NOT (s2.name = ANY(v_user_skills))
            ) AS miss_skills
        FROM jobs j
        WHERE j.is_active = true
          AND j.embedding IS NOT NULL
    )
    SELECT
        js.j_id,
        js.j_title,
        js.j_company,
        js.j_location,
        js.v_score,
        js.s_score,
        js.b_score,
        (js.v_score * 0.6 + js.s_score * 0.3 + js.b_score * 0.1) AS f_score,
        js.m_skills,
        js.miss_skills
    FROM job_scores js
    WHERE (js.v_score * 0.6 + js.s_score * 0.3 + js.b_score * 0.1) >= p_min_score
    ORDER BY f_score DESC
    LIMIT p_limit;
END;
$$;

-- Calculate job quality score
CREATE OR REPLACE FUNCTION calculate_job_quality(p_job_id UUID)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_score INTEGER := 0;
    v_job RECORD;
BEGIN
    SELECT * INTO v_job FROM jobs WHERE id = p_job_id;

    IF v_job.company IS NOT NULL AND LENGTH(v_job.company) > 0 THEN
        v_score := v_score + 15;
    END IF;
    IF v_job.apply_email IS NOT NULL OR v_job.apply_url IS NOT NULL THEN
        v_score := v_score + 20;
    END IF;
    IF LENGTH(v_job.description) > 200 THEN
        v_score := v_score + 10;
    END IF;
    IF v_job.salary_min IS NOT NULL OR v_job.salary_max IS NOT NULL THEN
        v_score := v_score + 10;
    END IF;
    IF v_job.source IN ('partner', 'manual') THEN
        v_score := v_score + 25;
    END IF;
    IF v_job.closing_date IS NOT NULL THEN
        v_score := v_score + 10;
    END IF;
    IF v_job.location IS NOT NULL AND LENGTH(v_job.location) > 0 THEN
        v_score := v_score + 10;
    END IF;

    -- Update the job record
    UPDATE jobs SET quality_score = v_score, updated_at = NOW() WHERE id = p_job_id;

    RETURN v_score;
END;
$$;

-- Heartbeat function (called by n8n every 6 hours)
CREATE OR REPLACE FUNCTION heartbeat()
RETURNS TEXT
LANGUAGE sql
AS $$
    SELECT 'alive: ' || NOW()::TEXT;
$$;

-- Auto-deactivate expired jobs
CREATE OR REPLACE FUNCTION deactivate_expired_jobs()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_count INTEGER;
BEGIN
    UPDATE jobs
    SET is_active = false, updated_at = NOW()
    WHERE is_active = true
      AND closing_date < CURRENT_DATE;

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$;

-- Reset monthly match counters
CREATE OR REPLACE FUNCTION reset_monthly_matches()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_count INTEGER;
BEGIN
    UPDATE subscriptions
    SET matches_used = 0, updated_at = NOW()
    WHERE current_period_end < NOW()
      AND status = 'active';

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$;

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE cvs ENABLE ROW LEVEL SECURITY;
ALTER TABLE matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE generated_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE whatsapp_sessions ENABLE ROW LEVEL SECURITY;

-- Users can only read/update their own data
CREATE POLICY users_self ON users
    FOR ALL USING (id = auth.uid());

CREATE POLICY cvs_self ON cvs
    FOR ALL USING (user_id = auth.uid());

CREATE POLICY matches_self ON matches
    FOR ALL USING (user_id = auth.uid());

CREATE POLICY subscriptions_self ON subscriptions
    FOR ALL USING (user_id = auth.uid());

CREATE POLICY payments_self ON payments
    FOR ALL USING (user_id = auth.uid());

CREATE POLICY gen_docs_self ON generated_documents
    FOR ALL USING (user_id = auth.uid());

-- Jobs are readable by all authenticated users
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY jobs_read ON jobs
    FOR SELECT USING (true);

-- Service role can do everything (for backend/n8n)
-- This is handled by Supabase's service_role key which bypasses RLS

-- ============================================================
-- TRIGGERS
-- ============================================================

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER set_updated_at_users
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER set_updated_at_jobs
    BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER set_updated_at_subscriptions
    BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- Auto-calculate quality score on job insert/update
CREATE OR REPLACE FUNCTION trigger_calculate_quality()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM calculate_job_quality(NEW.id);
    RETURN NEW;
END;
$$;

CREATE TRIGGER calc_quality_on_insert
    AFTER INSERT ON jobs
    FOR EACH ROW EXECUTE FUNCTION trigger_calculate_quality();

-- ============================================================
-- SEED DATA: Common Skills
-- ============================================================

INSERT INTO skills (name, category) VALUES
    -- Programming
    ('python', 'programming'),
    ('javascript', 'programming'),
    ('typescript', 'programming'),
    ('java', 'programming'),
    ('csharp', 'programming'),
    ('php', 'programming'),
    ('sql', 'programming'),
    ('html', 'programming'),
    ('css', 'programming'),
    ('react', 'programming'),
    ('nodejs', 'programming'),
    ('nextjs', 'programming'),
    ('django', 'programming'),
    ('flask', 'programming'),
    ('fastapi', 'programming'),
    -- Office / Tools
    ('microsoft office', 'tools'),
    ('excel', 'tools'),
    ('powerpoint', 'tools'),
    ('google workspace', 'tools'),
    ('sap', 'tools'),
    ('quickbooks', 'tools'),
    ('autocad', 'tools'),
    -- Soft Skills
    ('communication', 'soft_skill'),
    ('leadership', 'soft_skill'),
    ('teamwork', 'soft_skill'),
    ('problem solving', 'soft_skill'),
    ('project management', 'soft_skill'),
    ('time management', 'soft_skill'),
    ('customer service', 'soft_skill'),
    -- Domain
    ('accounting', 'domain'),
    ('marketing', 'domain'),
    ('sales', 'domain'),
    ('human resources', 'domain'),
    ('supply chain', 'domain'),
    ('data analysis', 'domain'),
    ('teaching', 'domain'),
    ('nursing', 'domain'),
    ('mining engineering', 'domain'),
    ('agriculture', 'domain'),
    ('banking', 'domain')
ON CONFLICT (name) DO NOTHING;

-- Seed skill aliases
INSERT INTO skill_aliases (alias, skill_id) VALUES
    ('js', (SELECT id FROM skills WHERE name = 'javascript')),
    ('ts', (SELECT id FROM skills WHERE name = 'typescript')),
    ('c#', (SELECT id FROM skills WHERE name = 'csharp')),
    ('node', (SELECT id FROM skills WHERE name = 'nodejs')),
    ('node.js', (SELECT id FROM skills WHERE name = 'nodejs')),
    ('next.js', (SELECT id FROM skills WHERE name = 'nextjs')),
    ('ms word', (SELECT id FROM skills WHERE name = 'microsoft office')),
    ('word', (SELECT id FROM skills WHERE name = 'microsoft office')),
    ('ms excel', (SELECT id FROM skills WHERE name = 'excel')),
    ('ppt', (SELECT id FROM skills WHERE name = 'powerpoint')),
    ('ms powerpoint', (SELECT id FROM skills WHERE name = 'powerpoint')),
    ('google docs', (SELECT id FROM skills WHERE name = 'google workspace')),
    ('google sheets', (SELECT id FROM skills WHERE name = 'google workspace')),
    ('hr', (SELECT id FROM skills WHERE name = 'human resources')),
    ('pm', (SELECT id FROM skills WHERE name = 'project management')),
    ('data entry', (SELECT id FROM skills WHERE name = 'data analysis'))
ON CONFLICT (alias) DO NOTHING;
