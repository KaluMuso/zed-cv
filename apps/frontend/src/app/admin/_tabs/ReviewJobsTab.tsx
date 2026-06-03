"use client";

import { useCallback, useEffect, useState } from "react";
import { admin, type AdminJobReviewRow } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { notify } from "@/lib/toast";
import { ReviewQueueOverviewStrip } from "../_components/ReviewQueueOverviewStrip";

type Draft = {
  apply_url: string;
  apply_email: string;
  closing_date: string;
};

type QueuePreset = "all" | "active_no_deadline";

const PRESET_LABELS: Record<QueuePreset, string> = {
  all: "All pending review",
  active_no_deadline: "Active · no deadline · has apply path",
};

function emptyDraft(): Draft {
  return { apply_url: "", apply_email: "", closing_date: "" };
}

export function ReviewJobsTab({ token }: { token: string }) {
  const [jobs, setJobs] = useState<AdminJobReviewRow[]>([]);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [preset, setPreset] = useState<QueuePreset>("all");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [savingId, setSavingId] = useState<string | null>(null);
  const [bulkClearing, setBulkClearing] = useState(false);
  const [bulkActioning, setBulkActioning] = useState(false);

  const loadQueue = useCallback(async () => {
    setLoading(true);
    try {
      const res = await admin.track4eReviewQueue(token, {
        page,
        per_page: 25,
        preset: preset === "all" ? undefined : preset,
      });
      setJobs(res.jobs);
      setPages(res.pages);
      setTotal(res.total);
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
  }, [page, preset, token]);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  useEffect(() => {
    setPage(1);
    setSelected(new Set());
  }, [preset]);

  const updateDraft = (jobId: string, field: keyof Draft, value: string) => {
    setDrafts((current) => ({
      ...current,
      [jobId]: { ...(current[jobId] ?? emptyDraft()), [field]: value },
    }));
  };

  const saveJob = async (jobId: string) => {
    const draft = drafts[jobId] ?? emptyDraft();
    const payload = Object.fromEntries(
      Object.entries(draft).filter(([, v]) => v.trim())
    );
    setSavingId(jobId);
    try {
      await admin.updateTrack4eReviewJob(token, jobId, payload);
      notify.custom.success("Job updated.");
      setSelected((prev) => {
        const next = new Set(prev);
        next.delete(jobId);
        return next;
      });
      await loadQueue();
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Could not save job");
    } finally {
      setSavingId(null);
    }
  };

  const autoDismissHidden = async (dryRun: boolean) => {
    setBulkClearing(true);
    try {
      const res = await admin.bulkAutoDismissHiddenReview(token, { dry_run: dryRun });
      if (dryRun) {
        notify.custom.info(`${res.eligible} hidden job(s) can leave the review queue.`);
      } else {
        notify.custom.success(`Cleared ${res.dismissed} hidden job(s).`);
        await loadQueue();
      }
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Bulk clear failed");
    } finally {
      setBulkClearing(false);
    }
  };

  const bulkAction = async (action: "duplicate" | "inactive") => {
    const ids = [...selected];
    if (!ids.length) {
      notify.error("Select at least one job.");
      return;
    }
    setBulkActioning(true);
    try {
      const res =
        action === "duplicate"
          ? await admin.bulkMarkReviewDuplicate(token, ids)
          : await admin.bulkPermanentlyInactive(token, ids);
      setSelected(new Set());
      const verb = action === "duplicate" ? "marked duplicate" : "set permanently inactive";
      notify.custom.success(`${res.updated} job(s) ${verb}.`);
      await loadQueue();
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Bulk action failed");
    } finally {
      setBulkActioning(false);
    }
  };

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAllOnPage = () => {
    const pageIds = jobs.map((j) => j.id);
    const allSelected = pageIds.length > 0 && pageIds.every((id) => selected.has(id));
    setSelected((prev) => {
      const next = new Set(prev);
      if (allSelected) {
        for (const id of pageIds) next.delete(id);
      } else {
        for (const id of pageIds) next.add(id);
      }
      return next;
    });
  };

  const pageIds = jobs.map((j) => j.id);
  const allOnPageSelected =
    pageIds.length > 0 && pageIds.every((id) => selected.has(id));

  return (
    <div className="space-y-4">
      <ReviewQueueOverviewStrip token={token} onChanged={() => void loadQueue()} />

      <div className="flex flex-wrap items-center gap-2">
        <label className="text-sm text-muted-foreground" htmlFor="review-queue-preset">
          Filter
        </label>
        <select
          id="review-queue-preset"
          className="rounded-md border bg-background px-2 py-1.5 text-sm"
          value={preset}
          onChange={(e) => setPreset(e.target.value as QueuePreset)}
        >
          {(Object.keys(PRESET_LABELS) as QueuePreset[]).map((key) => (
            <option key={key} value={key}>
              {PRESET_LABELS[key]}
            </option>
          ))}
        </select>
        {!loading && (
          <span className="text-xs text-muted-foreground">
            {total.toLocaleString()} matching
            {selected.size > 0 ? ` · ${selected.size} selected` : ""}
          </span>
        )}
      </div>

      {preset === "active_no_deadline" && (
        <p className="text-xs text-amber-900 dark:text-amber-100 rounded-md border border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/50 px-3 py-2 max-w-3xl">
          These jobs are live on /jobs but blocked from matches until you add a closing date or
          confirm a duplicate. Do not use safe bulk dismiss — judge each row. See{" "}
          <code className="text-[11px]">docs/admin_job_review_cleanup.md</code>.
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={bulkClearing || bulkActioning}
          onClick={() => void autoDismissHidden(true)}
        >
          Preview hidden clear
        </Button>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          disabled={bulkClearing || bulkActioning}
          onClick={() => void autoDismissHidden(false)}
        >
          Clear hidden backlog
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => void bulkAction("duplicate")}
          disabled={!selected.size || bulkActioning || bulkClearing}
        >
          {bulkActioning ? "Working…" : `Mark selected duplicate (${selected.size})`}
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => void bulkAction("inactive")}
          disabled={!selected.size || bulkActioning || bulkClearing}
        >
          Permanently inactive ({selected.size})
        </Button>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading review queue…</p>
      ) : jobs.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No jobs pending review{preset !== "all" ? " for this filter" : ""}.
        </p>
      ) : (
        <>
          <div className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              id="review-select-all-page"
              checked={allOnPageSelected}
              onChange={toggleSelectAllOnPage}
              aria-label="Select all jobs on this page"
            />
            <label htmlFor="review-select-all-page" className="text-muted-foreground">
              Select all on this page
            </label>
          </div>
          {jobs.map((job) => {
            const draft = drafts[job.id] ?? emptyDraft();
            return (
              <Card key={job.id}>
                <CardHeader className="pb-2">
                  <div className="flex items-start gap-2">
                    <input
                      type="checkbox"
                      checked={selected.has(job.id)}
                      onChange={() => toggleSelect(job.id)}
                      aria-label={`Select ${job.title}`}
                    />
                    <div className="flex-1 min-w-0">
                      <CardTitle className="text-base">{job.title}</CardTitle>
                      <p className="text-sm text-muted-foreground">
                        {job.company || "—"} · {job.source}
                        {job.is_active ? " · active" : " · inactive"}
                        {job.reasons.length > 0 && (
                          <> · Missing: {job.reasons.join(", ")}</>
                        )}
                      </p>
                      {job.source_url && (
                        <a
                          href={job.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs underline"
                          style={{ color: "var(--copper-600)" }}
                        >
                          View original posting →
                        </a>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="grid gap-3 sm:grid-cols-3">
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
                    type="date"
                    value={draft.closing_date}
                    onChange={(e) => updateDraft(job.id, "closing_date", e.target.value)}
                  />
                  <Button
                    type="button"
                    size="sm"
                    className="sm:col-span-3 w-fit"
                    disabled={savingId === job.id}
                    onClick={() => saveJob(job.id)}
                  >
                    {savingId === job.id ? "Saving…" : "Save & publish"}
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </>
      )}

      {pages > 1 && (
        <div className="flex gap-2 justify-center">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Previous
          </Button>
          <span className="text-sm self-center">
            Page {page} of {pages}
          </span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={page >= pages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
