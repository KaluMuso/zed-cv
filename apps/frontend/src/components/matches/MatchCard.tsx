"use client";

import Link from "next/link";
import { MatchScore } from "@/components/MatchScore";
import { Avatar } from "@/components/ui/Avatar";
import { formatMatchedRelative } from "@/lib/formatMatchedRelative";
import {
  isExternalApplyHref,
  resolveApplyAction,
  type ApplyJobFields,
} from "@/lib/applyLink";
import type { MatchData } from "@/lib/api";
import { isGreyedClosedListing, isRecentlyClosedJob } from "@/lib/jobVisibility";
import { SkillBadge } from "@/components/SkillBadge";
import {
  MATCH_CARD_MAX_MATCHED_SKILLS,
  MATCH_CARD_MAX_MISSING_SKILLS,
  formatSkillOverflowSuffix,
  truncateSkillList,
} from "@/lib/matchSkillsDisplay";
import { Icon } from "@/components/ui/Icon";
import { SaveJobButton } from "@/components/SaveJobButton";
import { JobShareButtons } from "@/components/share/JobShareButtons";
import { MatchPremiumActions } from "@/components/matches/MatchPremiumActions";
import { btnClass } from "@/lib/cn-ui";
import { stashMatchHandoff } from "@/lib/matchHandoff";
import { cn } from "@/lib/utils";

export interface MatchCardProps {
  match: MatchData;
  expired?: boolean;
  authToken?: string | null;
  jobSaved?: boolean;
  onSavedChange?: (jobId: string, next: boolean) => void;
  onApplyClick?: () => void;
  onTailorCvClick?: () => void;
  onCoverLetterClick?: () => void;
  onInterviewPrepClick?: () => void;
  onWhyMatchClick?: () => void;
  onDismissClick?: () => void;
  dismissing?: boolean;
}

