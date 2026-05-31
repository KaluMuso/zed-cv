"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
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
  const router = useRouter();
  const { token, isAuthenticated, isLoading } = useAuth();
  const [overview, setOverview] = useState<InterviewPrepOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const [placeholder, setPlaceholder] = useState<string | null>(null);

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated || !token) {
      router.replace("/auth?next=/interview-prep");
      return;
    }
    apiFetch<InterviewPrepOverview>("/interview-prep", { token })
      .then(setOverview)
      .catch((err: Error) => {
        if (err.message.includes("403")) {
          notify.error("Bwana Interview requires the Super Standard plan.");
          router.replace("/pricing");
          return;
        }
        notify.error(err.message || "Could not load interview prep.");
      })
      .finally(() => setLoading(false));
  }, [isAuthenticated, isLoading, token, router]);

  const loadPlaceholder = async (sectionId: string) => {
    if (!token) return;
    setActiveSection(sectionId);
    setPlaceholder(null);
    try {
      const res = await apiFetch<{ content: string }>("/interview-prep", {
        method: "POST",
        token,
        body: JSON.stringify({ section_id: sectionId }),
      });
      setPlaceholder(res.content);
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Preview unavailable.");
    }
  };

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-16 text-center" style={{ color: "var(--muted)" }}>
        Loading Bwana Interview…
      </div>
    );
  }

  if (!overview) {
    return null;
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

      {placeholder && activeSection && (
        <div className="card p-6 mt-8">
          <pre
            className="text-sm whitespace-pre-wrap font-sans"
            style={{ color: "var(--ink-2)" }}
          >
            {placeholder}
          </pre>
        </div>
      )}

      <div className="mt-10 flex flex-wrap gap-3">
        <Link href="/matches" className="btn btn-ghost btn-sm">
          <Icon name="arrowLeft" size={14} /> Back to matches
        </Link>
        <Link href="/pricing" className="btn btn-accent btn-sm">
          View plans
        </Link>
      </div>
    </div>
  );
}
