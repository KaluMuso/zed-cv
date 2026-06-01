"use client";

import Link from "next/link";
import { SaveJobButton } from "@/components/SaveJobButton";
import { Icon } from "@/components/ui/Icon";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/badge";
import type { EmploymentType, PayFrequency, WorkArrangement } from "@/lib/api";
import { cn } from "@/lib/utils";

interface JobCardProps {
  /** Job UUID — required for navigation and save. */
  id?: string;
  title: string;
  company: string | null;
  location: string | null;
  skills: string[];
  closingDate: string | null;
  postedAt?: string | null;
  salaryMin?: number | null;
  salaryMax?: number | null;
  employmentType?: EmploymentType | null;
  workArrangement?: WorkArrangement | null;
  hybridDaysPerWeek?: number | null;
  payFrequency?: PayFrequency | null;
  /**
   * Personalised match score (0–100) from match_jobs_for_user. Only set
   * when rendering inside an authenticated, CV-backed context like /matches.
   */
  matchScore?: number;
  /** Skills that overlap the viewer's CV — highlighted on the card. */
  matchedSkills?: string[];
  /** When set with `id`, shows save / unsave (guests get a sign-in toast). */
  saveToken?: string | null;
  jobSaved?: boolean;
  onSaveChange?: (jobId: string, nextSaved: boolean) => void;
  /** Greyed closed listing still visible in the 3-day grace window. */
  listingClosed?: boolean;
}

const EMPLOYMENT_TYPE_LABEL: Record<string, string> = {
  full_time: "Full-time",
  part_time: "Part-time",
  contract: "Contract",
  freelance: "Freelance",
  internship: "Internship",
  temporary: "Temporary",
};

const WORK_ARRANGEMENT_LABEL: Record<string, string> = {
  remote: "Remote",
  hybrid: "Hybrid",
  on_site: "On-site",
};

const PAY_FREQUENCY_SUFFIX: Record<string, string> = {
  monthly: "/mo",
  annual: "/yr",
  hourly: "/hr",
  daily: "/day",
};

function formatSalaryRange(
  min?: number | null,
  max?: number | null,
  payFrequency?: PayFrequency | null,
): string | null {
  if (!min && !max) return null;
  const fmt = (ngwee: number) =>
    `K${(ngwee / 100).toLocaleString("en-ZM", { maximumFractionDigits: 0 })}`;
  const suffix = payFrequency ? PAY_FREQUENCY_SUFFIX[payFrequency] ?? "" : "";
  if (min && max && min !== max) return `${fmt(min)} - ${fmt(max)}${suffix}`;
  return `${fmt(min ?? max ?? 0)}${suffix}`;
}

function formatSetup(
  workArrangement?: WorkArrangement | null,
  hybridDays?: number | null,
): string | null {
  if (!workArrangement) return null;
  const base =
    WORK_ARRANGEMENT_LABEL[workArrangement] ?? workArrangement.replace(/_/g, " ");
  if (workArrangement === "hybrid" && hybridDays != null && hybridDays > 0) {
    const dayWord = hybridDays === 1 ? "day" : "days";
    return `${base} · ${hybridDays} ${dayWord} office`;
  }
  return base;
}

function formatJobType(employmentType?: EmploymentType | null): string | null {
  if (!employmentType) return null;
  return (
    EMPLOYMENT_TYPE_LABEL[employmentType] ??
    employmentType.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
  );
}

