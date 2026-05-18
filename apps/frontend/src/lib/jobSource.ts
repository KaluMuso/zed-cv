/**
 * Render a human-readable provenance label for a job listing. Mirrors
 * the `jobs.source` column values from the backend: manual, scraper,
 * ocr, partner. Falls back to a generic label when source is missing
 * or an unknown future value lands client-side.
 *
 * For scraper rows we try to surface the source domain (e.g.
 * "Scraped from linkedin.com") because candidates judge listings
 * partly by where they came from. If source_url is missing or
 * unparseable we degrade to a bare "Scraped" rather than show a
 * confusing "Scraped from undefined".
 */
export function formatJobSource(
  source: string | null | undefined,
  sourceUrl?: string | null,
): string {
  if (!source) return "Listed externally";
  switch (source) {
    case "manual":
      return "Posted by admin";
    case "scraper": {
      const host = extractHost(sourceUrl);
      return host ? `Scraped from ${host}` : "Scraped";
    }
    case "ocr":
      return "Scraped from WhatsApp";
    case "partner":
      return "Partner post";
    default:
      return "Listed externally";
  }
}

function extractHost(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    const host = new URL(url).hostname;
    return host.replace(/^www\./, "");
  } catch {
    return null;
  }
}
