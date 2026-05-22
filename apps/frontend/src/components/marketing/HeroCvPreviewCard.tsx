"use client";

import { cn } from "@/lib/utils";

/** Back-left CV mini-card in the hero composition (Card A). */
export function HeroCvPreviewCard({ className }: { className?: string }) {
  const skills = ["Excel", "IFRS", "SAP", "Audit"];

  return (
    <div
      className={cn(
        "w-full max-w-[300px] rounded-md border border-line bg-surface p-4 shadow-lg sm:p-5",
        className
      )}
      role="img"
      aria-label="CV preview: Chanda Mwape, Senior Accountant"
    >
      <div className="flex items-center justify-between gap-2 border-b border-line pb-3">
        <span className="font-mono text-[10px] uppercase tracking-wide text-muted">
          chanda_mwape_cv.pdf
        </span>
        <span className="rounded-full bg-green-100 px-2 py-0.5 text-[10px] font-medium text-green-700">
          Parsed
        </span>
      </div>
      <h3 className="font-display mt-3 text-xl text-ink">Chanda Mwape</h3>
      <p className="mt-0.5 text-sm text-ink-2">Senior Accountant · Lusaka</p>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {skills.map((skill) => (
          <span
            key={skill}
            className="rounded-full bg-bg-2 px-2 py-0.5 text-[11px] text-ink-2"
          >
            {skill}
          </span>
        ))}
      </div>
      <div className="mt-4">
        <div className="mb-1 flex justify-between text-[11px] text-muted">
          <span>Profile complete</span>
          <span className="font-mono text-ink-2">94%</span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-bg-2">
          <div
            className="h-full rounded-full bg-brand"
            style={{ width: "94%" }}
          />
        </div>
      </div>
    </div>
  );
}
