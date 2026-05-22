"use client";

import { Medal } from "lucide-react";
import { cn } from "@/lib/utils";

const matches = [
  {
    title: "Senior Accountant",
    company: "ZANACO",
    score: 92,
    meta: "Lusaka · K28–35K · Closes in 5d",
    pill: "bg-emerald-600/90 text-white",
  },
  {
    title: "Frontend Engineer",
    company: "MTN",
    score: 88,
    meta: "Lusaka · K32–42K · Hybrid",
    pill: "bg-amber-500/90 text-white",
  },
] as const;

function ScorePill({ score, className }: { score: number; className: string }) {
  return (
    <span
      className={cn(
        "shrink-0 rounded-full px-2 py-0.5 font-mono text-[11px] font-semibold tabular-nums",
        className
      )}
    >
      {score}
    </span>
  );
}

/** WhatsApp digest mock for hero Card B (marketing decoration only). */
export function WhatsAppDigestCard({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "w-full max-w-[340px] rounded-md bg-surface-dark-elevated p-4 text-ink-dark shadow-2xl shadow-black/30 ring-1 ring-white/10 sm:max-w-[380px] sm:p-5",
        className
      )}
      role="img"
      aria-label="WhatsApp digest preview: Good morning Chanda, 3 new matches"
    >
      <div className="flex items-start justify-between gap-3 border-b border-white/10 pb-3">
        <div className="flex min-w-0 items-center gap-2.5">
          <div
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand text-sm font-bold text-white"
            aria-hidden
          >
            Z
          </div>
          <span className="text-sm font-semibold text-[#e9edef]">ZedApply</span>
        </div>
        <span className="shrink-0 font-mono text-[10px] text-[#8696a0]">
          Today 07:00
        </span>
      </div>

      <p className="mt-3 text-[15px] font-medium leading-snug text-[#e9edef] sm:text-base">
        Good morning Chanda! 3 new matches:
      </p>

      <ul className="mt-3 flex flex-col gap-2.5">
        {matches.map(({ title, company, score, meta, pill }) => (
          <li
            key={title}
            className="rounded-md bg-[#1f2c34]/80 px-3 py-2.5"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex min-w-0 items-start gap-1.5">
                <Medal
                  className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-400/90"
                  aria-hidden
                />
                <div className="min-w-0">
                  <p className="truncate text-[13px] font-semibold text-[#e9edef]">
                    {title}
                    <span className="font-normal text-[#8696a0]">
                      {" "}
                      · {company}
                    </span>
                  </p>
                  <p className="mt-0.5 text-[11px] leading-snug text-[#8696a0]">
                    {meta}
                  </p>
                </div>
              </div>
              <ScorePill score={score} className={pill} />
            </div>
          </li>
        ))}
      </ul>

      <p className="mt-3 text-[10px] leading-relaxed text-[#667781]">
        Reply 1, 2, or 3 to apply, or open ZedApply for details.
      </p>
    </div>
  );
}
