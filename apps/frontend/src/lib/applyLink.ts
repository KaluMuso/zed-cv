/** Apply button targets + analytics source for match/job cards (Track 4e). */

export type ApplyClickSource = "direct" | "source_fallback" | "enriched" | "description_email";

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
  secondary?: ApplyAction;
}

const SUPPORT_MAIL =
  "mailto:support@zedapply.com?subject=Help%20applying%20to%20a%20job";

function mailtoApply(email: string, job: ApplyJobFields): string {
  const subject = encodeURIComponent(`Application: ${job.title}`);
  const body = encodeURIComponent(
    `Dear hiring manager,\n\nI am writing to apply for the ${job.title} role${
      job.company ? ` at ${job.company}` : ""
    }.\n\nI found this opportunity on ZedApply and would welcome the chance to discuss my application.\n\nKind regards`
  );
  return `mailto:${email}?subject=${subject}&body=${body}`;
}

function applySourceFromField(
  job: ApplyJobFields,
  field: "url" | "email"
): ApplyClickSource {
  if (job.apply_source === "description_email" || job.apply_source === "description_url") {
    return "description_email";
  }
  if (job.apply_source === "enriched") return "enriched";
  return field === "url" ? "direct" : "direct";
}

/** Resolve primary + optional secondary apply affordances. */
export function resolveApplyAction(job: ApplyJobFields): ApplyAction {
  const hasUrl = Boolean(job.apply_url && /^https?:\/\//i.test(job.apply_url));
  const hasEmail = Boolean(job.apply_email?.trim());

  if (hasUrl && hasEmail) {
    return {
      href: job.apply_url as string,
      label: "Apply now",
      applySource: applySourceFromField(job, "url"),
      external: true,
      secondary: {
        href: mailtoApply(job.apply_email as string, job),
        label: "Or email instead →",
        applySource: applySourceFromField(job, "email"),
        external: false,
      },
    };
  }

  if (hasUrl) {
    return {
      href: job.apply_url as string,
      label: "Apply now",
      applySource: applySourceFromField(job, "url"),
      external: true,
    };
  }

  if (hasEmail) {
    return {
      href: mailtoApply(job.apply_email as string, job),
      label: "Apply via email",
      applySource: applySourceFromField(job, "email"),
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
    label: "Contact Support",
    applySource: "source_fallback",
    external: false,
  };
}
