"use client";

import {
  formatBreakdownFraction,
  matchBreakdownRows,
  type MatchBreakdownRow,
} from "@/lib/matchBreakdown";

interface MatchScoreBreakdownProps {
  match: Parameters<typeof matchBreakdownRows>[0] & {
    matched_skills?: string[];
    missing_skills?: string[];
  };
  className?: string;
}

function BreakdownBar({ row }: { row: MatchBreakdownRow }) {
  const pct = row.max > 0 ? Math.min(100, Math.round((row.value / row.max) * 100)) : 0;
  return (
    <div className="mb-3.5 last:mb-0">
      <div className="flex justify-between items-baseline gap-2 mb-1">
        <span className="text-sm font-medium">{row.label}</span>
        <span className="font-mono text-xs text-right shrink-0" style={{ color: "var(--muted)" }}>
          {formatBreakdownFraction(row.value, row.max)}
        </span>
      </div>
      {row.detail ? (
        <p className="text-[11px] mb-1" style={{ color: "var(--muted)" }}>
          {row.detail}
        </p>
      ) : null}
      <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "var(--bg)" }}>
        <div
          className="h-full rounded-full"
          style={{
            width: `${pct}%`,
            background: row.tone === "green" ? "var(--green-500)" : "var(--copper-500)",
            transition: "width 800ms ease",
          }}
        />
      </div>
    </div>
  );
}

export function MatchScoreBreakdown({ match, className }: MatchScoreBreakdownProps) {
  const rows = matchBreakdownRows(match);
  return (
    <div className={className}>
      {rows.map((row) => (
        <BreakdownBar key={row.key} row={row} />
      ))}
    </div>
  );
}
