import type { Metadata } from "next";

/** Canonical production origin for metadataBase, OG URLs, and sitemap. */
export const SITE_URL = "https://www.zedapply.com";

export const SITE_NAME = "ZedApply";

export const SITE_DEFAULT_TITLE =
  "ZedApply — AI Job Matching for Zambian Professionals";

export const SITE_DEFAULT_DESCRIPTION =
  "Find your next role in Zambia. AI-powered matching against your CV, WhatsApp digests, and zero spam. Free to start.";

export const SITE_OG_DESCRIPTION =
  "Built on the country's largest aggregated jobs feed. Tailored CVs and WhatsApp delivery.";

const SITE_KEYWORDS = [
  "jobs Zambia",
  "Lusaka jobs",
  "Zambian careers",
  "jobs in Zambia",
  "AI job matching",
  "CV matching",
] as const;

const googleVerification = process.env.NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION;

/** Default OG image (edge-generated). */
export const SITE_OG_IMAGE_PATH = "/api/og";

/** Site-wide defaults merged into the root layout `metadata` export. */
export const siteDefaultMetadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: SITE_DEFAULT_TITLE,
    template: `%s | ${SITE_NAME}`,
  },
  description: SITE_DEFAULT_DESCRIPTION,
  keywords: [...SITE_KEYWORDS],
  authors: [{ name: "Zed Apply", url: SITE_URL }],
  creator: "Vergeo Group",
  publisher: "Zed Apply",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: SITE_NAME,
  },
  openGraph: {
    type: "website",
    locale: "en_ZM",
    url: SITE_URL,
    siteName: SITE_NAME,
    title: SITE_DEFAULT_TITLE,
    description: SITE_OG_DESCRIPTION,
    images: [
      {
        url: SITE_OG_IMAGE_PATH,
        width: 1200,
        height: 630,
        alt: SITE_NAME,
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: SITE_DEFAULT_TITLE,
    description:
      "Find your next role in Zambia. AI matches against your CV.",
    images: [SITE_OG_IMAGE_PATH],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-snippet": -1,
      "max-image-preview": "large",
      "max-video-preview": -1,
    },
  },
  ...(googleVerification
    ? { verification: { google: googleVerification } }
    : {}),
  alternates: { canonical: SITE_URL },
  other: {
    "mobile-web-app-capable": "yes",
  },
  icons: {
    icon: [
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180" }],
  },
};

type PageMetaInput = {
  title: string;
  description: string;
};

/** Per-route metadata — `title` becomes "{title} | ZedApply" via the root template. */
export function pageMetadata({ title, description }: PageMetaInput): Metadata {
  const ogTitle = `${title} | ${SITE_NAME}`;
  return {
    title,
    description,
    openGraph: {
      title: ogTitle,
      description,
      type: "website",
      images: [{ url: SITE_OG_IMAGE_PATH, width: 1200, height: 630 }],
    },
    twitter: {
      card: "summary_large_image",
      title: ogTitle,
      description,
      images: [SITE_OG_IMAGE_PATH],
    },
  };
}

/** Absolute URL for per-job dynamic OG cards. */
export function jobOgImageUrl(jobId: string): string {
  return `${SITE_URL}/api/og?jobId=${encodeURIComponent(jobId)}`;
}
