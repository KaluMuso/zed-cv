import type { ManualCvDraft } from "./types";

export function draftToBuildPayload(draft: ManualCvDraft) {
  return {
    summary: draft.summary,
    basics: {
      full_name: draft.basics.fullName,
      phone: draft.basics.phone,
      email: draft.basics.email,
      location: draft.basics.location,
      headline: draft.basics.headline,
    },
    experience: draft.experience.map((e) => ({
      title: e.title,
      company: e.company,
      location: e.location,
      start_date: e.startDate,
      end_date: e.isPresent ? "Present" : e.endDate,
      achievements: e.achievements.filter(Boolean),
    })),
    education: draft.education.map((e) => ({
      degree: e.degree,
      institution: e.institution,
      location: e.location,
      start_date: e.startDate,
      end_date: e.endDate,
      gpa: e.gpa,
    })),
    skills: draft.skills,
    style: {
      template: draft.style.template,
      accent_color: draft.style.accentColor,
      show_summary: draft.style.showSummary,
    },
  };
}

/** Map manual draft to tailored preview shape for shared preview styles. */
export function draftToPreviewDraft(draft: ManualCvDraft) {
  return {
    basics: {
      fullName: draft.basics.fullName,
      headline: draft.basics.headline,
      email: draft.basics.email,
      phone: draft.basics.phone,
      location: draft.basics.location,
      summary: draft.summary,
    },
    experience: draft.experience.map((e) => ({
      title: e.title,
      company: e.company,
      location: e.location,
      startDate: e.startDate,
      endDate: e.isPresent ? "Present" : e.endDate,
      achievements: e.achievements,
    })),
    education: draft.education.map((e) => ({
      degree: e.degree,
      institution: e.institution,
      location: e.location,
      startDate: e.startDate,
      endDate: e.endDate,
    })),
    skills: draft.skills,
    style: {
      density: draft.style.template === "compact" ? ("compact" as const) : ("standard" as const),
      showSummary: draft.style.showSummary,
    },
  };
}
