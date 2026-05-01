"use client";

import { useState } from "react";
import { cv as cvApi, type CVGenerateResult, type UserProfile } from "@/lib/api";
import { Icon } from "@/components/ui/Icon";

export function GeneratorTab({
  token,
  profileData,
}: {
  token: string;
  profileData: UserProfile;
}) {
  const [jobTitle, setJobTitle] = useState("");
  const [company, setCompany] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [result, setResult] = useState<CVGenerateResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const tier = profileData.subscription_tier;
  const tierAllowed = tier === "starter" || tier === "professional";

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!jobTitle.trim()) {
      setError("Job title is required.");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    setCopied(false);
    try {
      const r = await cvApi.generate(token, {
        job_title: jobTitle.trim(),
        company: company.trim() || undefined,
        job_description: jobDescription.trim() || undefined,
      });
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setLoading(false);
    }
  };

  const onCopy = async () => {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Could not copy to clipboard.");
    }
  };

  if (!profileData.cv_uploaded) {
    return (
      <div className="card p-6">
        <div className="eyebrow mb-2">CV generator</div>
        <p className="text-sm" style={{ color: "var(--muted)" }}>
          Upload your CV first — the generator tailors your existing CV to a target role.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="card p-6">
        <div className="eyebrow mb-1">Tailored CV generator</div>
        <p className="text-sm mb-5" style={{ color: "var(--muted)" }}>
          Rewrite your CV for a specific role.{" "}
          {tierAllowed
            ? "Available on your current plan."
            : "Requires the Starter or Professional plan."}
        </p>

        <form onSubmit={onSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium block mb-1" style={{ color: "var(--ink-2)" }}>
                Job title <span style={{ color: "var(--danger)" }}>*</span>
              </label>
              <input
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
                placeholder="e.g. Senior Accountant"
                className="w-full h-10 px-3 rounded-md text-sm"
                style={{
                  border: "1px solid var(--line-2)",
                  background: "var(--surface)",
                  color: "var(--ink)",
                }}
                required
              />
            </div>
            <div>
              <label className="text-xs font-medium block mb-1" style={{ color: "var(--ink-2)" }}>
                Company
              </label>
              <input
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="e.g. ZANACO"
                className="w-full h-10 px-3 rounded-md text-sm"
                style={{
                  border: "1px solid var(--line-2)",
                  background: "var(--surface)",
                  color: "var(--ink)",
                }}
              />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium block mb-1" style={{ color: "var(--ink-2)" }}>
              Job description (optional)
            </label>
            <textarea
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              placeholder="Paste the JD if you have it. Improves tailoring."
              rows={5}
              className="w-full p-3 rounded-md text-sm"
              style={{
                border: "1px solid var(--line-2)",
                background: "var(--surface)",
                color: "var(--ink)",
              }}
            />
          </div>
          <div className="flex justify-end">
            <button type="submit" disabled={loading} className="btn btn-primary btn-sm">
              {loading ? (
                <span className="spinner" />
              ) : (
                <>
                  Generate <Icon name="arrowRight" size={14} />
                </>
              )}
            </button>
          </div>
          {error && (
            <p className="text-sm" style={{ color: "var(--danger)" }}>
              {error}
            </p>
          )}
        </form>
      </div>

      {result && (
        <div className="card p-6">
          <div className="flex items-center justify-between gap-4 mb-4">
            <div>
              <div className="eyebrow">Generated CV</div>
              <p className="text-xs" style={{ color: "var(--muted)" }}>
                {result.word_count} words · {result.job_title}
                {result.company && ` · ${result.company}`}
              </p>
            </div>
            <button onClick={onCopy} className="btn btn-ghost btn-sm">
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>
          <pre
            className="text-sm whitespace-pre-wrap leading-relaxed p-4 rounded-md"
            style={{
              background: "var(--bg-2)",
              border: "1px solid var(--line)",
              color: "var(--ink)",
              fontFamily: "inherit",
            }}
          >
            {result.content}
          </pre>
        </div>
      )}
    </div>
  );
}
