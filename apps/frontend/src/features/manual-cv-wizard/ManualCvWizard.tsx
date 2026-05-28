"use client";

import { useEffect, useRef } from "react";
import { Icon } from "@/components/ui/Icon";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { AtsLivePreview } from "@/features/tailored-cv-builder/AtsLivePreview";
import "@/features/tailored-cv-builder/builder.css";
import { useManualCvWizardStore } from "./store";
import { EMPTY_MANUAL_DRAFT, MANUAL_STEP_LABELS, MANUAL_WIZARD_STEPS, type ManualWizardStep } from "./types";
import { useManualDraftPersistence } from "./useDraftPersistence";
import { draftToPreviewDraft } from "./mapDraft";
import { BasicsStep } from "./steps/BasicsStep";
import { SummaryStep } from "./steps/SummaryStep";
import { ExperienceStep } from "./steps/ExperienceStep";
import { EducationStep } from "./steps/EducationStep";
import { SkillsStyleStep } from "./steps/SkillsStyleStep";

function StepNav({
  current,
  onStepClick,
}: {
  current: ManualWizardStep;
  onStepClick: (s: ManualWizardStep) => void;
}) {
  const idx = MANUAL_WIZARD_STEPS.indexOf(current);
  return (
    <nav className="flex flex-wrap gap-2 mb-4" aria-label="CV wizard steps">
      {MANUAL_WIZARD_STEPS.map((s, i) => {
        const done = i < idx;
        const active = s === current;
        return (
          <button
            key={s}
            type="button"
            onClick={() => onStepClick(s)}
            className="text-xs px-3 py-1.5 rounded-full font-medium"
            style={{
              background: active ? "var(--green-700)" : done ? "var(--green-100)" : "var(--bg-2)",
              color: active ? "#fff" : "var(--ink-2)",
              border: active ? "none" : "1px solid var(--line-2)",
            }}
          >
            {i + 1}. {MANUAL_STEP_LABELS[s]}
          </button>
        );
      })}
    </nav>
  );
}

export function ManualCvWizard({
  token,
  onCvCreated,
}: {
  token: string;
  onCvCreated?: () => void;
}) {
  const step = useManualCvWizardStore((s) => s.step);
  const draft = useManualCvWizardStore((s) => s.draft);
  const setStep = useManualCvWizardStore((s) => s.setStep);
  const setDraft = useManualCvWizardStore((s) => s.setDraft);
  const resetDraft = useManualCvWizardStore((s) => s.resetDraft);
  const { initialDraft, initialStep, queueWrite, clearDraft } = useManualDraftPersistence();
  const isDesktop = useMediaQuery("(min-width: 1024px)");
  const seeded = useRef(false);

  useEffect(() => {
    if (seeded.current || !initialDraft) return;
    seeded.current = true;
    setDraft(initialDraft);
    if (initialStep && MANUAL_WIZARD_STEPS.includes(initialStep as ManualWizardStep)) {
      setStep(initialStep as ManualWizardStep);
    }
  }, [initialDraft, initialStep, setDraft, setStep]);

  useEffect(() => {
    queueWrite(step, draft);
  }, [step, draft, queueWrite]);

  const previewDraft = draftToPreviewDraft(draft);

  return (
    <div className="w-full">
      <div className="mb-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div>
          <div className="eyebrow mb-1">CV generator</div>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            Build your CV from scratch — progress saves automatically.
          </p>
        </div>
        <button
          type="button"
          className="btn btn-ghost btn-sm shrink-0"
          onClick={() => {
            resetDraft();
            setDraft(EMPTY_MANUAL_DRAFT);
            clearDraft();
          }}
        >
          Start fresh
        </button>
      </div>

      <StepNav current={step} onStepClick={setStep} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6 lg:items-stretch">
        <div className="min-w-0">
          {step === "basics" ? <BasicsStep /> : null}
          {step === "summary" ? <SummaryStep token={token} /> : null}
          {step === "experience" ? <ExperienceStep token={token} /> : null}
          {step === "education" ? <EducationStep /> : null}
          {step === "skillsStyle" ? (
            <SkillsStyleStep token={token} onExported={onCvCreated} />
          ) : null}
        </div>
        {isDesktop ? (
          <div
            className="rounded-lg p-4 lg:sticky lg:top-4 max-h-[calc(100vh-160px)] overflow-auto"
            style={{ background: "var(--bg-2)", border: "1px solid var(--line)" }}
          >
            <div className="flex items-center gap-2 mb-3">
              <Icon name="eye" size={14} />
              <span className="eyebrow">Live preview</span>
            </div>
            <AtsLivePreview draft={previewDraft} />
          </div>
        ) : null}
      </div>
    </div>
  );
}
