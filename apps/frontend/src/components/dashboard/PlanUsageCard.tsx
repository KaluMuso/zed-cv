"use client";

import Link from "next/link";
import type { Subscription } from "@/lib/api";
import { TIER_NAV_LABELS } from "@/lib/tier-display";
import { formatMatchesLimit } from "@/lib/tier-config";

const TIER_FEATURES: Record<string, string[]> = {
  free: ["3 matches/mo (7 welcome bonus first 2 months)", "WhatsApp alerts", "Basic CV analysis"],
  starter: ["50 matches/mo", "AI tailored CVs", "Priority matching", "Score breakdowns"],
  professional: [
    "125 matches/mo",
    "Cover letters",
    "Career insights",
    "Everything in Starter",
  ],
  super_standard: [
    "Unlimited matches",
    "Interview prep",
    "Everything in Professional",
  ],
};

type PlanUsageCardProps = {
  tier: string;
  sub: Subscription | null;
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

export function PlanUsageCard({ tier, sub }: PlanUsageCardProps) {
  const label = TIER_NAV_LABELS[tier] ?? tier;
  const features = TIER_FEATURES[tier] ?? [];
  const limitLabel = sub ? formatMatchesLimit(sub.matches_limit) : "—";
  const usage =
    sub && sub.matches_limit < 99999
      ? `${sub.matches_used} / ${limitLabel} matches this period`
      : sub
        ? `${sub.matches_used} matches (unlimited plan)`
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
