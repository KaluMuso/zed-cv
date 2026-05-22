import type { Metadata } from "next";

/** Canonical production origin for metadataBase, OG URLs, and sitemap. */
export const SITE_URL = "https://www.zedapply.com";

export const SITE_NAME = "ZedApply";

/** Root layout default — homepage and any route without a page-level title. */
export const SITE_DEFAULT_TITLE = "ZedApply - Zambian AI Job Matching";

export const SITE_DEFAULT_DESCRIPTION =
  "Find jobs that match your skills. AI-powered matching, CV generation, and WhatsApp delivery for Zambian professionals.";

export const SITE_OG_DESCRIPTION =
  "Upload your CV and let AI score you against every open role in Zambia. Get matches on WhatsApp.";

const SITE_KEYWORDS = [
  "Zambia jobs",
  "CV matching",
  "AI job matching",
  "Lusaka jobs",
  "Zambian careers",
  "CV builder Zambia",
  "job search Zambia",
] as const;

/** Site-wide defaults merged into the root layout `metadata` export. */
export const siteDefaultMetadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: SITE_DEFAULT_TITLE,
    template: `%s — ${SITE_NAME}`,
  },
  description: SITE_DEFAULT_DESCRIPTION,
  keywords: [...SITE_KEYWORDS],
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
      { url: "/og-image.png", width: 1200, height: 630, alt: SITE_NAME },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: SITE_DEFAULT_TITLE,
    description: SITE_OG_DESCRIPTION,
  },
  robots: { index: true, follow: true },
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

/** Per-route metadata — `title` becomes "{title} — ZedApply" via the root template. */
export function pageMetadata({ title, description }: PageMetaInput): Metadata {
  const ogTitle = `${title} — ${SITE_NAME}`;
  return {
    title,
    description,
    openGraph: {
      title: ogTitle,
      description,
      type: "website",
    },
    twitter: {
      title: ogTitle,
      description,
    },
  };
}
