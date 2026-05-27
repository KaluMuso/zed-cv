"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";
import { cv as cvApi, ApiError, type MatchTailorCvResult } from "@/lib/api";
import { trackCvTailoredForMatch } from "@/lib/trackCvTailoredForMatch";
import { Icon } from "@/components/ui/Icon";
import { ModalPortal } from "@/components/shared/ModalPortal";

function downloadMarkdown(filename: string, markdown: string): void {
  const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function TailoredCvModal({
  open,
  onClose,
  token,
  matchId,
  jobTitle,
  company,
}: {
  open: boolean;
  onClose: () => void;
  token: string;
  matchId: string;
  jobTitle: string;
  company: string | null;
}) {
  const [data, setData] = useState<MatchTailorCvResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tierLocked, setTierLocked] = useState(false);

  useEffect(() => {
    if (!open) {
      setData(null);
      setError(null);
      setTierLocked(false);
      return;
    }
    setLoading(true);
    cvApi
      .tailorForMatch(token, matchId)
      .then((result) => {
        setData(result);
        if (!result.cached) {
          trackCvTailoredForMatch(matchId);
        }
      })
      .catch((e) => {
        if (e instanceof ApiError && e.status === 403) {
          setTierLocked(true);
        } else {
          setError(e instanceof Error ? e.message : "Could not tailor your CV.");
        }
      })
      .finally(() => setLoading(false));
  }, [open, token, matchId]);

  if (!open) return null;

  const slug =
    `cv-${jobTitle.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "")}` ||
    "tailored-cv";

  return (
    <ModalPortal>
      <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
        <div className="modal-backdrop" onClick={onClose} aria-hidden />
        <div
          role="dialog"
          aria-modal="true"
          className="modal-panel w-full max-w-2xl max-h-[90vh] flex flex-col rounded-t-2xl sm:rounded-2xl overflow-hidden"
        >
          <header
            className="flex items-start justify-between gap-4 p-5 sm:p-6 border-b"
            style={{ borderColor: "var(--line)" }}
          >
            <div className="min-w-0">
              <div className="eyebrow mb-1">Tailored CV</div>
              <h3
                className="font-display text-xl sm:text-2xl truncate"
                style={{ letterSpacing: "-0.01em" }}
                title={jobTitle}
              >
                {jobTitle}
              </h3>
              {company ? (
                <p className="text-sm" style={{ color: "var(--muted)" }}>
                  {company}
                </p>
              ) : null}
            </div>
            <button
              onClick={onClose}
              aria-label="Close"
              className="shrink-0 w-8 h-8 rounded-full flex items-center justify-center"
              style={{ border: "1px solid var(--line-2)", color: "var(--muted)" }}
            >
              <Icon name="x" size={14} />
            </button>
          </header>

          <div className="flex-1 overflow-y-auto p-5 sm:p-6 prose prose-sm max-w-none">
            {loading && (
              <div className="flex items-center gap-2 text-sm" style={{ color: "var(--muted)" }}>
                <span className="spinner" /> Tailoring your CV for this role…
              </div>
            )}

            {tierLocked && (
              <div className="text-center py-8">
                <h4 className="font-display text-xl mb-2">Professional plan</h4>
                <p className="text-sm mb-5 max-w-md mx-auto" style={{ color: "var(--muted)" }}>
                  Per-match tailored CVs are included on Professional (K250/mo) and Super Standard.
                </p>
                <Link href="/pricing" className="btn btn-accent">
                  See pricing <Icon name="arrowRight" size={14} />
                </Link>
              </div>
            )}

            {error && !tierLocked && (
              <p className="text-sm" style={{ color: "var(--danger)" }}>
                {error}
              </p>
            )}

            {data && (
              <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
                {data.markdown}
              </ReactMarkdown>
            )}
          </div>

          {data && (
            <footer
              className="flex items-center justify-between gap-3 p-4 sm:p-5 border-t"
              style={{ borderColor: "var(--line)" }}
            >
              <span className="text-xs" style={{ color: "var(--muted)" }}>
                {data.word_count} words
                {data.cached ? " · saved copy" : ""}
              </span>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => downloadMarkdown(`${slug}.md`, data.markdown)}
              >
                <Icon name="download" size={14} /> Download as Markdown
              </button>
            </footer>
          )}
        </div>
      </div>
    </ModalPortal>
  );
}
