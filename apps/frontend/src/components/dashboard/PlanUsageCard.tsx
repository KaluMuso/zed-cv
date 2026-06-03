"use client";

import Link from "next/link";
import type { Subscription } from "@/lib/api";
import { formatTierLabel } from "@/lib/tier-display";
import { TIER_MARKETING_FEATURES, formatQuotaSummary } from "@/lib/tier-marketing";
import type { DashboardQuotaDisplay } from "@/lib/dashboard-stats";

type PlanUsageCardProps = {
  tier: string;
  sub: Subscription | null;
  quota?: DashboardQuotaDisplay;
};

function formatPeriodEnd(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("en-ZM", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return "—";
  }
}

export function PlanUsageCard({ tier, sub, quota }: PlanUsageCardProps) {
  const label = formatTierLabel(tier);
  const features = TIER_MARKETING_FEATURES[tier] ?? [];
  const usage =
    quota != null
      ? formatQuotaSummary(quota.matchesUsed, quota.matchesLimit)
      : sub
        ? formatQuotaSummary(sub.matches_used, sub.matches_limit)
        : null;

  return (
    <div
      className="rounded-xl border p-5 sm:p-6"
      style={{ borderColor: "var(--line)", background: "var(--surface)" }}
    >
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <p className="text-[11px] font-medium uppercase tracking-wider mb-1" style={{ color: "var(--muted)" }}>
            Your plan
          </p>
          <h2 className="font-display text-2xl" style={{ letterSpacing: "-0.02em" }}>
            {label}
          </h2>
          {usage ? (
            <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
              {usage}
            </p>
          ) : null}
          {sub?.expires_at && tier !== "free" ? (
            <p className="text-xs mt-1" style={{ color: "var(--muted)" }}>
              Renews / ends {formatPeriodEnd(sub.expires_at)}
            </p>
          ) : null}
        </div>
        {tier !== "super_standard" ? (
          <Link href="/pricing" className="btn btn-primary btn-sm shrink-0">
            Upgrade
          </Link>
        ) : (
          <Link href="/settings/billing" className="btn btn-outline btn-sm shrink-0">
            Billing
          </Link>
        )}
      </div>
      {features.length > 0 ? (
        <ul className="mt-4 space-y-1 text-sm" style={{ color: "var(--muted)" }}>
          {features.map((f) => (
            <li key={f}>· {f}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
