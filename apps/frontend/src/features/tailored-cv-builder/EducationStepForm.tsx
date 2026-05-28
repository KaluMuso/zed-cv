"use client";

import { Icon } from "@/components/ui/Icon";
import { BuilderStepShell } from "./BuilderStepShell";
import {
  builderFieldStyle,
  builderInputClass,
  builderLabelClass,
} from "./builderFormStyles";
import { useTailoredCvBuilderStore } from "./store";

export function EducationStepForm() {
  const education = useTailoredCvBuilderStore((s) => s.draft.education);
  const updateEducation = useTailoredCvBuilderStore((s) => s.updateEducation);
  const addEducation = useTailoredCvBuilderStore((s) => s.addEducation);
  const removeEducation = useTailoredCvBuilderStore((s) => s.removeEducation);
  const setStep = useTailoredCvBuilderStore((s) => s.setStep);

  return (
    <BuilderStepShell
      title="Education"
      description="Degrees, diplomas, and professional certifications."
      onBack={() => setStep("experience")}
      backLabel="Experience"
      onNext={() => setStep("skills")}
      nextLabel="Next: Skills"
    >
      <div className="flex-1 overflow-y-auto space-y-4 pr-1 -mr-1 max-h-[min(60vh,520px)]">
        {education.map((edu, index) => (
          <div
            key={index}
            className="rounded-lg p-4 space-y-3"
            style={{ border: "1px solid var(--line)", background: "var(--bg-2)" }}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
                Entry {index + 1}
              </span>
              {education.length > 1 ? (
                <button
                  type="button"
                  className="text-xs hover:underline"
                  style={{ color: "var(--danger)" }}
                  onClick={() => removeEducation(index)}
                >
                  Remove
                </button>
              ) : null}
            </div>
            <div>
              <label className={builderLabelClass} style={{ color: "var(--ink-2)" }}>
                Degree / qualification
              </label>
              <input
                value={edu.degree}
                onChange={(e) => updateEducation(index, { degree: e.target.value })}
                className={builderInputClass}
                style={builderFieldStyle}
                placeholder="e.g. BAcc, ICAZ"
              />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className={builderLabelClass} style={{ color: "var(--ink-2)" }}>
                  Institution
                </label>
                <input
                  value={edu.institution}
                  onChange={(e) => updateEducation(index, { institution: e.target.value })}
                  className={builderInputClass}
                  style={builderFieldStyle}
                />
              </div>
              <div>
                <label className={builderLabelClass} style={{ color: "var(--ink-2)" }}>
                  Location
                </label>
                <input
                  value={edu.location}
                  onChange={(e) => updateEducation(index, { location: e.target.value })}
                  className={builderInputClass}
                  style={builderFieldStyle}
                />
              </div>
              <div>
                <label className={builderLabelClass} style={{ color: "var(--ink-2)" }}>
                  Start year
                </label>
                <input
                  value={edu.startDate}
                  onChange={(e) => updateEducation(index, { startDate: e.target.value })}
                  className={builderInputClass}
                  style={builderFieldStyle}
                />
              </div>
              <div>
                <label className={builderLabelClass} style={{ color: "var(--ink-2)" }}>
                  End year
                </label>
                <input
                  value={edu.endDate}
                  onChange={(e) => updateEducation(index, { endDate: e.target.value })}
                  className={builderInputClass}
                  style={builderFieldStyle}
                />
              </div>
              <div>
                <label className={builderLabelClass} style={{ color: "var(--ink-2)" }}>
                  GPA (optional)
                </label>
                <input
                  value={edu.gpa}
                  onChange={(e) => updateEducation(index, { gpa: e.target.value })}
                  className={builderInputClass}
                  style={builderFieldStyle}
                  placeholder="3.8 / Distinction"
                />
              </div>
            </div>
          </div>
        ))}
      </div>
      <button type="button" className="btn btn-ghost btn-sm w-fit" onClick={addEducation}>
        <Icon name="plus" size={14} /> Add education
      </button>
    </BuilderStepShell>
  );
}
