import type { Metadata } from "next";
import { pageMetadata } from "@/lib/site-metadata";
import { DashboardPageClient } from "./DashboardPageClient";

export const metadata: Metadata = pageMetadata({
  title: "Dashboard",
  description: "Your ZedApply job matching overview — matches, applications, and activity.",
});

export default function DashboardPage() {
  return (
    <div
      className="min-h-[calc(100vh-8rem)] px-4 py-8 sm:px-6 sm:py-10"
      style={{ background: "var(--bg)" }}
    >
      <DashboardPageClient />
    </div>
  );
}
