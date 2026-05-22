"use client";

import { Icon } from "@/components/ui/Icon";
import { BUILDER_STEP_LABELS, BUILDER_STEPS, type BuilderStep } from "./types";
import { useTailoredCvBuilderStore } from "./store";

export function StepPlaceholder({ step }: { step: BuilderStep }) {
  const setStep = useTailoredCvBuilderStore((s) => s.setStep);
  const index = BUILDER_STEPS.indexOf(step);
  const prev = index > 0 ? BUILDER_STEPS[index - 1] : null;
  const next = index < BUILDER_STEPS.length - 1 ? BUILDER_STEPS[index + 1] : null;

  return (
    <div
      className="flex flex-col h-full rounded-lg p-6 justify-center items-center text-center gap-4"
      style={{
        background: "var(--surface)",
        border: "1px solid var(--line-2)",
        minHeight: 360,
      }}
    >
      <p className="eyebrow">{BUILDER_STEP_LABELS[step]}</p>
      <p className="text-sm max-w-sm" style={{ color: "var(--muted)" }}>
        This step&apos;s editor is next. Use the preview on the right — it still reflects your basics
        and sample sections.
      </p>
      <div className="flex gap-2 flex-wrap justify-center">
        {prev ? (
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setStep(prev)}>
            <Icon name="arrowLeft" size={12} />
            {BUILDER_STEP_LABELS[prev]}
          </button>
        ) : null}
        {next ? (
          <button type="button" className="btn btn-primary btn-sm" onClick={() => setStep(next)}>
            {BUILDER_STEP_LABELS[next]}
            <Icon name="arrowRight" size={12} />
          </button>
        ) : null}
      </div>
    </div>
  );
}
