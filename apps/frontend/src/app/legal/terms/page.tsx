import type { Metadata } from "next";
import { LegalMarkdown } from "../_components/LegalMarkdown";
import { fetchLegalDocFromDB } from "../_fetch";
import { TERMS_MARKDOWN, LAST_UPDATED, VERSION } from "./_content";

// task #62 — see /legal/privacy/page.tsx for the DB-fallback rationale.
export const revalidate = 300;

export const metadata: Metadata = {
  title: "Terms of Service",
  description:
    "The terms governing your use of ZedApply &mdash; eligibility, paid tiers, acceptable use, and dispute resolution under Zambian law.",
  openGraph: {
    title: "Terms of Service | ZedApply",
    description:
      "The terms governing your use of ZedApply &mdash; eligibility, paid tiers, acceptable use, and dispute resolution under Zambian law.",
    type: "article",
    modifiedTime: LAST_UPDATED,
  },
  other: {
    "article:modified_time": LAST_UPDATED,
    "document:version": VERSION,
  },
};

export default async function TermsPage() {
  const dbDoc = await fetchLegalDocFromDB("terms");
  const markdown = dbDoc?.content_md || TERMS_MARKDOWN;
  return <LegalMarkdown markdown={markdown} />;
}
