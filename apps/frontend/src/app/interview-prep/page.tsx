"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { InterviewPrepGate } from "@/app/interview-prep/_components/InterviewPrepGate";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { Icon } from "@/components/ui/Icon";
import { Button } from "@/components/ui/button";
import { notify } from "@/lib/toast";

interface InterviewPrepSection {
  id: string;
  title: string;
  description: string;
  status: string;
}

interface InterviewPrepOverview {
  product_name: string;
  sections: InterviewPrepSection[];
  message: string;
}

export default function InterviewPrepPage() {
  return (
    <InterviewPrepGate nextPath="/interview-prep">
      <InterviewPrepHub />
    </InterviewPrepGate>
  );
}

function InterviewPrepHub() {
  const { token } = useAuth();
  const [overview, setOverview] = useState<InterviewPrepOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const loadOverview = useCallback(() => {
    if (!token) return;
    setLoading(true);
    setLoadError(null);
    apiFetch<InterviewPrepOverview>("/interview-prep", { token })
      .then(setOverview)
      .catch((err: Error) => {
        setOverview(null);
        const message = err.message || "Could not load interview prep.";
        setLoadError(message);
        notify.error(message);
      })
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => {
    loadOverview();
  }, [loadOverview]);

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-16 text-center" style={{ color: "var(--muted)" }}>
        Loading Bwana Interview…
      </div>
    );
  }

  if (loadError || !overview) {
    return (
      <div className="max-w-lg mx-auto px-6 py-16 text-center">
        <h1 className="font-display text-3xl mb-3">Could not load Bwana Interview</h1>
        <p className="text-sm mb-6" style={{ color: "var(--muted)" }}>
          {loadError ?? "Something went wrong. Check your connection and try again."}
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          <Button type="button" variant="primary" onClick={() => loadOverview()}>
            Try again
          </Button>
          <Link href="/matches">
            <Button type="button" variant="outline">
              Back to matches
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-6 py-12 md:py-16">
      <div className="mb-10">
        <div className="eyebrow mb-2">Super Standard</div>
        <h1 className="font-display text-4xl mb-2" style={{ letterSpacing: "-0.02em" }}>
          {overview.product_name}
        </h1>
        <p className="text-sm" style={{ color: "var(--muted)" }}>
          Mock interviews and aptitude tests are live. More modules roll out in v2.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 mb-10">
        <Link href="/interview-prep/mock" className="card p-6 block hover:border-[var(--green-500)] transition-colors">
          <h2 className="font-display text-xl mb-2">Mock interview</h2>
          <p className="text-sm" style={{ color: "var(--ink-2)" }}>
            Seven STAR questions with live feedback from Bwana.
          </p>
        </Link>
        <Link href="/interview-prep/aptitude" className="card p-6 block hover:border-[var(--green-500)] transition-colors">
          <h2 className="font-display text-xl mb-2">Aptitude tests</h2>
          <p className="text-sm" style={{ color: "var(--ink-2)" }}>
            Numerical, verbal, and abstract reasoning packs (20 questions each).
          </p>
        </Link>
        <Link href="/interview-prep/history" className="card p-6 block hover:border-[var(--green-500)] transition-colors md:col-span-2">
          <h2 className="font-display text-xl mb-2">History</h2>
          <p className="text-sm" style={{ color: "var(--ink-2)" }}>
            Review past mock sessions and aptitude percentiles.
          </p>
        </Link>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {overview.sections.map((section) => (
          <div key={section.id} className="card p-6 opacity-80">
            <h2 className="font-display text-xl mb-2">{section.title}</h2>
            <p className="text-sm mb-4" style={{ color: "var(--ink-2)" }}>
              {section.description}
            </p>
            <span className="text-xs uppercase tracking-wide" style={{ color: "var(--muted)" }}>
              Coming in v2
            </span>
          </div>
        ))}
      </div>

      <div className="mt-10 flex flex-wrap gap-3">
        <Link href="/matches" className="btn btn-ghost btn-sm">
          <Icon name="arrowLeft" size={14} /> Back to matches
        </Link>
        <Link href="/pricing#super_standard" className="btn btn-accent btn-sm">
          View plans
        </Link>
      </div>
    </div>
  );
}
