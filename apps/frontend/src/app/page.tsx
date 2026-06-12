import type { Metadata } from "next";
import { HomeStructuredData } from "@/components/marketing/HomeStructuredData";
import {
  SITE_DEFAULT_DESCRIPTION,
  SITE_DEFAULT_TITLE,
  SITE_OG_DESCRIPTION,
  SITE_OG_IMAGE_PATH,
  SITE_URL,
} from "@/lib/site-metadata";
import HomePageClient from "./HomePageClient";

export const metadata: Metadata = {
  title: { absolute: SITE_DEFAULT_TITLE },
  description: SITE_DEFAULT_DESCRIPTION,
  alternates: { canonical: SITE_URL },
  openGraph: {
    title: SITE_DEFAULT_TITLE,
    description: SITE_OG_DESCRIPTION,
    url: SITE_URL,
    type: "website",
    images: [{ url: SITE_OG_IMAGE_PATH, width: 1200, height: 630, alt: SITE_DEFAULT_TITLE }],
  },
  twitter: {
    card: "summary_large_image",
    title: SITE_DEFAULT_TITLE,
    description: SITE_OG_DESCRIPTION,
    images: [SITE_OG_IMAGE_PATH],
  },
};

import { Suspense } from "react";

async function DynamicHomeContent() {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  
  let faqsData = [];
  let tiersData = [];
  
  try {
    const [faqsRes, tiersRes] = await Promise.all([
      fetch(`${API_URL}/faqs`, { next: { revalidate: 300 } }),
      fetch(`${API_URL}/tiers`, { next: { revalidate: 300 } }),
    ]);
    
    if (faqsRes.ok) {
      const data = await faqsRes.json();
      faqsData = data.faqs || [];
    }
    
    if (tiersRes.ok) {
      const data = await tiersRes.json();
      tiersData = data.tiers || [];
    }
  } catch (error) {
    console.error("Failed to fetch dynamic content for home page:", error);
  }

  return <HomePageClient initialFaqs={faqsData} initialTiers={tiersData} />;
}

export default function HomePage() {
  return (
    <>
      <HomeStructuredData />
      <Suspense fallback={<div className="min-h-screen flex items-center justify-center">Loading...</div>}>
        <DynamicHomeContent />
      </Suspense>
    </>
  );
}
