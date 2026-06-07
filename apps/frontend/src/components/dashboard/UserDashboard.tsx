"use client";

import Link from "next/link";
import { btnClass } from "@/lib/cn-ui";
import type { MatchData, Subscription } from "@/lib/api";
import { MOCK_DASHBOARD } from "./dashboard-mock-data";
import { formatDashboardHeaderDate } from "./format-dashboard-date";
import { formatSalary } from "@/components/jobs/jobDetailFormatters";
import type { DashboardQuotaDisplay } from "@/lib/dashboard-stats";
import { formatTierLabel, getNextUpgradeTier } from "@/lib/tier-display";
import { PlanUsageCard } from "./PlanUsageCard";
import {
  CondensedJobCard,
  DashboardStatCard,
  ProfileCompletenessRing,
  RecentActivityTimeline,
  UpgradeBanner,
} from "./DashboardWidgets";
import { DashboardInsights, type ApplicationFunnel } from "./DashboardInsights";
import { ProfileReferralCard } from "@/app/profile/_tabs/ProfileReferralCard";

export type DashboardLiveData = {
  totalMatches: number;
  savedJobs: number;
  avgScore: number | null;
  topMatches: MatchData[];
};

const EMPTY_FUNNEL: ApplicationFunnel = {
  saved: 0,
  applied: 0,
  interviewing: 0,
  offered: 0,
  closed: 0,
};

export type UserDashboardProps = {
  userName?: string;
  liveData?: DashboardLiveData;
  subscription?: Subscription | null;
  subscriptionTier?: string;
  subscriptionTierLabel?: string;
  matchQuota?: DashboardQuotaDisplay;
  profileCompleteness?: { percent: number; hints: readonly string[] };
  applicationsCount?: number;
  applicationFunnel?: ApplicationFunnel;
  /** Referral card — all optional so mock / logged-out mode never crashes. */
  userId?: string;
  referralCode?: string;
  referralSignupsCount?: number;
  referralQualifiedCount?: number;
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

export function UserDashboard({
  userName,
  liveData,
  subscription,
  subscriptionTier = "free",
  subscriptionTierLabel,
  matchQuota,
  profileCompleteness,
  applicationsCount = 0,
  applicationFunnel,
  userId = "",
  referralCode = "",
  referralSignupsCount = 0,
  referralQualifiedCount = 0,
}: UserDashboardProps) {
  const data = MOCK_DASHBOARD;
  const displayName = userName ?? data.userName;
  const headerDate = formatDashboardHeaderDate(new Date());
  const useLive = Boolean(liveData);

  const quotaPct =
    matchQuota && !matchQuota.unlimited
      ? Math.round(matchQuota.usagePct)
      : null;
  const nextUpgradeTier = getNextUpgradeTier(subscriptionTier);
  const currentTierLabel = subscriptionTierLabel ?? formatTierLabel(subscriptionTier);
  const upgradeTierLabel = nextUpgradeTier ? formatTierLabel(nextUpgradeTier) : null;

  const stats = useLive
    ? [
        {
          label: "Total matches",
          value: String(liveData!.totalMatches),
          detail: quotaPct != null ? `${quotaPct}% of quota` : undefined,
        },
        {
          label: "In pipeline",
          value: String(applicationsCount),
          detail: "applications",
        },
        {
          label: "Saved jobs",
          value: String(liveData!.savedJobs),
        },
        {
          label: "Avg. match score",
          value: liveData!.avgScore != null ? `${liveData!.avgScore}%` : "—",
          detail: liveData!.avgScore != null && liveData!.avgScore >= 70 ? "Strong" : undefined,
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

      {useLive ? (
        <PlanUsageCard
          tier={subscriptionTier}
          sub={subscription ?? null}
          quota={matchQuota}
        />
      ) : null}

      {useLive && liveData && matchQuota ? (
        <DashboardInsights
          totalMatches={liveData.totalMatches}
          avgScore={liveData.avgScore}
          topScore={liveData.topMatches[0]?.score ?? null}
          quota={matchQuota}
          funnel={applicationFunnel ?? EMPTY_FUNNEL}
        />
      ) : null}

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
          <Link href="/matches" className={btnClass("primary", "sm")}>
            View matches
          </Link>
          <Link href="/profile?tab=cv-skills" className={btnClass("outline", "sm")}>
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
          {referralCode ? (
            <ProfileReferralCard
              userId={userId}
              userName={userName}
              referralCode={referralCode}
              referralSignupsCount={referralSignupsCount}
              referralQualifiedCount={referralQualifiedCount}
            />
          ) : null}
          {profileCompleteness ? (
            <ProfileCompletenessRing
              percent={profileCompleteness.percent}
              hints={profileCompleteness.hints}
            />
          ) : !useLive ? (
            <ProfileCompletenessRing
              percent={data.profileCompleteness}
              hints={data.profileHints}
            />
          ) : null}
          {!useLive ? (
            <RecentActivityTimeline items={data.recentActivity} />
          ) : (
            <div
              className="rounded-xl border p-5"
              style={{ borderColor: "var(--line)", background: "var(--surface)" }}
            >
              <h2 className="type-section-title mb-3">Recent actions</h2>
              <ul className="space-y-2 text-sm" style={{ color: "var(--muted)" }}>
                <li>
                  <Link href="/matches" className="hover:underline" style={{ color: "var(--green-700)" }}>
                    Review {liveData?.totalMatches ?? 0} matches
                  </Link>
                </li>
                <li>
                  <Link href="/applications" className="hover:underline" style={{ color: "var(--green-700)" }}>
                    Track {applicationsCount} applications
                  </Link>
                </li>
                <li>
                  <Link href="/jobs" className="hover:underline" style={{ color: "var(--green-700)" }}>
                    Browse open roles
                  </Link>
                </li>
              </ul>
            </div>
          )}
        </div>
      </section>

      {subscriptionTier !== "super_standard" && (useLive ? upgradeTierLabel : data.upgradeTier) ? (
        <UpgradeBanner
          currentTier={useLive ? currentTierLabel : data.currentTier}
          upgradeTier={useLive ? upgradeTierLabel! : data.upgradeTier}
        />
      ) : null}
    </div>
  );
}
