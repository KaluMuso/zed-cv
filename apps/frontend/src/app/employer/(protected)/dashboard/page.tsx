"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import {
  employer,
  type ContactStatusSummary,
  type EmployerMe,
  type EmployerSubscription,
} from "@/lib/api";
import { EmployerQuotaBar } from "../../_components/EmployerQuotaBar";
import { EmptyState } from "@/components/shared/EmptyState";
import { Users } from "lucide-react";

export default function EmployerDashboardPage() {
  const { token } = useAuth();
  const [me, setMe] = useState<EmployerMe | null>(null);
  const [sub, setSub] = useState<EmployerSubscription | null>(null);
  const [summary, setSummary] = useState<ContactStatusSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setLoading(true);
    void Promise.all([
      employer.me(token),
      employer.subscription(token),
      employer.contacts(token).catch(() => null),
    ])
      .then(([m, s, contacts]) => {
        if (cancelled) return;
        setMe(m);
        setSub(s);
        setSummary(contacts?.summary ?? null);
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
      <div className="space-y-4 animate-pulse">
        <div className="h-5 w-48 rounded bg-muted" />
        <div className="h-24 rounded-lg border bg-muted/40" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-16 rounded-lg border bg-muted/30" />
          ))}
        </div>
      </div>
    );
  }

  const statCards = [
    { label: "Pending", value: summary?.pending ?? 0, href: "/employer/contacts" },
    { label: "Consented", value: summary?.consented ?? 0, href: "/employer/contacts" },
    {
      label: "Declined / expired",
      value: (summary?.declined ?? 0) + (summary?.expired ?? 0),
      href: "/employer/contacts",
    },
    { label: "Total requests", value: summary?.total ?? 0, href: "/employer/contacts" },
  ];

  return (
    <div className="space-y-6">
      <p className="text-sm">
        Welcome, <strong>{me?.employer.company_name ?? "…"}</strong>
        {me?.my_role ? (
          <span className="text-muted-foreground"> · {me.my_role}</span>
        ) : null}
      </p>

      <div className="rounded-lg border p-4 space-y-4">
        <h2 className="font-medium">Subscription</h2>
        {sub?.active ? (
          <>
            <p className="text-sm text-muted-foreground">
              {sub.tier === "pro" ? "Employer Pro" : "Employer Lite"}
              {sub.current_period_end
                ? ` · renews ${new Date(sub.current_period_end).toLocaleDateString()}`
                : null}
            </p>
            <EmployerQuotaBar used={sub.contacts_used} limit={sub.contacts_limit} />
          </>
        ) : (
          <p className="text-sm text-muted-foreground">
            No active plan — subscribe to search and contact candidates.{" "}
            <Link href="/employer/billing" className="text-primary underline">
              View plans
            </Link>
          </p>
        )}
      </div>

      {summary && summary.total > 0 ? (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {statCards.map((card) => (
            <Link
              key={card.label}
              href={card.href}
              className="rounded-lg border p-3 hover:bg-muted/30 transition-colors"
            >
              <p className="text-2xl font-semibold tabular-nums">{card.value}</p>
              <p className="text-xs text-muted-foreground mt-1">{card.label}</p>
            </Link>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={Users}
          title="No contact requests yet"
          description="Search anonymized candidates and send a consent request. Details appear here after they reply YES on WhatsApp or email."
          ctaText="Search candidates"
          ctaHref="/employer/search"
        />
      )}

      <div className="flex flex-wrap gap-3">
        <Link
          href="/employer/search"
          className="rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm font-medium"
        >
          Search candidates
        </Link>
        <Link href="/employer/contacts" className="rounded-lg border px-4 py-2 text-sm font-medium">
          Contact log
        </Link>
      </div>
    </div>
  );
}
