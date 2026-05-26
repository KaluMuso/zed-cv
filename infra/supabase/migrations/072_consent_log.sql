-- 072 — Consent audit log for privacy settings toggles (Bucket 9 consent UI)
--
-- INSERT via backend service role; SELECT scoped to owner.

BEGIN;

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

COMMIT;
