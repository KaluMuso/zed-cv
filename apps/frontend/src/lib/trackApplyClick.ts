import { apiFetch } from "@/lib/api";
import type { ApplyClickSource } from "@/lib/applyLink";

/** Fire-and-forget apply_click analytics (authenticated). */
export function trackApplyClick(
  token: string,
  jobId: string,
  applySource: ApplyClickSource
): void {
  void apiFetch<void>("/analytics/events", {
    method: "POST",
    token,
    body: { event: "apply_click", properties: { job_id: jobId, apply_source: applySource } },
  }).catch(() => {
    /* analytics must not block apply navigation */
  });
}
