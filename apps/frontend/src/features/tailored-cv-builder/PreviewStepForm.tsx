"use client";

import { Icon } from "@/components/ui/Icon";
import { BuilderStepShell } from "./BuilderStepShell";
import { printTailoredCv } from "./printTailoredCv";
import { useTailoredCvBuilderStore } from "./store";

export function PreviewStepForm({ onOpenPreview }: { onOpenPreview?: () => void }) {
  const setStep = useTailoredCvBuilderStore((s) => s.setStep);
  const draft = useTailoredCvBuilderStore((s) => s.draft);

  const copyBasics = async () => {
    const text = [
      draft.basics.fullName,
      draft.basics.headline,
      [draft.basics.phone, draft.basics.email, draft.basics.location].filter(Boolean).join(" · "),
      "",
      draft.basics.summary,
    ]
      .filter(Boolean)
      .join("\n");
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      /* clipboard unavailable */
    }
  };

  return (
    <BuilderStepShell
      title="Review & export"
      description="Your CV and cover letter are ready to review. Use the preview pane to check formatting before you apply."
      onBack={() => setStep("coverLetter")}
      backLabel="Cover letter"
    >
      <ul className="text-sm space-y-2 list-disc pl-5" style={{ color: "var(--ink-2)" }}>
        <li>{draft.experience.length} work experience entries</li>
        <li>{draft.education.length} education entries</li>
        <li>{draft.skills.length} skills listed</li>
      </ul>
      <div className="flex flex-wrap gap-2 pt-2">
        {onOpenPreview ? (
          <button type="button" className="btn btn-primary btn-sm" onClick={onOpenPreview}>
            <Icon name="eye" size={14} /> Open preview
          </button>
        ) : null}
        <button
          type="button"
          className="btn btn-outline btn-sm"
          onClick={() => printTailoredCv(`cv-${draft.basics.fullName.trim() || "tailored"}`)}
        >
          <Icon name="download" size={14} /> Download PDF
        </button>
        <button type="button" className="btn btn-outline btn-sm" onClick={() => void copyBasics()}>
          Copy header block
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => setStep("basics")}>
          Edit from start
        </button>
      </div>
      <p className="text-xs mt-4" style={{ color: "var(--muted)" }}>
        Download PDF opens your browser print dialog — choose &quot;Save as PDF&quot;. Layout matches
        the live preview on the right.
      </p>
    </BuilderStepShell>
  );
}
