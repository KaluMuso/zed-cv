import type { Metadata } from "next";
import { LegalMarkdown } from "../_components/LegalMarkdown";
import { TERMS_MARKDOWN, LAST_UPDATED, VERSION } from "./_content";

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

export default function TermsPage() {
  return <LegalMarkdown markdown={TERMS_MARKDOWN} />;
}
