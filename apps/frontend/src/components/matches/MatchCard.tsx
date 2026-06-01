"use client";

import Link from "next/link";
import { MatchScore } from "@/components/MatchScore";
import { Avatar } from "@/components/ui/Avatar";
import { formatMatchedRelative } from "@/lib/formatMatchedRelative";
import {
  resolveApplyAction,
  type ApplyJobFields,
} from "@/lib/applyLink";
import type { MatchData } from "@/lib/api";
import { isGreyedClosedListing, isRecentlyClosedJob } from "@/lib/jobVisibility";
import { SkillBadge } from "@/components/SkillBadge";
import { Icon } from "@/components/ui/Icon";
import { SaveJobButton } from "@/components/SaveJobButton";
import { TierGate } from "@/components/shared/TierGate";
import { JobShareButtons } from "@/components/share/JobShareButtons";
import { btnClass } from "@/lib/cn-ui";
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
  onWhyMatchClick?: () => void;
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
  onWhyMatchClick,
}: MatchCardProps) {
  const apply = resolveApplyAction(match.job as ApplyJobFields);
  const useExternalLink = Boolean(apply?.external && !onApplyClick);
  const recentlyClosed = isRecentlyClosedJob(match.job);
  const greyed = expired || isGreyedClosedListing(match.job);
  const closed = expired || recentlyClosed || greyed;

  return (
    <article
      className="card job-card overflow-hidden relative"
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
      <div
        className="match-row p-5 sm:p-6 grid gap-6 items-center"
        style={{ gridTemplateColumns: "auto 1fr auto" }}
      >
        <MatchScore
          score={match.score}
          breakdown={{
            vector: match.vector_score,
            skill: match.skill_score,
            bonus: match.bonus_score,
          }}
          size="lg"
        />

        <div className="min-w-0">
          <div className="flex items-center gap-2.5 mb-2">
            <Avatar name={match.job.company || "ZC"} size={28} />
            <span className="text-sm" style={{ color: "var(--muted)" }}>
              {match.job.company || "Company"} &middot; {match.job.location || "Zambia"}
            </span>
          </div>
          <Link
            href={`/jobs/${match.job.id}`}
            className={cn(
              "font-display text-2xl md:text-3xl block hover:underline",
              recentlyClosed && "line-through opacity-80",
            )}
            style={{ letterSpacing: "-0.01em", lineHeight: 1.1, color: "inherit" }}
          >
            {match.job.title}
          </Link>
          {match.created_at ? (
            <p className="text-xs mt-1.5" style={{ color: "var(--muted)" }}>
              {formatMatchedRelative(match.created_at)}
            </p>
          ) : null}
          {(match.matched_skills.length > 0 || match.missing_skills.length > 0) && (
            <div className="flex flex-wrap gap-1.5 mt-3">
              {match.matched_skills.slice(0, 6).map((s) => (
                <SkillBadge key={s} skill={s} matched />
              ))}
              {match.missing_skills.slice(0, 4).map((s) => (
                <span key={s} className="tag tag-mono opacity-75">
                  {s}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="match-actions flex flex-col gap-2 items-stretch sm:items-end min-w-[10rem] sm:min-w-[12rem]">
          <div className="grid grid-cols-3 gap-2 w-full">
            {closed ? (
              <button
                type="button"
                className={cn(btnClass("primary", "sm"), "col-span-3")}
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
                  "text-center gap-1 flex items-center justify-center",
                )}
                data-testid="match-apply-external"
              >
                Apply
                <Icon name="external" size={13} />
              </a>
            ) : apply || onApplyClick ? (
              <button
                type="button"
                className={cn(btnClass("primary", "sm"))}
                onClick={onApplyClick}
                data-testid="match-apply-active"
              >
                {apply?.label ?? "Apply"}
              </button>
            ) : (
              <span />
            )}
            {!closed &&
              (authToken && onSavedChange ? (
                <SaveJobButton
                  jobId={match.job.id}
                  saved={jobSaved}
                  token={authToken}
                  onChange={onSavedChange}
                  className={cn(btnClass("outline", "sm"), "w-full")}
                />
              ) : (
                <span />
              ))}
            {!closed && (
              <div className="flex justify-end">
                <JobShareButtons
                  job={{
                    id: match.job.id,
                    title: match.job.title,
                    company: match.job.company,
                    location: match.job.location,
                  }}
                />
              </div>
            )}
          </div>
          {closed && authToken && onSavedChange && (
            <SaveJobButton
              jobId={match.job.id}
              saved={jobSaved}
              token={authToken}
              onChange={onSavedChange}
              className={cn(btnClass("outline", "sm"), "w-full")}
            />
          )}

          <div className="grid grid-cols-2 gap-2 w-full">
            <TierGate feature="tailor_cv">
              <button
                type="button"
                className={cn(btnClass("accent", "sm"), "w-full text-xs")}
                onClick={onTailorCvClick}
                data-testid="match-tailor-cv"
              >
                Tailor my CV
              </button>
            </TierGate>
            <TierGate feature="cover_letter">
              <button
                type="button"
                className={cn(btnClass("outline", "sm"), "w-full text-xs")}
                onClick={onCoverLetterClick}
                data-testid="match-cover-letter"
              >
                Cover letter
              </button>
            </TierGate>
          </div>

          <button
            type="button"
            onClick={onWhyMatchClick}
            className="text-xs text-left sm:text-right underline-offset-2 hover:underline w-full"
            style={{ color: "var(--muted)" }}
            data-testid="match-why-link"
          >
            Why this match?
          </button>
        </div>
      </div>
    </article>
  );
}
