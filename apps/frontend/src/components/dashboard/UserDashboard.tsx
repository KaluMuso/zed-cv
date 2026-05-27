"use client";

import Link from "next/link";
import type { MatchData } from "@/lib/api";
import { MOCK_DASHBOARD } from "./dashboard-mock-data";
import { formatDashboardHeaderDate } from "./format-dashboard-date";
import { formatSalary } from "@/components/jobs/jobDetailFormatters";
import {
  CondensedJobCard,
  DashboardStatCard,
  ProfileCompletenessRing,
  RecentActivityTimeline,
  UpgradeBanner,
} from "./DashboardWidgets";

export type DashboardLiveData = {
  totalMatches: number;
  savedJobs: number;
  avgScore: number | null;
  topMatches: MatchData[];
};

export type UserDashboardProps = {
  userName?: string;
  liveData?: DashboardLiveData;
};

function mapMatchToCondensed(m: MatchData) {
  const salary = formatSalary(m.job.salary_min, m.job.salary_max);
  return {
    id: m.job.id,
    title: m.job.title,
    company: m.job.company || "Company",
    location: m.job.location || "Zambia",
    matchScore: m.score,
    matchedSkills: m.matched_skills.slice(0, 4),
    salaryLabel: salary,
  };
}

export function UserDashboard({ userName, liveData }: UserDashboardProps) {
  const data = MOCK_DASHBOARD;
  const displayName = userName ?? data.userName;
  const headerDate = formatDashboardHeaderDate(new Date());
  const useLive = Boolean(liveData);

  const stats = useLive
    ? [
        {
          label: "Total matches",
          value: String(liveData!.totalMatches),
        },
        {
          label: "Saved jobs",
          value: String(liveData!.savedJobs),
        },
        {
          label: "Avg. match score",
          value: liveData!.avgScore != null ? `${liveData!.avgScore}%` : "—",
        },
        {
          label: "Top match today",
          value:
            liveData!.topMatches[0] != null
              ? `${liveData!.topMatches[0].score}%`
              : "—",
        },
      ]
    : data.stats;

  const topMatches = useLive
    ? liveData!.topMatches.map(mapMatchToCondensed)
    : data.topMatches;

  return (
    <div className="mx-auto w-full max-w-6xl space-y-8 pb-10" style={{ color: "var(--ink)" }}>
      <header className="space-y-2">
        <p
          className="text-[11px] font-medium uppercase tracking-[0.2em]"
          style={{ color: "var(--muted)" }}
        >
          {headerDate}
        </p>
        <h1
          className="font-display text-2xl sm:text-3xl tracking-tight"
          style={{ letterSpacing: "-0.02em" }}
        >
          <span style={{ color: "var(--green-700)" }}>Mwauka uli,</span> {displayName}.
        </h1>
        <p className="max-w-xl text-sm sm:text-base" style={{ color: "var(--muted)" }}>
          {useLive ? (
            <>
              You have <span className="font-mono font-medium">{liveData!.totalMatches}</span>{" "}
              active matches. Review your best fits or refresh from the matches page.
            </>
          ) : (
            <>
              <span className="font-mono">{data.whatsappMatchesToday}</span> new matches landed in
              your WhatsApp this morning.
            </>
          )}
        </p>
      </header>

      <section
        className="rounded-xl border p-5 sm:p-6"
        style={{ borderColor: "var(--line)", background: "var(--surface)" }}
      >
        <h2 className="text-sm font-semibold mb-2" style={{ color: "var(--ink)" }}>
          Your next step
        </h2>
        <p className="text-sm mb-4" style={{ color: "var(--muted)" }}>
          {liveData?.topMatches.length
            ? "Open your strongest match and apply with a tailored CV."
            : "Upload your CV and run matching to see roles here."}
        </p>
        <div className="flex flex-wrap gap-2">
          <Link href="/matches" className="btn btn-primary btn-sm">
            View matches
          </Link>
          <Link href="/profile?tab=cv-skills" className="btn btn-outline btn-sm">
            Upload CV
          </Link>
        </div>
      </section>

      <section
        className="grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-4"
        aria-label="Dashboard statistics"
      >
        {stats.map((stat) => (
          <DashboardStatCard key={stat.label} {...stat} />
        ))}
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.4fr_1fr] lg:gap-8">
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-3">
            <h2
              className="text-xs font-bold uppercase tracking-widest"
              style={{ color: "var(--muted)" }}
            >
              Recent matches
            </h2>
            <Link
              href="/matches"
              className="text-xs font-medium hover:underline"
              style={{ color: "var(--green-700)" }}
            >
              View all
            </Link>
          </div>
          {topMatches.length === 0 ? (
            <p className="text-sm py-8 text-center rounded-xl border" style={{ borderColor: "var(--line)", color: "var(--muted)" }}>
              No matches yet.{" "}
              <Link href="/matches" className="underline" style={{ color: "var(--green-700)" }}>
                Refresh matches
              </Link>
            </p>
          ) : (
            <ul className="space-y-3" aria-label="Top job matches">
              {topMatches.map((job) => (
                <li key={job.id}>
                  <CondensedJobCard job={job} />
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="space-y-4">
          <div
            className="rounded-xl border p-5"
            style={{ borderColor: "var(--line)", background: "var(--surface)" }}
          >
            <h2 className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: "var(--muted)" }}>
              Quick actions
            </h2>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/profile?tab=cv-skills" className="hover:underline" style={{ color: "var(--green-700)" }}>
                  Upload CV
                </Link>
              </li>
              <li>
                <Link href="/matches" className="hover:underline" style={{ color: "var(--green-700)" }}>
                  Refresh matches
                </Link>
              </li>
              <li>
                <Link href="/applications" className="hover:underline" style={{ color: "var(--green-700)" }}>
                  Track applications
                </Link>
              </li>
              <li>
                <Link href="/jobs" className="hover:underline" style={{ color: "var(--green-700)" }}>
                  Browse all jobs
                </Link>
              </li>
            </ul>
          </div>
          {!useLive && (
            <>
              <ProfileCompletenessRing
                percent={data.profileCompleteness}
                hints={data.profileHints}
              />
              <RecentActivityTimeline items={data.recentActivity} />
            </>
          )}
        </div>
      </section>

      {!useLive && (
        <UpgradeBanner currentTier={data.currentTier} upgradeTier={data.upgradeTier} />
      )}
    </div>
  );
}
