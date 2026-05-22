import { create } from "zustand";
import type { BuilderStep, TailoredCvDraft } from "./types";

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
};

type TailoredCvBuilderState = {
  step: BuilderStep;
  draft: TailoredCvDraft;
  setStep: (step: BuilderStep) => void;
  updateBasics: (patch: Partial<TailoredCvDraft["basics"]>) => void;
  resetDraft: () => void;
};

export const useTailoredCvBuilderStore = create<TailoredCvBuilderState>((set) => ({
  step: "basics",
  draft: DEFAULT_DRAFT,
  setStep: (step) => set({ step }),
  updateBasics: (patch) =>
    set((state) => ({
      draft: {
        ...state.draft,
        basics: { ...state.draft.basics, ...patch },
      },
    })),
  resetDraft: () => set({ draft: DEFAULT_DRAFT, step: "basics" }),
}));
