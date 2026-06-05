"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
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
import { MatchCard } from "@/components/matches/MatchCard";
import { Icon } from "@/components/ui/Icon";
import { Counter } from "@/components/ui/Counter";
import Link from "next/link";
import { notify } from "@/lib/toast";
import { InterviewPrepModal } from "./_components/InterviewPrepModal";
import { MatchExplanationModal } from "./_components/MatchExplanationModal";
import {
  MatchDismissModal,
  type MatchDismissPayload,
} from "@/components/matches/MatchDismissModal";
import { TailoredCvModal } from "@/components/matches/TailoredCvModal";
import { CoverLetterMatchModal } from "@/components/matches/CoverLetterMatchModal";
import { resolveMatchQuotaDisplay } from "@/lib/matchQuota";
import { isClosedForMatchesFeed } from "@/lib/jobVisibility";
import { trackApplyClick } from "@/lib/trackApplyClick";
import { ApplyModal } from "@/components/jobs/ApplyModal";
import { PushPermissionPrompt } from "@/components/notifications/PushPermissionPrompt";
import { btnClass, surfaceCardClass, tagClass } from "@/lib/cn-ui";
import { cn } from "@/lib/utils";
import { MATCHES_FETCH_LIMIT } from "@/lib/matchConstants";

// Human-friendly tier label. Free → "Free", super_standard → "Super",
// etc. Falls back to the raw key if we don't recognize it so we don't
// hide unknown tiers entirely.
const MATCHES_CACHE_KEY = "zedapply_matches_cache_v3";

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
  const searchParams = useSearchParams();
  const { token, isAuthenticated, isLoading: authLoading, logout } = useAuth();
  const [data, setData] = useState<MatchRefreshResponse | null>(null);
  const [sub, setSub] = useState<Subscription | null>(null);
  const [prefs, setPrefs] = useState<JobPreferences | null>(null);
  const [autoPrefs, setAutoPrefs] = useState<AutoMatchPreferences | null>(null);
  const [savingAutoPrefs, setSavingAutoPrefs] = useState(false);
  const [loading, setLoading] = useState(true);
  const [detailMatch, setDetailMatch] = useState<MatchData | null>(null);
  const [scoreFilter, setScoreFilter] = useState(0);
  const [showClosed, setShowClosed] = useState(false);
  const [keywordFilter, setKeywordFilter] = useState("");
  const [sort, setSort] = useState<"score" | "closing">("score");
  const [prepFor, setPrepFor] = useState<MatchData | null>(null);
  const [tailorFor, setTailorFor] = useState<MatchData | null>(null);
  const [coverLetterFor, setCoverLetterFor] = useState<MatchData | null>(null);
  const [applyJob, setApplyJob] = useState<MatchData["job"] | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshCooldown, setRefreshCooldown] = useState(false);
  const [savedJobIds, setSavedJobIds] = useState<Set<string>>(() => new Set());
  const [autoTriggering, setAutoTriggering] = useState(false);
  const [dismissingId, setDismissingId] = useState<string | null>(null);
  const [dismissFor, setDismissFor] = useState<MatchData | null>(null);
  const autoTriggeredRef = useRef(false);
  const deepLinkHandledRef = useRef(false);

  const loadMatches = useCallback(async (authToken: string, includeClosed = false) => {
    const [matchesRes, subRes, prefsRes, autoPrefsRes] = await Promise.allSettled([
      matchesApi.get(authToken, {
        limit: MATCHES_FETCH_LIMIT,
        includeArchived: includeClosed,
      }),
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

  useEffect(() => {
    const openId = searchParams.get("open");
    if (!openId || !data?.matches?.length || deepLinkHandledRef.current) return;
    const match = data.matches.find((m) => m.id === openId);
    if (match) {
      deepLinkHandledRef.current = true;
      setDetailMatch(match);
      router.replace("/matches", { scroll: false });
    }
  }, [searchParams, data?.matches, router]);

  const handleRefreshMatches = useCallback(async () => {
    if (!token || refreshing || refreshCooldown) return;
    const preIds = new Set((data?.matches ?? []).map((m) => m.id));

    setRefreshing(true);
    try {
      const refreshed = await matchesApi.refresh(token);
      setData(refreshed);
      setAutoTriggering(Boolean(refreshed.refresh_computing));
      const next = refreshed.matches ?? [];
      const newOnes = next.filter((m) => !preIds.has(m.id));
      if (refreshed.refresh_computing) {
        notify.custom.message(
          refreshed.message ??
            "Your first matches are computing — check back in a moment.",
        );
      } else if (refreshed.message) {
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

  const confirmDismissMatch = useCallback(
    async (payload: MatchDismissPayload) => {
      const match = dismissFor;
      if (!token || !match || dismissingId) return;
      setDismissingId(match.id);
      try {
        const body =
          payload.reason || payload.note
            ? {
                ...(payload.reason ? { reason: payload.reason } : {}),
                ...(payload.note ? { note: payload.note } : {}),
              }
            : undefined;
        await matchesApi.dismiss(token, match.id, body);
        setData((prev) =>
          prev
            ? {
                ...prev,
                matches: (prev.matches ?? []).filter((m) => m.id !== match.id),
              }
            : prev,
        );
        if (detailMatch?.id === match.id) setDetailMatch(null);
        setDismissFor(null);
        notify.custom.success("Match hidden.");
      } catch (e: unknown) {
        notify.error(
          e instanceof ApiError ? e.detail || "Could not hide match." : "Could not hide match.",
        );
      } finally {
        setDismissingId(null);
      }
    },
    [token, dismissFor, dismissingId, detailMatch?.id],
  );

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
    loadMatches(token, showClosed).then(async (result) => {
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
            setAutoTriggering(Boolean(refreshed.refresh_computing));
          }
        } catch {
          setAutoTriggering(false);
        }
      }
    }).finally(() => setLoading(false));
  }, [token, isAuthenticated, authLoading, router, logout, loadMatches, showClosed]);

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
      <div className="max-w-[1280px] mx-auto px-5 sm:px-6 py-8 md:py-12">
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
          <div className={cn(surfaceCardClass, "p-6")}>
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
            <div key={i} className={cn(surfaceCardClass, "overflow-hidden")}>
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

  const keyword = keywordFilter.trim().toLowerCase();
  let filtered = data.matches.filter((m) => {
    if (m.score < scoreFilter) return false;
    if (!showClosed && isClosedForMatchesFeed(m.job)) return false;
    if (
      keyword &&
      !m.job.title.toLowerCase().includes(keyword) &&
      !(m.job.company?.toLowerCase().includes(keyword) ?? false) &&
      !m.matched_skills.some((s) => s.toLowerCase().includes(keyword))
    ) {
      return false;
    }
    return true;
  });
  if (sort === "score") {
    filtered = [...filtered].sort((a, b) => {
      const byScore = b.score - a.score;
      if (byScore !== 0) return byScore;
      return closingKey(a.job.closing_date) - closingKey(b.job.closing_date);
    });
  } else {
    filtered = [...filtered].sort((a, b) => {
      const byClose =
        closingKey(a.job.closing_date) - closingKey(b.job.closing_date);
      if (byClose !== 0) return byClose;
      return b.score - a.score;
    });
  }

  const {
    matchesUsed,
    unlimited: quotaUnlimited,
    limitLabel: quotaLimitLabel,
    usagePct,
  } = resolveMatchQuotaDisplay(data, sub);
  const tierLabel = TIER_LABELS[sub?.tier ?? ""] ?? (sub?.tier ?? "Starter");

  const showRefreshProgress =
    refreshing || Boolean(data?.refresh_computing) || autoTriggering;
  const lastBatchLabel = formatLastBatchRun(data?.last_batch_run_at);
  const refreshTitle =
    data?.message ??
    (lastBatchLabel
      ? `Last refreshed ${lastBatchLabel}. Matches update nightly at 02:00.`
      : "Your first matches are computing — check back in a moment. After that, matches refresh nightly at 02:00.");

  return (
    <div className="max-w-[1280px] mx-auto px-5 sm:px-6 py-8 md:py-12">
      <PushPermissionPrompt creditedMatchCount={matchesUsed} />
      {/* Header */}
      <div
        className="matches-header grid gap-8 items-start mb-10 lg:grid-cols-[1.4fr_1fr]"
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
            className="font-display mb-4 text-foreground"
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
            {matchesUsed > 0 ? (
              <>
                Showing <Counter to={filtered.length} />
                {data.matches.length < matchesUsed
                  ? ` of ${data.matches.length} loaded`
                  : ""}
                {matchesUsed > data.matches.length
                  ? ` (${matchesUsed} delivered this period)`
                  : ""}
                .
              </>
            ) : (
              <>
                <Counter to={filtered.length} /> roles scored against your CV.
              </>
            )}{" "}
            Tap any card to expand the breakdown.
          </p>
        </div>

        {/* Quota card */}
        <div className={cn(surfaceCardClass, "p-6")}>
          <div className="flex justify-between items-start">
            <div>
              <div className="eyebrow">This month</div>
              <div className="mt-2 font-display text-4xl leading-none">
                {quotaUnlimited ? (
                  matchesUsed > 0 ? (
                    <>
                      {matchesUsed}
                      <span
                        className="text-lg ml-2"
                        style={{ color: "var(--muted)" }}
                      >
                        · Unlimited
                      </span>
                    </>
                  ) : (
                    <span>Unlimited</span>
                  )
                ) : (
                  <>
                    {matchesUsed}
                    <span
                      className="text-2xl"
                      style={{ color: "var(--muted)" }}
                    >
                      {" "}
                      / {quotaLimitLabel}
                    </span>
                  </>
                )}
              </div>
              <div
                className="text-xs mt-1"
                style={{ color: "var(--muted)" }}
              >
                {quotaUnlimited && matchesUsed === 0
                  ? "Unlimited plan — deliveries appear here as they arrive"
                  : "matches delivered"}
              </div>
            </div>
            <span className={tagClass("copper", "inline-flex items-center gap-1")}>
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
          className={cn(
            surfaceCardClass,
            "p-4 mb-6 flex items-center gap-3 border-dashed no-underline",
          )}
          style={{
            borderColor: "var(--copper-500)",
            color: "var(--ink)",
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
              type="button"
              onClick={() => setScoreFilter(v as number)}
              aria-pressed={scoreFilter === v}
              className={cn(
                btnClass("outline", "sm"),
                scoreFilter === v &&
                  "border-transparent bg-primary text-primary-foreground hover:bg-primary/90",
              )}
            >
              {l as string}
            </button>
          ))}
        </div>
        <div className="flex gap-2 items-center flex-wrap justify-end w-full sm:w-auto">
          <label className="flex items-center gap-2 text-xs" style={{ color: "var(--ink-2)" }}>
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-input"
              checked={showClosed}
              onChange={(e) => setShowClosed(e.target.checked)}
              aria-label="Show closed jobs"
            />
            Show closed
          </label>
          <input
            type="search"
            value={keywordFilter}
            onChange={(e) => setKeywordFilter(e.target.value)}
            placeholder="Search title, company, skills…"
            className="field min-w-[200px] flex-1 sm:flex-none sm:w-56"
            style={{ height: 36 }}
            aria-label="Filter matches by keyword"
          />
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
              type="button"
              onClick={() => setSort(v as "score" | "closing")}
              aria-pressed={sort === v}
              className={cn(
                btnClass("outline", "sm"),
                sort === v && "bg-muted font-semibold",
              )}
            >
              {l}
            </button>
          ))}
          <button
            type="button"
            onClick={handleRefreshMatches}
            disabled={showRefreshProgress || refreshCooldown}
            title={refreshTitle}
            className={cn(btnClass("primary", "sm"), "gap-2")}
            aria-busy={showRefreshProgress}
          >
            <Icon
              name="refresh"
              size={13}
              className={showRefreshProgress ? "animate-spin" : undefined}
            />
            <span className="flex flex-col items-start leading-tight">
              <span>
                {showRefreshProgress ? "Refreshing\u2026" : "Refresh matches"}
              </span>
              {data?.refresh_computing && (
                <span className="font-mono text-[10px] opacity-90">
                  First batch computing
                </span>
              )}
            </span>
          </button>
          {lastBatchLabel && !showRefreshProgress && (
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
            <Link href="/profile" className={btnClass("primary")}>
              Upload CV <Icon name="upload" size={14} />
            </Link>
            <button
              type="button"
              onClick={handleRefreshMatches}
              disabled={showRefreshProgress || refreshCooldown}
              className={btnClass("ghost")}
            >
              <Icon name="refresh" size={14} />
              {showRefreshProgress ? "Refreshing\u2026" : "Refresh matches"}
            </button>
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-3.5 mobile-stagger-list">
          {filtered.map((match) => (
            <MatchCard
              key={match.id}
              match={match}
              expired={isClosedForMatchesFeed(match.job)}
              authToken={token}
              jobSaved={savedJobIds.has(match.job.id)}
              onSavedChange={(jobId, next) => {
                setSavedJobIds((prev) => {
                  const n = new Set(prev);
                  if (next) n.add(jobId);
                  else n.delete(jobId);
                  return n;
                });
              }}
              onApplyClick={() => {
                setApplyJob(match.job);
                if (token) {
                  void trackApplyClick(token, match.job.id, "direct");
                }
              }}
              onTailorCvClick={() => setTailorFor(match)}
              onCoverLetterClick={() => setCoverLetterFor(match)}
              onInterviewPrepClick={() => setPrepFor(match)}
              onWhyMatchClick={() => setDetailMatch(match)}
              onDismissClick={() => setDismissFor(match)}
              dismissing={dismissingId === match.id}
            />
          ))}
        </div>
      )}

      <MatchExplanationModal
        match={detailMatch}
        open={detailMatch !== null}
        onClose={() => setDetailMatch(null)}
        subscriptionTier={sub?.tier}
      />

      <MatchDismissModal
        match={dismissFor}
        open={dismissFor !== null}
        saving={dismissingId === dismissFor?.id}
        onClose={() => setDismissFor(null)}
        onConfirm={(reason) => void confirmDismissMatch(reason)}
      />

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

      {token && tailorFor && (
        <TailoredCvModal
          open={!!tailorFor}
          onClose={() => setTailorFor(null)}
          token={token}
          matchId={tailorFor.id}
          jobId={tailorFor.job.id}
          jobTitle={tailorFor.job.title}
          company={tailorFor.job.company}
        />
      )}

      {token && coverLetterFor && (
        <CoverLetterMatchModal
          open={!!coverLetterFor}
          onClose={() => setCoverLetterFor(null)}
          token={token}
          matchId={coverLetterFor.id}
          jobTitle={coverLetterFor.job.title}
          company={coverLetterFor.job.company}
          subscriptionTier={sub?.tier}
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
          <Link href="/pricing" className={btnClass("accent")}>
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
