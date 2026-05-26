"use client";

import type { MatchData } from "@/lib/api";
import { MatchScoreBreakdown } from "@/components/MatchScoreBreakdown";
import { SkillBadge } from "@/components/SkillBadge";
import { Icon } from "@/components/ui/Icon";
import { splitMatchExplanation } from "@/lib/matchExplanationDisplay";

export function MatchExplanationModal({
  match,
  open,
  onClose,
}: {
  match: MatchData | null;
  open: boolean;
  onClose: () => void;
}) {
  if (!open || !match) return null;

  const { main, preferencesNote } = splitMatchExplanation(match.explanation);
  const missing = match.missing_skills;

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div
        className="fixed inset-0"
        style={{ backgroundColor: "rgba(0,0,0,0.5)", backdropFilter: "blur(4px)" }}
        onClick={onClose}
        aria-hidden
      />
      <div
        role="dialog"
        aria-labelledby="match-explanation-title"
        className="relative z-10 w-full max-w-3xl max-h-[90vh] flex flex-col rounded-t-2xl sm:rounded-2xl overflow-hidden"
        style={{ background: "var(--surface)", boxShadow: "var(--shadow-lg)" }}
      >
        <header
          className="flex items-start justify-between gap-4 p-5 sm:p-6 border-b shrink-0"
          style={{ borderColor: "var(--line)" }}
        >
          <div className="min-w-0">
            <div className="eyebrow mb-1">Why this match?</div>
            <h2
              id="match-explanation-title"
              className="font-display text-xl sm:text-2xl truncate"
              style={{ letterSpacing: "-0.01em" }}
              title={match.job.title}
            >
              {match.job.title}
            </h2>
            {(match.job.company || match.job.location) && (
              <p className="text-sm mt-0.5" style={{ color: "var(--muted)" }}>
                {[match.job.company, match.job.location].filter(Boolean).join(" · ")}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="shrink-0 w-8 h-8 rounded-full flex items-center justify-center"
            style={{ border: "1px solid var(--line-2)", color: "var(--muted)" }}
          >
            <Icon name="x" size={14} />
          </button>
        </header>

        <div className="flex-1 overflow-y-auto p-5 sm:p-6">
          <div className="breakdown-grid grid gap-6 sm:grid-cols-2">
            <div>
              <div className="eyebrow mb-4">Score breakdown</div>
              <MatchScoreBreakdown match={match} />
            </div>

            <div className="min-w-0">
              <div className="eyebrow mb-4">AI explanation</div>

              {main ? (
                <p
                  className="text-sm leading-relaxed mb-4"
                  style={{ color: "var(--ink-2)" }}
                >
                  {main}
                </p>
              ) : (
                <p className="text-sm mb-4" style={{ color: "var(--muted)" }}>
                  No detailed explanation yet for this match.
                </p>
              )}

              {preferencesNote && (
                <div
                  className="mb-4 p-3.5 rounded-lg"
                  style={{
                    background: "var(--green-100)",
                    border: "1px solid color-mix(in srgb, var(--green-500) 35%, transparent)",
                  }}
                >
                  <div
                    className="text-[10px] font-bold uppercase tracking-wider mb-1"
                    style={{ color: "var(--green-700)" }}
                  >
                    Preferences match
                  </div>
                  <p className="text-sm leading-relaxed" style={{ color: "var(--ink-2)" }}>
                    {preferencesNote.replace(/^Preferences match:\s*/i, "")}
                  </p>
                </div>
              )}

              {missing.length > 0 && (
                <div
                  className="p-4 rounded-lg"
                  style={{
                    background: "#FEF3C7",
                    border: "1px solid #F59E0B",
                  }}
                >
                  <div
                    className="text-[10px] font-bold uppercase tracking-wider mb-2"
                    style={{ color: "#B45309" }}
                  >
                    Skill gap
                  </div>
                  <p className="text-sm mb-3 leading-relaxed" style={{ color: "var(--ink-2)" }}>
                    These required skills aren&apos;t on your CV yet — consider highlighting
                    related experience or upskilling before you apply.
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {missing.map((skill) => (
                      <SkillBadge key={skill} skill={skill} matched={false} />
                    ))}
                  </div>
                </div>
              )}

              {match.matched_skills.length > 0 && (
                <div className="mt-4">
                  <div
                    className="text-[10px] uppercase tracking-wider mb-2"
                    style={{ color: "var(--muted)" }}
                  >
                    Matched skills
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {match.matched_skills.map((skill) => (
                      <SkillBadge key={skill} skill={skill} matched />
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
