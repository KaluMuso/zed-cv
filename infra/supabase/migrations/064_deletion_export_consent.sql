-- 064 — ZDPA deletion grace period, portable export, consent audit log (Bucket 9)
--
-- Replaces immediate DELETE /me with scheduled erasure + ZIP export requests.
-- consent_log INSERT is service-role only; SELECT is owner-scoped.

BEGIN;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

COMMENT ON COLUMN users.deleted_at IS
    'Set when execute_deletion completes; PII nulled but row retained for FK integrity.';

CREATE TABLE IF NOT EXISTS data_deletion_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    requested_at TIMESTAMPTZ DEFAULT NOW(),
    scheduled_at TIMESTAMPTZ NOT NULL,
    executed_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'cancelled', 'executing', 'completed', 'failed')),
    failure_reason TEXT,
    artifacts JSONB
);

CREATE INDEX IF NOT EXISTS idx_ddr_user_status
    ON data_deletion_requests (user_id, status);

ALTER TABLE data_deletion_requests ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS ddr_owner ON data_deletion_requests;
CREATE POLICY ddr_owner ON data_deletion_requests
    FOR ALL TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE TABLE IF NOT EXISTS data_export_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    requested_at TIMESTAMPTZ DEFAULT NOW(),
    generated_at TIMESTAMPTZ,
    download_url TEXT,
    download_expires_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'generating', 'ready', 'expired', 'failed')),
    failure_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_der_user_status
    ON data_export_requests (user_id, status);

ALTER TABLE data_export_requests ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS der_owner ON data_export_requests;
CREATE POLICY der_owner ON data_export_requests
    FOR ALL TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE TABLE IF NOT EXISTS consent_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    consent_type TEXT NOT NULL CHECK (consent_type IN (
        'terms_of_service',
        'privacy_policy',
        'marketing_email',
        'marketing_whatsapp',
        'analytics_cookies',
        'third_party_data_sharing'
    )),
    granted BOOLEAN NOT NULL,
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    legal_doc_version TEXT,
    ip_address INET,
    user_agent TEXT
);

CREATE INDEX IF NOT EXISTS idx_consent_log_user_type
    ON consent_log (user_id, consent_type, granted_at DESC);

ALTER TABLE consent_log ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS consent_log_owner ON consent_log;
CREATE POLICY consent_log_owner ON consent_log
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

CREATE TABLE IF NOT EXISTS deletion_safety_allowlist (
    phone TEXT PRIMARY KEY,
    reason TEXT NOT NULL,
    added_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE deletion_safety_allowlist IS
    'Phones that must never be erased by execute_deletion (founder/family test accounts).';

COMMIT;
