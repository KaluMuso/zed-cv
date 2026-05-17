"use client";

/**
 * Target-roles input for the Preferences tab.
 *
 * Uses the same TagInput primitive as RegionsInput. The suggestion list
 * is a small curated set of common Zambian job titles; user can still
 * type any free-form title. Up to 10 entries (matches the API cap).
 */
import { TagInput } from "@/components/TagInput";

// Curated default suggestions. Deliberately conservative — these are
// what people most often type, not an exhaustive taxonomy. The
// autocomplete is a hint, not a constraint.
const COMMON_ROLES = [
  "Software Engineer",
  "Data Analyst",
  "Data Scientist",
  "Product Manager",
  "Project Manager",
  "Operations Manager",
  "Accountant",
  "Auditor",
  "Marketing Manager",
  "Sales Manager",
  "Business Analyst",
  "Administrative Assistant",
  "Customer Service Representative",
  "Human Resources Manager",
  "Procurement Officer",
  "Logistics Coordinator",
  "Field Officer",
  "Programme Officer",
  "Monitoring and Evaluation Officer",
  "Communications Officer",
  "Civil Engineer",
  "Mechanical Engineer",
  "Electrical Engineer",
  "Teacher",
  "Lecturer",
  "Nurse",
  "Pharmacist",
  "Medical Officer",
  "Legal Counsel",
  "Compliance Officer",
] as const;

interface TargetRolesInputProps {
  value: string[];
  onChange: (next: string[]) => void;
  /** Extra suggestions (e.g. roles already in the user's CV). */
  extraSuggestions?: readonly string[];
  max?: number;
  disabled?: boolean;
}

export function TargetRolesInput({
  value,
  onChange,
  extraSuggestions = [],
  max = 10,
  disabled,
}: TargetRolesInputProps) {
  // Merge curated + extras (deduplicated, preserve curated order). Some
  // callers pass the user's CV-derived titles as extras so the
  // autocomplete surfaces the roles the user actually held.
  const merged = (() => {
    const seen = new Set(COMMON_ROLES.map((r) => r.toLowerCase()));
    const out: string[] = [...COMMON_ROLES];
    for (const extra of extraSuggestions) {
      const key = extra.trim().toLowerCase();
      if (!key || seen.has(key)) continue;
      seen.add(key);
      out.push(extra.trim());
    }
    return out;
  })();

  return (
    <TagInput
      value={value}
      onChange={onChange}
      suggestions={merged}
      placeholder="Add a role (e.g. Software Engineer)"
      max={max}
      inputId="target-roles-input"
      ariaLabel="Target roles"
      disabled={disabled}
    />
  );
}
