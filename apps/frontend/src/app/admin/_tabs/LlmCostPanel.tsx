"use client";

import { useEffect, useState } from "react";
import { admin, type AdminLlmCostStats } from "@/lib/api";
import { notify } from "@/lib/toast";
import { Loader2 } from "lucide-react";

const FEATURE_LABELS: Record<string, string> = {
  matching: "Matching (embeddings)",
  cv_parsing: "CV parsing",
  bwana: "Bwana chat",
  interview_prep: "Interview prep",
  match_tailored_cv: "Match-tailored CV",
  aptitude: "Bwana Interview / aptitude",
  other: "Other",
};

function formatUsd(value: number): string {
  if (value >= 1) return `$${value.toFixed(2)}`;
  if (value >= 0.01) return `$${value.toFixed(4)}`;
  return `$${value.toFixed(6)}`;
}

export function LlmCostPanel({ token }: { token: string }) {
  const [stats, setStats] = useState<AdminLlmCostStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    admin
      .llmCostStats(token, { days: 7 })
      .then(setStats)
      .catch((e) =>
        notify.error(e instanceof Error ? e.message : "Failed to load LLM costs")
      )
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <div className="mt-6 rounded-lg border p-4 flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading AI cost (7-day)…
      </div>
    );
  }

  if (!stats) return null;

  return (
    <section className="mt-6 rounded-lg border p-4" aria-labelledby="llm-cost-heading">
      <h2 id="llm-cost-heading" className="text-lg font-semibold">
        AI inference cost (7 days)
      </h2>
      <p className="text-sm text-muted-foreground mt-1">
        Estimated USD from OpenRouter pricing constants + Gemini embed rates.
        {stats.total_requests > 0
          ? ` ${stats.total_requests.toLocaleString()} requests · ${formatUsd(stats.total_cost_usd)} total.`
          : " No logged requests yet — trigger Bwana chat or CV upload to populate."}
      </p>

      <div className="mt-4 grid sm:grid-cols-2 gap-4">
        <div>
          <h3 className="text-sm font-medium mb-2">By feature</h3>
          <ul className="text-sm space-y-1">
            {stats.by_feature.length === 0 ? (
              <li className="text-muted-foreground">—</li>
            ) : (
              stats.by_feature.map((row) => (
                <li key={row.feature} className="flex justify-between gap-2">
                  <span>{FEATURE_LABELS[row.feature] ?? row.feature}</span>
                  <span className="tabular-nums text-muted-foreground">
                    {formatUsd(row.cost_usd)} ({row.request_count})
                  </span>
                </li>
              ))
            )}
          </ul>
        </div>
        <div>
          <h3 className="text-sm font-medium mb-2">By model</h3>
          <ul className="text-sm space-y-1 max-h-48 overflow-y-auto">
            {stats.by_model.length === 0 ? (
              <li className="text-muted-foreground">—</li>
            ) : (
              stats.by_model.map((row) => (
                <li key={row.model} className="flex justify-between gap-2">
                  <span className="truncate" title={row.model}>
                    {row.model}
                  </span>
                  <span className="tabular-nums text-muted-foreground shrink-0">
                    {formatUsd(row.cost_usd)}
                  </span>
                </li>
              ))
            )}
          </ul>
        </div>
      </div>

      {stats.daily.length > 0 && (
        <div className="mt-4">
          <h3 className="text-sm font-medium mb-2">Daily spend</h3>
          <ul className="text-sm flex flex-wrap gap-2">
            {stats.daily.map((d) => (
              <li
                key={d.date}
                className="rounded-md bg-muted px-2 py-1 tabular-nums"
              >
                {d.date}: {formatUsd(d.cost_usd)}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
