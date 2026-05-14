"use client";

import { Icon } from "@/components/ui/Icon";
import type { CVSections } from "@/lib/api";
import type { ParsedCV } from "./parseCv";
import { AtsTemplate } from "./templates/AtsTemplate";
import { DesignerTemplate } from "./templates/DesignerTemplate";

export type TemplateKey = "ats" | "designer";

const TEMPLATES: { key: TemplateKey; label: string; sub: string }[] = [
  { key: "ats", label: "ATS-friendly", sub: "Recommended for online applications" },
  { key: "designer", label: "Designer", sub: "Copper sidebar, for human reviewers" },
];

export function PreviewStep({
  parsed,
  cvSections,
  template,
  setTemplate,
  meta,
  onBack,
  onEdit,
  onStartOver,
}: {
  parsed: ParsedCV;
  /** Structured shape from /cv/generate (task #59). When non-null,
   *  templates prefer this over `parsed` for richer rendering. Null
   *  after the user edits or on legacy free-text responses. */
  cvSections: CVSections | null;
  template: TemplateKey;
  setTemplate: (t: TemplateKey) => void;
  meta: { jobTitle: string; company: string; wordCount: number };
  onBack: () => void;
  onEdit: () => void;
  onStartOver: () => void;
}) {
  const onDownload = () => {
    // window.print() targets the entire page; the print.css uses visibility
    // rules to show only `.cv-print-root`. The user picks "Save as PDF" in
    // their browser's print dialog. Filename will follow browser defaults —
    // updating document.title around the call hints at a sensible filename.
    const previousTitle = document.title;
    const slug = `cv-${meta.jobTitle.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "tailored"}`;
    document.title = slug;
    window.print();
    // Restore title after print. Browsers run print() synchronously and the
    // dialog blocks, so this fires after the user dismisses it.
    setTimeout(() => {
      document.title = previousTitle;
    }, 100);
  };

  return (
    <div className="space-y-6">
      <div className="card p-6">
        <div className="flex items-start justify-between gap-3 mb-4 flex-wrap">
          <div>
            <div className="eyebrow">Preview · {meta.jobTitle}</div>
            <p className="text-xs" style={{ color: "var(--muted)" }}>
              {meta.company && `${meta.company} · `}
              {meta.wordCount} words · {parsed.sections.length} sections
            </p>
          </div>
          <div className="flex gap-2 flex-wrap">
            <button onClick={onBack} className="btn btn-ghost btn-sm">
              <Icon name="arrowLeft" size={12} /> Back
            </button>
            <button onClick={onEdit} className="btn btn-ghost btn-sm">
              Edit sections
            </button>
            <button onClick={onStartOver} className="btn btn-ghost btn-sm">
              Start over
            </button>
            <button onClick={onDownload} className="btn btn-primary btn-sm">
              <Icon name="download" size={14} /> Download PDF
            </button>
          </div>
        </div>

        <div className="flex gap-2 mb-4 flex-wrap">
          {TEMPLATES.map((t) => {
            const active = t.key === template;
            return (
              <button
                key={t.key}
                onClick={() => setTemplate(t.key)}
                className="text-left rounded-md px-3 py-2"
                style={{
                  border: `1px solid ${active ? "var(--copper-500)" : "var(--line-2)"}`,
                  background: active ? "var(--bg-2)" : "var(--surface)",
                  color: "var(--ink)",
                  cursor: "pointer",
                  minWidth: 200,
                }}
              >
                <div className="text-sm font-medium flex items-center gap-2">
                  {active && <Icon name="check" size={12} />}
                  {t.label}
                </div>
                <div className="text-xs" style={{ color: "var(--muted)" }}>
                  {t.sub}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      <div className="cv-preview-shell">
        {template === "ats" ? (
          <AtsTemplate parsed={parsed} cvSections={cvSections} />
        ) : (
          <DesignerTemplate parsed={parsed} cvSections={cvSections} />
        )}
      </div>
    </div>
  );
}
