-- migration: 108_rls_audit_gap_tables

-- Auditor finding: Six tables created without ENABLE ROW LEVEL SECURITY.
-- Date: 2026-06-08

BEGIN;

-- 1. applications (handled dynamically below to support production where table is absent)

-- 2. aptitude_question_bank
-- Auditor finding: RLS gap. Date: 2026-06-08.
ALTER TABLE public.aptitude_question_bank ENABLE ROW LEVEL SECURITY;

-- Question bank is admin/service_role only. Reject all public anon/authenticated access.
DROP POLICY IF EXISTS aptitude_question_bank_authenticated_read ON public.aptitude_question_bank;
DROP POLICY IF EXISTS aptitude_question_bank_read_auth ON public.aptitude_question_bank;


-- 3. canonical_skills
-- Auditor finding: RLS gap. Date: 2026-06-08.
ALTER TABLE public.canonical_skills ENABLE ROW LEVEL SECURITY;

-- Allow authenticated SELECT access only (read-only catalog). Reject anon.
DROP POLICY IF EXISTS canonical_skills_public_read ON public.canonical_skills;
DROP POLICY IF EXISTS canonical_skills_read_all ON public.canonical_skills;
CREATE POLICY canonical_skills_read_auth ON public.canonical_skills
  FOR SELECT
  TO authenticated
  USING (true);


-- 4. raw_skill_mappings
-- Auditor finding: RLS gap. Date: 2026-06-08.
ALTER TABLE public.raw_skill_mappings ENABLE ROW LEVEL SECURITY;

-- Allow authenticated SELECT access only. Reject anon.
DROP POLICY IF EXISTS raw_skill_mappings_authenticated_read ON public.raw_skill_mappings;
CREATE POLICY raw_skill_mappings_read_auth ON public.raw_skill_mappings
  FOR SELECT
  TO authenticated
  USING (true);


-- 5. match_batch_runs
-- Auditor finding: RLS gap. Date: 2026-06-08.
ALTER TABLE public.match_batch_runs ENABLE ROW LEVEL SECURITY;

-- No policies for public roles; accessible by service_role only.
DROP POLICY IF EXISTS match_batch_runs_policy ON public.match_batch_runs;


-- 6. apply_url_backfill_log
-- Auditor finding: RLS gap. Date: 2026-06-08.
ALTER TABLE public.apply_url_backfill_log ENABLE ROW LEVEL SECURITY;

-- No policies for public roles; accessible by service_role only.
DROP POLICY IF EXISTS apply_url_backfill_log_policy ON public.apply_url_backfill_log;


-- RLS Validation / Test Block
DO $$
DECLARE
  v_test_user_id UUID := '00000000-0000-0000-0000-000000000001';
  v_other_user_id UUID := '00000000-0000-0000-0000-000000000002';
  v_cnt INTEGER;
  v_applications_exist BOOLEAN;
BEGIN
  -- Check if applications table exists (it might not exist in production but does locally)
  SELECT EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = 'applications'
  ) INTO v_applications_exist;

  -- Setup applications RLS and policies dynamically if it exists
  IF v_applications_exist THEN
    EXECUTE 'ALTER TABLE public.applications ENABLE ROW LEVEL SECURITY';
    EXECUTE 'DROP POLICY IF EXISTS applications_owner ON public.applications';
    EXECUTE 'CREATE POLICY applications_owner ON public.applications
      FOR ALL
      TO authenticated
      USING (user_id = auth.uid())
      WITH CHECK (user_id = auth.uid())';
  END IF;

  -- Setup minimal seed data for RLS testing
  INSERT INTO public.users (id, phone, referral_code)
  VALUES (v_test_user_id, '+260999999999', 'TESTCODE9999')
  ON CONFLICT (id) DO NOTHING;

  INSERT INTO public.jobs (id, title, company, location, description, source)
  VALUES ('99999999-9999-9999-9999-999999999999', 'Test Job', 'Test Co', 'Lusaka', 'Desc', 'manual')
  ON CONFLICT (id) DO NOTHING;

  IF v_applications_exist THEN
    EXECUTE 'INSERT INTO public.applications (id, user_id, job_id, status)
      VALUES (''99999999-9999-9999-9999-999999999991'', $1, ''99999999-9999-9999-9999-999999999999'', ''applied'')
      ON CONFLICT (user_id, job_id) DO NOTHING' USING v_test_user_id;
  END IF;

  -- 1. Test as anon role
  EXECUTE 'SET LOCAL ROLE anon';
  PERFORM set_config('request.jwt.claims', '{}', true);

  -- applications (if exists): anon should see 0 rows
  IF v_applications_exist THEN
    EXECUTE 'SELECT COUNT(*) FROM public.applications' INTO v_cnt;
    IF v_cnt > 0 THEN
      RAISE EXCEPTION 'RLS FAIL: anon user could read applications table';
    END IF;
  END IF;

  -- canonical_skills: anon should see 0 rows
  SELECT COUNT(*) INTO v_cnt FROM public.canonical_skills;
  IF v_cnt > 0 THEN
    RAISE EXCEPTION 'RLS FAIL: anon user could read canonical_skills table';
  END IF;

  -- aptitude_question_bank: anon should see 0 rows
  SELECT COUNT(*) INTO v_cnt FROM public.aptitude_question_bank;
  IF v_cnt > 0 THEN
    RAISE EXCEPTION 'RLS FAIL: anon user could read aptitude_question_bank table';
  END IF;

  -- 2. Test as authenticated role (matching user_id)
  EXECUTE 'SET LOCAL ROLE authenticated';
  PERFORM set_config('request.jwt.claims', format('{"sub": "%s"}', v_test_user_id), true);

  -- applications (if exists): should see their own application
  IF v_applications_exist THEN
    EXECUTE 'SELECT COUNT(*) FROM public.applications' INTO v_cnt;
    IF v_cnt = 0 THEN
      RAISE EXCEPTION 'RLS FAIL: authenticated user could not read their own applications';
    END IF;
  END IF;

  -- 3. Test as authenticated role (non-matching user_id)
  PERFORM set_config('request.jwt.claims', format('{"sub": "%s"}', v_other_user_id), true);
  
  -- applications (if exists): should see 0 rows for other user
  IF v_applications_exist THEN
    EXECUTE 'SELECT COUNT(*) FROM public.applications' INTO v_cnt;
    IF v_cnt > 0 THEN
      RAISE EXCEPTION 'RLS FAIL: authenticated user could read other users applications';
    END IF;
  END IF;

  -- aptitude_question_bank: authenticated should see 0 rows
  SELECT COUNT(*) INTO v_cnt FROM public.aptitude_question_bank;
  IF v_cnt > 0 THEN
    RAISE EXCEPTION 'RLS FAIL: authenticated user could read aptitude_question_bank';
  END IF;

  -- match_batch_runs: authenticated should see 0 rows
  SELECT COUNT(*) INTO v_cnt FROM public.match_batch_runs;
  IF v_cnt > 0 THEN
    RAISE EXCEPTION 'RLS FAIL: authenticated user could read match_batch_runs';
  END IF;

  -- Reset role to service_role/admin to clean up test data
  EXECUTE 'RESET ROLE';
  
  IF v_applications_exist THEN
    EXECUTE 'DELETE FROM public.applications WHERE id = ''99999999-9999-9999-9999-999999999991''';
  END IF;
  DELETE FROM public.users WHERE id = v_test_user_id;
  DELETE FROM public.jobs WHERE id = '99999999-9999-9999-9999-999999999999';

  RAISE NOTICE 'RLS audit verification block passed.';
END $$;

COMMIT;
