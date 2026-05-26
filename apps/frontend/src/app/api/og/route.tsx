import { ImageResponse } from "next/og";
import {
  buildJobOgImageElement,
  buildSiteOgImageElement,
  normalizeOgJobCard,
  OG_IMAGE_SIZE,
} from "@/lib/og-image-builder";

export const runtime = "edge";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function fetchJobLite(id: string) {
  try {
    const res = await fetch(`${API_BASE}/jobs/${encodeURIComponent(id)}`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return null;
    return (await res.json()) as {
      title?: string | null;
      company?: string | null;
      location?: string | null;
    };
  } catch {
    return null;
  }
}

/**
 * Dynamic OG image endpoint for share previews and external tools.
 * Usage: `/api/og?jobId=<uuid>` or `/api/og` for the site default card.
 */
export async function GET(request: Request) {
  const jobId = new URL(request.url).searchParams.get("jobId")?.trim();

  const element = jobId
    ? buildJobOgImageElement(normalizeOgJobCard(await fetchJobLite(jobId)))
    : buildSiteOgImageElement();

  return new ImageResponse(element, { ...OG_IMAGE_SIZE });
}
