import type { Metadata } from "next";
import { Suspense } from "react";
import { pageMetadata } from "@/lib/site-metadata";
import JobsPageClient from "./JobsPageClient";

export const metadata: Metadata = pageMetadata({
  title: "Jobs",
  description:
    "Browse open roles across Zambia — filter by location, salary, and employment type on ZedApply.",
});

export default function JobsPage() {
  return (
    <Suspense fallback={null}>
      <JobsPageClient />
    </Suspense>
  );
}
