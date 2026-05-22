"use client";

import Link from "next/link";
import type { MatchData } from "@/lib/api";
import { Avatar } from "@/components/ui/Avatar";
import { ScoreRing } from "@/components/ui/ScoreRing";
import { DeadlineBadge } from "@/components/jobs/DeadlineBadge";
import { formatSalary } from "@/components/jobs/jobDetailFormatters";

function MiniMatchCard({ match }: { match: MatchData }) {
  const { job } = match;
  const salary = formatSalary(
    (job as { salary_min?: number | null }).salary_min,
    (job as { salary_max?: number | null }).salary_max,
  );

  return (
    <Link
      href={`/jobs/${job.id}`}
      className="card card-hover block p-4 h-full transition-shadow"
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <Avatar name={job.company || "ZC"} size={32} />
          <div className="min-w-0">
            <p className="text-xs truncate" style={{ color: "var(--muted)" }}>
              {job.company || "Company"}
            </p>
            <h3
              className="font-display text-base truncate"
              style={{ letterSpacing: "-0.01em", lineHeight: 1.2 }}
            >
              {job.title}
            </h3>
          </div>
        </div>
        <ScoreRing score={match.score} size={48} stroke={4} />
      </div>
      <div
        className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs"
        style={{ color: "var(--muted)" }}
      >
        {job.location && <span>{job.location}</span>}
        {salary && (
          <span className="font-mono" style={{ color: "var(--ink-2)" }}>
            {salary}
          </span>
        )}
        <DeadlineBadge closingDate={job.closing_date} />
      </div>
    </Link>
  );
}

export function JobDetailSimilarMatches({
  matches,
  currentJobId,
}: {
  matches: MatchData[];
  currentJobId: string;
}) {
  const similar = matches
    .filter((m) => m.job.id !== currentJobId)
    .slice(0, 3);

  if (similar.length === 0) return null;

  return (
    <section className="mt-12 pt-10 border-t" style={{ borderColor: "var(--line)" }}>
      <h2 className="text-xs font-bold tracking-widest uppercase text-muted-foreground mb-5">
        Similar matches
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {similar.map((m) => (
          <MiniMatchCard key={m.id} match={m} />
        ))}
      </div>
    </section>
  );
}
