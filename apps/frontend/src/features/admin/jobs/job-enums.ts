// Frontend mirror of backend enums for the admin job-create wizard.
// Authoritative source: apps/backend/app/schemas/jobs.py
// + docs/openapi.yaml schemas/AdminJobCreate. Any drift here will 422
// on submit because the backend uses extra='forbid' and Enum validation.

import type {
  EmploymentType,
  WorkArrangement,
  PayFrequency,
} from "@/lib/api";

export const EMPLOYMENT_TYPES: ReadonlyArray<{
  value: EmploymentType;
  label: string;
}> = [
  { value: "full_time", label: "Full-time" },
  { value: "part_time", label: "Part-time" },
  { value: "contract", label: "Contract" },
  { value: "freelance", label: "Freelance" },
  { value: "internship", label: "Internship" },
  { value: "temporary", label: "Temporary" },
];

export const WORK_ARRANGEMENTS: ReadonlyArray<{
  value: WorkArrangement;
  label: string;
}> = [
  { value: "on_site", label: "On-site" },
  { value: "remote", label: "Remote" },
  { value: "hybrid", label: "Hybrid" },
];

// Per Pydantic _normalize_currency comment in schemas/jobs.py: ZMW is
// the local currency; USD/EUR/GBP are the others observed in the wild.
// Backend caps the column at exactly 3 chars (ISO 4217 alpha).
export const CURRENCIES: ReadonlyArray<{ value: string; label: string }> = [
  { value: "ZMW", label: "ZMW — Zambian Kwacha" },
  { value: "USD", label: "USD — US Dollar" },
  { value: "EUR", label: "EUR — Euro" },
  { value: "GBP", label: "GBP — British Pound" },
];

export const PAY_FREQUENCIES: ReadonlyArray<{
  value: PayFrequency;
  label: string;
}> = [
  { value: "monthly", label: "Monthly" },
  { value: "annual", label: "Annual" },
  { value: "hourly", label: "Hourly" },
  { value: "daily", label: "Daily" },
];

// Backend allows 1-5 (apps/backend/app/schemas/jobs.py — hybrid_days_per_week
// Field(None, ge=1, le=5)). Brief said 1-4 but backend wins (contract-first).
export const HYBRID_DAYS_MIN = 1;
export const HYBRID_DAYS_MAX = 5;

// Backend cap (jobs.py _cap_benefits): 20 entries × 200 chars each.
export const BENEFITS_MAX_ITEMS = 20;
export const BENEFIT_MAX_LENGTH = 200;

// Backend caps for free-text compensation fields.
export const BONUS_STRUCTURE_MAX_LENGTH = 500;
