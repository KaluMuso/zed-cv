"use client";

import { useEffect, useRef, useState } from "react";
import { Icon } from "@/components/ui/Icon";
import { cv as cvApi } from "@/lib/api";
import { BuilderStepShell } from "@/features/tailored-cv-builder/BuilderStepShell";
import { builderFieldStyle, builderInputClass, builderLabelClass } from "@/features/tailored-cv-builder/builderFormStyles";
import type { CvTemplate } from "../types";
import { useManualCvWizardStore } from "../store";
import { draftToBuildPayload } from "../mapDraft";

const ACCENT_PRESETS = [
  { label: "Green (default)", value: "#0E5C3A" },
  { label: "Copper", value: "#B87333" },
  { label: "Navy", value: "#1E3A5F" },
  { label: "Charcoal", value: "#2D2D2D" },
];

const TEMPLATES: { id: CvTemplate; label: string; hint: string }[] = [
  { id: "modern", label: "Modern", hint: "Sans-serif with accent sidebar headings" },
  { id: "classic", label: "Classic", hint: "Serif typography, traditional layout" },
  { id: "compact", label: "Compact", hint: "Tighter spacing for one-page CVs" },
];

export function SkillsStyleStep({
  token,
  onExported,
}: {
  token: string;
  onExported?: () => void;
}) {
  const skills = useManualCvWizardStore((s) => s.draft.skills);
  const style = useManualCvWizardStore((s) => s.draft.style);
  const draft = useManualCvWizardStore((s) => s.draft);
  const setSkills = useManualCvWizardStore((s) => s.setSkills);
  const updateStyle = useManualCvWizardStore((s) => s.updateStyle);
  const setStep = useManualCvWizardStore((s) => s.setStep);
  const [draftSkill, setDraftSkill] = useState("");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [renderMs, setRenderMs] = useState<number | null>(null);
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const q = draftSkill.trim();
    if (q.length < 2) {
      setSuggestions([]);
      return;
    }
    if (debounce.current) clearTimeout(debounce.current);
    debounce.current = setTimeout(() => {
      cvApi
        .suggestSkills(token, q)
        .then((res) => setSuggestions(res.skills.map((s) => s.name)))
        .catch(() => setSuggestions([]));
    }, 250);
    return () => {
      if (debounce.current) clearTimeout(debounce.current);
    };
  }, [draftSkill, token]);

  const addSkill = (name: string) => {
    const next = name.trim();
    if (!next) return;
    if (skills.some((s) => s.toLowerCase() === next.toLowerCase())) return;
    setSkills([...skills, next]);
    setDraftSkill("");
    setSuggestions([]);
  };

  const downloadPdf = async () => {
    if (!draft.basics.fullName.trim()) {
      setDownloadError("Add your full name on the Basics step first.");
      return;
    }
    setDownloading(true);
    setDownloadError(null);
    try {
      const res = await cvApi.buildFromScratch(token, draftToBuildPayload(draft));
      setRenderMs(res.render_time_ms);
      window.open(res.pdf_url, "_blank", "noopener,noreferrer");
      onExported?.();
    } catch (e) {
      setDownloadError(e instanceof Error ? e.message : "PDF export failed");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <BuilderStepShell
      title="Skills & style"
      description="Tag skills recruiters search for, pick a layout, then download your PDF."
      onBack={() => setStep("education")}
      backLabel="Education"
    >
      <div>
        <label className={builderLabelClass}>Skills</label>
        <div className="flex gap-2 relative">
          <input
            value={draftSkill}
            onChange={(e) => setDraftSkill(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addSkill(draftSkill);
              }
            }}
            className={builderInputClass}
            style={builderFieldStyle}
            placeholder="Start typing — e.g. Excel"
          />
          <button type="button" className="btn btn-primary shrink-0" onClick={() => addSkill(draftSkill)}>Add</button>
          {suggestions.length > 0 ? (
            <ul className="absolute z-20 top-full left-0 right-0 mt-1 rounded-md border shadow-lg max-h-40 overflow-auto text-sm" style={{ background: "var(--surface)", borderColor: "var(--line-2)" }}>
              {suggestions.map((s) => (
                <li key={s}>
                  <button type="button" className="w-full text-left px-3 py-2 hover:bg-[var(--bg-2)]" onClick={() => addSkill(s)}>
                    {s}
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
        {skills.length > 0 ? (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {skills.map((skill) => (
              <span key={skill} className="tag tag-green inline-flex items-center gap-1">
                {skill}
                <button type="button" onClick={() => setSkills(skills.filter((s) => s !== skill))} aria-label={`Remove ${skill}`}>
                  <Icon name="x" size={10} />
                </button>
              </span>
            ))}
          </div>
        ) : (
          <p className="text-sm mt-2" style={{ color: "var(--muted)" }}>Add at least three skills.</p>
        )}
      </div>

      <fieldset className="space-y-2">
        <legend className={builderLabelClass}>Template</legend>
        {TEMPLATES.map((t) => (
          <label key={t.id} className="flex items-start gap-2 text-sm cursor-pointer">
            <input type="radio" name="cv-template" checked={style.template === t.id} onChange={() => updateStyle({ template: t.id })} />
            <span><strong>{t.label}</strong> — {t.hint}</span>
          </label>
        ))}
      </fieldset>

      <div>
        <label className={builderLabelClass}>Accent colour</label>
        <div className="flex flex-wrap gap-2">
          {ACCENT_PRESETS.map((p) => (
            <button
              key={p.value}
              type="button"
              className="btn btn-ghost btn-sm"
              style={{
                border: style.accentColor === p.value ? "2px solid var(--green-700)" : "1px solid var(--line-2)",
              }}
              onClick={() => updateStyle({ accentColor: p.value })}
            >
              <span className="inline-block w-3 h-3 rounded-full mr-1.5" style={{ background: p.value }} />
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <label className="flex items-start gap-2 text-sm cursor-pointer">
        <input type="checkbox" checked={style.showSummary} onChange={(e) => updateStyle({ showSummary: e.target.checked })} />
        Include career summary section
      </label>

      <div className="pt-2 border-t flex flex-col gap-2" style={{ borderColor: "var(--line)" }}>
        <button type="button" className="btn btn-primary" disabled={downloading} onClick={() => void downloadPdf()}>
          <Icon name="download" size={14} />
          {downloading ? "Generating PDF…" : "Download PDF"}
        </button>
        {renderMs !== null ? (
          <p className="text-xs" style={{ color: "var(--muted)" }}>Server render: {renderMs}ms</p>
        ) : null}
        {downloadError ? <p className="text-sm" style={{ color: "var(--danger)" }}>{downloadError}</p> : null}
      </div>
    </BuilderStepShell>
  );
}
