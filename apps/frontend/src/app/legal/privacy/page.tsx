import type { Metadata } from "next";
import { LegalMarkdown } from "../_components/LegalMarkdown";
import { PRIVACY_MARKDOWN, LAST_UPDATED, VERSION } from "./_content";

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

export default function PrivacyPage() {
  return <LegalMarkdown markdown={PRIVACY_MARKDOWN} />;
}
