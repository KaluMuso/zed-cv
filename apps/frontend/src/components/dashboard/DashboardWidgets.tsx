import Link from "next/link";
import { Icon } from "@/components/ui/Icon";
import { Avatar } from "@/components/ui/Avatar";
import { btnClass, tagClass } from "@/lib/cn-ui";
import { cn } from "@/lib/utils";
import type {
  ActivityItem,
  CondensedMatchJob,
  DashboardStat,
} from "./dashboard-mock-data";

const cardShell =
  "relative overflow-hidden rounded-xl border bg-[var(--surface)]";

function CardTopAccent() {
  return (
    <div
      className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-[var(--green-400)] to-transparent opacity-60"
      aria-hidden
    />
  );
}

export function DashboardStatCard({ label, value, detail }: DashboardStat) {
  return (
    <div className={cn(cardShell, "p-4 sm:p-5")} style={{ borderColor: "var(--line)" }}>
      <CardTopAccent />
      <p
        className="text-[11px] font-medium uppercase tracking-wider"
        style={{ color: "var(--muted)" }}
      >
        {label}
      </p>
      <p
        className="mt-2 font-mono text-2xl font-semibold tabular-nums"
        style={{ color: "var(--ink)" }}
      >
        {value}
        {detail ? (
          <span className="ml-1.5 text-base font-normal" style={{ color: "var(--muted)" }}>
            {detail}
          </span>
        ) : null}
      </p>
    </div>
  );
}

function MatchScoreBadge({ score }: { score: number }) {
  const tone =
    score >= 85
      ? "bg-[var(--green-50)] text-[var(--green-700)] ring-[var(--green-300)]"
      : score >= 70
        ? "bg-[var(--copper-100)] text-[var(--copper-600)] ring-[var(--copper-300)]"
        : "bg-[var(--bg-2)] text-[var(--muted)] ring-[var(--line)]";
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 font-mono text-xs font-semibold ring-1 ring-inset",
        tone
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-80" />
      {score}%
    </span>
  );
}

export function CondensedJobCard({ job }: { job: CondensedMatchJob }) {
  return (
    <Link href={`/jobs/${job.id}`} className="block">
    <article
      className={cn(
        cardShell,
        "group p-4 transition-colors hover:shadow-md"
      )}
      style={{ borderColor: "var(--line)" }}
    >
      <CardTopAccent />
      <div className="flex items-start gap-3">
        <Avatar name={job.company} size={32} />
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <h3 className="truncate text-sm font-semibold group-hover:underline" style={{ color: "var(--ink)" }}>
              {job.title}
            </h3>
            <MatchScoreBadge score={job.matchScore} />
          </div>
          <p className="mt-0.5 truncate text-xs" style={{ color: "var(--muted)" }}>
            {job.company} · {job.location}
          </p>
          {job.salaryLabel ? (
            <p className="mt-1 font-mono text-xs" style={{ color: "var(--muted)" }}>
              {job.salaryLabel}/mo
            </p>
          ) : null}
          {job.matchedSkills.length > 0 ? (
            <div className="mt-2 flex flex-wrap gap-1">
              {job.matchedSkills.slice(0, 3).map((skill) => (
                <span key={skill} className={tagClass("green", "text-[10px] py-0.5")}>
                  {skill}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </article>
    </Link>
  );
}

export function ProfileCompletenessRing({
  percent,
  hints,
}: {
  percent: number;
  hints: readonly string[];
}) {
  const size = 112;
  const stroke = 8;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percent / 100) * circumference;

  return (
    <div className={cn(cardShell, "p-5")} style={{ borderColor: "var(--line)" }}>
      <CardTopAccent />
      <h2 className="text-sm font-semibold" style={{ color: "var(--ink)" }}>
        Profile completeness
      </h2>
      <div className="mt-4 flex flex-col items-center gap-4 sm:flex-row sm:items-start">
        <div className="relative shrink-0">
          <svg width={size} height={size} className="-rotate-90" aria-hidden>
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke="var(--bg-2)"
              strokeWidth={stroke}
            />
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke="var(--copper-500)"
              strokeWidth={stroke}
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
            />
          </svg>
          <span
            className="absolute inset-0 flex items-center justify-center font-mono text-2xl font-bold"
            style={{ color: "var(--copper-600)" }}
          >
            {percent}%
          </span>
        </div>
        <ul className="flex-1 space-y-2 text-xs" style={{ color: "var(--muted)" }}>
          {hints.map((hint) => (
            <li key={hint} className="flex items-start gap-2">
              <Icon
                name="chevronRight"
                size={12}
                className="mt-0.5 shrink-0 text-muted-foreground"
              />
              <span>{hint}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export function RecentActivityTimeline({ items }: { items: readonly ActivityItem[] }) {
  return (
    <div className={cn(cardShell, "p-5")} style={{ borderColor: "var(--line)" }}>
      <CardTopAccent />
      <h2 className="text-sm font-semibold" style={{ color: "var(--ink)" }}>
        Recent activity
      </h2>
      <ul className="mt-4 space-y-0">
        {items.map((item, index) => (
          <li key={item.id} className="relative flex gap-3 pb-5 last:pb-0">
            {index < items.length - 1 ? (
              <span
                className="absolute left-[15px] top-8 bottom-0 w-px"
                style={{ background: "var(--line)" }}
                aria-hidden
              />
            ) : null}
            <span
              className="relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border"
              style={{
                borderColor: "var(--line)",
                background: "var(--bg-2)",
                color: "var(--copper-600)",
              }}
            >
              <Icon name={item.icon} size={14} />
            </span>
            <div className="min-w-0 pt-0.5">
              <p className="text-sm leading-snug" style={{ color: "var(--ink-2)" }}>
                {item.title}
              </p>
              <p className="mt-0.5 text-xs" style={{ color: "var(--muted)" }}>
                {item.time}
              </p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function UpgradeBanner({
  currentTier,
  upgradeTier,
}: {
  currentTier: string;
  upgradeTier: string;
}) {
  return (
    <div
      className={cn(
        cardShell,
        "flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6",
      )}
      style={{
        borderColor: "var(--copper-300)",
        background:
          "linear-gradient(135deg, color-mix(in oklab, var(--copper-100) 40%, var(--surface)) 0%, var(--surface) 60%)",
      }}
    >
      <CardTopAccent />
      <div>
        <p
          className="text-xs font-medium uppercase tracking-wider"
          style={{ color: "var(--copper-600)" }}
        >
          Plan upgrade
        </p>
        <p className="mt-1 text-base sm:text-lg" style={{ color: "var(--ink-2)" }}>
          You&apos;re on <span className="font-semibold" style={{ color: "var(--ink)" }}>{currentTier}</span>.
          Unlock unlimited matches.
        </p>
      </div>
      <Link href="/pricing" className={btnClass("accent", "default", "shrink-0")}>
        Upgrade to {upgradeTier}
      </Link>
    </div>
  );
}
