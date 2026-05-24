import type { Metadata } from "next";
import Link from "next/link";
import type { Job } from "@/lib/api";
import { buildJobPostingJsonLd, cleanForJobSchema } from "@/lib/job-posting-jsonld";
import { SITE_URL } from "@/lib/site-metadata";
import { JobDetailClient } from "./JobDetailClient";
import { Icon } from "@/components/ui/Icon";

/**
 * Public job-detail permalink. Server-rendered so WhatsApp / Twitter /
 * LinkedIn previews work properly when someone shares a /jobs/:id URL.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

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

  const baseTitle = `${job.title}${job.company ? ` at ${job.company}` : ""}`;
  const ogTitle = `${baseTitle} — ZedApply`;
  const description =
    cleanForJobSchema(job.description, 200) ||
    `Open role in ${job.location || "Zambia"}. Apply via ZedApply.`;
  const url = `${SITE_URL}/jobs/${job.id}`;

  return {
    title: baseTitle,
    description,
    alternates: { canonical: url },
    openGraph: {
      type: "website",
      title: ogTitle,
      description,
      url,
      siteName: "ZedApply",
    },
    twitter: {
      card: "summary_large_image",
      title: ogTitle,
      description,
    },
  };
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

  const jsonLd = buildJobPostingJsonLd(job);

  return (
    <article className="max-w-6xl mx-auto px-2 sm:px-6 py-6 md:py-10">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <JobDetailClient job={job} />
    </article>
  );
}
