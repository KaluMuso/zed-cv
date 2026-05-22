export const BUILDER_STEPS = [
  "basics",
  "experience",
  "education",
  "skills",
  "style",
  "preview",
] as const;

export type BuilderStep = (typeof BUILDER_STEPS)[number];

export const BUILDER_STEP_LABELS: Record<BuilderStep, string> = {
  basics: "Basics",
  experience: "Experience",
  education: "Education",
  skills: "Skills",
  style: "Style",
  preview: "Preview",
};

export type BasicsInfo = {
  fullName: string;
  headline: string;
  email: string;
  phone: string;
  location: string;
  summary: string;
};

export type ExperienceEntry = {
  title: string;
  company: string;
  location: string;
  startDate: string;
  endDate: string;
  achievements: string[];
};

export type EducationEntry = {
  degree: string;
  institution: string;
  location: string;
  startDate: string;
  endDate: string;
};

export type TailoredCvDraft = {
  basics: BasicsInfo;
  experience: ExperienceEntry[];
  education: EducationEntry[];
  skills: string[];
};
