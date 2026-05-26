"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import { coverLetter, ApiError } from "@/lib/api";
import { Icon } from "@/components/ui/Icon";
import { notify } from "@/lib/toast";
export function CoverLetterStep({
  jobId,
  jobTitle,
  company,
  token,
  onBack,
  onNext,
}: {
  jobId: string | null;
  jobTitle: string;
  company: string;
  token: string | null;
  onBack: () => void;
  onNext: () => void;
}) {
  const [letter, setLetter] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const generate = useCallback(async () => {
    if (!token) {
      notify.error("Sign in to generate a cover letter.");
      return;
    }
    if (!jobId) {
      notify.error("Open this builder from a job to generate a tailored cover letter.");
      return;
    }
    setLoading(true);
    setLetter(null);
    try {
      const res = await coverLetter.generate(token, jobId);
      setLetter(res.content);
      notify.custom.success("Cover letter ready");
    } catch (e: unknown) {
      if (e instanceof ApiError && e.status === 403) {
        notify.error("Cover letters require the Professional plan.");
      } else if (e instanceof ApiError) {
        notify.error(e.detail || "Could not generate cover letter.");
      } else {
        notify.error("Could not generate cover letter.");
      }
    } finally {
      setLoading(false);
    }
  }, [token, jobId]);

  const copy = useCallback(async () => {
    if (!letter) return;
    try {
      await navigator.clipboard.writeText(letter);
      notify.custom.success("Copied to clipboard");
    } catch {
      notify.error("Could not copy — select the text manually");
    }
  }, [letter]);

  return (
    <div className="card p-6 flex flex-col gap-4 max-w-xl">
      <div>
        <h2 className="text-lg font-semibold mb-1" style={{ color: "var(--ink)" }}>
          Cover letter
        </h2>
        <p className="text-sm" style={{ color: "var(--muted)" }}>
          {jobTitle}
          {company ? ` at ${company}` : ""}
        </p>
      </div>

      {!jobId && (
        <p className="text-sm rounded-lg border p-4" style={{ borderColor: "var(--line)", color: "var(--ink-2)" }}>
          Pick a job from{" "}
          <Link href="/matches" className="underline" style={{ color: "var(--green-700)" }}>
            your matches
          </Link>{" "}
          or a job detail page to generate a letter aligned to that role.
        </p>
      )}

      {!letter && !loading && (
        <button
          type="button"
          className="btn btn-primary w-full sm:w-auto"
          onClick={() => void generate()}
          disabled={!token || !jobId}
        >
          <Icon name="sparkle" size={14} /> Generate cover letter
        </button>
      )}

      {loading && (
        <p className="text-sm py-6 text-center" style={{ color: "var(--muted)" }}>
          Writing your cover letter…
        </p>
      )}

      {letter && (
        <div className="space-y-3">
          <div
            className="max-h-72 overflow-y-auto rounded-lg border p-4 text-sm leading-relaxed whitespace-pre-wrap"
            style={{ borderColor: "var(--line)", color: "var(--ink-2)" }}
          >
            {letter}
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn btn-outline btn-sm" onClick={() => void copy()}>
              Copy
            </button>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => void generate()}>
              Regenerate
            </button>
          </div>
        </div>
      )}

      <div className="flex justify-between pt-4 mt-2 border-t" style={{ borderColor: "var(--line)" }}>
        <button type="button" className="btn btn-ghost" onClick={onBack}>
          Back
        </button>
        <button type="button" className="btn btn-primary" onClick={onNext}>
          Continue to review
        </button>
      </div>
    </div>
  );
}
