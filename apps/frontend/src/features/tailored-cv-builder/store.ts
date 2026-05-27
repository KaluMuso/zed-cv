import { create } from "zustand";
import type {
  BuilderStep,
  CvStyleOptions,
  EducationEntry,
  ExperienceEntry,
  TailoredCvDraft,
} from "./types";

export const DEFAULT_STYLE: CvStyleOptions = {
  density: "standard",
  showSummary: true,
};

export const DEFAULT_DRAFT: TailoredCvDraft = {
  basics: {
    fullName: "Chanda Banda",
    headline: "Chartered Accountant · Financial Reporting",
    email: "chanda.banda@email.com",
    phone: "+260971234567",
    location: "Lusaka, Zambia",
    summary:
      "ICAZ-qualified accountant with 8+ years in banking and audit. Experienced in IFRS reporting, month-end close, and stakeholder management across multi-branch operations.",
  },
  experience: [
    {
      title: "Senior Accountant",
      company: "ZANACO",
      location: "Lusaka",
      startDate: "Jan 2019",
      endDate: "Present",
      achievements: [
        "Led month-end close for 12 branches, reducing reporting cycle by 18%.",
        "Prepared IFRS-aligned financial statements reviewed by external auditors with zero material findings.",
        "Mentored a team of 4 junior accountants on reconciliation and compliance workflows.",
      ],
    },
    {
      title: "Accountant",
      company: "Grant Thornton Zambia",
      location: "Lusaka",
      startDate: "Jun 2015",
      endDate: "Dec 2018",
      achievements: [
        "Supported audit engagements for clients in financial services and mining sectors.",
        "Improved working-paper quality checks, cutting review rework by 25%.",
      ],
    },
  ],
  education: [
    {
      degree: "Bachelor of Accountancy (BAcc)",
      institution: "University of Zambia",
      location: "Lusaka",
      startDate: "2011",
      endDate: "2014",
      gpa: "",
    },
  ],
  skills: [
    "IFRS",
    "Financial Reporting",
    "Month-end Close",
    "SAP",
    "Excel",
    "Tax Compliance",
    "Stakeholder Management",
  ],
  style: DEFAULT_STYLE,
};

export function emptyExperience(): ExperienceEntry {
  return {
    title: "",
    company: "",
    location: "",
    startDate: "",
    endDate: "",
    achievements: [""],
  };
}

export function emptyEducation(): EducationEntry {
  return {
    degree: "",
    institution: "",
    location: "",
    startDate: "",
    endDate: "",
    gpa: "",
  };
}

type TailoredCvBuilderState = {
  step: BuilderStep;
  draft: TailoredCvDraft;
  hydratedFromProfile: boolean;
  setStep: (step: BuilderStep) => void;
  setDraft: (draft: TailoredCvDraft, options?: { fromProfile?: boolean }) => void;
  updateBasics: (patch: Partial<TailoredCvDraft["basics"]>) => void;
  setExperience: (entries: ExperienceEntry[]) => void;
  updateExperience: (index: number, patch: Partial<ExperienceEntry>) => void;
  addExperience: () => void;
  removeExperience: (index: number) => void;
  setEducation: (entries: EducationEntry[]) => void;
  updateEducation: (index: number, patch: Partial<EducationEntry>) => void;
  addEducation: () => void;
  removeEducation: (index: number) => void;
  setSkills: (skills: string[]) => void;
  updateStyle: (patch: Partial<CvStyleOptions>) => void;
  resetDraft: () => void;
};

export const useTailoredCvBuilderStore = create<TailoredCvBuilderState>((set) => ({
  step: "basics",
  draft: DEFAULT_DRAFT,
  hydratedFromProfile: false,
  setStep: (step) => set({ step }),
  setDraft: (draft, options) =>
    set({
      draft,
      hydratedFromProfile: options?.fromProfile ?? false,
    }),
  updateBasics: (patch) =>
    set((state) => ({
      draft: { ...state.draft, basics: { ...state.draft.basics, ...patch } },
    })),
  setExperience: (entries) =>
    set((state) => ({ draft: { ...state.draft, experience: entries } })),
  updateExperience: (index, patch) =>
    set((state) => ({
      draft: {
        ...state.draft,
        experience: state.draft.experience.map((e, i) =>
          i === index ? { ...e, ...patch } : e,
        ),
      },
    })),
  addExperience: () =>
    set((state) => ({
      draft: {
        ...state.draft,
        experience: [...state.draft.experience, emptyExperience()],
      },
    })),
  removeExperience: (index) =>
    set((state) => ({
      draft: {
        ...state.draft,
        experience: state.draft.experience.filter((_, i) => i !== index),
      },
    })),
  setEducation: (entries) =>
    set((state) => ({ draft: { ...state.draft, education: entries } })),
  updateEducation: (index, patch) =>
    set((state) => ({
      draft: {
        ...state.draft,
        education: state.draft.education.map((e, i) =>
          i === index ? { ...e, ...patch } : e,
        ),
      },
    })),
  addEducation: () =>
    set((state) => ({
      draft: {
        ...state.draft,
        education: [...state.draft.education, emptyEducation()],
      },
    })),
  removeEducation: (index) =>
    set((state) => ({
      draft: {
        ...state.draft,
        education: state.draft.education.filter((_, i) => i !== index),
      },
    })),
  setSkills: (skills) =>
    set((state) => ({ draft: { ...state.draft, skills } })),
  updateStyle: (patch) =>
    set((state) => ({
      draft: { ...state.draft, style: { ...state.draft.style, ...patch } },
    })),
  resetDraft: () =>
    set({ draft: DEFAULT_DRAFT, step: "basics", hydratedFromProfile: false }),
}));
