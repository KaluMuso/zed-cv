"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";
import {
  interviewPrep as interviewPrepApi,
  type InterviewPrepResult,
  ApiError,
} from "@/lib/api";
import { Icon } from "@/components/ui/Icon";
import { ModalPortal } from "@/components/shared/ModalPortal";

export function InterviewPrepModal({
  open,
  onClose,
  token,
  jobId,
  jobTitle,
  company,
}: {
  open: boolean;
  onClose: () => void;
  token: string;
  jobId: string;
  jobTitle: string;
  company: string | null;
}) {
  const [data, setData] = useState<InterviewPrepResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tierLocked, setTierLocked] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!open) {
      setData(null);
      setError(null);
      setTierLocked(false);
      setCopied(false);
      return;
    }
    setLoading(true);
    interviewPrepApi
      .generate(token, jobId)
      .then((r) => setData(r))
      .catch((e) => {
        if (e instanceof ApiError && e.status === 403) {
          setTierLocked(true);
        } else {
          setError(e instanceof Error ? e.message : "Could not generate prep notes.");
        }
      })
      .finally(() => setLoading(false));
  }, [open, token, jobId]);

  const onCopy = async () => {
    if (!data) return;
    try {
      await navigator.clipboard.writeText(data.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Could not copy to clipboard.");
    }
  };

  if (!open) return null;

  return (
    <ModalPortal>
      <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
        <div className="modal-backdrop" onClick={onClose} aria-hidden />
        <div
          role="dialog"
          aria-modal="true"
          className="modal-panel w-full max-w-2xl max-h-[90vh] flex flex-col rounded-t-2xl sm:rounded-2xl overflow-hidden"
        >
        <header className="flex items-start justify-between gap-4 p-5 sm:p-6 border-b" style={{ borderColor: "var(--line)" }}>
          <div className="min-w-0">
            <div className="eyebrow mb-1">Interview prep</div>
            <h3
              className="font-display text-xl sm:text-2xl truncate"
              style={{ letterSpacing: "-0.01em" }}
              title={jobTitle}
            >
              {jobTitle}
            </h3>
            {company && (
              <p className="text-sm" style={{ color: "var(--muted)" }}>
                {company}
              </p>
            )}
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

        <div className="flex-1 overflow-y-auto p-5 sm:p-6">
          {loading && (
            <div className="flex items-center gap-2 text-sm" style={{ color: "var(--muted)" }}>
              <span className="spinner" /> Generating tailored prep notes…
            </div>
          )}

          {tierLocked && (
            <div className="text-center py-8">
              <div
                className="w-14 h-14 mx-auto mb-4 rounded-2xl flex items-center justify-center"
                style={{ background: "var(--copper-100)", color: "var(--copper-600)" }}
              >
                <Icon name="zap" size={22} />
              </div>
              <h4 className="font-display text-xl mb-2">Super Standard plan only</h4>
              <p className="text-sm mb-5 max-w-md mx-auto" style={{ color: "var(--muted)" }}>
                Interview prep notes are part of the Super Standard plan (K500/mo). It includes
                everything in Professional plus unlimited matches and tailored prep briefs.
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

          {data && <PrepBody markdown={data.content} />}
        </div>

        {data && (
          <footer
            className="flex items-center justify-between gap-3 p-4 sm:p-5 border-t"
            style={{ borderColor: "var(--line)" }}
          >
            <span className="text-xs" style={{ color: "var(--muted)" }}>
              {data.word_count} words{data.cached ? " · cached" : ""}
            </span>
            <button onClick={onCopy} className="btn btn-ghost btn-sm">
              {copied ? "Copied!" : "Copy notes"}
            </button>
          </footer>
        )}
        </div>
      </div>
    </ModalPortal>
  );
}

function PrepBody({ markdown }: { markdown: string }) {
  // react-markdown handles the full CommonMark + GFM spec — bold, italic,
  // numbered lists, inline code, links, tables, strikethrough — instead of
  // the lightweight inline parser this component used to ship with (which
  // missed **bold** + *italic* and rendered them as literal asterisks).
  //
  // AI-safety: rehypeSanitize is mandatory because the markdown source is
  // LLM output. Without it a prompt-injection could emit raw HTML (script
  // tags, iframes, on* handlers) that would execute in the user's browser.
  // The default rehype-sanitize schema strips dangerous elements/attrs
  // and is the same hardened schema GitHub uses for issue rendering.
  return (
    <div className="prep-body text-sm leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]}
        components={{
          // Brand the headings — copper accent matches the rest of the UI.
          h1: ({ children }) => (
            <h3 className="font-display text-xl mt-5 mb-2">{children}</h3>
          ),
          h2: ({ children }) => (
            <h4
              className="font-display text-lg mt-5 mb-2"
              style={{ letterSpacing: "-0.01em", color: "var(--copper-600)" }}
            >
              {children}
            </h4>
          ),
          h3: ({ children }) => (
            <h5 className="font-display text-base mt-4 mb-2 font-semibold">
              {children}
            </h5>
          ),
          p: ({ children }) => <p className="mb-3">{children}</p>,
          ul: ({ children }) => (
            <ul className="list-disc pl-5 mb-4 space-y-1.5">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal pl-5 mb-4 space-y-1.5">{children}</ol>
          ),
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          strong: ({ children }) => (
            <strong className="font-semibold" style={{ color: "var(--ink)" }}>
              {children}
            </strong>
          ),
          em: ({ children }) => (
            <em style={{ color: "var(--ink-2)" }}>{children}</em>
          ),
          code: ({ children }) => (
            <code
              className="px-1 py-0.5 rounded text-xs"
              style={{ background: "var(--bg-2)", color: "var(--copper-600)" }}
            >
              {children}
            </code>
          ),
          a: ({ children, href }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: "var(--green-700)", textDecoration: "underline" }}
            >
              {children}
            </a>
          ),
        }}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  );
}
