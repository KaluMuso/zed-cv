/** Apply button target + analytics source for match/job cards. */

export type ApplyClickSource = "direct" | "source_fallback" | "enriched";

export interface ApplyJobFields {
  title: string;
  company?: string | null;
  apply_url?: string | null;
  apply_email?: string | null;
  source_url?: string | null;
  apply_source?: string | null;
}

export interface ApplyAction {
  href: string;
  label: string;
  applySource: ApplyClickSource;
  external: boolean;
}

const SUPPORT_MAIL = "mailto:support@zedapply.com?subject=Help%20applying%20to%20a%20job";

function mailtoApply(email: string, job: ApplyJobFields): string {
  const subject = encodeURIComponent(`Application: ${job.title}`);
  const body = encodeURIComponent(
    `Hello${job.company ? ` ${job.company}` : ""},\n\nI'd like to apply for the ${job.title} role I saw on ZedApply.\n\n— Sent from zedapply.com`
  );
  return `mailto:${email}?subject=${subject}&body=${body}`;
}

/** Resolve label, href, and analytics source for the Apply affordance. */
export function resolveApplyAction(job: ApplyJobFields): ApplyAction | null {
  if (job.apply_url && /^https?:\/\//i.test(job.apply_url)) {
    const src: ApplyClickSource =
      job.apply_source === "enriched" ? "enriched" : "direct";
    return {
      href: job.apply_url,
      label: "Apply now",
      applySource: src,
      external: true,
    };
  }
  if (job.apply_email) {
    const src: ApplyClickSource =
      job.apply_source === "enriched" ? "enriched" : "direct";
    return {
      href: mailtoApply(job.apply_email, job),
      label: "Apply now",
      applySource: src,
      external: false,
    };
  }
  if (job.source_url && /^https?:\/\//i.test(job.source_url)) {
    return {
      href: job.source_url,
      label: "Apply via source",
      applySource: "source_fallback",
      external: true,
    };
  }
  return {
    href: SUPPORT_MAIL,
    label: "Contact ZedApply Support",
    applySource: "source_fallback",
    external: false,
  };
}
