"use client";

import { useCallback, useEffect, useState } from "react";
import { admin, type AdminJobReviewRow } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { notify } from "@/lib/toast";
import { ReviewQueueOverviewStrip } from "../../_components/ReviewQueueOverviewStrip";

type Draft = {
  apply_url: string;
  apply_email: string;
  application_instructions: string;
};

function emptyDraft(): Draft {
  return { apply_url: "", apply_email: "", application_instructions: "" };
}

export default function AdminJobReviewPage() {
  const { token } = useAuth();
  const [jobs, setJobs] = useState<AdminJobReviewRow[]>([]);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [savingId, setSavingId] = useState<string | null>(null);
  const [bulkClearing, setBulkClearing] = useState(false);

  const loadQueue = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const res = await admin.track4eReviewQueue(token, { page, per_page: 10 });
      setJobs(res.jobs);
      setPages(res.pages);
      setDrafts((current) => {
        const next = { ...current };
        for (const job of res.jobs) {
          next[job.id] = next[job.id] ?? emptyDraft();
        }
        return next;
      });
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Failed to load review queue");
    } finally {
      setLoading(false);
    }
  }, [page, token]);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  const updateDraft = (jobId: string, field: keyof Draft, value: string) => {
    setDrafts((current) => ({
      ...current,
      [jobId]: { ...(current[jobId] ?? emptyDraft()), [field]: value },
    }));
  };

  const approve = async (jobId: string) => {
    if (!token) return;
    const draft = drafts[jobId] ?? emptyDraft();
    const payload = Object.fromEntries(
      Object.entries(draft).filter(([, value]) => value.trim())
    );
    setSavingId(jobId);
    try {
      await admin.approveReviewJob(token, jobId, payload);
      notify.custom.success("Job approved.");
      await loadQueue();
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Could not approve job");
    } finally {
      setSavingId(null);
    }
  };

  const dismiss = async (jobId: string) => {
    if (!token) return;
    setSavingId(jobId);
    try {
      await admin.dismissReviewJob(token, jobId);
      notify.custom.success("Job dismissed.");
      await loadQueue();
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Could not dismiss job");
    } finally {
      setSavingId(null);
    }
  };

  const autoDismissHidden = async (dryRun: boolean) => {
    if (!token) return;
    setBulkClearing(true);
    try {
      const res = await admin.bulkAutoDismissHiddenReview(token, { dry_run: dryRun });
      if (dryRun) {
        notify.custom.info(
          `${res.eligible} hidden job(s) can be cleared from the queue (already off /jobs).`
        );
      } else {
        notify.custom.success(`Cleared ${res.dismissed} hidden job(s) from review.`);
        await loadQueue();
      }
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Bulk clear failed");
    } finally {
      setBulkClearing(false);
    }
  };

  if (!token) return null;

  return (
    <div className="space-y-4">
      <ReviewQueueOverviewStrip token={token} onChanged={() => void loadQueue()} />
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          disabled={bulkClearing}
          onClick={() => void autoDismissHidden(true)}
        >
          Preview hidden backlog clear
        </Button>
        <Button
          type="button"
          variant="secondary"
          disabled={bulkClearing}
          onClick={() => void autoDismissHidden(false)}
        >
          Clear hidden backlog
        </Button>
      </div>
      {loading ? (
        <p className="text-sm text-muted-foreground">Loading review queue...</p>
      ) : jobs.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-sm text-muted-foreground">
            No jobs need review.
          </CardContent>
        </Card>
      ) : (
        jobs.map((job) => {
          const draft = drafts[job.id] ?? emptyDraft();
          return (
            <Card key={job.id}>
              <CardHeader>
                <CardTitle className="text-lg">{job.title}</CardTitle>
                <p className="text-sm text-muted-foreground">
                  {job.company || "Unknown company"} · {job.source}
                </p>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex flex-wrap gap-2">
                  {job.reasons.map((reason) => (
                    <span
                      key={reason}
                      className="rounded-full bg-amber-100 px-2 py-1 text-xs text-amber-900 dark:bg-amber-950/80 dark:text-amber-100"
                    >
                      {reason.replaceAll("_", " ")}
                    </span>
                  ))}
                </div>
                {job.source_url && (
                  <a className="text-sm text-primary underline" href={job.source_url} target="_blank" rel="noreferrer">
                    Open source listing
                  </a>
                )}
                <div className="grid gap-3 md:grid-cols-3">
                  <Input
                    placeholder="Apply URL"
                    value={draft.apply_url}
                    onChange={(e) => updateDraft(job.id, "apply_url", e.target.value)}
                  />
                  <Input
                    placeholder="Apply email"
                    value={draft.apply_email}
                    onChange={(e) => updateDraft(job.id, "apply_email", e.target.value)}
                  />
                  <Input
                    placeholder="Application instructions"
                    value={draft.application_instructions}
                    onChange={(e) => updateDraft(job.id, "application_instructions", e.target.value)}
                  />
                </div>
                <div className="flex gap-2">
                  <Button type="button" disabled={savingId === job.id} onClick={() => approve(job.id)}>
                    Approve
                  </Button>
                  <Button type="button" variant="outline" disabled={savingId === job.id} onClick={() => dismiss(job.id)}>
                    Dismiss
                  </Button>
                </div>
              </CardContent>
            </Card>
          );
        })
      )}

      <div className="flex items-center justify-between pt-2">
        <Button type="button" variant="outline" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
          Previous
        </Button>
        <span className="text-sm text-muted-foreground">
          Page {page} of {pages}
        </span>
        <Button type="button" variant="outline" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>
          Next
        </Button>
      </div>
    </div>
  );
}
