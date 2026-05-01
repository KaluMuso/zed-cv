"use client";

import { useState } from "react";
import { cv as cvApi, type CVAnalysis, type UserProfile } from "@/lib/api";
import { ScoreRing } from "@/components/ui/ScoreRing";
import { Icon } from "@/components/ui/Icon";

export function AnalysisTab({
  token,
  profileData,
}: {
  token: string;
  profileData: UserProfile;
}) {
  const [data, setData] = useState<CVAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onRun = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await cvApi.analyze(token);
      setData(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  if (!profileData.cv_uploaded) {
    return (
      <div className="card p-6">
        <div className="eyebrow mb-2">CV analysis</div>
        <p className="text-sm" style={{ color: "var(--muted)" }}>
          Upload your CV first — analysis runs against the text we&apos;ve parsed.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="card p-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <div className="eyebrow mb-1">CV analysis</div>
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              AI scoring on overall quality, skills, format, and impact.
            </p>
          </div>
          <button onClick={onRun} disabled={loading} className="btn btn-primary btn-sm">
            {loading ? (
              <span className="spinner" />
            ) : data ? (
              <>
                Re-run <Icon name="arrowRight" size={14} />
              </>
            ) : (
              <>
                Run analysis <Icon name="arrowRight" size={14} />
              </>
            )}
          </button>
        </div>
        {error && (
          <p className="mt-3 text-sm" style={{ color: "var(--danger)" }}>
            {error}
          </p>
        )}
        {data?.cached && (
          <p className="mt-3 text-xs" style={{ color: "var(--muted)" }}>
            Cached result — re-upload your CV to refresh.
          </p>
        )}
      </div>

      {data && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <ScoreCard label="Overall" score={data.overall} tone="copper" />
            <ScoreCard label="Skills" score={data.skills} tone="green" />
            <ScoreCard label="Format" score={data.format} tone="green" />
            <ScoreCard label="Impact" score={data.impact} tone="copper" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="card p-6">
              <div className="eyebrow mb-3" style={{ color: "var(--success)" }}>
                Strengths
              </div>
              {data.strengths.length === 0 ? (
                <p className="text-sm" style={{ color: "var(--muted)" }}>
                  None detected.
                </p>
              ) : (
                <ul className="space-y-2.5">
                  {data.strengths.map((s, i) => (
                    <li key={i} className="text-sm flex gap-2">
                      <Icon name="check" size={14} className="mt-0.5 shrink-0" />
                      <span>{s}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="card p-6">
              <div className="eyebrow mb-3" style={{ color: "var(--copper-500)" }}>
                Improvements
              </div>
              {data.improvements.length === 0 ? (
                <p className="text-sm" style={{ color: "var(--muted)" }}>
                  None detected.
                </p>
              ) : (
                <ul className="space-y-2.5">
                  {data.improvements.map((s, i) => (
                    <li key={i} className="text-sm flex gap-2">
                      <Icon name="arrowRight" size={14} className="mt-0.5 shrink-0" />
                      <span>{s}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function ScoreCard({
  label,
  score,
  tone,
}: {
  label: string;
  score: number;
  tone: "green" | "copper";
}) {
  return (
    <div className="card p-4 flex flex-col items-center gap-2">
      <ScoreRing score={score} size={84} stroke={6} />
      <div className="text-xs" style={{ color: "var(--muted)" }}>
        {label}
      </div>
      <div
        className="font-display text-base"
        style={{ color: tone === "green" ? "var(--green-700)" : "var(--copper-500)" }}
      >
        {score}/100
      </div>
    </div>
  );
}
