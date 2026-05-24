/**
 * Server-side fetch for legal-docs rows from the public backend
 * endpoint (task #62). Each /legal/<slug>/page.tsx calls this in its
 * render function and falls back to the inline _content.ts constant
 * if the row doesn't exist or the call fails.
 *
 * Deliberately defensive: a backend outage MUST NOT 500 a legal page.
 * Returns null on any non-success and lets the page render the inline
 * default — that's the safe behaviour for content these pages are
 * legally required to display.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface LegalDocFromDB {
  slug: string;
  version: string;
  content_md: string;
  content_html: string;
  last_modified_by: string | null;
  last_modified_at: string | null;
}

export async function fetchLegalDocFromDB(
  slug: "privacy" | "terms" | "cookies" | "refund",
): Promise<LegalDocFromDB | null> {
  try {
    const res = await fetch(`${API_BASE}/legal/${slug}`, {
      // The page itself owns the cache window via `export const
      // revalidate = 300`; this fetch piggy-backs on that, so we
      // don't double-cache.
      cache: "no-store",
    });
    if (res.status === 404) {
      // No DB row yet — page should render the inline fallback.
      return null;
    }
    if (!res.ok) {
      return null;
    }
    return (await res.json()) as LegalDocFromDB;
  } catch {
    return null;
  }
}
