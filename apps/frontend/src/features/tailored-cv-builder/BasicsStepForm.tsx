"use client";

import { Icon } from "@/components/ui/Icon";
import { useTailoredCvBuilderStore } from "./store";

const inputClass =
  "w-full h-10 px-3 rounded-md text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--brand-500,#0E5C3A)] focus:ring-offset-0";

const fieldStyle = {
  border: "1px solid var(--line-2)",
  background: "var(--surface)",
  color: "var(--ink)",
} as const;

const labelClass = "text-xs font-medium block mb-1.5";

export function BasicsStepForm() {
  const basics = useTailoredCvBuilderStore((s) => s.draft.basics);
  const updateBasics = useTailoredCvBuilderStore((s) => s.updateBasics);
  const setStep = useTailoredCvBuilderStore((s) => s.setStep);

  return (
    <div
      className="flex flex-col h-full rounded-lg p-5 sm:p-6"
      style={{
        background: "var(--surface)",
        border: "1px solid var(--line-2)",
      }}
    >
      <div className="mb-5">
        <h2 className="text-lg font-semibold" style={{ color: "var(--ink)" }}>
          Basic info
        </h2>
        <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
          Header details recruiters scan first. Changes appear in the preview instantly.
        </p>
      </div>

      <form
        className="flex flex-col flex-1 gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          setStep("experience");
        }}
      >
        <div>
          <label className={labelClass} style={{ color: "var(--ink-2)" }} htmlFor="cv-full-name">
            Full name
          </label>
          <input
            id="cv-full-name"
            value={basics.fullName}
            onChange={(e) => updateBasics({ fullName: e.target.value })}
            placeholder="e.g. Chanda Banda"
            className={inputClass}
            style={fieldStyle}
            autoComplete="name"
          />
        </div>

        <div>
          <label className={labelClass} style={{ color: "var(--ink-2)" }} htmlFor="cv-headline">
            Headline
          </label>
          <input
            id="cv-headline"
            value={basics.headline}
            onChange={(e) => updateBasics({ headline: e.target.value })}
            placeholder="e.g. Chartered Accountant · IFRS"
            className={inputClass}
            style={fieldStyle}
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className={labelClass} style={{ color: "var(--ink-2)" }} htmlFor="cv-email">
              Email
            </label>
            <input
              id="cv-email"
              type="email"
              value={basics.email}
              onChange={(e) => updateBasics({ email: e.target.value })}
              placeholder="you@email.com"
              className={inputClass}
              style={fieldStyle}
              autoComplete="email"
            />
          </div>
          <div>
            <label className={labelClass} style={{ color: "var(--ink-2)" }} htmlFor="cv-phone">
              Phone
            </label>
            <input
              id="cv-phone"
              type="tel"
              value={basics.phone}
              onChange={(e) => updateBasics({ phone: e.target.value })}
              placeholder="+260XXXXXXXXX"
              className={inputClass}
              style={fieldStyle}
              autoComplete="tel"
            />
          </div>
        </div>

        <div>
          <label className={labelClass} style={{ color: "var(--ink-2)" }} htmlFor="cv-location">
            Location
          </label>
          <input
            id="cv-location"
            value={basics.location}
            onChange={(e) => updateBasics({ location: e.target.value })}
            placeholder="e.g. Lusaka, Zambia"
            className={inputClass}
            style={fieldStyle}
          />
        </div>

        <div className="flex-1 flex flex-col min-h-[120px]">
          <label className={labelClass} style={{ color: "var(--ink-2)" }} htmlFor="cv-summary">
            Professional summary
          </label>
          <textarea
            id="cv-summary"
            value={basics.summary}
            onChange={(e) => updateBasics({ summary: e.target.value })}
            placeholder="2–3 sentences tailored to the role you're targeting."
            rows={5}
            className="w-full flex-1 min-h-[120px] p-3 rounded-md text-sm resize-y"
            style={{ ...fieldStyle, lineHeight: 1.55 }}
          />
        </div>

        <div className="pt-2 flex justify-end">
          <button type="submit" className="btn btn-primary">
            Next: Experience
            <Icon name="arrowRight" size={14} />
          </button>
        </div>
      </form>
    </div>
  );
}
