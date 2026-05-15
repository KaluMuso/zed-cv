import type { Metadata } from "next";
import { LegalMarkdown } from "../_components/LegalMarkdown";
import { COOKIES_MARKDOWN, LAST_UPDATED, VERSION } from "./_content";

export const metadata: Metadata = {
  title: "Cookie Policy",
  description:
    "Which cookies ZedApply uses, what they do, and how to control them.",
  openGraph: {
    title: "Cookie Policy | ZedApply",
    description:
      "Which cookies ZedApply uses, what they do, and how to control them.",
    type: "article",
    modifiedTime: LAST_UPDATED,
  },
  other: {
    "article:modified_time": LAST_UPDATED,
    "document:version": VERSION,
  },
};

export default function CookiesPage() {
  return <LegalMarkdown markdown={COOKIES_MARKDOWN} />;
}
