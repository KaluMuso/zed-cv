"use client";

import Link from "next/link";
import type { DashboardQuotaDisplay } from "@/lib/dashboard-stats";
import { Icon } from "@/components/ui/Icon";
import { surfaceCardClass } from "@/lib/cn-ui";
import { cn } from "@/lib/utils";

export type ApplicationFunnel = {
  saved: number;
  applied: number;
  interviewing: number;
  offered: number;
  closed: number;
};

type DashboardInsightsProps = {
  totalMatches: number;
  avgScore: number | null;
  topScore: number | null;
  quota: DashboardQuotaDisplay;
  funnel: ApplicationFunnel;
};

function TrendPill({
  label,
  value,
  hint,
  trend,
}: {
  label: string;
  value: string;
  hint?: string;
  trend?: "up" | "neutral" | "down";
}) {
  const trendColor =
    trend === "up"
      ? "text-primary"
      : trend === "down"
        ? "text-danger"
        : "text-muted-foreground";
  return (
    <div className={cn(surfaceCardClass, "p-4")}>
      <p className="type-section-title mb-1">{label}</p>
      <p className="font-mono text-2xl font-semibold tabular-nums" style={{ color: "var(--ink)" }}>
        {value}
      </p>
      {hint ? (
        <p className="type-caption mt-1 flex items-center gap-1">
          {trend ? (
            <span className={trendColor} aria-hidden>
              {trend === "up" ? "↑" : trend === "down" ? "↓" : "→"}
            </span>
          ) : null}
          {hint}
        </p>
      ) : null}
    </div>
  );
}

export function DashboardInsights({
  totalMatches,
  avgScore,
  topScore,
  quota,
  funnel,
}: DashboardInsightsProps) {
  const quotaUsed = quota.matchesUsed;
  const quotaLimit = quota.matchesLimit;
  const quotaPct = quota.unlimited ? null : Math.round(quota.usagePct);

  const pipelineTotal =
    funnel.saved + funnel.applied + funnel.interviewing + funnel.offered + funnel.closed;

  return (
    <section className="space-y-4" aria-label="Performance insights">
      <div className="flex items-center justify-between gap-3">
        <h2 className="type-h3" style={{ color: "var(--ink)" }}>
          Insights
        </h2>
        <Link
          href="/matches"
          className="text-sm font-medium hover:underline"
          style={{ color: "var(--green-700)" }}
        >
          View all matches
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <TrendPill
          label="Match pool"
          value={String(totalMatches)}
          hint={totalMatches > 0 ? "Active scored roles" : "Run matching from profile"}
          trend={totalMatches > 0 ? "up" : "neutral"}
        />
        <TrendPill
          label="Avg. score"
          value={avgScore != null ? `${avgScore}%` : "—"}
          hint={
            avgScore != null
              ? avgScore >= 70
                ? "Strong overall fit"
                : "Refine preferences"
              : undefined
          }
          trend={avgScore != null && avgScore >= 70 ? "up" : "neutral"}
        />
        <TrendPill
          label="Best match"
          value={topScore != null ? `${topScore}%` : "—"}
          hint="Highest current score"
          trend={topScore != null && topScore >= 85 ? "up" : "neutral"}
        />
        <TrendPill
          label="Quota used"
          value={
            quota.unlimited
              ? `${quotaUsed}`
              : quotaLimit > 0
                ? `${quotaUsed}/${quota.limitLabel}`
                : "—"
          }
          hint={
            quota.unlimited
              ? "Unlimited plan"
              : `${quotaPct ?? 0}% of monthly allowance`
          }
          trend={!quota.unlimited && (quotaPct ?? 0) > 80 ? "down" : "neutral"}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className={cn(surfaceCardClass, "p-5")}>
          <h3 className="type-card-title mb-3 flex items-center gap-2">
            <Icon name="briefcase" size={16} />
            Application funnel
          </h3>
          {pipelineTotal === 0 ? (
            <p className="type-caption">Save jobs from Browse to track your pipeline.</p>
          ) : (
            <ul className="space-y-2">
              {(
                [
                  ["Saved", funnel.saved, "var(--muted)"],
                  ["Applied", funnel.applied, "var(--copper-500)"],
                  ["Interviewing", funnel.interviewing, "var(--green-700)"],
                  ["Offered", funnel.offered, "var(--green-500)"],
                  ["Closed", funnel.closed, "var(--ink-2)"],
                ] as const
              ).map(([label, count, color]) => {
                const pct = pipelineTotal ? Math.round((count / pipelineTotal) * 100) : 0;
                return (
                  <li key={label}>
                    <div className="flex justify-between text-sm mb-1">
                      <span style={{ color: "var(--ink-2)" }}>{label}</span>
                      <span className="font-mono tabular-nums" style={{ color: "var(--muted)" }}>
                        {count} ({pct}%)
                      </span>
                    </div>
                    <div
                      className="h-2 rounded-full overflow-hidden"
                      style={{ background: "var(--bg-2)" }}
                      role="presentation"
                    >
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{ width: `${pct}%`, background: color }}
                      />
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
          <Link
            href="/applications"
            className="inline-block mt-4 text-sm font-medium hover:underline"
            style={{ color: "var(--green-700)" }}
          >
            Open application tracker →
          </Link>
        </div>

        <div className={cn(surfaceCardClass, "p-5")}>
          <h3 className="type-card-title mb-3">Match performance</h3>
          <p className="type-caption mb-4">
            Scores combine CV similarity, skills overlap, and local signals. Focus on 70+ matches
            first.
          </p>
          <div className="grid grid-cols-3 gap-2 text-center">
            {[
              { band: "85+", label: "Strong", min: 85 },
              { band: "70–84", label: "Good", min: 70 },
              { band: "<70", label: "Stretch", min: 0 },
            ].map((b) => (
              <div
                key={b.band}
                className="rounded-lg border border-border px-2 py-3 bg-muted/20"
              >
                <div className="text-xs font-medium text-muted-foreground">{b.band}</div>
                <div className="text-[10px] text-muted-foreground mt-0.5">{b.label}</div>
              </div>
            ))}
          </div>
          <p className="type-caption mt-4">
            Tip: set{" "}
            <Link href="/profile?tab=preferences" className="underline" style={{ color: "var(--green-700)" }}>
              job preferences
            </Link>{" "}
            to lift match quality on the next batch.
          </p>
        </div>
      </div>
    </section>
  );
}