export function MatchCard({
  match,
  expired = false,
  authToken,
  jobSaved = false,
  onSavedChange,
  onApplyClick,
  onTailorCvClick,
  onCoverLetterClick,
  onInterviewPrepClick,
  onWhyMatchClick,
  onDismissClick,
  dismissing = false,
}: MatchCardProps) {
  const apply = resolveApplyAction(match.job as ApplyJobFields);
  const useExternalLink = Boolean(
    apply && isExternalApplyHref(apply.href) && !onApplyClick,
  );
  const recentlyClosed = isRecentlyClosedJob(match.job);
  const greyed = expired || isGreyedClosedListing(match.job);
  const closed = expired || recentlyClosed || greyed;
  const matchedPreview = truncateSkillList(
    match.matched_skills,
    MATCH_CARD_MAX_MATCHED_SKILLS,
  );
  const missingPreview = truncateSkillList(
    match.missing_skills,
    MATCH_CARD_MAX_MISSING_SKILLS,
  );
  const matchedOverflow = formatSkillOverflowSuffix(matchedPreview.overflowCount);
  const missingOverflow = formatSkillOverflowSuffix(missingPreview.overflowCount);

  return (
    <article
      className="card job-card overflow-hidden relative native-pressable"
      style={{ opacity: greyed ? 0.6 : 1 }}
      data-testid="match-card"
      data-visibility={match.job.visibility_status ?? undefined}
    >
      {expired && (
        <span
          className="absolute top-3 right-3 z-10 px-2 py-0.5 rounded text-[10px] font-bold font-mono tracking-wide bg-muted text-[#faf7f2]"
        >
          EXPIRED
        </span>
      )}
      {recentlyClosed && !expired && (
        <span
          className="absolute top-3 right-3 z-10 px-2 py-0.5 rounded text-[10px] font-bold font-mono tracking-wide bg-destructive text-destructive-foreground"
          data-testid="match-closed-badge"
        >
          CLOSED
        </span>
      )}
      <div className="match-row p-5 sm:p-6 grid gap-6 items-start">
        <MatchScore
          score={match.score}
          breakdown={{
            vector: match.vector_score,
            skill: match.skill_score,
            bonus: match.bonus_score,
          }}
          size="lg"
        />

        <div className="min-w-0 match-body">
          <div className="flex items-center gap-2.5 mb-2">
            <Avatar name={match.job.company || "ZC"} size={28} />
            <span className="text-sm truncate" style={{ color: "var(--muted)" }}>
              {match.job.company || "Company"} &middot; {match.job.location || "Zambia"}
            </span>
          </div>
          <Link
            href={`/jobs/${match.job.id}`}
            onClick={() => stashMatchHandoff(match)}
            className={cn(
              "font-display text-xl sm:text-2xl md:text-3xl block hover:underline break-words",
              recentlyClosed && "line-through opacity-80",
            )}
            style={{ letterSpacing: "-0.01em", lineHeight: 1.15, color: "inherit" }}
          >
            {match.job.title}
          </Link>
          {match.created_at ? (
            <p className="text-xs mt-1.5" style={{ color: "var(--muted)" }}>
              {formatMatchedRelative(match.created_at)}
            </p>
          ) : null}
          {(matchedPreview.visible.length > 0 || missingPreview.visible.length > 0) && (
            <div className="flex flex-wrap gap-1.5 mt-3 items-center" data-testid="match-card-skills">
              {matchedPreview.visible.map((s) => (
                <SkillBadge key={s} skill={s} matched />
              ))}
              {matchedOverflow ? (
                <span className="text-xs font-mono" style={{ color: "var(--muted)" }}>
                  {matchedOverflow}
                </span>
              ) : null}
              {missingPreview.visible.map((s) => (
                <span key={s} className="tag tag-mono opacity-75">
                  {s}
                </span>
              ))}
              {missingOverflow ? (
                <span className="text-xs font-mono" style={{ color: "var(--muted)" }}>
                  {missingOverflow}
                </span>
              ) : null}
            </div>
          )}
        </div>

        <div className="match-actions flex flex-col gap-3 w-full min-w-0">
          <div className="flex flex-wrap gap-2 w-full">
            {closed ? (
              <button
                type="button"
                className={cn(btnClass("primary", "sm"), "flex-1 min-w-[8rem]")}
                disabled
                data-testid="match-apply-closed"
              >
                Closed
              </button>
            ) : apply && useExternalLink ? (
              <a
                href={apply.href}
                target="_blank"
                rel="noopener noreferrer"
                className={cn(
                  btnClass("primary", "sm"),
                  "flex-1 min-w-[8rem] text-center gap-1 inline-flex items-center justify-center",
                )}
                data-testid="match-apply-external"
              >
                Apply
                <Icon name="external" size={13} />
              </a>
            ) : apply || onApplyClick ? (
              <button
                type="button"
                className={cn(btnClass("primary", "sm"), "flex-1 min-w-[8rem]")}
                onClick={onApplyClick}
                data-testid="match-apply-active"
              >
                {apply?.label ?? "Apply"}
              </button>
            ) : null}
            {!closed && authToken && onSavedChange ? (
              <SaveJobButton
                jobId={match.job.id}
                saved={jobSaved}
                token={authToken}
                onChange={onSavedChange}
                className={cn(btnClass("outline", "sm"), "shrink-0")}
              />
            ) : null}
          </div>

          {!closed && (
            <div className="match-share w-full overflow-x-auto">
              <JobShareButtons
                variant="compact"
                job={{
                  id: match.job.id,
                  title: match.job.title,
                  company: match.job.company,
                  location: match.job.location,
                }}
                className="flex-wrap"
              />
            </div>
          )}

          <MatchPremiumActions
            onTailorCvClick={onTailorCvClick}
            onCoverLetterClick={onCoverLetterClick}
            onInterviewPrepClick={onInterviewPrepClick}
          />

          <div className="flex flex-wrap items-center justify-between gap-2 w-full">
            <button
              type="button"
              onClick={onWhyMatchClick}
              className="text-xs underline-offset-2 hover:underline"
              style={{ color: "var(--muted)" }}
              data-testid="match-why-link"
            >
              Why this match?
            </button>
            {onDismissClick ? (
              <button
                type="button"
                onClick={onDismissClick}
                disabled={dismissing}
                className="text-xs underline-offset-2 hover:underline disabled:opacity-50"
                style={{ color: "var(--muted)" }}
                data-testid="match-dismiss"
              >
                {dismissing ? "Hiding…" : "Hide match"}
              </button>
            ) : null}
          </div>
        </div>
      </div>
    </article>
  );
}
