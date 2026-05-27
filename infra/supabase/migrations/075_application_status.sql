-- 075 — Application tracking on saved_jobs (Kanban statuses + audit history)

BEGIN;

ALTER TABLE public.saved_jobs
  ADD COLUMN IF NOT EXISTS application_status TEXT NOT NULL DEFAULT 'saved'
    CHECK (application_status IN (
      'saved',
      'applied',
      'interviewing',
      'offered',
      'closed_won',
      'closed_lost'
    )),
  ADD COLUMN IF NOT EXISTS status_updated_at TIMESTAMPTZ DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS application_notes TEXT,
  ADD COLUMN IF NOT EXISTS interview_date DATE;

CREATE INDEX IF NOT EXISTS idx_saved_jobs_user_status
  ON public.saved_jobs (user_id, application_status);

CREATE TABLE IF NOT EXISTS public.application_status_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  saved_job_id UUID NOT NULL REFERENCES public.saved_jobs (id) ON DELETE CASCADE,
  from_status TEXT,
  to_status TEXT NOT NULL,
  changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  changed_by_user_id UUID REFERENCES public.users (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_application_status_history_saved_job
  ON public.application_status_history (saved_job_id, changed_at DESC);

-- Allow owners to update their own saved_jobs application fields (031 had no UPDATE policy).
DROP POLICY IF EXISTS saved_jobs_update_own ON public.saved_jobs;
CREATE POLICY saved_jobs_update_own ON public.saved_jobs
  FOR UPDATE
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

ALTER TABLE public.application_status_history ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS application_status_history_owner ON public.application_status_history;
CREATE POLICY application_status_history_owner ON public.application_status_history
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.saved_jobs sj
      WHERE sj.id = application_status_history.saved_job_id
        AND sj.user_id = auth.uid()
    )
  );

COMMIT;