function daysUntilClose(closingDate: string | null | undefined): number | null {
  if (!closingDate) return null;
  const end = new Date(closingDate);
  if (Number.isNaN(end.getTime())) return null;
  return Math.ceil((end.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
}

function closesInLabel(days: number): string {
  if (days < 0) return "Closed";
  if (days === 0) return "Closes today";
  if (days === 1) return "Closes tomorrow";
  return `Closes in ${days} days`;
}

function closesInToneClass(days: number): string {
  if (days < 0) {
    return "text-muted-foreground border-border/50 bg-muted/20";
  }
  if (days < 3) {
    return "text-red-500 border-red-500/20 bg-red-500/10 dark:text-red-400";
  }
  if (days < 7) {
    return "text-orange-500 border-orange-500/20 bg-orange-500/10 dark:text-orange-400";
  }
  return "text-green-600 border-green-500/20 bg-green-500/10 dark:text-green-400";
}

function ClosesInPill({ closingDate }: { closingDate: string | null }) {
  const days = daysUntilClose(closingDate);
  if (days === null) return null;
  return (
    <Badge
      variant="outline"
      className={cn(
        "shrink-0 border font-medium tabular-nums",
        closesInToneClass(days),
      )}
    >
      {closesInLabel(days)}
    </Badge>
  );
}

function MatchPill({ score }: { score: number }) {
  let tone =
    "text-muted-foreground border-border/50 bg-muted/20 dark:text-muted-foreground";
  if (score >= 75) {
    tone = "text-green-600 border-green-500/25 bg-green-500/10 dark:text-green-400";
  } else if (score >= 50) {
    tone = "text-orange-500 border-orange-500/20 bg-orange-500/10 dark:text-orange-400";
  }
  return (
    <Badge
      variant="outline"
      className={cn("shrink-0 border font-semibold tabular-nums", tone)}
      title="Match score based on your CV and skills"
    >
      {Math.round(score)}% match
    </Badge>
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
  return `Posted ${Math.floor(days / 30)}mo ago`;
}

function SkillPill({ skill, matched }: { skill: string; matched: boolean }) {
  return (
    <Badge
      variant="outline"
      className={cn(
        "text-xs font-normal",
        matched
          ? "border-green-500/30 bg-green-500/20 text-green-400"
          : "border-border/60 bg-muted/30 text-muted-foreground",
      )}
    >
      {matched && <Icon name="check" size={10} className="mr-0.5" />}
      {skill}
    </Badge>
  );
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
  employmentType,
  workArrangement,
  hybridDaysPerWeek,
  payFrequency,
  matchScore,
  matchedSkills = [],
  saveToken,
  jobSaved = false,
  onSaveChange,
  listingClosed = false,
}: JobCardProps) {
  const matchedSet = new Set(matchedSkills.map((s) => s.toLowerCase()));
  const hasCvContext = matchedSet.size > 0;

  const metadataParts = [
    formatJobType(employmentType),
    formatSalaryRange(salaryMin, salaryMax, payFrequency),
    formatSetup(workArrangement, hybridDaysPerWeek),
  ].filter((part): part is string => Boolean(part));

  const postedLabel = formatRelativeTime(postedAt);
  const href = id ? `/jobs/${id}` : undefined;

  const cardBody = (
    <>
      {listingClosed && (
        <span className="absolute top-3 right-3 z-10 px-2 py-0.5 rounded text-[10px] font-bold font-mono tracking-wide bg-destructive text-destructive-foreground">
          CLOSED
        </span>
      )}
      <div className="flex items-start gap-3 pr-10 sm:pr-12">
        <Avatar name={company || "ZC"} size={40} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <h3
              className={cn(
                "font-display text-lg sm:text-xl leading-snug text-foreground truncate",
                listingClosed && "line-through opacity-80",
              )}
            >
              {title}
            </h3>
            <div className="flex flex-wrap items-center justify-end gap-1.5 shrink-0">
              <ClosesInPill closingDate={closingDate} />
              {typeof matchScore === "number" && <MatchPill score={matchScore} />}
            </div>
          </div>
          <p className="mt-0.5 text-sm text-muted-foreground truncate">
            {company || "Company not listed"}
            {location ? (
              <span>
                {" "}
                &middot; {location}
              </span>
            ) : null}
          </p>
          {metadataParts.length > 0 && (
            <p className="mt-2 text-xs sm:text-sm text-foreground/80 flex flex-wrap items-center gap-x-1.5 gap-y-1">
              {metadataParts.map((part, index) => (
                <span key={part} className="inline-flex items-center gap-1.5">
                  {index > 0 && (
                    <span className="text-muted-foreground/60" aria-hidden>
                      ·
                    </span>
                  )}
                  <span className="rounded-md border border-border/50 bg-muted/20 px-2 py-0.5 text-xs font-medium">
                    {part}
                  </span>
                </span>
              ))}
            </p>
          )}
        </div>
      </div>

      {skills.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-1.5">
          {skills.slice(0, 8).map((skill) => (
            <SkillPill
              key={skill}
              skill={skill}
              matched={hasCvContext && matchedSet.has(skill.toLowerCase())}
            />
          ))}
          {skills.length > 8 && (
            <span className="self-center text-xs text-muted-foreground">
              +{skills.length - 8} more
            </span>
          )}
        </div>
      )}

      {postedLabel && (
        <p className="mt-3 text-xs text-muted-foreground">{postedLabel}</p>
      )}
    </>
  );

  return (
    <article
      className={cn(
        "group relative w-full rounded-xl border border-border/80",
        "bg-card",
        "job-card shadow-sm",
        "hover:border-border",
        "focus-within:ring-2 focus-within:ring-primary/40 focus-within:ring-offset-2 focus-within:ring-offset-background",
      )}
      style={{ opacity: listingClosed ? 0.6 : 1 }}
    >
      {id && saveToken !== undefined && (
        <div
          className="absolute top-4 right-4 z-10"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
          }}
          onKeyDown={(e) => e.stopPropagation()}
        >
          <SaveJobButton
            jobId={id}
            saved={jobSaved}
            token={saveToken}
            onChange={onSaveChange}
            className="!min-h-9 !h-9 !w-9 !p-0 !rounded-full !border-border/60 !bg-background/90 dark:!bg-secondary hover:!bg-muted"
          />
        </div>
      )}

      {href ? (
        <Link
          href={href}
          className="block p-5 sm:p-6 rounded-xl outline-none"
          aria-label={`View ${title}${company ? ` at ${company}` : ""}`}
        >
          {cardBody}
        </Link>
      ) : (
        <div className="p-5 sm:p-6">{cardBody}</div>
      )}
    </article>
  );
}
