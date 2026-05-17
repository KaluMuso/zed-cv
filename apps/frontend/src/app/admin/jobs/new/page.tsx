"use client";

import Link from "next/link";

import { JobCreateWizard } from "@/features/admin/jobs/JobCreateWizard";

// Admin guard is applied by apps/frontend/src/app/admin/layout.tsx, so
// non-admins are redirected before this page renders. No per-page check
// needed — matches every other /admin/* route.

export default function NewAdminJobPage() {
  return (
    <div className="flex flex-col gap-6">
      <nav aria-label="Breadcrumb" className="text-sm text-muted-foreground">
        <ol className="flex flex-wrap items-center gap-1">
          <li>
            <Link
              href="/admin"
              className="hover:text-foreground hover:underline"
            >
              Admin
            </Link>
          </li>
          <li aria-hidden="true">/</li>
          <li>
            <Link
              href="/admin"
              className="hover:text-foreground hover:underline"
            >
              Jobs
            </Link>
          </li>
          <li aria-hidden="true">/</li>
          <li aria-current="page" className="text-foreground">
            New
          </li>
        </ol>
      </nav>

      <header>
        <h1 className="text-2xl font-bold">Create a job</h1>
        <p className="text-sm text-muted-foreground">
          Multi-step wizard. The first two steps capture basics and
          compensation; the rest land in the next release.
        </p>
      </header>

      <JobCreateWizard />
    </div>
  );
}
