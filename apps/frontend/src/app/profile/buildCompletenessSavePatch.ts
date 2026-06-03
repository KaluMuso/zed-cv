import type { JobPreferences, JobPreferencesUpdate } from "@/lib/api";
import type { ProfileCompletenessFieldId } from "@/lib/profileCompleteness";
import { validateSalaryRange } from "@/components/profile/preferences/PreferenceFields";

export type CompletenessSaveTarget =
  | { kind: "profile"; patch: { full_name?: string | null; email?: string | null; years_experience?: number } }
  | { kind: "preferences"; patch: JobPreferencesUpdate }
  | { kind: "invalid"; salaryError: string };

export function buildCompletenessSavePatch(
  fieldId: ProfileCompletenessFieldId,
  prefs: JobPreferences | null,
  form: {
    fullName: string;
    email: string;
    yearsExperience: number;
  },
): CompletenessSaveTarget | null {
  switch (fieldId) {
    case "full_name":
      return { kind: "profile", patch: { full_name: form.fullName.trim() || null } };
    case "email":
      return { kind: "profile", patch: { email: form.email.trim() || null } };
    case "years_of_experience":
      return { kind: "profile", patch: { years_experience: form.yearsExperience } };
    case "preferred_work_arrangements":
      return {
        kind: "preferences",
        patch: { preferred_work_arrangement: prefs?.preferred_work_arrangement ?? null },
      };
    case "preferred_locations":
      return { kind: "preferences", patch: { acceptable_regions: prefs?.acceptable_regions ?? [] } };
    case "target_salary": {
      const salaryError = validateSalaryRange(prefs?.salary_min ?? null, prefs?.salary_max ?? null);
      if (salaryError || !prefs) return salaryError ? { kind: "invalid", salaryError } : null;
      return {
        kind: "preferences",
        patch: {
          salary_min: prefs.salary_min,
          salary_max: prefs.salary_max,
          salary_frequency: prefs.salary_frequency,
          salary_currency: prefs.salary_currency,
        },
      };
    }
    case "education_level": {
      if (!prefs) return null;
      const extras = { ...(prefs.extras ?? {}) };
      const level = typeof extras.education_level === "string" ? extras.education_level : "";
      if (level) extras.education_level = level;
      else delete extras.education_level;
      return { kind: "preferences", patch: { extras } };
    }
    case "languages":
      return { kind: "preferences", patch: { languages: prefs?.languages ?? [] } };
    case "preferred_industries":
      return { kind: "preferences", patch: { industries: prefs?.industries ?? [] } };
    case "notice_period": {
      if (!prefs) return null;
      const extras = { ...(prefs.extras ?? {}) };
      const period = typeof extras.notice_period === "string" ? extras.notice_period : "";
      if (period) extras.notice_period = period;
      else delete extras.notice_period;
      return { kind: "preferences", patch: { extras } };
    }
    case "willing_to_relocate":
      return {
        kind: "preferences",
        patch: {
          willing_to_relocate: prefs?.willing_to_relocate ?? false,
          preferred_work_arrangement: prefs?.preferred_work_arrangement ?? null,
        },
      };
    default:
      return null;
  }
}
