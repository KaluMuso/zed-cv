"use client";

import { useCallback, useEffect, useState } from "react";
import { admin, type AdminReviewQueueOverview } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { notify } from "@/lib/toast";

function StatPill({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border px-3 py-2 text-center min-w-[7rem]">
      <p className="text-lg font-semibold tabular-nums">{value.toLocaleString()}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

export function ReviewQueueOverviewStrip({
  token,
  onChanged,
}: {
  token: string;
  onChanged?: () => void;
}) {
  const [overview, setOverview] = useState<AdminReviewQueueOverview | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await admin.reviewQueueOverview(token);
      setOverview(data);
    } catch {
      setOverview(null);
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  const runSafe = async (dryRun: boolean) => {
    setBusy(true);
    try {
      const res = await admin.bulkDismissSafeReview(token, { dry_run: dryRun });
      if (dryRun) {
        notify.custom.info(
          `Safe to clear: ${res.hidden_eligible} hidden, ${res.expired_eligible} expired, ${res.junk_eligible} junk.`
        );
      } else {
        const total =
          res.hidden_dismissed + res.expired_dismissed + res.junk_dismissed;
        notify.custom.success(`Cleared ${total} job(s) from review.`);
        await load();
        onChanged?.();
      }
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Bulk dismiss failed");
    } finally {
      setBusy(false);
    }
  };

  if (!overview) return null;

  return (
    <div className="space-y-3 rounded-lg border bg-muted/30 p-4">
      <div className="flex flex-wrap gap-2 justify-center sm:justify-start">
        <StatPill label="Need review" value={overview.need_review} />
        <StatPill
          label="Active, no deadline"
          value={overview.active_no_deadline_pending ?? 0}
        />
        <StatPill label="Deactivated" value={overview.deactivated} />
        <StatPill label="Active public" value={overview.active_public} />
      </div>
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={busy}
          onClick={() => void runSafe(true)}
        >
          Preview safe bulk clear
        </Button>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          disabled={busy}
          onClick={() => void runSafe(false)}
        >
          Clear all safe backlog
        </Button>
      </div>
      <p className="text-xs text-muted-foreground max-w-3xl">
        Safe bulk clear removes review flags only (never changes quality score or deletes
        rows). Criteria: hidden with no contact, past closing date, or ingest junk
        (thin description / bad URL). See docs/admin_job_review_cleanup.md.
      </p>
    </div>
  );
}
