import type { Job } from "@/lib/api";
import { isJobListingClosed } from "@/lib/isJobListingClosed";

export type JobVisibilityStatus = "open" | "recently_closed" | "archived";

const GRACE_DAYS = 3;

function parseClosingDate(closingDate: string | null | undefined): Date | null {
  if (!closingDate) return null;
  const d = new Date(closingDate);
  return Number.isNaN(d.getTime()) ? null : d;
}

function startOfDay(d: Date): number {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
}

/** Client mirror of jobs_user_facing.visibility_status (migration 095). */
export function computeJobVisibilityStatus(
  job: Pick<Job, "is_active" | "closing_date" | "visibility_status">,
  ref: Date = new Date(),
): JobVisibilityStatus {
  if (job.visibility_status === "open" || job.visibility_status === "recently_closed" || job.visibility_status === "archived") {
    return job.visibility_status;
  }
  const today = startOfDay(ref);
  const active = job.is_active !== false;
  const close = parseClosingDate(job.closing_date);
  if (active && (!close || startOfDay(close) >= today)) {
    return "open";
  }
  if (close) {
    const closeStart = startOfDay(close);
    const graceStart = today - GRACE_DAYS * 24 * 60 * 60 * 1000;
    if (closeStart < today && closeStart >= graceStart) {
      return "recently_closed";
    }
  }
  return "archived";
}

export function isRecentlyClosedJob(
  job: Pick<Job, "is_active" | "closing_date" | "visibility_status">,
): boolean {
  return computeJobVisibilityStatus(job) === "recently_closed";
}

/** Greyed card treatment for closed roles still visible in the grace window. */
export function isGreyedClosedListing(
  job: Pick<Job, "is_active" | "closing_date" | "visibility_status">,
): boolean {
  return isJobListingClosed(job) || isRecentlyClosedJob(job);
}
