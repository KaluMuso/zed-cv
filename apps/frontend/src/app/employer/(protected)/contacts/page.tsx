"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { employer, type ContactRequestRow, type ContactStatusSummary } from "@/lib/api";
import { EmptyState } from "@/components/shared/EmptyState";
import { EmployerContactStatusBadge } from "../../_components/EmployerContactStatusBadge";
import { Inbox } from "lucide-react";

export default function EmployerContactsPage() {
  const { token } = useAuth();
  const [rows, setRows] = useState<ContactRequestRow[]>([]);
  const [summary, setSummary] = useState<ContactStatusSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setLoading(true);
    void employer
      .contacts(token)
      .then((d) => {
        if (cancelled) return;
        setRows(d.contacts);
        setSummary(d.summary);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (loading) {
    return (
      <div className="space-y-3 animate-pulse">
        <div className="h-4 w-full max-w-md rounded bg-muted" />
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-24 rounded-lg border bg-muted/30" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Phone and email appear only when the candidate consents (YES). Declined or expired
        requests hide PII.
      </p>

      {summary && summary.total > 0 ? (
        <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
          <span>{summary.pending} pending</span>
          <span aria-hidden>·</span>
          <span>{summary.consented} consented</span>
          <span aria-hidden>·</span>
          <span>
            {summary.declined + summary.expired} declined or expired
          </span>
        </div>
      ) : null}

      {rows.length === 0 ? (
        <EmptyState
          icon={Inbox}
          title="No contact requests yet"
          description="When you request contact from a candidate profile, the request appears here with status updates."
          ctaText="Search candidates"
          ctaHref="/employer/search"
        />
      ) : (
        <ul className="space-y-3">
          {rows.map((r) => (
            <li key={r.id} className="rounded-lg border p-4 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <EmployerContactStatusBadge status={r.status} />
                <span className="text-muted-foreground capitalize">{r.channel}</span>
              </div>
              <p className="mt-2 text-muted-foreground line-clamp-2">{r.message_text}</p>
              {r.status === "consented" ? (
                <p className="mt-2 font-medium">
                  {r.candidate_name ?? "Candidate"} — {r.candidate_phone ?? "—"} ·{" "}
                  {r.candidate_email ?? "—"}
                </p>
              ) : r.status === "pending" ? (
                <p className="mt-2 text-xs text-muted-foreground">
                  Waiting for candidate reply (7-day window).
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      )}

      {rows.length > 0 ? (
        <p className="text-xs text-muted-foreground">
          <Link href="/employer/search" className="text-primary underline">
            Find more candidates
          </Link>
        </p>
      ) : null}
    </div>
  );
}
