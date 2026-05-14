import type { Metadata } from "next";
import Link from "next/link";
import type { Job } from "@/lib/api";
import { JobDetailClient } from "./JobDetailClient";
import { Icon } from "@/components/ui/Icon";

/**
 * Public job-detail permalink. Server-rendered so WhatsApp / Twitter /
 * LinkedIn previews work properly when someone shares a /jobs/:id URL.
 *
 * generateMetadata fetches the job once at request time (with 60s ISR
 * revalidation) and emits og:title / og:description / canonical so
 * shares have a real card. The per-route opengraph-image.tsx file
 * (sibling) generates a branded 1200×630 PNG per job at request time
 * — Next.js auto-wires it into the og:image meta tag, so we no longer
 * set `images:` explicitly here.
 *
 * Anonymous-friendly: matches the public `/jobs` policy. The previous
 * `(app)/jobs/[id]` route is gone (deleted in commit 21c5d35).
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") ||
  "https://www.zedapply.com";

interface PageParams {
  params: { id: string };
}

async function fetchJob(id: string): Promise<Job | null> {
  try {
    const res = await fetch(`${API_BASE}/jobs/${encodeURIComponent(id)}`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) return null;
    return (await res.json()) as Job;
  } catch {
    return null;
  }
}

/** Strip HTML, collapse whitespace, truncate to N chars with ellipsis. */
function cleanForMeta(s: string | null | undefined, max = 160): string {
  if (!s) return "";
  const t = s
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  if (t.length <= max) return t;
  return t.slice(0, max - 1).trimEnd() + "…";
}

export async function generateMetadata({
  params,
}: PageParams): Promise<Metadata> {
  const job = await fetchJob(params.id);
  if (!job) {
    return {
      title: "Job not found",
      robots: { index: false, follow: false },
    };
  }

  // Spec'd og:title shape: "{title} at {company} — ZedApply". The
  // " at {company}" half is dropped when company is null so titles
  // don't read "Senior Accountant at  — ZedApply".
  const baseTitle = `${job.title}${job.company ? ` at ${job.company}` : ""}`;
  const ogTitle = `${baseTitle} — ZedApply`;
  const description =
    cleanForMeta(job.description, 200) ||
    `Open role in ${job.location || "Zambia"}. Apply via ZedApply.`;
  const url = `${SITE_URL}/jobs/${job.id}`;

  return {
    // Page <title> stays short — the layout's title template appends
    // "— ZedApply" so the tab reads "Senior Accountant — ZedApply".
    title: baseTitle,
    description,
    alternates: { canonical: url },
    openGraph: {
      // Spec says "website" — kept literally. (Open Graph itself accepts
      // "article" as a better fit for content pages, but we honour the
      // spec; crawlers don't penalise either choice.)
      type: "website",
      title: ogTitle,
      description,
      url,
      siteName: "ZedApply",
      // No explicit images: opengraph-image.tsx in this same route
      // segment auto-generates the per-job card. Setting `images:` here
      // would override that, so we deliberately leave it off.
    },
    twitter: {
      card: "summary_large_image",
      title: ogTitle,
      description,
    },
  };
}

/**
 * Optional task-#60 enrichment fields. Treated as additive: present
 * once /lib/api.ts's Job type widens (task #60), harmless until then.
 * Kept local to this file so the SEO slice doesn't take a hard dep
 * on task #60 shipping first.
 */
type EnrichedJob = Job & {
  employment_type?: string | null;
  pay_frequency?: string | null;
  currency?: string | null;
};

/**
 * Build the Schema.org JobPosting structured data for Google's Job
 * Search rich results. Only fields backed by real job data are emitted;
 * we never fabricate values to satisfy the schema, which would risk a
 * "deceptive structured data" manual action from Google.
 */
