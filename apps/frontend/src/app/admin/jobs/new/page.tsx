"use client";

import Link from "next/link";

import { useAuth } from "@/lib/auth";
import { AdminJobManualForm } from "@/features/admin/jobs/AdminJobManualForm";

export default function NewAdminJobPage() {
  const { token } = useAuth();

  return (
    <div className="flex flex-col gap-6">
      <nav aria-label="Breadcrumb" className="text-sm text-muted-foreground">
        <ol className="flex flex-wrap items-center gap-1">
          <li>
            <Link href="/admin/jobs" className="hover:text-foreground hover:underline">
              Admin
            </Link>
          </li>
          <li aria-hidden="true">/</li>
          <li>
            <Link href="/admin/jobs" className="hover:text-foreground hover:underline">
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
        <h1 className="text-2xl font-bold">New job</h1>
        <p className="text-sm text-muted-foreground">
          Manual entry with markdown description preview. Jobs go through the same
          quality pipeline as scraper ingest.
        </p>
      </header>

      {token ? (
        <AdminJobManualForm token={token} />
      ) : (
        <p className="text-sm text-muted-foreground">Sign in as admin to create jobs.</p>
      )}
    </div>
  );
}
