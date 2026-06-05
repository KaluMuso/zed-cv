"use client";

import { useEffect } from "react";
import type { MatchData } from "@/lib/api";
import { MatchScoreBreakdown } from "@/components/MatchScoreBreakdown";
import { MatchSkillsBreakdown } from "@/components/matches/MatchSkillsBreakdown";
import { MatchBreakdownUpgradePrompt } from "@/components/shared/MatchBreakdownUpgradePrompt";
import { Icon } from "@/components/ui/Icon";
import { ModalPortal } from "@/components/shared/ModalPortal";
import { ScoreRing } from "@/components/ui/ScoreRing";
import { splitMatchExplanation } from "@/lib/matchExplanationDisplay";
import { formatRequiredSkillsDetail, countRequiredJobSkills } from "@/lib/matchBreakdown";
import { canViewMatchScoreBreakdown } from "@/lib/tier-gating";

export function MatchExplanationModal({
  match,
  open,
  onClose,
  subscriptionTier,
}: {
  match: MatchData | null;
  open: boolean;
  onClose: () => void;
  subscriptionTier?: string | null;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  if (!open || !match) return null;

  const breakdownUnlocked = canViewMatchScoreBreakdown(subscriptionTier);
  const { main, preferencesNote } = splitMatchExplanation(match.explanation);
  const requiredSkillsNote = formatRequiredSkillsDetail(countRequiredJobSkills(match));

  return (
    <ModalPortal>
      <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4">
        <div
          className="modal-backdrop"
          onClick={onClose}
          aria-hidden
        />
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="match-explanation-title"
          className="modal-panel w-full max-w-3xl max-h-[90vh] flex flex-col rounded-t-2xl sm:rounded-2xl overflow-hidden"
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
            {breakdownUnlocked ? (
              <div className="breakdown-grid grid gap-6 sm:grid-cols-2">
                <div>
                  <div className="eyebrow mb-4">Score breakdown</div>
                  <p className="text-xs mb-3 leading-relaxed" style={{ color: "var(--muted)" }}>
                    Each bar shows points out of a fixed weight (total 100).{" "}
                    {requiredSkillsNote
                      ? `Required skills: ${requiredSkillsNote} — a full bar means you match every required skill on the listing.`
                      : "Required skills compares your CV skills to the job’s required skills."}
                  </p>
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

                  <MatchSkillsBreakdown
                    className="mt-4"
                    matchedSkills={match.matched_skills}
                    missingSkills={match.missing_skills}
                  />
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-6 max-w-md mx-auto">
                <div className="text-center">
                  <ScoreRing score={match.score} size={132} stroke={10} />
                  <p className="mt-3 text-xs" style={{ color: "var(--muted)" }}>
                    Your overall match score
                  </p>
                </div>
                <MatchBreakdownUpgradePrompt className="w-full" />
              </div>
            )}
          </div>
        </div>
      </div>
    </ModalPortal>
  );
}
