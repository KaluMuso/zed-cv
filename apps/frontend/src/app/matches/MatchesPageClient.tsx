"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { RefreshCountdownRing } from "@/components/RefreshCountdownRing";
import { SaveJobButton } from "@/components/SaveJobButton";
import { formatMatchRelativeTime } from "@/lib/formatMatchRelativeTime";
import { isJobExpired } from "@/lib/isJobExpired";
import {
  matches as matchesApi,
  subscription as subscriptionApi,
  preferencesApi,
  profile as profileApi,
  autoMatchPreferences,
  savedJobs,
  ApiError,
  type MatchData,
  type MatchListResponse,
  type MatchRefreshResponse,
  type Subscription,
  type JobPreferences,
  type AutoMatchPreferences,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { MatchScore } from "@/components/MatchScore";
import { MatchScoreBreakdown } from "@/components/MatchScoreBreakdown";
import { SkillBadge } from "@/components/SkillBadge";
import { Icon } from "@/components/ui/Icon";
import { Avatar } from "@/components/ui/Avatar";
import { Counter } from "@/components/ui/Counter";
import Link from "next/link";
import { notify } from "@/lib/toast";
import { InterviewPrepModal } from "./_components/InterviewPrepModal";
import { CountdownRing } from "@/components/CountdownRing";
import { formatMatchedRelative } from "@/lib/formatMatchedRelative";
import { isJobPastClosing } from "@/lib/isJobPastClosing";
import { isJobHiddenFromUserFeed } from "@/lib/isJobHiddenFromUserFeed";
import { trackApplyClick } from "@/lib/trackApplyClick";
import { ApplyModal } from "@/components/jobs/ApplyModal";

// Human-friendly tier label. Free → "Free", super_standard → "Super",
// etc. Falls back to the raw key if we don't recognize it so we don't
// hide unknown tiers entirely.
const MATCHES_CACHE_KEY = "zedapply_matches_cache_v1";
/** Seconds for refresh countdown ring when API omits estimated_seconds. */
const DEFAULT_REFRESH_COUNTDOWN_SECONDS = 30;
const REFRESH_MAX_WAIT_MS = 30_000;

function formatLastBatchRun(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const at = new Date(iso);
  if (Number.isNaN(at.getTime())) return null;
  const hours = Math.floor((Date.now() - at.getTime()) / (1000 * 60 * 60));
  if (hours < 1) return "less than 1h ago";
  if (hours === 1) return "1h ago";
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return days === 1 ? "1 day ago" : `${days} days ago`;
}

const TIER_LABELS: Record<string, string> = {
  free: "Free",
  starter: "Starter",
  professional: "Professional",
  super_standard: "Super",
};

export default function MatchesPageClient() {
  const router = useRouter();
  const { token, isAuthenticated, isLoading: authLoading, logout } = useAuth();
  const [data, setData] = useState<MatchRefreshResponse | null>(null);
  const [sub, setSub] = useState<Subscription | null>(null);
  const [prefs, setPrefs] = useState<JobPreferences | null>(null);
  const [autoPrefs, setAutoPrefs] = useState<AutoMatchPreferences | null>(null);
  const [savingAutoPrefs, setSavingAutoPrefs] = useState(false);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [scoreFilter, setScoreFilter] = useState(0);
  const [sort, setSort] = useState<"score" | "closing">("score");
  const [prepFor, setPrepFor] = useState<MatchData | null>(null);
  const [applyJob, setApplyJob] = useState<MatchData["job"] | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshCooldown, setRefreshCooldown] = useState(false);
  const [savedJobIds, setSavedJobIds] = useState<Set<string>>(() => new Set());
  /** UI while POST /matches/trigger + optional wait + refetch */
  const [refreshRing, setRefreshRing] = useState<{
    phase: "countdown" | "working";
    total: number;
    secondsLeft: number;
  } | null>(null);
  const refreshTimersRef = useRef<{
    tick?: ReturnType<typeof setInterval>;
    watchdog?: ReturnType<typeof setTimeout>;
  }>({});
  const [autoTriggering, setAutoTriggering] = useState(false);
  const autoTriggeredRef = useRef(false);
  const countdownTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const refreshStartedAtRef = useRef<number | null>(null);

  const loadMatches = useCallback(async (authToken: string) => {
    const [matchesRes, subRes, prefsRes, autoPrefsRes] = await Promise.allSettled([
      matchesApi.get(authToken),
      subscriptionApi.get(authToken),
      preferencesApi.get(authToken),
      autoMatchPreferences.get(authToken),
    ]);
    const unauthorized =
      (matchesRes.status === "rejected" &&
        matchesRes.reason instanceof ApiError &&
        matchesRes.reason.status === 401) ||
      (subRes.status === "rejected" &&
        subRes.reason instanceof ApiError &&
        subRes.reason.status === 401);
    if (unauthorized) {
      return { unauthorized: true } as const;
    }
    if (matchesRes.status === "fulfilled") setData(matchesRes.value);
    if (subRes.status === "fulfilled") setSub(subRes.value);
    if (prefsRes.status === "fulfilled") setPrefs(prefsRes.value);
    if (autoPrefsRes.status === "fulfilled") setAutoPrefs(autoPrefsRes.value);
    return {
      unauthorized: false,
      matches: matchesRes.status === "fulfilled" ? matchesRes.value : null,
    } as const;
  }, []);

  useEffect(() => {
    if (!token) {
      setSavedJobIds(new Set());
      return;
    }
    let cancelled = false;
    savedJobs
      .list(token)
      .then((res) => {
        if (!cancelled) setSavedJobIds(new Set(res.jobs.map((j) => j.id)));
      })
      .catch(() => {
        if (!cancelled) setSavedJobIds(new Set());
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(
    () => () => {
      if (refreshTimersRef.current.tick) {
        clearInterval(refreshTimersRef.current.tick);
      }
      if (refreshTimersRef.current.watchdog) {
        clearTimeout(refreshTimersRef.current.watchdog);
      }
    },
    [],
  );

  const handleRefreshMatches = useCallback(async () => {
    if (!token || refreshing || refreshCooldown) return;
    const preIds = new Set((data?.matches ?? []).map((m) => m.id));

    setRefreshing(true);
    setRefreshRing(null);
    try {
      const refreshed = await matchesApi.refresh(token);
      setData(refreshed);
      const next = refreshed.matches ?? [];
      const newOnes = next.filter((m) => !preIds.has(m.id));
      if (refreshed.message) {
        notify.custom.message(refreshed.message);
      } else if (newOnes.length > 0) {
        notify.custom.success(`${newOnes.length} new matches scored.`);
      } else {
        notify.custom.message("Your queue is up to date with the latest nightly batch.");
      }
    } catch (e: unknown) {
      if (e instanceof ApiError) {
        if (e.status === 403) notify.error("Monthly match quota used up.");
        else if (e.status === 422) notify.error("Upload a CV first before matching.");
        else if (e.status === 429)
          notify.error("Too many refreshes — try again in a minute.");
        else
          notify.error(e.detail || "Couldn't refresh matches. Try again in a moment.");
      } else {
        notify.error("Couldn't refresh matches. Try again in a moment.");
      }
    } finally {
      setRefreshing(false);
      setRefreshCooldown(true);
      setTimeout(() => setRefreshCooldown(false), 60_000);
    }
  }, [token, refreshing, refreshCooldown, data]);

  const toggleAutoMatch = useCallback(async () => {
    if (!token || !autoPrefs || savingAutoPrefs) return;
    const next = !autoPrefs.auto_match_enabled;
    setSavingAutoPrefs(true);
    try {
      const saved = await autoMatchPreferences.patch(token, { auto_match_enabled: next });
      setAutoPrefs(saved);
      notify.custom.success(next ? "Auto-match is on." : "Auto-match is off.");
    } catch (e: unknown) {
      notify.error(e instanceof Error ? e.message : "Could not update auto-match.");
    } finally {
      setSavingAutoPrefs(false);
    }
  }, [token, autoPrefs, savingAutoPrefs]);

  useEffect(() => {
    if (authLoading) return;
    if (!isAuthenticated || !token) {
      router.push("/auth");
      return;
    }
    try {
      const cached = sessionStorage.getItem(MATCHES_CACHE_KEY);
      if (cached) {
        const parsed = JSON.parse(cached) as MatchListResponse;
        if (parsed?.matches) setData(parsed);
      }
    } catch {
      /* ignore corrupt cache */
    }
    loadMatches(token).then(async (result) => {
      if (result.unauthorized) {
        logout();
        router.replace("/auth?next=/matches");
        return;
      }
      // First visit with CV but no rows yet: pull cached batch or onboarding fallback
      if (
        result.matches &&
        result.matches.matches.length === 0 &&
        !autoTriggeredRef.current
      ) {
        autoTriggeredRef.current = true;
        try {
          const userProfile = await profileApi.get(token);
          if (userProfile.cv_uploaded) {
            setAutoTriggering(true);
            const refreshed = await matchesApi.refresh(token);
            setData(refreshed);
            setAutoTriggering(false);
          }
        } catch {
          setAutoTriggering(false);
        }
      }
    }).finally(() => setLoading(false));
  }, [token, isAuthenticated, authLoading, router, logout, loadMatches]);

  useEffect(() => {
    if (!data) return;
    try {
      sessionStorage.setItem(MATCHES_CACHE_KEY, JSON.stringify(data));
    } catch {
      /* quota exceeded — non-fatal */
    }
  }, [data]);

  const showInitialSkeleton = (loading || authLoading) && !data;

  if (showInitialSkeleton) {
    // Skeleton mirrors the real layout: header headline + quota card,
    // filter/sort row, then 3 match cards with the auto/1fr/auto grid
    // (circular score badge · title+meta · button stack). Same outer
    // padding as the loaded page so there's no layout shift on resolve.
    return (
      <div className="max-w-[1280px] mx-auto px-6 py-8 md:py-12">
        <div
          className="matches-header grid gap-8 items-start mb-10"
          style={{ gridTemplateColumns: "1.4fr 1fr" }}
        >
          <div>
            <div className="skeleton h-3 w-40 mb-2" />
            <div className="skeleton h-14 md:h-20 w-11/12 mb-3" />
            <div className="skeleton h-14 md:h-20 w-3/4 mb-4" />
            <div className="skeleton h-4 w-2/3" />
          </div>
          <div className="card p-6">
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <div className="skeleton h-3 w-20 mb-3" />
                <div className="skeleton h-10 w-32 mb-1" />
                <div className="skeleton h-3 w-24" />
              </div>
              <div className="skeleton h-6 w-16 rounded-full" />
            </div>
            <div className="skeleton h-2 w-full mt-5 rounded-full" />
            <div className="flex justify-between mt-3">
              <div className="skeleton h-3 w-24" />
              <div className="skeleton h-3 w-32" />
            </div>
          </div>
        </div>

        <div
          className="flex items-center justify-between flex-wrap gap-3 pb-4 mb-6"
          style={{ borderBottom: "1px solid var(--line)" }}
        >
          <div className="flex gap-2 flex-wrap">
            <div className="skeleton h-8 w-12 rounded-md" />
            <div className="skeleton h-8 w-14 rounded-md" />
            <div className="skeleton h-8 w-20 rounded-md" />
          </div>
          <div className="flex gap-2 items-center">
            <div className="skeleton h-3 w-8" />
            <div className="skeleton h-8 w-16 rounded-md" />
            <div className="skeleton h-8 w-24 rounded-md" />
          </div>
        </div>

        <div className="flex flex-col gap-3.5">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card overflow-hidden">
              <div
                className="match-row p-5 sm:p-6 grid gap-6 items-center"
                style={{ gridTemplateColumns: "auto 1fr auto" }}
              >
                <div
                  className="skeleton rounded-full"
                  style={{ width: 80, height: 80 }}
                />
                <div className="min-w-0">
                  <div className="flex items-center gap-2.5 mb-2">
                    <div
                      className="skeleton rounded-full"
                      style={{ width: 28, height: 28 }}
                    />
                    <div className="skeleton h-3 w-40" />
                  </div>
                  <div className="skeleton h-7 md:h-8 w-3/4 mb-3" />
                  <div className="flex flex-wrap gap-1.5">
                    <div className="skeleton h-6 w-14 rounded-md" />
                    <div className="skeleton h-6 w-20 rounded-md" />
                    <div className="skeleton h-6 w-16 rounded-md" />
                    <div className="skeleton h-6 w-12 rounded-md" />
                  </div>
                </div>
                <div className="match-actions flex flex-col gap-2 items-end">
                  <div className="skeleton h-8 w-40 rounded-md" />
                  <div className="skeleton h-8 w-40 rounded-md" />
                  <div className="skeleton h-8 w-40 rounded-md" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!data && !autoTriggering) {
    return (
      <div className="max-w-[1280px] mx-auto px-6 py-20 text-center">
        <p style={{ color: "var(--muted)" }}>Could not load matches.</p>
      </div>
    );
  }

  if (autoTriggering) {
    return (
      <div className="max-w-[1280px] mx-auto px-6 py-20 text-center">
        <div
          className="w-16 h-16 mx-auto mb-4 rounded-2xl flex items-center justify-center animate-pulse"
          style={{ background: "var(--bg-2)", color: "var(--copper-500)" }}
        >
          <Icon name="target" size={24} />
        </div>
        <h3 className="font-display text-2xl mb-2">Generating your first matches&hellip;</h3>
        <p className="text-sm" style={{ color: "var(--muted)" }}>
          Scoring your CV against available jobs. This takes about 30 seconds.
        </p>
      </div>
    );
  }

  // Apply filters + sort. "Closing soon" must sort by closing_date — without
  // this branch the UI button is a no-op (regression from quota work, 2026-05).
  const closingKey = (iso: string | null | undefined): number => {
    if (!iso) return Number.POSITIVE_INFINITY;
    const t = new Date(iso).getTime();
    return Number.isNaN(t) ? Number.POSITIVE_INFINITY : t;
  };

  if (!data) return null;

  let filtered = data.matches.filter(
    (m) =>
      m.score >= scoreFilter &&
      !isJobHiddenFromUserFeed(m.job.closing_date),
  );
  if (sort === "score") {
    filtered = [...filtered].sort((a, b) => b.score - a.score);
  } else {
    filtered = [...filtered].sort(
      (a, b) => closingKey(a.job.closing_date) - closingKey(b.job.closing_date)
    );
  }

  // Real quota from /subscription (sub.matches_limit). Falls back to the
  // sum used+remaining if subscription failed to load — gives a coherent
  // bar even in the degraded case. The historical hard-coded "25" was
  // wrong for every tier except Starter.
  const matchesUsed =
    data.credited_count ?? sub?.matches_used ?? Math.max(0, 25 - data.remaining_quota);
  const matchesLimit =
    (data.matches_limit ?? sub?.matches_limit ?? (matchesUsed + data.remaining_quota)) || 25;
  const usagePct = matchesLimit > 0 ? Math.min(100, (matchesUsed / matchesLimit) * 100) : 0;
  const tierLabel = TIER_LABELS[sub?.tier ?? ""] ?? (sub?.tier ?? "Starter");

  const refreshCountdown =
    refreshing && refreshRing?.phase === "countdown" ? refreshRing.secondsLeft : null;
  const refreshCountdownTotal =
    refreshRing?.total ?? DEFAULT_REFRESH_COUNTDOWN_SECONDS;
  const lastBatchLabel = formatLastBatchRun(data?.last_batch_run_at);
  const refreshTitle =
    data?.message ??
    (lastBatchLabel
      ? `Last refreshed ${lastBatchLabel}. Matches update nightly at 02:00.`
      : "Your first matches are computing — check back in a moment. After that, matches refresh nightly at 02:00.");

  return (
    <div className="max-w-[1280px] mx-auto px-6 py-8 md:py-12">
      {/* Header */}
      <div
        className="matches-header grid gap-8 items-start mb-10"
        style={{ gridTemplateColumns: "1.4fr 1fr" }}
      >
        <div>
          <div className="eyebrow mb-2">
            {new Date().toLocaleDateString("en-ZM", {
              weekday: "long",
              day: "numeric",
              month: "long",
              year: "numeric",
            })}
          </div>
          <h1
            className="font-display mb-4"
            style={{
              fontSize: "clamp(40px, 5.5vw, 72px)",
              letterSpacing: "-0.025em",
              lineHeight: 1,
            }}
          >
            Here are your{" "}
            <span className="italic" style={{ color: "var(--copper-500)" }}>
              top matches
            </span>
            .
          </h1>
          <p className="text-base" style={{ color: "var(--muted)" }}>
            <Counter to={filtered.length} /> roles scored against your CV.
            Tap any card to expand the breakdown.
          </p>
        </div>

        {/* Quota card */}
        <div className="card p-6">
          <div className="flex justify-between items-start">
            <div>
              <div className="eyebrow">This month</div>
              <div className="mt-2 font-display text-4xl leading-none">
                {matchesUsed}
                <span
                  className="text-2xl"
                  style={{ color: "var(--muted)" }}
                >
                  {" "}
                  / {matchesLimit}
                </span>
              </div>
              <div
                className="text-xs mt-1"
                style={{ color: "var(--muted)" }}
              >
                matches delivered
              </div>
            </div>
            <span className="tag tag-copper">
              <Icon name="zap" size={11} /> {tierLabel}
            </span>
          </div>
          <div
            className="mt-5 h-2 rounded-full overflow-hidden"
            style={{ background: "var(--bg-2)" }}
          >
            <div
              className="h-full rounded-full"
              style={{
                width: `${usagePct}%`,
                background:
                  "linear-gradient(90deg, var(--green-500), var(--copper-500))",
                transition: "width 1.4s cubic-bezier(0.2,0.7,0.2,1)",
              }}
            />
          </div>
          <div
            className="mt-3 flex justify-between text-xs"
            style={{ color: "var(--muted)" }}
          >
            <span>Resets next month</span>
            {/* Hide the upgrade link for users who are already on the top
                paid tiers — showing "Upgrade for K125/mo" to a Super
                Standard user (K500/mo, unlimited matches) is both wrong
                and corrosive to trust. */}
            {sub?.tier !== "professional" && sub?.tier !== "super_standard" && (
              <Link
                href="/pricing"
                className="font-medium"
                style={{ color: "var(--green-700)" }}
              >
                Upgrade for K125/mo &rarr;
              </Link>
            )}
          </div>
          <div className="mt-4 flex items-center justify-between gap-3 rounded-xl border border-[var(--line)] px-3 py-2">
            <div>
              <div className="text-sm font-medium">Auto-match</div>
              <div className="text-xs" style={{ color: "var(--muted)" }}>
                Manual refresh still works when this is off.
              </div>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                aria-label="Auto-match"
                type="checkbox"
                className="h-5 w-5 rounded border-input"
                checked={autoPrefs?.auto_match_enabled ?? true}
                disabled={!autoPrefs || savingAutoPrefs}
                onChange={toggleAutoMatch}
              />
              {autoPrefs?.auto_match_enabled === false ? "Off" : "On"}
            </label>
          </div>
        </div>
      </div>

      {/*
        Empty-preferences hint. Phase 2 Initiative #4 — conversion UX.
        Shown only when the user's preferences row is empty across the
        signals that actually affect matching (target_roles, salary,
        arrangement). Conservative: a single target_role is enough to
        suppress the hint, because at that point we're already factoring
        preferences in. Self-dismisses once the user fills anything in.
      */}
      {prefs && _preferencesAreEmpty(prefs) && (
        <Link
          href="/profile?tab=preferences"
          className="card p-4 mb-6 flex items-center gap-3"
          style={{
            borderColor: "var(--copper-500)",
            borderStyle: "dashed",
            color: "var(--ink)",
            textDecoration: "none",
          }}
        >
          <Icon name="sliders" size={18} />
          <div className="flex-1 text-sm">
            <strong>Set your job preferences</strong> to get better matches and
            tailored CVs.
          </div>
          <Icon name="arrowRight" size={14} />
        </Link>
      )}

      {/* Filter bar */}
      <div
        className="flex items-center justify-between flex-wrap gap-3 pb-4 mb-6"
        style={{ borderBottom: "1px solid var(--line)" }}
      >
        <div className="flex gap-2 flex-wrap">
          {[
            [0, "All"],
            [70, "70+"],
            [85, "85+ Strong"],
          ].map(([v, l]) => (
            <button
              key={String(v)}
              onClick={() => setScoreFilter(v as number)}
              className="btn btn-sm"
              style={{
                background:
                  scoreFilter === v ? "var(--green-700)" : "transparent",
                color: scoreFilter === v ? "#faf7f2" : "var(--ink-2)",
                border:
                  scoreFilter === v
                    ? "none"
                    : "1px solid var(--line-2)",
              }}
            >
              {l as string}
            </button>
          ))}
        </div>
        <div className="flex gap-2 items-center flex-wrap justify-end">
          <span
            className="font-mono text-[11px]"
            style={{ color: "var(--muted)" }}
          >
            SORT
          </span>
          {[
            ["score", "Score"],
            ["closing", "Closing soon"],
          ].map(([v, l]) => (
            <button
              key={v}
              onClick={() => setSort(v as "score" | "closing")}
              className="btn btn-sm"
              style={{
                background: sort === v ? "var(--bg-2)" : "transparent",
                color: "var(--ink-2)",
                border: "1px solid var(--line)",
                fontWeight: sort === v ? 600 : 400,
              }}
            >
              {l}
            </button>
          ))}
          {refreshRing && (
            <div
              className="flex flex-col items-center gap-1 px-1"
              aria-live="polite"
            >
              <CountdownRing
                phase={refreshRing.phase}
                total={refreshRing.total}
                secondsLeft={refreshRing.secondsLeft}
              />
              <span
                className="text-[11px] font-mono text-center leading-tight"
                style={{ color: "var(--muted)", maxWidth: 100 }}
              >
                {refreshRing.phase === "working"
                  ? "Still working…"
                  : `~${refreshRing.secondsLeft}s remaining`}
              </span>
            </div>
          )}
          <button
            onClick={handleRefreshMatches}
            disabled={refreshing || refreshCooldown}
            title={refreshTitle}
            className="btn btn-sm flex items-center gap-2"
            style={{
              background: "var(--green-700)",
              color: "#faf7f2",
              opacity: refreshing || refreshCooldown ? 0.6 : 1,
              cursor: refreshing || refreshCooldown ? "not-allowed" : "pointer",
            }}
          >
            {refreshing && refreshCountdown !== null ? (
              <RefreshCountdownRing
                totalSeconds={refreshCountdownTotal}
                remainingSeconds={refreshCountdown}
                size={36}
              />
            ) : (
              <Icon name="refresh" size={13} />
            )}
            <span className="flex flex-col items-start leading-tight">
              <span>
                {refreshing ? "Refreshing\u2026" : "Refresh matches"}
              </span>
              {refreshing && refreshCountdown !== null && (
                <span className="font-mono text-[10px] opacity-90">
                  ~{refreshCountdown}s remaining
                </span>
              )}
            </span>
          </button>
          {lastBatchLabel && !refreshing && (
            <p
              className="text-[11px] text-right col-span-full sm:col-span-1"
              style={{ color: "var(--muted)", maxWidth: 220 }}
            >
              Last refreshed {lastBatchLabel}
              <span className="block">Nightly update 02:00 CAT</span>
            </p>
          )}
        </div>
      </div>

      {/* Match cards */}
      {data && data.matches.length === 0 ? (
        <div className="text-center py-20">
          <div
            className="w-16 h-16 mx-auto mb-4 rounded-2xl flex items-center justify-center"
            style={{
              border: "2px dashed var(--line-2)",
              color: "var(--muted)",
            }}
          >
            <Icon name="target" size={24} />
          </div>
          <h3 className="font-display text-2xl mb-2">No matches yet</h3>
          <p className="text-sm mb-4" style={{ color: "var(--muted)" }}>
            Upload your CV to get started, then refresh your matches.
          </p>
          <div className="flex gap-3 justify-center">
            <Link href="/profile" className="btn btn-primary">
              Upload CV <Icon name="upload" size={14} />
            </Link>
            <button
              onClick={handleRefreshMatches}
              disabled={refreshing || refreshCooldown}
              className="btn btn-ghost"
              style={{
                opacity: refreshing || refreshCooldown ? 0.6 : 1,
              }}
            >
              <Icon name="refresh" size={14} />
              {refreshing ? "Refreshing\u2026" : "Refresh matches"}
            </button>
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-3.5">
          {filtered.map((match) => {
            const expired = isJobPastClosing(match.job.closing_date);
            return (
            <article
              key={match.id}
              className="card overflow-hidden relative"
              style={{ opacity: expired ? 0.5 : 1 }}
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
                    <span
                      className="text-sm"
                      style={{ color: "var(--muted)" }}
                    >
                      {match.job.company || "Company"} &middot;{" "}
                      {match.job.location || "Zambia"}
                    </span>
                  </div>
                  {/* Title links to the public /jobs/[id] page so the
                      same URL is shareable / openable in another tab.
                      Keeps card body click-free so the buttons on the
                      right (Apply, Interview, Why-this-match) remain
                      the primary affordances. */}
                  <Link
                    href={`/jobs/${match.job.id}`}
                    className="font-display text-2xl md:text-3xl block hover:underline"
                    style={{ letterSpacing: "-0.01em", lineHeight: 1.1, color: "inherit" }}
                  >
                    {match.job.title}
                  </Link>
                  {match.created_at ? (
                    <p
                      className="text-xs mt-1.5"
                      style={{ color: "var(--muted)" }}
                    >
                      {formatMatchedRelative(match.created_at)}
                    </p>
                  ) : null}

                  {/* Match explainability — tells the user WHY the score is
                      what it is. When matched_skills is non-empty, surface
                      the actual skill overlap. When it's empty, the match
                      came purely from vector similarity (CV semantically
                      similar to the JD even with no overlapping skill
                      tags), so we say so explicitly instead of leaving
                      the row label-less. Missing skills are shown after
                      with a different visual treatment so the user sees
                      both "what got us in" and "what to grow toward". */}
                  {(match.matched_skills.length > 0 || match.missing_skills.length > 0) && (
                    <div className="mt-3">
                      {match.matched_skills.length > 0 ? (
                        <div
                          className="text-[10px] uppercase tracking-wider mb-1.5"
                          style={{ color: "var(--muted)" }}
                        >
                          Matched on
                        </div>
                      ) : (
                        <div
                          className="text-[10px] uppercase tracking-wider mb-1.5"
                          style={{ color: "var(--muted)" }}
                        >
                          Strong semantic match
                        </div>
                      )}
                      <div className="flex flex-wrap gap-1.5">
                        {match.matched_skills.map((s) => (
                          <SkillBadge key={s} skill={s} matched />
                        ))}
                        {match.missing_skills.slice(0, 3).map((s) => (
                          <SkillBadge key={s} skill={s} matched={false} />
                        ))}
                      </div>
                      {match.missing_skills.length > 0 && (
                        <div
                          className="text-[10px] mt-1.5"
                          style={{ color: "var(--muted)" }}
                        >
                          Faded chips are skills to grow toward
                        </div>
                      )}
                    </div>
                  )}
                </div>

                <div className="match-actions flex flex-col gap-2 items-end">
                  {/* Apply button uses the same helper as the public
                      drawer / standalone job page. Falls back to mailto
                      then source listing; disables when nothing is
                      available so we never ship a dead button. */}
                  {expired ? (
                    <button
                      type="button"
                      className="btn btn-primary btn-sm w-40"
                      disabled
                      style={{ cursor: "not-allowed" }}
                    >
                      Application closed
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="btn btn-primary btn-sm w-40"
                      onClick={() => {
                        setApplyJob(match.job);
                        if (token) {
                          void trackApplyClick(token, match.job.id, "direct");
                        }
                      }}
                    >
                      Apply
                    </button>
                  )}
                  <SaveJobButton
                    jobId={match.job.id}
                    saved={savedJobIds.has(match.job.id)}
                    token={token}
                    onChange={(jobId, next) => {
                      setSavedJobIds((prev) => {
                        const n = new Set(prev);
                        if (next) n.add(jobId);
                        else n.delete(jobId);
                        return n;
                      });
                    }}
                  />
                  {/* Interview Prep is Super Standard only (backend enforced
                      in interview_prep.py). Mirror that gate here so users
                      below SS see a clear upgrade affordance instead of
                      clicking a button that just 403s. Backend enforcement
                      remains the source of truth. */}
                  {sub?.tier === "super_standard" ? (
                    <button
                      onClick={() => setPrepFor(match)}
                      className="btn btn-accent btn-sm w-40"
                      title="Generate interview prep notes for this role"
                    >
                      Interview Call <Icon name="zap" size={13} />
                    </button>
                  ) : (
                    <Link
                      href="/pricing"
                      className="btn btn-ghost btn-sm w-40"
                      title="Interview Prep is a Super Standard feature"
                      style={{ opacity: 0.85 }}
                    >
                      Unlock prep <Icon name="zap" size={13} />
                    </Link>
                  )}
                  <button
                    onClick={() =>
                      setExpanded(expanded === match.id ? null : match.id)
                    }
                    className="btn btn-ghost btn-sm w-40"
                  >
                    {expanded === match.id ? "Hide details" : "Why this match?"}{" "}
                    <Icon
                      name={
                        expanded === match.id
                          ? "chevronDown"
                          : "chevronRight"
                      }
                      size={13}
                    />
                  </button>
                </div>
              </div>

              {/* Expanded breakdown */}
              <div
                className="overflow-hidden transition-all duration-300"
                style={{
                  maxHeight: expanded === match.id ? 560 : 0,
                  borderTop:
                    expanded === match.id
                      ? "1px solid var(--line)"
                      : "none",
                  background: "var(--bg-2)",
                }}
              >
                <div
                  className="breakdown-grid p-6 grid gap-6"
                  style={{ gridTemplateColumns: "1fr 1fr" }}
                >
                  <div>
                    <div className="eyebrow mb-4">Score breakdown</div>
                    <MatchScoreBreakdown match={match} />
                  </div>
                  <div>
                    <div className="eyebrow mb-4">AI explanation</div>
                    {match.explanation && (
                      <p
                        className="text-sm leading-relaxed mb-4"
                        style={{ color: "var(--ink-2)" }}
                      >
                        {match.explanation}
                      </p>
                    )}
                    {match.missing_skills.length > 0 && (
                      <div
                        className="p-3.5 rounded-lg"
                        style={{
                          background: "var(--surface)",
                          border: "1px dashed var(--line-2)",
                        }}
                      >
                        <div
                          className="eyebrow mb-1.5"
                          style={{ color: "var(--copper-600)" }}
                        >
                          Skill gap
                        </div>
                        <div
                          className="text-sm font-mono"
                          style={{ color: "var(--ink-2)" }}
                        >
                          Missing: {match.missing_skills.join(", ")}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </article>
            );
          })}
        </div>
      )}

      <ApplyModal
        job={applyJob}
        open={applyJob !== null}
        onOpenChange={(open) => {
          if (!open) setApplyJob(null);
        }}
      />

      {token && prepFor && (
        <InterviewPrepModal
          open={!!prepFor}
          onClose={() => setPrepFor(null)}
          token={token}
          jobId={prepFor.job.id}
          jobTitle={prepFor.job.title}
          company={prepFor.job.company}
        />
      )}

      {/* Upgrade CTA — promotes tailored CVs (a Professional+ feature).
          Hide for users who already have it. Professional and Super
          Standard both include tailored CV generation, so the "Pro tip"
          is only relevant for free + starter tiers. */}
      {data && data.matches.length > 0 &&
        sub?.tier !== "professional" &&
        sub?.tier !== "super_standard" && (
        <div
          className="upgrade-cta mt-12 p-8 rounded-xl grid gap-6 items-center"
          style={{
            gridTemplateColumns: "1fr auto",
            background: "var(--bg-2)",
            border: "1px solid var(--line)",
          }}
        >
          <div>
            <div className="eyebrow mb-1">Pro tip</div>
            <h3
              className="font-display text-2xl mb-1.5"
              style={{ letterSpacing: "-0.01em" }}
            >
              Want{" "}
              <span
                className="italic"
                style={{ color: "var(--copper-500)" }}
              >
                tailored CVs
              </span>{" "}
              per role?
            </h3>
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              Professional tier rewrites your CV for each match — typically
              lifts callback rates by 2-3x.
            </p>
          </div>
          <Link href="/pricing" className="btn btn-accent">
            See pricing <Icon name="arrowRight" size={14} />
          </Link>
        </div>
      )}
    </div>
  );
}

/**
 * True when the user has set none of the match-relevant preferences.
 * Languages and extras don't count — we don't yet factor them into
 * /matches scoring, so prompting users to fill them wouldn't change
 * the match list.
 */
function _preferencesAreEmpty(prefs: JobPreferences): boolean {
  return (
    prefs.target_roles.length === 0 &&
    prefs.salary_min === null &&
    prefs.salary_max === null &&
    prefs.preferred_work_arrangement === null &&
    prefs.acceptable_regions.length === 0
  );
}
