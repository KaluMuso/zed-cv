"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { AdminTabLoader } from "../_components/AdminTabLoader";

const JobsTab = dynamic(
  () => import("../_tabs/JobsTab").then((m) => ({ default: m.JobsTab })),
  { loading: () => <AdminTabLoader /> }
);

export default function AdminJobsPage() {
  const { token } = useAuth();
  if (!token) return null;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2 text-sm">

        <Link
          href="/admin/jobs/review"
          className="rounded-md border border-border px-3 py-1.5 hover:bg-muted"
        >
          Review queue →
        </Link>
      </div>
      <JobsTab token={token} />
    </div>
  );
}
