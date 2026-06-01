"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { savedJobs, matches, profile as profileApi, type Job, type MatchData } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { JobDetailBody } from "@/components/JobDetailBody";
import { computeJobVisibilityStatus } from "@/lib/jobVisibility";

/**
 * Thin client wrapper around JobDetailBody so the parent page can stay
 * server-rendered (for proper generateMetadata + og:image / Twitter
 * preview support). Loads saved state and personalised match breakdown.
 */
export function JobDetailClient({ job }: { job: Job }) {
  const router = useRouter();
  const { token } = useAuth();
  const [jobSaved, setJobSaved] = useState(false);
  const [match, setMatch] = useState<MatchData | null>(null);
  const [similarMatches, setSimilarMatches] = useState<MatchData[]>([]);
  const [viewerName, setViewerName] = useState<string | null>(null);
  const [subscriptionTier, setSubscriptionTier] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setJobSaved(false);
      return;
    }
    let cancelled = false;
    savedJobs
      .list(token)
      .then((res) => {
        if (!cancelled) setJobSaved(res.jobs.some((j) => j.id === job.id));
      })
      .catch(() => {
        if (!cancelled) setJobSaved(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token, job.id]);

  useEffect(() => {
    if (!token) {
      setMatch(null);
      setSimilarMatches([]);
      setViewerName(null);
      setSubscriptionTier(null);
      return;
    }
    let cancelled = false;
    Promise.all([matches.get(token), profileApi.get(token).catch(() => null)])
      .then(([res, profile]) => {
        if (cancelled) return;
        const forJob = res.matches.find((m) => m.job.id === job.id) ?? null;
        setMatch(forJob);
        setSimilarMatches(
          [...res.matches]
            .filter((m) => m.job.id !== job.id)
            .filter((m) => computeJobVisibilityStatus(m.job) === "open")
            .sort((a, b) => b.score - a.score)
            .slice(0, 3),
        );
        if (profile) {
          setViewerName(profile.full_name ?? null);
          setSubscriptionTier(profile.subscription_tier);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setMatch(null);
          setSimilarMatches([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [token, job.id]);

  return (
    <JobDetailBody
      job={job}
      showBack
      backLabel="All jobs"
      onBack={() => router.push("/jobs")}
      authToken={token}
      jobSaved={jobSaved}
      onSavedChange={setJobSaved}
      match={match}
      similarMatches={similarMatches}
      viewerName={viewerName}
      subscriptionTier={subscriptionTier}
    />
  );
}
