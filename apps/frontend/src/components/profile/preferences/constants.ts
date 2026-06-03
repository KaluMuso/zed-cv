export const EDUCATION_LEVEL_OPTIONS = [
  "Primary / Grade 12",
  "Certificate / Diploma",
  "Bachelor's degree",
  "Honours / Postgraduate diploma",
  "Master's degree",
  "Doctorate (PhD)",
  "Professional qualification",
  "Other",
] as const;

export const NOTICE_PERIOD_OPTIONS = [
  "Immediate",
  "1 week",
  "2 weeks",
  "1 month",
  "3+ months",
] as const;

export const PREFERENCE_FIELD_CLASS =
  "block mt-1 w-full text-sm rounded-md px-3";

export const preferenceFieldStyle = {
  background: "var(--bg-2)",
  border: "1px solid var(--line)",
  color: "var(--ink)",
  minHeight: 44,
} as const;
