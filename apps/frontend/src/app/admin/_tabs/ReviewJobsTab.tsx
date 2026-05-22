"use client";

import { useCallback, useEffect, useState } from "react";
import { admin, type AdminJobReviewRow } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { notify } from "@/lib/toast";

type Draft = {
  apply_url: string;
  apply_email: string;
  closing_date: string;
};

function emptyDraft(): Draft {
  return { apply_url: "", apply_email: "", closing_date: "" };
}

export function ReviewJobsTab({ token }: { token: string }) {
  const [jobs, setJobs] = useState<AdminJobReviewRow[]>([]);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [savingId, setSavingId] = useState<string | null>(null);

  const loadQueue = useCallback(async () => {
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

  const saveJob = async (jobId: string) => {
    const draft = drafts[jobId] ?? emptyDraft();
    const payload = Object.fromEntries(
      Object.entries(draft).filter(([, v]) => v.trim())
    );
    setSavingId(jobId);
    try {
      await admin.updateTrack4eReviewJob(token, jobId, payload);
      notify.custom.success("Job updated.");
      await loadQueue();
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Could not save job");
    } finally {
      setSavingId(null);
    }
  };

  const bulkAction = async (action: "duplicate" | "inactive") => {
    const ids = [...selected];
    if (!ids.length) {
      notify.error("Select at least one job.");
      return;
    }
    try {
      if (action === "duplicate") {
        await admin.bulkMarkReviewDuplicate(token, ids);
      } else {
        await admin.bulkPermanentlyInactive(token, ids);
      }
      setSelected(new Set());
      notify.custom.success("Bulk action completed.");
      await loadQueue();
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Bulk action failed");
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

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => bulkAction("duplicate")}
          disabled={!selected.size}
        >
          Mark as duplicate
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => bulkAction("inactive")}
          disabled={!selected.size}
        >
          Permanently inactive
        </Button>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading review queue…</p>
      ) : jobs.length === 0 ? (
        <p className="text-sm text-muted-foreground">No jobs pending review.</p>
      ) : (
        jobs.map((job) => {
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
        })
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