function buildJobPostingJsonLd(job: EnrichedJob): Record<string, unknown> {
  const url = `${SITE_URL}/jobs/${job.id}`;

  // Map our internal employment_type enum to Schema.org's accepted
  // values. https://schema.org/employmentType
  const employmentTypeMap: Record<string, string> = {
    full_time: "FULL_TIME",
    part_time: "PART_TIME",
    contract: "CONTRACTOR",
    freelance: "CONTRACTOR",
    internship: "INTERN",
    temporary: "TEMPORARY",
  };

  // Map our pay_frequency to Schema.org's unitText for QuantitativeValue.
  // https://schema.org/baseSalary
  const payFrequencyMap: Record<string, string> = {
    monthly: "MONTH",
    annual: "YEAR",
    hourly: "HOUR",
    daily: "DAY",
  };

  const data: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "JobPosting",
    title: job.title,
    // 5,000 chars is well under Google's stated 30k limit for the field
    // and avoids dumping massive raw descriptions into the page source.
    description: cleanForMeta(job.description, 5000),
    url,
  };

  if (job.posted_at) data.datePosted = job.posted_at;
  if (job.closing_date) data.validThrough = job.closing_date;

  if (job.employment_type && employmentTypeMap[job.employment_type]) {
    data.employmentType = employmentTypeMap[job.employment_type];
  }

  if (job.company) {
    data.hiringOrganization = {
      "@type": "Organization",
      name: job.company,
      // sameAs intentionally left off — we don't reliably know the
      // employer's homepage and a wrong URL is worse than none.
    };
  }

  if (job.location) {
    data.jobLocation = {
      "@type": "Place",
      address: {
        "@type": "PostalAddress",
        addressLocality: job.location,
        addressCountry: "ZM",
      },
    };
  }

  if (job.salary_min || job.salary_max) {
    // Salaries are stored as ngwee (1 ZMW = 100 ngwee); Schema.org
    // wants the major-unit value. Falling back to "MONTH" when
    // pay_frequency is null matches the most common case in our feed.
    const ngweeToZmw = (n: number | null | undefined) =>
      typeof n === "number" ? Math.round(n / 100) : undefined;
    const minZmw = ngweeToZmw(job.salary_min);
    const maxZmw = ngweeToZmw(job.salary_max);
    const value: Record<string, unknown> = {
      "@type": "QuantitativeValue",
      unitText:
        (job.pay_frequency && payFrequencyMap[job.pay_frequency]) || "MONTH",
    };
    if (typeof minZmw === "number") value.minValue = minZmw;
    if (typeof maxZmw === "number") value.maxValue = maxZmw;
    data.baseSalary = {
      "@type": "MonetaryAmount",
      currency: job.currency || "ZMW",
      value,
    };
  }

  if (job.apply_email) {
    // Schema.org JobPosting uses `applicationContact` (a ContactPoint)
    // when an email is the canonical apply route. apply_url, when set,
    // is the more important signal but lives in `url` above + the page
    // itself, so we don't duplicate it here.
    data.applicationContact = {
      "@type": "ContactPoint",
      email: job.apply_email,
    };
  }

  return data;
}

export default async function JobDetailPage({ params }: PageParams) {
  const job = await fetchJob(params.id);

  if (!job) {
    return (
      <div className="max-w-[820px] mx-auto px-6 py-20 text-center">
        <div
          className="w-16 h-16 mx-auto mb-4 rounded-2xl flex items-center justify-center"
          style={{ border: "2px dashed var(--line-2)", color: "var(--muted)" }}
        >
          <Icon name="search" size={24} />
        </div>
        <h1
          className="font-display text-3xl mb-2"
          style={{ letterSpacing: "-0.01em" }}
        >
          Job not found
        </h1>
        <p className="text-sm mb-6" style={{ color: "var(--muted)" }}>
          This listing may have been removed, closed, or never existed.
        </p>
        <Link href="/jobs" className="btn btn-primary btn-sm">
          <Icon name="arrowLeft" size={14} /> Browse open roles
        </Link>
      </div>
    );
  }

  const jsonLd = buildJobPostingJsonLd(job as EnrichedJob);

  return (
    <article className="max-w-[820px] mx-auto px-2 sm:px-6 py-6 md:py-10">
      {/* JSON-LD JobPosting — Google's Job Search rich-results requirement.
          Server-rendered so the structured data lands in the initial HTML,
          where every crawler (including ones that don't run JS) can see it. */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <JobDetailClient job={job} />
    </article>
  );
}
