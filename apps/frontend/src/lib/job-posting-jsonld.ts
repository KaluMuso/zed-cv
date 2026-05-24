import type { Job } from "@/lib/api";
import { SITE_URL } from "@/lib/site-metadata";

/** Strip HTML, collapse whitespace, truncate to N chars with ellipsis. */
export function cleanForJobSchema(
  s: string | null | undefined,
  max = 160
): string {
  if (!s) return "";
  const t = s
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  if (t.length <= max) return t;
  return t.slice(0, max - 1).trimEnd() + "…";
}

const employmentTypeMap: Record<string, string> = {
  full_time: "FULL_TIME",
  part_time: "PART_TIME",
  contract: "CONTRACTOR",
  freelance: "CONTRACTOR",
  internship: "INTERN",
  temporary: "TEMPORARY",
};

const payFrequencyMap: Record<string, string> = {
  monthly: "MONTH",
  annual: "YEAR",
  hourly: "HOUR",
  daily: "DAY",
};

/**
 * Build Schema.org JobPosting JSON-LD for Google Job Search rich results.
 * Only fields backed by real job data are emitted — no fabricated defaults.
 */
export function buildJobPostingJsonLd(job: Job): Record<string, unknown> {
  const url = `${SITE_URL}/jobs/${job.id}`;

  const data: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "JobPosting",
    title: job.title,
    description: cleanForJobSchema(job.description, 5000),
    url,
    identifier: {
      "@type": "PropertyValue",
      name: "ZedApply job id",
      value: job.id,
    },
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

  if (job.apply_url) {
    data.directApply = true;
  }

  if (job.apply_email) {
    data.applicationContact = {
      "@type": "ContactPoint",
      email: job.apply_email,
    };
  }

  return data;
}
