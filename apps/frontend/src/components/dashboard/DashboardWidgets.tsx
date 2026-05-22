import Link from "next/link";
import { Icon } from "@/components/ui/Icon";
import { Avatar } from "@/components/ui/Avatar";
import { cn } from "@/lib/utils";
import type {
  ActivityItem,
  CondensedMatchJob,
  DashboardStat,
} from "./dashboard-mock-data";

const cardShell =
  "relative overflow-hidden rounded-xl border border-zinc-800/80 bg-zinc-900/50 dark:border-zinc-800/80 dark:bg-zinc-900/50";

function CardTopAccent() {
  return (
    <div
      className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-amber-500/50 to-transparent"
      aria-hidden
    />
  );
}

export function DashboardStatCard({ label, value, detail }: DashboardStat) {
  return (
    <div className={cn(cardShell, "p-4 sm:p-5")}>
      <CardTopAccent />
      <p className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">
        {label}
      </p>
      <p className="mt-2 font-mono text-2xl font-semibold tabular-nums text-zinc-50">
        {value}
        {detail ? (
          <span className="ml-1.5 text-base font-normal text-zinc-500">
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
      ? "bg-emerald-500/15 text-emerald-400 ring-emerald-500/30"
      : score >= 70
        ? "bg-amber-500/15 text-amber-400 ring-amber-500/30"
        : "bg-zinc-800 text-zinc-400 ring-zinc-700";
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
    <article
      className={cn(
        cardShell,
        "group p-4 transition-colors hover:border-zinc-700 hover:bg-zinc-900/70"
      )}
    >
      <CardTopAccent />
      <div className="flex items-start gap-3">
        <Avatar name={job.company} size={32} />
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <h3 className="truncate text-sm font-semibold text-zinc-100 group-hover:text-white">
              {job.title}
            </h3>
            <MatchScoreBadge score={job.matchScore} />
          </div>
          <p className="mt-0.5 truncate text-xs text-zinc-500">
            {job.company} · {job.location}
          </p>
          {job.salaryLabel ? (
            <p className="mt-1 font-mono text-xs text-zinc-400">{job.salaryLabel}/mo</p>
          ) : null}
          {job.matchedSkills.length > 0 ? (
            <div className="mt-2 flex flex-wrap gap-1">
              {job.matchedSkills.slice(0, 3).map((skill) => (
                <span
                  key={skill}
                  className="rounded-md bg-zinc-800/80 px-1.5 py-0.5 text-[10px] text-zinc-400"
                >
                  {skill}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </article>
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
    <div className={cn(cardShell, "p-5")}>
      <CardTopAccent />
      <h2 className="text-sm font-semibold text-zinc-200">Profile completeness</h2>
      <div className="mt-4 flex flex-col items-center gap-4 sm:flex-row sm:items-start">
        <div className="relative shrink-0">
          <svg width={size} height={size} className="-rotate-90" aria-hidden>
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              className="stroke-zinc-800"
              strokeWidth={stroke}
            />
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              className="stroke-amber-500"
              strokeWidth={stroke}
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
            />
          </svg>
          <span className="absolute inset-0 flex items-center justify-center font-mono text-2xl font-bold text-amber-400">
            {percent}%
          </span>
        </div>
        <ul className="flex-1 space-y-2 text-xs text-zinc-500">
          {hints.map((hint) => (
            <li key={hint} className="flex items-start gap-2">
              <Icon name="chevronRight" size={12} className="mt-0.5 shrink-0 text-zinc-600" />
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
    <div className={cn(cardShell, "p-5")}>
      <CardTopAccent />
      <h2 className="text-sm font-semibold text-zinc-200">Recent activity</h2>
      <ul className="mt-4 space-y-0">
        {items.map((item, index) => (
          <li key={item.id} className="relative flex gap-3 pb-5 last:pb-0">
            {index < items.length - 1 ? (
              <span
                className="absolute left-[15px] top-8 bottom-0 w-px bg-zinc-800"
                aria-hidden
              />
            ) : null}
            <span className="relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-zinc-700 bg-zinc-800/80 text-amber-500/90">
              <Icon name={item.icon} size={14} />
            </span>
            <div className="min-w-0 pt-0.5">
              <p className="text-sm leading-snug text-zinc-300">{item.title}</p>
              <p className="mt-0.5 text-xs text-zinc-600">{item.time}</p>
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
        "flex flex-col gap-4 border-amber-500/20 bg-gradient-to-br from-zinc-900/80 via-zinc-900/50 to-amber-950/20 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6"
      )}
    >
      <CardTopAccent />
      <div>
        <p className="text-xs font-medium uppercase tracking-wider text-amber-500/80">
          Plan upgrade
        </p>
        <p className="mt-1 text-base text-zinc-200 sm:text-lg">
          You&apos;re on <span className="font-semibold text-zinc-50">{currentTier}</span>.
          Unlock unlimited matches.
        </p>
      </div>
      <Link
        href="/pricing"
        className="inline-flex h-11 shrink-0 items-center justify-center rounded-lg bg-amber-500 px-5 text-sm font-semibold text-zinc-950 transition-colors hover:bg-amber-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-400"
      >
        Upgrade to {upgradeTier}
      </Link>
    </div>
  );
}
