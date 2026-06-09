"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { admin, type AdminContactFixJobRow } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { notify } from "@/lib/toast";
import { Loader2 } from "lucide-react";

// Patterns / values that the scraper sometimes captures from aggregator
// pages even though they're not a real apply route. Pre-filling the form
// with these means the admin clicks Save & next without typing anything,
// the backend dutifully re-saves the same junk, the row stays in the
// queue, and the progress counter never advances. Strip them so the form
// starts blank for these fields and the admin has to enter a real value.
const APPLY_URL_BLOCKED_RE =
  /^https?:\/\/(?:www\.)?(?:whatsapp\.com\/(?:channel|c)\/|wa\.me\/channel\/)/i;
const AGGREGATOR_OWNED_PHONES = new Set<string>([
  "+260813252760", // jobwebzambia.com listing line — appears on every jobwebzambia job
]);

type FormState = {
  apply_url: string;
  apply_email: string;
  contact_phone: string;
};

type Cleared = {
  apply_url?: string;
  contact_phone?: string;
};

function emptyForm(): FormState {
  return { apply_url: "", apply_email: "", contact_phone: "" };
}

function isBlockedApplyUrl(v: string | null | undefined): boolean {
  return !!v && APPLY_URL_BLOCKED_RE.test(v);
}

function isAggregatorPhone(v: string | null | undefined): boolean {
  return !!v && AGGREGATOR_OWNED_PHONES.has(v.trim());
}

function formFromJob(job: AdminContactFixJobRow): { form: FormState; cleared: Cleared } {
  const rawUrl = job.apply_url ?? "";
  const rawPhone = job.contact_phone ?? "";
  const blockedUrl = isBlockedApplyUrl(rawUrl);
  const blockedPhone = isAggregatorPhone(rawPhone);
  return {
    form: {
      apply_url: blockedUrl ? "" : rawUrl,
      apply_email: job.apply_email ?? "",
      contact_phone: blockedPhone ? "" : rawPhone,
    },
    cleared: {
      ...(blockedUrl ? { apply_url: rawUrl } : {}),
      ...(blockedPhone ? { contact_phone: rawPhone } : {}),
    },
  };
}

