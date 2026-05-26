import type { ReactElement } from "react";

/** Open Graph / Twitter card dimensions (1.91:1). */
export const OG_IMAGE_SIZE = { width: 1200, height: 630 } as const;

export type OgJobCardInput = {
  title: string;
  company: string;
  location: string;
};

const DEFAULT_JOB_CARD: OgJobCardInput = {
  title: "Open role on ZedApply",
  company: "ZedApply",
  location: "Zambia",
};

/** Normalise API/nullable job fields into OG card copy. */
export function normalizeOgJobCard(job: {
  title?: string | null;
  company?: string | null;
  location?: string | null;
} | null | undefined): OgJobCardInput {
  if (!job?.title?.trim()) {
    return DEFAULT_JOB_CARD;
  }
  return {
    title: job.title.trim(),
    company: job.company?.trim() || "ZedApply",
    location: job.location?.trim() || "Zambia",
  };
}

/**
 * JSX tree for `next/og` ImageResponse — shared by file-based
 * `opengraph-image.tsx` and `/api/og?jobId=…`.
 */
export function buildJobOgImageElement(card: OgJobCardInput): ReactElement {
  const { title, company, location } = card;

  return (
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
          {company} · {location}
        </div>
      </div>

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
          AI matching · Tailored CVs · WhatsApp delivery
        </div>
        <div style={{ display: "flex" }}>zedapply.com</div>
      </div>
    </div>
  );
}

/** Site-wide default OG card (homepage, static pages). */
export function buildSiteOgImageElement(): ReactElement {
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-start",
        justifyContent: "center",
        background:
          "linear-gradient(135deg, #052e16 0%, #166534 45%, #15803d 100%)",
        padding: 64,
        fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 20,
          maxWidth: 900,
        }}
      >
        <div
          style={{
            fontSize: 72,
            fontWeight: 800,
            color: "white",
            lineHeight: 1.1,
          }}
        >
          ZedApply
        </div>
        <div
          style={{
            fontSize: 36,
            color: "rgba(255,255,255,0.92)",
            lineHeight: 1.3,
          }}
        >
          AI job matching in Zambia — results on WhatsApp
        </div>
      </div>
    </div>
  );
}
