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
import { isJobListingClosed } from "@/lib/isJobListingClosed";
import { SkillBadge } from "@/components/SkillBadge";
import { Icon } from "@/components/ui/Icon";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export interface MatchCardProps {
  match: MatchData;
  expired?: boolean;
  /** Opens in-app apply flow (matches page modal). */
  onApplyClick?: () => void;
  /** Professional+ — opens match-tailored CV modal. */
  canTailorCv?: boolean;
  onTailorCvClick?: () => void;
}

export function MatchCard({
  match,
  expired = false,
  onApplyClick,
  canTailorCv = false,
  onTailorCvClick,
}: MatchCardProps) {
  const apply = resolveApplyAction(match.job as ApplyJobFields);
  const useExternalLink = Boolean(apply?.external && !onApplyClick);
  const closed = isJobListingClosed(match.job);
  const dimmed = expired || closed;

  return (
    <article
      className="card job-card overflow-hidden relative"
      style={{ opacity: dimmed ? 0.55 : 1 }}
      data-testid="match-card"
    >
      {expired && (
        <span
          className="absolute top-3 right-3 z-10 px-2 py-0.5 rounded text-[10px] font-bold font-mono tracking-wide"
          style={{
            background: "var(--muted)",
            color: "#faf7f2",
          }}
        >
          EXPIRED
        </span>
      )}
      {closed && !expired && (
        <span
          className="absolute top-3 right-3 z-10 px-2 py-0.5 rounded text-[10px] font-bold font-mono tracking-wide"
          style={{
            background: "var(--muted)",
            color: "#faf7f2",
          }}
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
            className="font-display text-2xl md:text-3xl block hover:underline"
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

        <div className="match-actions flex flex-col gap-2 items-end">
          {expired || closed ? (
            <button
              type="button"
              className="btn btn-primary btn-sm w-40"
              disabled
              style={{ cursor: "not-allowed" }}
            >
              Application closed
            </button>
          ) : apply && useExternalLink ? (
            <a
              href={apply.href}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-primary btn-sm w-40 text-center gap-1.5"
              data-testid="match-apply-external"
            >
              {apply.label}
              <Icon name="external" size={13} />
            </a>
          ) : apply ? (
            <button
              type="button"
              className="btn btn-primary btn-sm w-40"
              onClick={onApplyClick}
              data-testid="match-apply-active"
            >
              {apply.label}
            </button>
          ) : null}
          {canTailorCv ? (
            <button
              type="button"
              className="btn btn-accent btn-sm w-40"
              onClick={onTailorCvClick}
              data-testid="match-tailor-cv"
            >
              Tailor my CV <Icon name="file" size={13} />
            </button>
          ) : (
            <Tooltip>
              <TooltipTrigger
                type="button"
                className="btn btn-ghost btn-sm w-40"
                disabled
                style={{ opacity: 0.55, cursor: "not-allowed" }}
                data-testid="match-tailor-cv-locked"
              >
                Tailor my CV
              </TooltipTrigger>
              <TooltipContent>
                Professional or Super Standard — tailored CV per match. Upgrade at /pricing.
              </TooltipContent>
            </Tooltip>
          )}
          <Link
            href={`/jobs/${match.job.id}`}
            className="btn btn-ghost btn-sm w-40 text-center mt-1"
          >
            Learn more
          </Link>
        </div>
      </div>
    </article>
  );
}
