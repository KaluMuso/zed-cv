import type { Metadata } from "next";
import { LegalMarkdown } from "../_components/LegalMarkdown";
import { fetchLegalDocFromDB } from "../_fetch";
import { REFUND_MARKDOWN, LAST_UPDATED, VERSION } from "./_content";

export const revalidate = 300;

export const metadata: Metadata = {
  title: "Refund Policy",
  description:
    "ZedApply refund rules — 7-day money-back guarantee, Lenco and DPO Pay billing, and how to request a refund.",
  openGraph: {
    title: "Refund Policy | ZedApply",
    description:
      "ZedApply refund rules — 7-day money-back guarantee, Lenco and DPO Pay billing, and how to request a refund.",
    type: "article",
    modifiedTime: LAST_UPDATED,
  },
  other: {
    "article:modified_time": LAST_UPDATED,
    "document:version": VERSION,
  },
};

export default async function RefundPage() {
  const dbDoc = await fetchLegalDocFromDB("refund");
  const markdown = dbDoc?.content_md || REFUND_MARKDOWN;
  return <LegalMarkdown markdown={markdown} />;
}
