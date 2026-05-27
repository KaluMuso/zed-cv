import type { Metadata } from "next";
import { pageMetadata } from "@/lib/site-metadata";
import { ApplicationsPageClient } from "./ApplicationsPageClient";

export const metadata: Metadata = pageMetadata({
  title: "Applications",
  description:
    "Track saved jobs on a Kanban board — Saved, Applied, Interviewing, Offered, and Closed.",
});

export default function ApplicationsPage() {
  return (
    <div
      className="min-h-[calc(100vh-8rem)] px-4 py-8 sm:px-6 sm:py-10"
      style={{ background: "var(--bg)" }}
    >
      <ApplicationsPageClient />
    </div>
  );
}
