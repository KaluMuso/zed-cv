import { create } from "zustand";
import type { ManualCvDraft, ManualExperienceEntry, ManualEducationEntry, ManualWizardStep } from "./types";
import { EMPTY_MANUAL_DRAFT } from "./types";

export function emptyExperience(): ManualExperienceEntry {
  return {
    title: "",
    company: "",
    location: "",
    startDate: "",
    endDate: "",
    isPresent: false,
    achievements: [""],
  };
}

export function emptyEducation(): ManualEducationEntry {
  return {
    degree: "",
    institution: "",
    location: "",
    startDate: "",
    endDate: "",
    gpa: "",
  };
}

type ManualCvWizardState = {
  step: ManualWizardStep;
  draft: ManualCvDraft;
  setStep: (step: ManualWizardStep) => void;
  setDraft: (draft: ManualCvDraft) => void;
  updateBasics: (patch: Partial<ManualCvDraft["basics"]>) => void;
  setSummary: (summary: string) => void;
  setSummaryStrength: (index: number, value: string) => void;
  setExperience: (entries: ManualExperienceEntry[]) => void;
  updateExperience: (index: number, patch: Partial<ManualExperienceEntry>) => void;
  addExperience: () => void;
  removeExperience: (index: number) => void;
  setEducation: (entries: ManualEducationEntry[]) => void;
  updateEducation: (index: number, patch: Partial<ManualEducationEntry>) => void;
  addEducation: () => void;
  removeEducation: (index: number) => void;
  setSkills: (skills: string[]) => void;
  updateStyle: (patch: Partial<ManualCvDraft["style"]>) => void;
  resetDraft: () => void;
};

export const useManualCvWizardStore = create<ManualCvWizardState>((set) => ({
  step: "basics",
  draft: EMPTY_MANUAL_DRAFT,
  setStep: (step) => set({ step }),
  setDraft: (draft) => set({ draft }),
  updateBasics: (patch) =>
    set((s) => ({ draft: { ...s.draft, basics: { ...s.draft.basics, ...patch } } })),
  setSummary: (summary) => set((s) => ({ draft: { ...s.draft, summary } })),
  setSummaryStrength: (index, value) =>
    set((s) => {
      const next = [...s.draft.summaryStrengths];
      next[index] = value;
      return { draft: { ...s.draft, summaryStrengths: next } };
    }),
  setExperience: (entries) => set((s) => ({ draft: { ...s.draft, experience: entries } })),
  updateExperience: (index, patch) =>
    set((s) => ({
      draft: {
        ...s.draft,
        experience: s.draft.experience.map((e, i) => (i === index ? { ...e, ...patch } : e)),
      },
    })),
  addExperience: () =>
    set((s) => ({
      draft: { ...s.draft, experience: [...s.draft.experience, emptyExperience()] },
    })),
  removeExperience: (index) =>
    set((s) => ({
      draft: {
        ...s.draft,
        experience: s.draft.experience.filter((_, i) => i !== index),
      },
    })),
  setEducation: (entries) => set((s) => ({ draft: { ...s.draft, education: entries } })),
  updateEducation: (index, patch) =>
    set((s) => ({
      draft: {
        ...s.draft,
        education: s.draft.education.map((e, i) => (i === index ? { ...e, ...patch } : e)),
      },
    })),
  addEducation: () =>
    set((s) => ({
      draft: { ...s.draft, education: [...s.draft.education, emptyEducation()] },
    })),
  removeEducation: (index) =>
    set((s) => ({
      draft: {
        ...s.draft,
        education: s.draft.education.filter((_, i) => i !== index),
      },
    })),
  setSkills: (skills) => set((s) => ({ draft: { ...s.draft, skills } })),
  updateStyle: (patch) =>
    set((s) => ({ draft: { ...s.draft, style: { ...s.draft.style, ...patch } } })),
  resetDraft: () => set({ draft: EMPTY_MANUAL_DRAFT, step: "basics" }),
}));
