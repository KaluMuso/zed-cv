import type { UserProfile } from "@/lib/api";
import type { TailoredCvDraft, EducationEntry, ExperienceEntry } from "./types";
import { DEFAULT_STYLE } from "./store";

function mapExperience(
  items: NonNullable<UserProfile["cv_sections"]>["work_experience"],
): ExperienceEntry[] {
  return items.map((item) => ({
    title: item.title ?? "",
    company: item.company ?? "",
    location: item.location ?? "",
    startDate: item.start_date ?? "",
    endDate: item.end_date ?? "",
    achievements: item.achievements?.length ? [...item.achievements] : [""],
  }));
}

function mapEducation(
  items: NonNullable<UserProfile["cv_sections"]>["education"],
): EducationEntry[] {
  return items.map((item) => ({
    degree: item.degree ?? "",
    institution: item.institution ?? "",
    location: item.location ?? "",
    startDate: item.start_date ?? "",
    endDate: item.end_date ?? "",
  }));
}

/**
 * Build a tailored-CV draft from the user's uploaded profile CV (task #59 sections).
 * Returns null when no structured CV is on the profile.
 */
export function mapProfileToDraft(profile: UserProfile): TailoredCvDraft | null {
  if (!profile.cv_uploaded || !profile.cv_sections) {
    return null;
  }

  const sections = profile.cv_sections;
  const firstRole = sections.work_experience[0];
  const summaryText = sections.professional_summary?.text?.trim() ?? "";

  return {
    basics: {
      fullName: profile.full_name?.trim() ?? "",
      headline: firstRole?.title?.trim() ?? "",
      email: profile.email?.trim() ?? "",
      phone: profile.phone?.trim() ?? "",
      location: profile.location?.trim() ?? "",
      summary: summaryText,
    },
    experience:
      sections.work_experience.length > 0
        ? mapExperience(sections.work_experience)
        : [],
    education:
      sections.education.length > 0 ? mapEducation(sections.education) : [],
    skills: profile.skills?.length ? [...profile.skills] : [],
    style: { ...DEFAULT_STYLE },
  };
}