export function BulkFixWizard({ token }: { token: string }) {
  const [job, setJob] = useState<AdminContactFixJobRow | null>(null);
  const [remaining, setRemaining] = useState(0);
  const [baselineTotal, setBaselineTotal] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [cleared, setCleared] = useState<Cleared>({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const sessionStart = useRef(Date.now());
  const baselineCaptured = useRef(false);
  const skippedIds = useRef(new Set<string>());
  // Track the last id we processed (saved OR marked uncontactable). If
  // the server returns the SAME id back-to-back, we auto-skip it so the
  // admin doesn't get stuck on the same job (which happened when the
  // queue criteria didn't actually clear after a no-op save).
  const lastProcessedId = useRef<string | null>(null);

  const loadNext = useCallback(async () => {
    setLoading(true);
    try {
      const res = await admin.jobsNeedsContactFix(token, { page: 1, per_page: 50 });
      const effectiveRemaining = Math.max(0, res.total - skippedIds.current.size);
      setRemaining(effectiveRemaining);
      if (!baselineCaptured.current && res.total > 0) {
        baselineCaptured.current = true;
        setBaselineTotal(res.total);
      }
      // Skip the job we just processed if it comes back at the top of
      // the queue (server-side criteria likely still matches it). The
      // admin can re-visit it later via the regular Jobs tab.
      const candidates = res.jobs.filter((j) => !skippedIds.current.has(j.id));
      let next = candidates.find((j) => j.id !== lastProcessedId.current) ?? null;
      if (!next && candidates.length > 0) {
        // All candidates equal lastProcessedId — fall through to it so
        // we don't show an empty state when there's still work to do.
        next = candidates[0];
      }
      setJob(next);
      if (next) {
        const { form: f, cleared: c } = formFromJob(next);
        setForm(f);
        setCleared(c);
      } else {
        setForm(emptyForm());
        setCleared({});
      }
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Failed to load queue");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void loadNext();
  }, [loadNext]);

  const fixedCount =
    baselineTotal !== null ? Math.max(0, baselineTotal - remaining) : 0;
  const progressLabel =
    baselineTotal !== null && baselineTotal > 0
      ? `${fixedCount} of ${baselineTotal} fixed`
      : remaining > 0
        ? `${remaining} remaining`
        : "Queue clear";

  const pct =
    baselineTotal && baselineTotal > 0
      ? Math.round((fixedCount / baselineTotal) * 100)
      : remaining === 0
        ? 100
        : 0;

  const save = async () => {
    if (!job) return;
    const trimmedUrl = form.apply_url.trim();
    const trimmedEmail = form.apply_email.trim();
    const trimmedPhone = form.contact_phone.trim();
    // Defence in depth — if the admin pastes a blocked URL by hand,
    // refuse to send it to the server. The server should also reject
    // it, but catching here gives a clearer toast immediately.
    if (trimmedUrl && isBlockedApplyUrl(trimmedUrl)) {
      notify.error(
        "That URL is an aggregator broadcast channel, not a valid apply route. Enter the employer's own link.",
      );
      return;
    }
    if (trimmedPhone && isAggregatorPhone(trimmedPhone)) {
      notify.error(
        "That phone number belongs to the aggregator listing site, not the employer.",
      );
      return;
    }
    const payload = {
      apply_url: trimmedUrl || undefined,
      apply_email: trimmedEmail || undefined,
      contact_phone: trimmedPhone || undefined,
    };
    if (!payload.apply_url && !payload.apply_email && !payload.contact_phone) {
      notify.error("Enter at least one of apply URL, email, or phone.");
      return;
    }
    setBusy(true);
    try {
      await admin.patchJobContact(token, job.id, payload);
      lastProcessedId.current = job.id;
      notify.custom.success("Saved.");
      void admin.reEnrichJob(token, job.id).catch(() => {});
      await loadNext();
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const markUncontactable = async () => {
    if (!job) return;
    setBusy(true);
    try {
      await admin.patchJobContact(token, job.id, {
        mark_uncontactable: true,
        reason: "manual_uncontactable",
      });
      lastProcessedId.current = job.id;
      notify.custom.success("Marked un-contactable.");
      await loadNext();
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Update failed");
    } finally {
      setBusy(false);
    }
  };

  const skip = () => {
    if (job) skippedIds.current.add(job.id);
    void loadNext();
  };

  if (loading && !job) {
    return (
      <p className="text-sm text-muted-foreground flex items-center gap-2">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading queue…
      </p>
    );
  }

  if (!job) {
    return (
      <Card>
        <CardContent className="py-10 text-center space-y-3">
          <p className="text-sm text-muted-foreground">No jobs need contact fixes.</p>
          <Link href="/admin/jobs" className="text-sm text-primary underline">
            Back to jobs
          </Link>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4 max-w-2xl">
      <div>
        <div className="flex justify-between text-sm mb-1">
          <span className="font-medium">{progressLabel}</span>
          <span className="text-muted-foreground tabular-nums">{pct}%</span>
        </div>
        <div className="h-2 rounded-full bg-muted overflow-hidden">
          <div
            className="h-full bg-primary transition-all duration-300"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">{job.title}</CardTitle>
          <p className="text-sm text-muted-foreground">
            {job.company || "Unknown company"}
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          {job.source_url ? (
            <a
              href={job.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-primary underline break-all"
            >
              Original listing ↗
            </a>
          ) : null}

          {cleared.apply_url || cleared.contact_phone ? (
            <div className="rounded-md border border-amber-300 bg-amber-50 dark:bg-amber-950/30 p-3 space-y-1">
              <p className="text-xs font-semibold text-amber-900 dark:text-amber-200">
                Aggregator contamination cleared from this row
              </p>
              {cleared.apply_url ? (
                <p className="text-xs text-amber-800 dark:text-amber-300 break-all">
                  Previous apply URL was <code className="font-mono">{cleared.apply_url}</code> — not a valid apply route.
                </p>
              ) : null}
              {cleared.contact_phone ? (
                <p className="text-xs text-amber-800 dark:text-amber-300">
                  Previous contact phone was <code className="font-mono">{cleared.contact_phone}</code> — belongs to the aggregator listing site, not the employer.
                </p>
              ) : null}
              <p className="text-xs text-amber-800 dark:text-amber-300">
                Enter the employer&apos;s real apply route below.
              </p>
            </div>
          ) : null}

          <div className="grid gap-3">
            <label className="text-xs font-medium text-muted-foreground">
              Apply URL
              <Input
                className="mt-1"
                value={form.apply_url}
                onChange={(e) => setForm((f) => ({ ...f, apply_url: e.target.value }))}
                placeholder="https://employer.co.zm/careers/…"
              />
            </label>
            <label className="text-xs font-medium text-muted-foreground">
              Apply email
              <Input
                className="mt-1"
                type="email"
                value={form.apply_email}
                onChange={(e) => setForm((f) => ({ ...f, apply_email: e.target.value }))}
                placeholder="careers@company.co.zm"
              />
            </label>
            <label className="text-xs font-medium text-muted-foreground">
              Contact phone (+260…)
              <Input
                className="mt-1"
                value={form.contact_phone}
                onChange={(e) => setForm((f) => ({ ...f, contact_phone: e.target.value }))}
                placeholder="+260971234567"
              />
            </label>
          </div>

          <div className="flex flex-wrap gap-2 pt-2">
            <Button type="button" disabled={busy} onClick={() => void save()}>
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save & next"}
            </Button>
            <Button type="button" variant="outline" disabled={busy} onClick={skip}>
              Skip
            </Button>
            <Button
              type="button"
              variant="destructive"
              disabled={busy}
              onClick={() => void markUncontactable()}
            >
              Mark un-contactable
            </Button>
          </div>
        </CardContent>
      </Card>

      <p className="text-xs text-muted-foreground">
        Session started {new Date(sessionStart.current).toLocaleTimeString()}.{" "}
        {remaining} job{remaining === 1 ? "" : "s"} left in queue.
      </p>
    </div>
  );
}
