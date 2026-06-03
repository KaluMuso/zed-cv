"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { employer, type CandidatePreview } from "@/lib/api";
import { EmptyState } from "@/components/shared/EmptyState";
import { Search, CreditCard } from "lucide-react";

export default function EmployerSearchPage() {
  const { token } = useAuth();
  const [skills, setSkills] = useState("");
  const [location, setLocation] = useState("");
  const [results, setResults] = useState<CandidatePreview[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  async function runSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setLoading(true);
    setError(null);
    setHasSearched(true);
    try {
      const data = await employer.search(token, {
        skills: skills.trim() || undefined,
        location: location.trim() || undefined,
        limit: 20,
      });
      setResults(data.results);
      setTotal(data.total);
    } catch (err) {
      setResults([]);
      setTotal(0);
      const message = err instanceof Error ? err.message : "Search failed";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  const needsSubscription =
    error?.toLowerCase().includes("subscription") ||
    error?.includes("402") ||
    error?.toLowerCase().includes("payment required");

  return (
    <div className="space-y-6">
      <form onSubmit={runSearch} className="flex flex-wrap gap-3 items-end">
        <label className="text-sm">
          Skills
          <input
            className="block mt-1 rounded-md border px-3 py-2 text-sm w-48"
            value={skills}
            onChange={(e) => setSkills(e.target.value)}
            placeholder="e.g. accountant, excel"
          />
        </label>
        <label className="text-sm">
          Location
          <input
            className="block mt-1 rounded-md border px-3 py-2 text-sm w-40"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="e.g. Lusaka"
          />
        </label>
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm font-medium disabled:opacity-50"
        >
          {loading ? "Searching…" : "Search"}
        </button>
      </form>

      {needsSubscription ? (
        <EmptyState
          icon={CreditCard}
          title="Subscription required"
          description="Activate Employer Lite or Pro to search the candidate pool."
          ctaText="View plans"
          ctaHref="/employer/billing"
        />
      ) : error && !needsSubscription ? (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}

      {!hasSearched && !loading ? (
        <EmptyState
          icon={Search}
          title="Search the candidate pool"
          description="Enter skills and location, then search. Profiles are anonymized until a candidate consents to share contact details."
          ctaText="Run search"
          onCtaClick={() => {
            const form = document.querySelector<HTMLFormElement>("form");
            form?.requestSubmit();
          }}
        />
      ) : null}

      {hasSearched && !loading && total !== null && total > 0 ? (
        <p className="text-sm text-muted-foreground">
          {total} candidate{total === 1 ? "" : "s"} (anonymized)
        </p>
      ) : null}

      {hasSearched && !loading && total === 0 && !needsSubscription && !error ? (
        <EmptyState
          icon={Search}
          title="No candidates match"
          description="Try broader skills, a different location, or fewer filters."
          secondaryCtaText="Clear filters"
          onSecondaryCtaClick={() => {
            setSkills("");
            setLocation("");
            setHasSearched(false);
            setResults([]);
            setTotal(null);
          }}
        />
      ) : null}

      {results.length > 0 ? (
        <ul className="space-y-3">
          {results.map((c) => (
            <li key={c.candidate_id} className="rounded-lg border p-4">
              <p className="font-medium">{c.headline ?? "Candidate"}</p>
              <p className="text-sm text-muted-foreground">
                {c.location ?? "—"} · {c.years_experience ?? "?"} yrs
              </p>
              {c.skills.length > 0 ? (
                <p className="text-xs mt-2 text-muted-foreground">
                  {c.skills.slice(0, 6).join(" · ")}
                </p>
              ) : null}
              {c.match_hint ? (
                <p className="text-xs mt-1 text-primary/80">{c.match_hint}</p>
              ) : null}
              <Link
                href={`/employer/candidates/${c.candidate_id}`}
                className="inline-block mt-3 text-sm text-primary font-medium"
              >
                View profile →
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
