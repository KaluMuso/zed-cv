import type { MetadataRoute } from "next";

// sitemap.xml is what Search Console + Bing Webmaster Tools ingest to
// discover and re-crawl the per-job permalinks. We list the brand pages
// statically (priorities + change frequencies tuned to how often each
// actually moves) and append one entry per active job, fetched live
// from the backend.
//
// Re-validated every hour: the static block is cheap, and refreshing
// the per-job list more often than that costs the backend more than
// crawlers actually benefit from.

const BASE_URL =
  process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") ||
  "https://www.zedapply.com";
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// Sitemap protocol caps a single sitemap file at 50,000 URLs / 50 MB.
// We stay under by capping the job-id fetch at the same number on the
// backend. If the active-jobs total ever exceeds 50k, the right fix is
// a sitemap index — not silently dropping URLs.
const MAX_JOB_URLS = 50000;

export const revalidate = 3600; // 1 hour

interface SitemapJobId {
  id: string;
  lastmod: string | null;
}

async function fetchJobIds(): Promise<SitemapJobId[]> {
  try {
    const res = await fetch(`${API_BASE}/jobs/sitemap`, {
      next: { revalidate },
    });
    if (!res.ok) return [];
    const body = (await res.json()) as { ids?: SitemapJobId[] };
    return body.ids ?? [];
  } catch {
    // Don't let a backend outage break the entire sitemap — return the
    // static URLs and let the per-job entries fill in next revalidation.
    return [];
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();

  const staticEntries: MetadataRoute.Sitemap = [
    {
      url: `${BASE_URL}/`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 1.0,
    },
    {
      url: `${BASE_URL}/jobs`,
      lastModified: now,
      changeFrequency: "daily",
      priority: 0.9,
    },
    {
      url: `${BASE_URL}/pricing`,
      lastModified: now,
      changeFrequency: "monthly",
      priority: 0.7,
    },
    {
      url: `${BASE_URL}/legal/privacy`,
      lastModified: now,
      changeFrequency: "yearly",
      priority: 0.3,
    },
    {
      url: `${BASE_URL}/legal/terms`,
      lastModified: now,
      changeFrequency: "yearly",
      priority: 0.3,
    },
    {
      url: `${BASE_URL}/legal/cookies`,
      lastModified: now,
      changeFrequency: "yearly",
      priority: 0.3,
    },
    {
      url: `${BASE_URL}/legal/refund`,
      lastModified: now,
      changeFrequency: "yearly",
      priority: 0.3,
    },
  ];

  const ids = (await fetchJobIds()).slice(0, MAX_JOB_URLS);
  const jobEntries: MetadataRoute.Sitemap = ids.map((j) => ({
    url: `${BASE_URL}/jobs/${j.id}`,
    lastModified: j.lastmod ? new Date(j.lastmod) : now,
    changeFrequency: "weekly",
    priority: 0.6,
  }));

  return [...staticEntries, ...jobEntries];
}
