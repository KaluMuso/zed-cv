"use client";

import { useState } from "react";
import { Icon } from "@/components/ui/Icon";
import { cv as cvApi } from "@/lib/api";
import { BuilderStepShell } from "@/features/tailored-cv-builder/BuilderStepShell";
import { builderFieldStyle, builderInputClass, builderLabelClass } from "@/features/tailored-cv-builder/builderFormStyles";
import { useManualCvWizardStore } from "../store";

function achievementsToText(items: string[]): string {
  return items.filter(Boolean).join("\n");
}

function textToAchievements(text: string): string[] {
  const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
  return lines.length > 0 ? lines : [""];
}

export function ExperienceStep({ token }: { token: string }) {
  const experience = useManualCvWizardStore((s) => s.draft.experience);
  const updateExperience = useManualCvWizardStore((s) => s.updateExperience);
  const addExperience = useManualCvWizardStore((s) => s.addExperience);
  const removeExperience = useManualCvWizardStore((s) => s.removeExperience);
  const setStep = useManualCvWizardStore((s) => s.setStep);
  const [loadingIndex, setLoadingIndex] = useState<number | null>(null);

  const suggestBullets = async (index: number) => {
    const role = experience[index];
    if (!role.title.trim() || !role.company.trim()) return;
    setLoadingIndex(index);
    try {
      const res = await cvApi.suggestBullets(token, {
        title: role.title,
        company: role.company,
        context: role.location,
      });
      updateExperience(index, { achievements: res.bullets });
    } catch {
      /* user can type manually */
    } finally {
      setLoadingIndex(null);
    }
  };

  return (
    <BuilderStepShell
      title="Work experience"
      description="Add roles with measurable achievements. Use AI to draft bullet points from title and company."
      onBack={() => setStep("summary")}
      backLabel="Summary"
      onNext={() => setStep("education")}
      nextLabel="Next: Education"
    >
      <div className="flex-1 overflow-y-auto space-y-4 pr-1 max-h-[min(60vh,520px)]">
        {experience.map((role, index) => (
          <div key={index} className="rounded-lg p-4 space-y-3" style={{ border: "1px solid var(--line)", background: "var(--bg-2)" }}>
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--muted)" }}>Role {index + 1}</span>
              {experience.length > 1 ? (
                <button type="button" className="text-xs hover:underline" style={{ color: "var(--danger)" }} onClick={() => removeExperience(index)}>Remove</button>
              ) : null}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="sm:col-span-2">
                <label className={builderLabelClass}>Job title</label>
                <input value={role.title} onChange={(e) => updateExperience(index, { title: e.target.value })} className={builderInputClass} style={builderFieldStyle} />
              </div>
              <div>
                <label className={builderLabelClass}>Company</label>
                <input value={role.company} onChange={(e) => updateExperience(index, { company: e.target.value })} className={builderInputClass} style={builderFieldStyle} />
              </div>
              <div>
                <label className={builderLabelClass}>Location</label>
                <input value={role.location} onChange={(e) => updateExperience(index, { location: e.target.value })} className={builderInputClass} style={builderFieldStyle} />
              </div>
              <div>
                <label className={builderLabelClass}>Start date</label>
                <input value={role.startDate} onChange={(e) => updateExperience(index, { startDate: e.target.value })} placeholder="Jan 2020" className={builderInputClass} style={builderFieldStyle} />
              </div>
              <div>
                <label className={builderLabelClass}>End date</label>
                <input value={role.isPresent ? "" : role.endDate} disabled={role.isPresent} onChange={(e) => updateExperience(index, { endDate: e.target.value })} placeholder="Dec 2023" className={builderInputClass} style={builderFieldStyle} />
                <label className="flex items-center gap-2 text-xs mt-2 cursor-pointer">
                  <input type="checkbox" checked={role.isPresent} onChange={(e) => updateExperience(index, { isPresent: e.target.checked, endDate: e.target.checked ? "" : role.endDate })} />
                  Present
                </label>
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between gap-2 mb-1">
                <label className={builderLabelClass}>Achievements</label>
                <button type="button" className="btn btn-ghost btn-sm" disabled={loadingIndex === index} onClick={() => void suggestBullets(index)}>
                  <Icon name="zap" size={12} />
                  {loadingIndex === index ? "Suggesting…" : "Suggest bullets"}
                </button>
              </div>
              <textarea
                value={achievementsToText(role.achievements)}
                onChange={(e) => updateExperience(index, { achievements: textToAchievements(e.target.value) })}
                rows={4}
                className="w-full p-3 rounded-md text-sm resize-y"
                style={{ ...builderFieldStyle, lineHeight: 1.55 }}
              />
            </div>
          </div>
        ))}
      </div>
      <button type="button" className="btn btn-ghost btn-sm w-fit" onClick={addExperience}>
        <Icon name="plus" size={14} /> Add another role
      </button>
    </BuilderStepShell>
  );
}
