import { ImageResponse } from "next/og";

// Per-job Open Graph image. Next.js auto-discovers this file at the
// /jobs/[id] route segment and wires the generated PNG into the
// og:image (and twitter:image) meta tags — so we get a branded,
// per-job share card in WhatsApp / LinkedIn / Twitter previews with
// no extra metadata plumbing in page.tsx.

export const runtime = "edge";

export const alt = "ZedApply — job posting";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface PageParams {
  params: { id: string };
}

interface JobLite {
  title: string;
  company: string | null;
  location: string | null;
}

async function fetchJobLite(id: string): Promise<JobLite | null> {
  try {
    const res = await fetch(`${API_BASE}/jobs/${encodeURIComponent(id)}`, {
      // Cache one hour — the OG card content (title/company/location)
      // changes far less often than the page itself, and image gen is
      // the slowest step in a share preview round-trip.
      next: { revalidate: 3600 },
    });
    if (!res.ok) return null;
    const j = (await res.json()) as JobLite;
    return j;
  } catch {
    return null;
  }
}

export default async function Image({ params }: PageParams) {
  const job = await fetchJobLite(params.id);

  // Defensive: bad ID, missing job, or backend down → fall back to a
  // generic branded card rather than crashing the share preview path.
  const title = job?.title || "Open role on ZedApply";
  const company = job?.company || "ZedApply";
  const location = job?.location || "Zambia";

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background:
            "linear-gradient(135deg, #052e1c 0%, #0a3f26 45%, #0f5132 80%, #944f1d 130%)",
          padding: 72,
          color: "#faf7f2",
          fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
        }}
      >
        {/* Top brand row */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 14,
            fontSize: 28,
            letterSpacing: "0.04em",
            textTransform: "uppercase",
            color: "rgba(255,255,255,0.78)",
          }}
        >
          <div
            style={{
              display: "flex",
              width: 14,
              height: 14,
              borderRadius: 999,
              background: "#2faa6e",
            }}
          />
          ZedApply
        </div>

        {/* Job title + company */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 20,
            maxWidth: 1000,
          }}
        >
          <div
            style={{
              fontSize: 72,
              fontWeight: 800,
              lineHeight: 1.05,
              letterSpacing: "-0.02em",
              color: "#ffffff",
            }}
          >
            {title}
          </div>
          <div
            style={{
              fontSize: 34,
              lineHeight: 1.25,
              color: "rgba(255,255,255,0.86)",
            }}
          >
            {company} &middot; {location}
          </div>
        </div>

        {/* Footer tagline */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            fontSize: 22,
            color: "rgba(255,255,255,0.7)",
          }}
        >
          <div style={{ display: "flex" }}>
            AI matching &middot; Tailored CVs &middot; WhatsApp delivery
          </div>
          <div style={{ display: "flex" }}>zedapply.com</div>
        </div>
      </div>
    ),
    { ...size },
  );
}
