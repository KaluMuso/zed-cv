// Frontend mirror of AdminJobCreate from docs/openapi.yaml (Wave 4 PR 2).
// Kept in this file (not lib/api.ts) so the wizard owns its draft shape
// without dragging the legacy short-form AdminJobCreate type into PR 4's
// rewrite. PR 4 swaps lib/api.ts admin.createJob to take this type.
//
// Authoritative source: apps/backend/app/schemas/jobs.py::AdminJobCreate
// + docs/openapi.yaml schemas/AdminJobCreate. Backend uses extra='forbid'
// so any drift here → 422 at runtime.

import type {
  EmploymentType,
  WorkArrangement,
  PayFrequency,
} from "@/lib/api";

export type AdminJobSource = "manual" | "scraper" | "ocr" | "partner";

export type AdminJobCreatePayload = {
  // Step 1 — Basic info
  title: string;
  company?: string | null;
  location?: string | null;
  description: string;
  employment_type?: EmploymentType | null;
  work_arrangement?: WorkArrangement | null;
  hybrid_days_per_week?: number | null;

  // Step 2 — Compensation
  salary_min?: number | null;
  salary_max?: number | null;
  currency?: string | null;
  pay_frequency?: PayFrequency | null;
  bonus_structure?: string | null;
  equity_offered?: boolean | null;
  benefits?: string[] | null;

  // Step 3-5 — Role details / Application / Company context (PR 4 renders these)
  requirements?: string[] | null;
  skills_required?: string[] | null;
  reporting_structure?: string | null;
  manages_others?: number | null;
  interview_process?: string | null;
  success_metrics?: string | null;
  tools_tech_stack?: string[] | null;
  application_instructions?: string | null;
  apply_url?: string | null;
  apply_email?: string | null;
  contact_phone?: string | null;
  closing_date?: string | null;
  posted_at?: string | null;
  reference_number?: string | null;
  company_description?: string | null;
  source_url?: string | null;
  source_platform?: string | null;
  salary_text?: string | null;

  // Always "manual" for wizard-created jobs. Backend defaults to manual
  // when source is omitted, but we send it explicitly so the wire payload
  // is self-documenting.
  source: "manual";
};
