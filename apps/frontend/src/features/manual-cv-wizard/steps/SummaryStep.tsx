"use client";

import { useState } from "react";
import { Icon } from "@/components/ui/Icon";
import { cv as cvApi } from "@/lib/api";
import { BuilderStepShell } from "@/features/tailored-cv-builder/BuilderStepShell";
import { builderFieldStyle, builderInputClass, builderLabelClass } from "@/features/tailored-cv-builder/builderFormStyles";
import { useManualCvWizardStore } from "../store";

export function SummaryStep({ token }: { token: string }) {
  const summary = useManualCvWizardStore((s) => s.draft.summary);
  const strengths = useManualCvWizardStore((s) => s.draft.summaryStrengths);
  const basics = useManualCvWizardStore((s) => s.draft.basics);
  const setSummary = useManualCvWizardStore((s) => s.setSummary);
  const setSummaryStrength = useManualCvWizardStore((s) => s.setSummaryStrength);
  const setStep = useManualCvWizardStore((s) => s.setStep);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateSummary = async () => {
    const filled = strengths.map((s) => s.trim()).filter(Boolean);
    if (filled.length === 0) {
      setError("Add at least one strength first.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await cvApi.suggestSummary(token, {
        strengths: filled.slice(0, 3),
        headline: basics.headline,
        full_name: basics.fullName,
      });
      setSummary(res.summary);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not generate summary");
    } finally {
      setLoading(false);
    }
  };

  return (
    <BuilderStepShell
      title="Career summary"
      description="Write 2–4 sentences about your professional profile. AI can draft from your top strengths."
      onBack={() => setStep("basics")}
      backLabel="Basics"
      onNext={() => setStep("experience")}
      nextLabel="Next: Experience"
    >
      <div className="space-y-3">
        <p className="text-sm" style={{ color: "var(--ink-2)" }}>Top 3 strengths (for AI assist)</p>
        {strengths.map((s, i) => (
          <input
            key={i}
            value={s}
            onChange={(e) => setSummaryStrength(i, e.target.value)}
            placeholder={`Strength ${i + 1} — e.g. IFRS reporting`}
            className={builderInputClass}
            style={builderFieldStyle}
          />
        ))}
        <button type="button" className="btn btn-outline btn-sm" disabled={loading} onClick={() => void generateSummary()}>
          <Icon name="zap" size={14} />
          {loading ? "Generating…" : "Generate summary with AI"}
        </button>
        {error ? <p className="text-sm" style={{ color: "var(--danger)" }}>{error}</p> : null}
      </div>
      <div>
        <label className={builderLabelClass} htmlFor="m-summary">Professional summary</label>
        <textarea
          id="m-summary"
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          rows={6}
          className="w-full p-3 rounded-md text-sm resize-y"
          style={{ ...builderFieldStyle, lineHeight: 1.55 }}
          placeholder="2–4 sentences recruiters scan first."
        />
      </div>
    </BuilderStepShell>
  );
}
