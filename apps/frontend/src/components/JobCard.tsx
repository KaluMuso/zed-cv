"use client";

import { Icon } from "@/components/ui/Icon";
import { Avatar } from "@/components/ui/Avatar";

interface JobCardProps {
  title: string;
  company: string | null;
  location: string | null;
  qualityScore: number;
  skills: string[];
  closingDate: string | null;
  matchedSkills?: string[];
  onClick?: () => void;
}

function ScoreBadge({ score }: { score: number }) {
  let bg: string, color: string, label: string, dotColor: string;
  if (score >= 85) {
    bg = "var(--green-100)";
    color = "var(--green-700)";
    dotColor = "var(--green-500)";
    label = "Top";
  } else if (score >= 70) {
    bg = "var(--copper-100)";
    color = "var(--copper-600)";
    dotColor = "var(--copper-500)";
    label = "Good";
  } else {
    bg = "#ffedd5";
    color = "var(--orange-600)";
    dotColor = "var(--orange-500)";
    label = "Fair";
  }

  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold font-mono"
      style={{ background: bg, color }}
    >
      <span
        className="w-1.5 h-1.5 rounded-full"
        style={{ background: dotColor }}
      />
      {Math.round(score)}% {label}
    </span>
  );
}

export function JobCard({
  title,
  company,
  location,
  qualityScore,
  skills,
  closingDate,
  matchedSkills = [],
  onClick,
}: JobCardProps) {
  const matchedSet = new Set(matchedSkills.map((s) => s.toLowerCase()));

  const closesIn = closingDate
    ? Math.ceil(
        (new Date(closingDate).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
      )
    : null;

  return (
    <button
      onClick={onClick}
      className="card card-hover w-full text-left p-5 sm:p-6"
      type="button"
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
        <ScoreBadge score={qualityScore} />
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

      {/* Metadata row */}
      <div className="mt-3 flex items-center gap-4 text-xs" style={{ color: "var(--muted)" }}>
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
              : `${closesIn} days left`}
          </span>
        )}
      </div>
    </button>
  );
}
