"use client";

import Link from "next/link";
import { Icon } from "@/components/ui/Icon";
import { Avatar } from "@/components/ui/Avatar";
import { formatJobSource } from "@/lib/jobSource";

interface JobCardProps {
  /**
   * Job UUID. Optional for backwards compatibility, but required to render
   * the "View full details" link (without it, the card is click-only).
   */
  id?: string;
  title: string;
  company: string | null;
  location: string | null;
  /**
   * Listing-quality heuristic (0–100). Reflects how *complete* the listing
   * is (has company, apply link, salary, etc.) — NOT a personalised match
   * for the viewer. We no longer surface this on public cards because
   * users universally misread it as a personal match score.
   */
  qualityScore?: number;
  skills: string[];
  closingDate: string | null;
  postedAt?: string | null;
  salaryMin?: number | null;
  salaryMax?: number | null;
  source?: string | null;
  sourceUrl?: string | null;
  /**
   * Personalised match score (0–100) from match_jobs_for_user. Only set
   * when rendering inside an authenticated, CV-backed context like /matches.
   * Renders a clearly-labelled "Match" pill so users know it's about them.
   */
  matchScore?: number;
  matchedSkills?: string[];
  onClick?: () => void;
}

function MatchPill({ score }: { score: number }) {
  let bg: string, color: string, dot: string;
  if (score >= 75) {
    bg = "var(--green-100)";
    color = "var(--green-700)";
    dot = "var(--green-500)";
  } else if (score >= 50) {
    bg = "var(--copper-100)";
    color = "var(--copper-600)";
    dot = "var(--copper-500)";
  } else {
    bg = "rgba(0,0,0,0.04)";
    color = "var(--ink-2)";
    dot = "var(--muted)";
  }
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold font-mono"
      style={{ background: bg, color }}
      title="Match score based on your CV and skills"
    >
      <span
        className="w-1.5 h-1.5 rounded-full"
        style={{ background: dot }}
      />
      {Math.round(score)}% match
    </span>
  );
}

function formatRelativeTime(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return null;
  const diffMs = Date.now() - then;
  if (diffMs < 0) return null;
  const day = 24 * 60 * 60 * 1000;
  if (diffMs < day) return "Posted today";
  if (diffMs < 2 * day) return "Posted yesterday";
  const days = Math.floor(diffMs / day);
  if (days < 7) return `Posted ${days}d ago`;
  const weeks = Math.floor(days / 7);
  if (weeks < 5) return `Posted ${weeks}w ago`;
  const months = Math.floor(days / 30);
  return `Posted ${months}mo ago`;
}

function formatSalary(min?: number | null, max?: number | null): string | null {
  // Salaries are stored as ngwee (ZMW × 100). Display as ZMW kilo for
  // readability — most Zambian salaries are in the 3k–50k range.
  if (!min && !max) return null;
  const fmt = (ngwee: number) => {
    const kwacha = ngwee / 100;
    if (kwacha >= 1000) return `K${(kwacha / 1000).toFixed(kwacha % 1000 === 0 ? 0 : 1)}k`;
    return `K${kwacha.toFixed(0)}`;
  };
  if (min && max && min !== max) return `${fmt(min)}–${fmt(max)}`;
  return fmt(min ?? max ?? 0);
}

export function JobCard({
  id,
  title,
  company,
  location,
  skills,
  closingDate,
  postedAt,
  salaryMin,
  salaryMax,
  source,
  sourceUrl,
  matchScore,
  matchedSkills = [],
  onClick,
}: JobCardProps) {
  const matchedSet = new Set(matchedSkills.map((s) => s.toLowerCase()));

  const closesIn = closingDate
    ? Math.ceil(
        (new Date(closingDate).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
      )
    : null;

  const postedLabel = formatRelativeTime(postedAt);
  const salaryLabel = formatSalary(salaryMin, salaryMax);
  const sourceLabel = formatJobSource(source, sourceUrl);

  // role="button" + tabIndex pattern instead of a real <button>: HTML
  // forbids nesting a <Link> (which renders <a>) inside <button>, and we
  // need the inner "View full details" link to be a real anchor for
  // middle-click / cmd-click / right-click-copy-url to work. Keyboard
  // a11y is preserved: Enter/Space on the card fires onClick when focus
  // is on the card itself (not on the inner link).
  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.target !== e.currentTarget) return;
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onClick?.();
    }
  };

  return (
    <div
      onClick={onClick}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
      className="card card-hover w-full text-left p-5 sm:p-6"
      style={{ cursor: "pointer" }}
    >
      <div className="flex justify-between items-start gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <Avatar name={company || "ZC"} size={36} />
          <div className="min-w-0">
            <h3
              className="font-display text-xl truncate"
              style={{ letterSpacing: "-0.01em" }}
            >
              {title}
            </h3>
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              {company || "Company not listed"}
              {location && (
                <span>
                  {" "}
                  &middot; {location}
                </span>
              )}
            </p>
          </div>
        </div>
        {typeof matchScore === "number" && <MatchPill score={matchScore} />}
      </div>

      {skills.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {skills.slice(0, 8).map((skill) => (
            <span
              key={skill}
              className={`tag tag-mono ${
                matchedSet.has(skill.toLowerCase()) ? "tag-green" : ""
              }`}
            >
              {matchedSet.has(skill.toLowerCase()) && (
                <Icon name="check" size={10} />
              )}
              {skill}
            </span>
          ))}
          {skills.length > 8 && (
            <span className="text-xs self-center" style={{ color: "var(--muted)" }}>
              +{skills.length - 8} more
            </span>
          )}
        </div>
      )}

      {/* Metadata row — posted, salary, closing, source. Replaces the
          old misleading "quality_score%" badge. */}
      <div
        className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs"
        style={{ color: "var(--muted)" }}
      >
        {postedLabel && (
          <span className="flex items-center gap-1">
            <Icon name="clock" size={12} /> {postedLabel}
          </span>
        )}
        {salaryLabel && (
          <span
            className="flex items-center gap-1 font-mono"
            style={{ color: "var(--ink-2)" }}
          >
            {salaryLabel}/mo
          </span>
        )}
        {closesIn !== null && (
          <span
            className="flex items-center gap-1"
            style={{
              color: closesIn <= 3 ? "var(--danger)" : "var(--muted)",
              fontWeight: closesIn <= 3 ? 600 : 400,
            }}
          >
            <Icon name="clock" size={12} />
            {closesIn <= 0
              ? "Closed"
              : closesIn === 1
              ? "Closes tomorrow"
              : `Closes in ${closesIn}d`}
          </span>
        )}
        <span className="ml-auto text-[10px] opacity-60">{sourceLabel}</span>
      </div>

      {id && (
        <div
          className="mt-4 pt-3 flex items-center justify-end"
          style={{ borderTop: "1px solid var(--line)" }}
        >
          <Link
            href={`/jobs/${id}`}
            onClick={(e) => e.stopPropagation()}
            // Same stop pattern for keyboard: don't let Enter on the link
            // bubble up and re-trigger the card's drawer-open handler.
            onKeyDown={(e) => e.stopPropagation()}
            className="text-sm font-medium inline-flex items-center gap-1 hover:underline"
            style={{ color: "var(--copper-500)" }}
          >
            View full details <Icon name="arrowRight" size={13} />
          </Link>
        </div>
      )}
    </div>
  );
}
