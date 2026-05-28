"use client";

import { Icon } from "@/components/ui/Icon";
import { BuilderStepShell } from "@/features/tailored-cv-builder/BuilderStepShell";
import { builderFieldStyle, builderInputClass, builderLabelClass } from "@/features/tailored-cv-builder/builderFormStyles";
import { useManualCvWizardStore } from "../store";

export function EducationStep() {
  const education = useManualCvWizardStore((s) => s.draft.education);
  const updateEducation = useManualCvWizardStore((s) => s.updateEducation);
  const addEducation = useManualCvWizardStore((s) => s.addEducation);
  const removeEducation = useManualCvWizardStore((s) => s.removeEducation);
  const setStep = useManualCvWizardStore((s) => s.setStep);

  return (
    <BuilderStepShell
      title="Education"
      description="Degrees, diplomas, and certifications."
      onBack={() => setStep("experience")}
      backLabel="Experience"
      onNext={() => setStep("skillsStyle")}
      nextLabel="Next: Skills & style"
    >
      <div className="flex-1 overflow-y-auto space-y-4 pr-1 max-h-[min(60vh,520px)]">
        {education.map((edu, index) => (
          <div key={index} className="rounded-lg p-4 space-y-3" style={{ border: "1px solid var(--line)", background: "var(--bg-2)" }}>
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--muted)" }}>Entry {index + 1}</span>
              {education.length > 1 ? (
                <button type="button" className="text-xs hover:underline" style={{ color: "var(--danger)" }} onClick={() => removeEducation(index)}>Remove</button>
              ) : null}
            </div>
            <div>
              <label className={builderLabelClass}>Qualification</label>
              <input value={edu.degree} onChange={(e) => updateEducation(index, { degree: e.target.value })} className={builderInputClass} style={builderFieldStyle} placeholder="BAcc, Grade 12" />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className={builderLabelClass}>Institution</label>
                <input value={edu.institution} onChange={(e) => updateEducation(index, { institution: e.target.value })} className={builderInputClass} style={builderFieldStyle} />
              </div>
              <div>
                <label className={builderLabelClass}>Location</label>
                <input value={edu.location} onChange={(e) => updateEducation(index, { location: e.target.value })} className={builderInputClass} style={builderFieldStyle} />
              </div>
              <div>
                <label className={builderLabelClass}>Start</label>
                <input value={edu.startDate} onChange={(e) => updateEducation(index, { startDate: e.target.value })} className={builderInputClass} style={builderFieldStyle} />
              </div>
              <div>
                <label className={builderLabelClass}>End</label>
                <input value={edu.endDate} onChange={(e) => updateEducation(index, { endDate: e.target.value })} className={builderInputClass} style={builderFieldStyle} />
              </div>
              <div>
                <label className={builderLabelClass}>GPA (optional)</label>
                <input value={edu.gpa} onChange={(e) => updateEducation(index, { gpa: e.target.value })} className={builderInputClass} style={builderFieldStyle} placeholder="3.8 / Distinction" />
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
