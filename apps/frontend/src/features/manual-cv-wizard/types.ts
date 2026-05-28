export const MANUAL_WIZARD_STEPS = [
  "basics",
  "summary",
  "experience",
  "education",
  "skillsStyle",
] as const;

export type ManualWizardStep = (typeof MANUAL_WIZARD_STEPS)[number];

export const MANUAL_STEP_LABELS: Record<ManualWizardStep, string> = {
  basics: "Basics",
  summary: "Career summary",
  experience: "Experience",
  education: "Education",
  skillsStyle: "Skills & style",
};

export type ManualBasics = {
  fullName: string;
  headline: string;
  email: string;
  phone: string;
  location: string;
};

export type ManualExperienceEntry = {
  title: string;
  company: string;
  location: string;
  startDate: string;
  endDate: string;
  isPresent: boolean;
  achievements: string[];
};

export type ManualEducationEntry = {
  degree: string;
  institution: string;
  location: string;
  startDate: string;
  endDate: string;
  gpa: string;
};

export type CvTemplate = "modern" | "classic" | "compact";

export type ManualStyleOptions = {
  template: CvTemplate;
  accentColor: string;
  showSummary: boolean;
};

export type ManualCvDraft = {
  basics: ManualBasics;
  summary: string;
  summaryStrengths: string[];
  experience: ManualExperienceEntry[];
  education: ManualEducationEntry[];
  skills: string[];
  style: ManualStyleOptions;
};

export const DEFAULT_MANUAL_STYLE: ManualStyleOptions = {
  template: "modern",
  accentColor: "#0E5C3A",
  showSummary: true,
};

export const EMPTY_MANUAL_DRAFT: ManualCvDraft = {
  basics: {
    fullName: "",
    headline: "",
    email: "",
    phone: "",
    location: "",
  },
  summary: "",
  summaryStrengths: ["", "", ""],
  experience: [
    {
      title: "",
      company: "",
      location: "",
      startDate: "",
      endDate: "",
      isPresent: false,
      achievements: [""],
    },
  ],
  education: [
    {
      degree: "",
      institution: "",
      location: "",
      startDate: "",
      endDate: "",
      gpa: "",
    },
  ],
  skills: [],
  style: DEFAULT_MANUAL_STYLE,
};
