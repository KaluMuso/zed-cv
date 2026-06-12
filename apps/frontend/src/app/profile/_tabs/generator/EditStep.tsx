"use client";

import { Icon } from "@/components/ui/Icon";
import type { ParsedCV, ParsedHeader, ParsedSection } from "./parseCv";
import { MarkdownTextarea } from "@/components/ui/MarkdownTextarea";

/**
 * Section-by-section editor for the parsed CV. Lifts state up to the
 * parent (GeneratorTab) so navigating to the preview keeps edits and so
 * "Reset to original" can restore the unedited LLM output.
 */
export function EditStep({
  parsed,
  onChange,
  onDone,
  onReset,
}: {
  parsed: ParsedCV;
  onChange: (next: ParsedCV) => void;
  onDone: () => void;
  onReset: () => void;
}) {
  const setHeader = (patch: Partial<ParsedHeader>) =>
    onChange({ ...parsed, header: { ...parsed.header, ...patch } });

  const setSection = (idx: number, patch: Partial<ParsedSection>) => {
    const next = parsed.sections.map((s, i) => (i === idx ? { ...s, ...patch } : s));
    onChange({ ...parsed, sections: next });
  };

  const removeSection = (idx: number) => {
    if (!confirm("Remove this section?")) return;
    onChange({ ...parsed, sections: parsed.sections.filter((_, i) => i !== idx) });
  };

  const addSection = () => {
    const title = prompt("Enter section title (e.g. REFERENCES, PROJECTS):");
    if (!title) return;
    onChange({
      ...parsed,
      sections: [...parsed.sections, { title: title.toUpperCase(), body: "" }],
    });
  };

  const inputStyle = {
    border: "1px solid var(--line-2)",
    background: "var(--surface)",
    color: "var(--ink)",
  };

  return (
    <div className="space-y-6">
      <div className="card p-6">
        <div className="flex items-center justify-between gap-3 mb-4">
          <div>
            <div className="eyebrow">Edit your CV</div>
            <p className="text-xs" style={{ color: "var(--muted)" }}>
              Tweak any section before exporting. Changes stay local until you download.
            </p>
          </div>
          <div className="flex gap-2">
            <button onClick={onReset} className="btn btn-ghost btn-sm">
              <Icon name="arrowRight" size={12} /> Reset
            </button>
            <button onClick={onDone} className="btn btn-primary btn-sm">
              Done editing
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <Field label="Name" value={parsed.header.name} onChange={(v) => setHeader({ name: v })} style={inputStyle} />
          <Field label="Phone" value={parsed.header.phone} onChange={(v) => setHeader({ phone: v })} style={inputStyle} placeholder="+260 9XX XXX XXX" />
          <Field label="Email" value={parsed.header.email} onChange={(v) => setHeader({ email: v })} style={inputStyle} />
          <Field label="Location" value={parsed.header.location} onChange={(v) => setHeader({ location: v })} style={inputStyle} placeholder="Lusaka, Zambia" />
        </div>
      </div>

      {parsed.sections.map((section, idx) => (
        <div key={`${section.title}-${idx}`} className="card p-6">
          <div className="flex items-center justify-between gap-3 mb-2">
            <input
              value={section.title}
              onChange={(e) => setSection(idx, { title: e.target.value.toUpperCase() })}
              className="text-sm font-bold uppercase tracking-wide px-2 py-1 rounded-md"
              style={{ ...inputStyle, letterSpacing: "0.08em" }}
            />
            <button
              onClick={() => removeSection(idx)}
              className="btn btn-ghost btn-sm"
              style={{ color: "var(--danger)" }}
              title="Remove section"
            >
              <Icon name="x" size={14} />
            </button>
          </div>
          <MarkdownTextarea
            value={section.body}
            onChangeValue={(val) => setSection(idx, { body: val })}
            rows={Math.max(4, Math.min(14, section.body.split("\n").length + 1))}
            className="w-full text-sm"
            style={{ ...inputStyle }}
          />
          <p className="text-xs mt-2" style={{ color: "var(--muted)" }}>
            Start a line with <code>• </code> or <code>- </code> to add a bullet. Use the toolbar for bold/italics.
          </p>
        </div>
      ))}

      <div className="flex justify-center mt-4">
        <button onClick={addSection} className="btn btn-outline btn-sm">
          <Icon name="plus" size={14} /> Add missing section
        </button>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  style,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  style: React.CSSProperties;
  placeholder?: string;
}) {
  return (
    <div>
      <label className="text-xs font-medium block mb-1" style={{ color: "var(--ink-2)" }}>
        {label}
      </label>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full h-10 px-3 rounded-md text-sm"
        style={style}
      />
    </div>
  );
}
