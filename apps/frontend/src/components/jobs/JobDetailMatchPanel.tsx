"use client";

import type { MatchData } from "@/lib/api";
import { ScoreRing } from "@/components/ui/ScoreRing";
import { SkillBadge } from "@/components/SkillBadge";
import { matchStrengthCopy } from "@/components/jobs/jobDetailFormatters";
import { MatchScoreBreakdown } from "@/components/MatchScoreBreakdown";
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

export function JobDetailMatchPanel({
  match,
  signedIn,
}: {
  match: MatchData | null | undefined;
  signedIn: boolean;
}) {
  if (!match) {
    return <MatchPanelPlaceholder signedIn={signedIn} />;
  }

  const matched = match.matched_skills;
  const missing = match.missing_skills;
  const totalSkills = matched.length + missing.length;
  const haveCount = matched.length;
  const missingCount = missing.length;

  return (
    <div
      className="rounded-2xl border p-6 shadow-sm"
      style={{ borderColor: "var(--line)", background: "var(--surface)" }}
    >
      <div className="text-xs font-bold tracking-widest uppercase text-muted-foreground mb-5">
        Match breakdown
      </div>

      <div className="flex flex-col items-center text-center mb-6">
        <ScoreRing score={match.score} size={132} stroke={10} />
        <p
          className="mt-4 text-sm font-medium max-w-[220px]"
          style={{ color: "var(--green-700)" }}
        >
          {matchStrengthCopy(match.score)}
        </p>
      </div>

      <div className="mb-6 pb-6 border-b" style={{ borderColor: "var(--line)" }}>
        <MatchScoreBreakdown match={match} />
      </div>

      <div>
        <div className="text-xs font-bold tracking-widest uppercase text-muted-foreground mb-2">
          Skills overlap
        </div>
        {totalSkills > 0 ? (
          <p className="text-sm mb-3" style={{ color: "var(--ink-2)" }}>
            You have {haveCount} of {totalSkills}.
            {missingCount > 0 ? (
              <>
                {" "}
                Missing {missingCount}.
              </>
            ) : null}
          </p>
        ) : (
          <p className="text-sm mb-3" style={{ color: "var(--muted)" }}>
            Strong semantic match — your CV aligns with the role description even
            without overlapping skill tags.
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
    </div>
  );
}
