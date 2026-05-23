"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { InterviewPrepGate } from "@/app/interview-prep/_components/InterviewPrepGate";
import { useAuth } from "@/lib/auth";
import { bwanaInterview, type InterviewHistoryResult } from "@/lib/api";

export default function InterviewHistoryPage() {
  return (
    <InterviewPrepGate nextPath="/interview-prep/history">
      <HistoryContent />
    </InterviewPrepGate>
  );
}

function HistoryContent() {
  const { token } = useAuth();
  const [data, setData] = useState<InterviewHistoryResult | null>(null);

  useEffect(() => {
    if (!token) return;
    bwanaInterview.history(token).then(setData).catch(() => setData({ mock_sessions: [], aptitude_scores: [] }));
  }, [token]);

  return (
    <div className="max-w-3xl mx-auto px-6 py-10 md:py-14">
      <h1 className="font-display text-4xl mb-2">Interview history</h1>
      <p className="text-sm mb-8" style={{ color: "var(--muted)" }}>
        Past mock interviews and aptitude test scores.
      </p>

      <section className="mb-10">
        <h2 className="font-display text-xl mb-4">Mock interviews</h2>
        {!data?.mock_sessions.length ? (
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            No sessions yet.{" "}
            <Link href="/interview-prep/mock" className="underline">
              Start a mock interview
            </Link>
          </p>
        ) : (
          <ul className="space-y-2">
            {data.mock_sessions.map((s) => (
              <li key={s.id} className="card p-4 flex justify-between items-center text-sm">
                <span>
                  <strong>{s.role_label}</strong>
                  {s.created_at && (
                    <span className="block text-xs mt-1" style={{ color: "var(--muted)" }}>
                      {new Date(s.created_at).toLocaleString()}
                    </span>
                  )}
                </span>
                <span>
                  {s.overall_score != null
                    ? `${Number(s.overall_score).toFixed(0)}/100`
                    : "In progress"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2 className="font-display text-xl mb-4">Aptitude tests</h2>
        {!data?.aptitude_scores.length ? (
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            No aptitude scores yet.{" "}
            <Link href="/interview-prep/aptitude" className="underline">
              Take a test
            </Link>
          </p>
        ) : (
          <ul className="space-y-2">
            {data.aptitude_scores.map((a) => (
              <li key={a.id} className="card p-4 flex justify-between items-center text-sm capitalize">
                <span>
                  <strong>{a.pack}</strong>
                  {a.completed_at && (
                    <span className="block text-xs mt-1" style={{ color: "var(--muted)" }}>
                      {new Date(a.completed_at).toLocaleString()}
                    </span>
                  )}
                </span>
                <span>
                  {a.score}% · {a.percentile != null ? `${a.percentile}th pct` : "—"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <Link href="/interview-prep" className="inline-block mt-10 text-sm" style={{ color: "var(--muted)" }}>
        ← Hub
      </Link>
    </div>
  );
}
