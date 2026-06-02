/** Apply button targets + analytics source for match/job cards (Track 4e). */

export type ApplyClickSource = "direct" | "source_fallback" | "enriched" | "description_email";

export interface ApplyJobFields {
  title: string;
  company?: string | null;
  apply_url?: string | null;
  apply_email?: string | null;
  contact_phone?: string | null;
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

export type ApplyContactKind = "email" | "whatsapp" | "phone" | "website";

export interface ApplyContactMethod {
  kind: ApplyContactKind;
  label: string;
  display: string;
  copyValue: string;
  href?: string;
  applySource: ApplyClickSource;
}

const SUPPORT_MAIL =
  "mailto:support@zedapply.com?subject=Help%20applying%20to%20a%20job";

/** Known Zambian job-board hosts — never treat as direct employer apply links. */
const AGGREGATOR_HOSTS = new Set([
  "jobwebzambia.com",
  "gozambiajobs.com",
  "jobsearchzambia.com",
  "jobsearchzm.com",
  "careersinafrica.com",
  "everjobs.com.zm",
]);

function hostnameFromUrl(url: string): string | null {
  try {
    const host = new URL(url).hostname.toLowerCase();
    return host.startsWith("www.") ? host.slice(4) : host;
  } catch {
    return null;
  }
}

/** True when apply_url points at a job-board aggregator, not the employer. */
export function isAggregatorApplyUrl(url: string | null | undefined): boolean {
  if (!url?.trim()) return false;
  const host = hostnameFromUrl(url.trim());
  if (!host) return false;
  if (AGGREGATOR_HOSTS.has(host)) return true;
  return [...AGGREGATOR_HOSTS].some(
    (domain) => host === domain || host.endsWith(`.${domain}`),
  );
}

/** Plain-text intro users can paste into an email client (Apply modal). */
export function buildEmailIntroduction(job: ApplyJobFields): string {
  return `Dear hiring manager,

I am writing to apply for the ${job.title} role${
    job.company ? ` at ${job.company}` : ""
  }.

I found this opportunity on ZedApply and would welcome the chance to discuss my application.

Kind regards`;
}

export function buildEmailSubject(job: ApplyJobFields): string {
  return `Application: ${job.title}`;
}

function applySourceFromField(
  job: ApplyJobFields,
  field: "url" | "email",
): ApplyClickSource {
  if (job.apply_source === "description_email" || job.apply_source === "description_url") {
    return "description_email";
  }
  if (job.apply_source === "enriched") return "enriched";
  return field === "url" ? "direct" : "direct";
}

function normalizePhone(raw: string): string | null {
  const digits = raw.replace(/\D/g, "");
  if (digits.startsWith("260") && digits.length === 12) return `+${digits}`;
  if (digits.length === 10 && digits.startsWith("0")) return `+260${digits.slice(1)}`;
  if (digits.length === 9) return `+260${digits}`;
  return null;
}

function employerApplyUrl(job: ApplyJobFields): string | null {
  const url = job.apply_url?.trim();
  if (!url || !/^https?:\/\//i.test(url)) return null;
  if (isAggregatorApplyUrl(url)) return null;
  return url;
}

/** Resolve primary apply affordance for compact job cards. */
export function resolveApplyAction(job: ApplyJobFields): ApplyAction | null {
  const url = employerApplyUrl(job);
  const hasEmail = Boolean(job.apply_email?.trim());
  const phone = job.contact_phone ? normalizePhone(job.contact_phone) : null;

  if (url) {
    return {
      href: url,
      label: "Apply on company site",
      applySource: applySourceFromField(job, "url"),
      external: true,
    };
  }

  if (hasEmail) {
    return {
      href: "#",
      label: "Apply",
      applySource: applySourceFromField(job, "email"),
      external: false,
    };
  }

  if (phone) {
    return {
      href: "#",
      label: "Apply",
      applySource: "direct",
      external: false,
    };
  }

  return null;
}

/** Alias used in Phase 3 specs — same as {@link resolveApplyAction}. */
export const resolveApplyUrl = resolveApplyAction;

/** Legacy fallback when no structured contact exists (admin-only / stale clients). */
export function resolveApplyActionOrSupport(job: ApplyJobFields): ApplyAction {
  return (
    resolveApplyAction(job) ?? {
      href: SUPPORT_MAIL,
      label: "Contact Support",
      applySource: "source_fallback",
      external: false,
    }
  );
}

/** All structured apply channels for job detail + Apply modal. */
export function resolveApplyContactMethods(job: ApplyJobFields): ApplyContactMethod[] {
  const methods: ApplyContactMethod[] = [];
  const seen = new Set<string>();

  const push = (method: ApplyContactMethod) => {
    const key = `${method.kind}:${method.copyValue.toLowerCase()}`;
    if (seen.has(key)) return;
    seen.add(key);
    methods.push(method);
  };

  const url = employerApplyUrl(job);
  if (url) {
    push({
      kind: "website",
      label: "Web application portal",
      display: url.replace(/^https?:\/\//i, "").replace(/\/$/, ""),
      copyValue: url,
      href: url,
      applySource: applySourceFromField(job, "url"),
    });
  }

  const email = job.apply_email?.trim();
  if (email) {
    push({
      kind: "email",
      label: "Advertising email",
      display: email,
      copyValue: email,
      applySource: applySourceFromField(job, "email"),
    });
  }

  const phone = job.contact_phone ? normalizePhone(job.contact_phone) : null;
  if (phone) {
    const waDigits = phone.replace(/\D/g, "");
    push({
      kind: "phone",
      label: "Phone contact",
      display: phone,
      copyValue: phone,
      applySource: "direct",
    });
    push({
      kind: "whatsapp",
      label: "WhatsApp",
      display: phone,
      copyValue: phone,
      href: `https://wa.me/${waDigits}`,
      applySource: "direct",
    });
  }

  return methods;
}

/** True when the job has at least one listable apply channel in structured fields. */
export function hasStructuredApplyContact(job: ApplyJobFields): boolean {
  return resolveApplyContactMethods(job).length > 0;
}
