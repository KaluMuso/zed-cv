import type { Metadata } from "next";
import { LegalMarkdown } from "../_components/LegalMarkdown";
import { fetchLegalDocFromDB } from "../_fetch";
import { PRIVACY_MARKDOWN, LAST_UPDATED, VERSION } from "./_content";

// task #62 — DB-fallback render. The admin WYSIWYG saves to legal_docs;
// the public GET endpoint returns 404 when no row exists, in which case
// we render the inline _content.ts constant. Revalidate every 5 min so
// an edit propagates promptly; the admin save handler also fires an
// explicit revalidatePath() so the change is visible within seconds.
export const revalidate = 300;

export const metadata: Metadata = {
  title: "Privacy Policy",
  description:
    "How ZedApply collects, uses and protects your personal data, in compliance with the Zambia Data Protection Act, 2021.",
  openGraph: {
    title: "Privacy Policy | ZedApply",
    description:
      "How ZedApply collects, uses and protects your personal data, in compliance with the Zambia Data Protection Act, 2021.",
    type: "article",
    modifiedTime: LAST_UPDATED,
  },
  other: {
    "article:modified_time": LAST_UPDATED,
    "document:version": VERSION,
  },
};

export default async function PrivacyPage() {
  const dbDoc = await fetchLegalDocFromDB("privacy");
  // Prefer DB content when it exists. content_md is the source of
  // truth for the LegalMarkdown renderer (consistent rehype-sanitize
  // path with the inline-content fallback).
  const markdown = dbDoc?.content_md || PRIVACY_MARKDOWN;
  return <LegalMarkdown markdown={markdown} />;
}
