"use client";

import type { MatchData } from "@/lib/api";
import { ScoreRing } from "@/components/ui/ScoreRing";
import { SkillBadge } from "@/components/SkillBadge";
import {
  matchStrengthCopy,
  matchStrengthHeadline,
} from "@/components/jobs/jobDetailFormatters";
import { MatchScoreBreakdown } from "@/components/MatchScoreBreakdown";
import { splitMatchExplanation } from "@/lib/matchExplanationDisplay";
import { TIER_NAV_LABELS } from "@/lib/tier-display";
import Link from "next/link";

function MatchPanelPlaceholder({ signedIn }: { signedIn: boolean }) {
  return (
    <div
      className="rounded-2xl border p-6 text-center"
      style={{ borderColor: "var(--line)", background: "var(--bg-2)" }}
    >
      <p className="text-sm font-medium mb-2" style={{ color: "var(--ink)" }}>
        {signedIn ? "No match score yet" : "See your match score"}
      </p>
      <p className="text-xs leading-relaxed mb-4" style={{ color: "var(--muted)" }}>
        {signedIn
          ? "Run matching from your dashboard to see how this role fits your CV."
          : "Sign in and upload your CV to unlock AI match breakdowns for every role."}
      </p>
      <Link
        href={signedIn ? "/matches" : "/auth"}
        className="btn btn-outline btn-sm inline-flex"
      >
        {signedIn ? "Go to matches" : "Sign in"}
      </Link>
    </div>
  );
}

function SkillsOverlapBar({ matched, total }: { matched: number; total: number }) {
  const pct = total > 0 ? Math.round((matched / total) * 100) : 0;
  return (
    <div className="mb-3">
      <div className="flex justify-between text-xs mb-1.5">
        <span style={{ color: "var(--muted)" }}>Skills overlap</span>
        <span className="font-mono font-semibold" style={{ color: "var(--ink)" }}>
          {pct}%
        </span>
      </div>
      <div className="h-2 rounded-full overflow-hidden" style={{ background: "var(--bg)" }}>
        <div
          className="h-full rounded-full"
          style={{
            width: `${pct}%`,
            background: "var(--green-500)",
            transition: "width 800ms ease",
          }}
        />
      </div>
    </div>
  );
}

export function JobDetailMatchPanel({
  match,
  signedIn,
  viewerName,
  subscriptionTier,
}: {
  match: MatchData | null | undefined;
  signedIn: boolean;
  viewerName?: string | null;
  subscriptionTier?: string | null;
}) {
  if (!match) {
    return <MatchPanelPlaceholder signedIn={signedIn} />;
  }

  const matched = match.matched_skills;
  const missing = match.missing_skills;
  const totalSkills = matched.length + missing.length;
  const { main: explanationMain, preferencesNote } = splitMatchExplanation(match.explanation);
  const tierLabel = subscriptionTier
    ? TIER_NAV_LABELS[subscriptionTier] ?? subscriptionTier
    : null;
  const who = viewerName?.trim() || "your";

  return (
    <div
      className="rounded-2xl border p-6 shadow-sm"
      style={{ borderColor: "var(--line)", background: "var(--surface)" }}
    >
      <div className="text-xs font-bold tracking-widest uppercase text-muted-foreground mb-5">
        Why you&apos;re a good match
      </div>

      <div className="flex flex-col items-center text-center mb-6">
        <ScoreRing score={match.score} size={132} stroke={10} />
        <p className="mt-3 text-xs" style={{ color: "var(--muted)" }}>
          Based on {who}&apos;s CV
        </p>
        <p
          className="mt-4 text-[10px] font-bold tracking-widest uppercase max-w-[240px] leading-snug"
          style={{ color: "var(--green-700)" }}
        >
          {matchStrengthHeadline(match.score)}
        </p>
        <p className="mt-2 text-xs max-w-[220px]" style={{ color: "var(--muted)" }}>
          {matchStrengthCopy(match.score)}
        </p>
      </div>

      <div className="mb-6 pb-6 border-b" style={{ borderColor: "var(--line)" }}>
        <div className="text-xs font-bold tracking-widest uppercase text-muted-foreground mb-3">
          Score breakdown
        </div>
        <MatchScoreBreakdown match={match} />
      </div>

      <div className="mb-6">
        <div className="text-xs font-bold tracking-widest uppercase text-muted-foreground mb-2">
          Skills overlap
        </div>
        {totalSkills > 0 ? (
          <>
            <SkillsOverlapBar matched={matched.length} total={totalSkills} />
            <p className="text-sm mb-3" style={{ color: "var(--ink-2)" }}>
              You have {matched.length} of {totalSkills} listed skills.
              {missing.length > 0 ? ` Missing ${missing.length}.` : null}
            </p>
          </>
        ) : (
          <p className="text-sm mb-3" style={{ color: "var(--muted)" }}>
            Strong semantic match — your CV aligns with the role description even without overlapping skill tags.
          </p>
        )}

        {matched.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-3">
            {matched.map((s) => (
              <SkillBadge key={s} skill={s} matched />
            ))}
          </div>
        )}

        {missing.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {missing.map((s) => (
              <span
                key={s}
                className="tag tag-mono inline-flex items-center gap-1"
                style={{
                  background: "rgba(0,0,0,0.04)",
                  color: "var(--copper-600)",
                  border: "1px solid rgba(180, 100, 40, 0.25)",
                }}
              >
                {s}
              </span>
            ))}
          </div>
        )}
      </div>

      {(explanationMain || preferencesNote) && (
        <div
          className="rounded-xl p-4 text-sm leading-relaxed"
          style={{
            background: "color-mix(in srgb, var(--green-100) 65%, var(--surface))",
            border: "1px solid color-mix(in srgb, var(--green-500) 25%, var(--line))",
          }}
        >
          <div className="text-xs font-bold tracking-widest uppercase mb-2" style={{ color: "var(--green-700)" }}>
            Why this match
          </div>
          {explanationMain ? (
            <p className="mb-2" style={{ color: "var(--ink-2)" }}>
              {explanationMain}
            </p>
          ) : null}
          {preferencesNote ? (
            <p className="text-xs" style={{ color: "var(--muted)" }}>
              {preferencesNote}
            </p>
          ) : null}
          {tierLabel ? (
            <p className="text-xs mt-2" style={{ color: "var(--muted)" }}>
              Your {tierLabel} plan controls how many matches we surface each month.
            </p>
          ) : null}
        </div>
      )}
    </div>
  );
}
