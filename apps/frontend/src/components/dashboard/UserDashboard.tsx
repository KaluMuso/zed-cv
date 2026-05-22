"use client";

import Link from "next/link";
import { MOCK_DASHBOARD } from "./dashboard-mock-data";
import { formatDashboardHeaderDate } from "./format-dashboard-date";
import {
  CondensedJobCard,
  DashboardStatCard,
  ProfileCompletenessRing,
  RecentActivityTimeline,
  UpgradeBanner,
} from "./DashboardWidgets";

export type UserDashboardProps = {
  /** Override mock display name */
  userName?: string;
};

export function UserDashboard({ userName }: UserDashboardProps) {
  const data = MOCK_DASHBOARD;
  const displayName = userName ?? data.userName;
  const headerDate = formatDashboardHeaderDate(new Date());

  return (
    <div className="mx-auto w-full max-w-6xl space-y-8 pb-10 text-zinc-100">
      <header className="space-y-2">
        <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-zinc-500">
          {headerDate}
        </p>
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-50 sm:text-3xl">
          <span className="font-serif text-amber-500 dark:text-amber-500">Mwauka uli,</span>{" "}
          {displayName}.
        </h1>
        <p className="max-w-xl text-sm text-zinc-500 sm:text-base">
          <span className="font-mono text-zinc-400">{data.whatsappMatchesToday}</span> new
          matches landed in your WhatsApp this morning.
        </p>
      </header>

      <section
        className="grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-4"
        aria-label="Dashboard statistics"
      >
        {data.stats.map((stat) => (
          <DashboardStatCard key={stat.label} {...stat} />
        ))}
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.4fr_1fr] lg:gap-8">
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">
              Top Matches Today
            </h2>
            <Link
              href="/matches"
              className="text-xs font-medium text-amber-500/90 transition-colors hover:text-amber-400"
            >
              View all
            </Link>
          </div>
          <ul className="space-y-3" aria-label="Top job matches">
            {data.topMatches.map((job) => (
              <li key={job.id}>
                <CondensedJobCard job={job} />
              </li>
            ))}
          </ul>
        </div>

        <div className="space-y-4">
          <ProfileCompletenessRing
            percent={data.profileCompleteness}
            hints={data.profileHints}
          />
          <RecentActivityTimeline items={data.recentActivity} />
        </div>
      </section>

      <UpgradeBanner
        currentTier={data.currentTier}
        upgradeTier={data.upgradeTier}
      />
    </div>
  );
}
