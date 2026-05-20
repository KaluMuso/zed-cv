import { analytics } from "@/lib/api";
import type { ApplyClickSource } from "@/lib/applyLink";

/** Fire-and-forget apply_click analytics (authenticated). */
export function trackApplyClick(
  token: string,
  jobId: string,
  applySource: ApplyClickSource
): void {
  void analytics
    .trackEvent(token, "apply_click", {
      job_id: jobId,
      apply_source: applySource,
    })
    .catch(() => {
      /* analytics must not block apply navigation */
    });
}
