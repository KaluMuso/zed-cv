import type { ProfileCompletenessFieldId } from "@/lib/profileCompleteness";

export const PROFILE_COMPLETENESS_FIELD_TITLES: Record<ProfileCompletenessFieldId, string> = {
  phone: "Phone number",
  email: "Email address",
  full_name: "Full name",
  cv_uploaded: "CV uploaded",
  years_of_experience: "Years of experience",
  preferred_industries: "Preferred industries",
  preferred_work_arrangements: "Work arrangement",
  preferred_locations: "Preferred locations",
  target_salary: "Salary expectations",
  education_level: "Education level",
  languages: "Languages",
  certifications: "Certifications",
  notice_period: "Notice period",
  willing_to_relocate: "Relocation preference",
};

/** Fields that read/write job preferences (not profile PATCH). */
export const PREFERENCE_COMPLETENESS_FIELD_IDS = new Set<ProfileCompletenessFieldId>([
  "preferred_industries",
  "preferred_work_arrangements",
  "preferred_locations",
  "target_salary",
  "education_level",
  "languages",
  "notice_period",
  "willing_to_relocate",
]);

export function fieldNeedsPreferencesLoad(fieldId: ProfileCompletenessFieldId): boolean {
  return PREFERENCE_COMPLETENESS_FIELD_IDS.has(fieldId);
}

export function fieldShowsSaveButton(fieldId: ProfileCompletenessFieldId): boolean {
  return fieldId !== "phone" && fieldId !== "cv_uploaded" && fieldId !== "certifications";
}
