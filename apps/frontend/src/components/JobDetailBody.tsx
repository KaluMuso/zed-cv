"use client";

import { Icon } from "@/components/ui/Icon";
import { Avatar } from "@/components/ui/Avatar";
import type { Job } from "@/lib/api";

// Client-side defensive HTML strip for job descriptions. The backend
// _strip_html runs at ingest and the admin backfill cleaned most rows,
// but legacy rows ingested before the strip_html deploy can still carry
// HTML (the "We Effect" / `<p class="ql` half-tag leak from 2026-05-13).
// This belt-and-braces pass ensures the user always sees plain text even
// if a stray HTML row slips through.
//
// Mirrors the backend whitelist approach so behaviour stays consistent:
// block-level tags become newlines, list items become bullets, inline
// tags are stripped. Same whitelist Claude Code introduced in jobs.py so
// non-HTML angle-bracket content (salary ranges like "K3000<x<K5000",
// email placeholders) is preserved.
const HTML_TAG_NAMES = (
  "h1|h2|h3|h4|h5|h6|p|div|span|a|br|li|ul|ol|" +
  "strong|em|b|i|u|s|strike|sup|sub|table|thead|tbody|tr|td|th|" +
  "blockquote|pre|code|hr|figure|figcaption|img|small"
).split("|");

const _HTML_TAG_RE = new RegExp(
  `</?\\s*(${HTML_TAG_NAMES.join("|")})(\\s[^>]*)?>`,
  "gi",
);
const _BR_RE = /<\s*br\s*\/?\s*>/gi;
const _LI_OPEN_RE = /<\s*li\b[^>]*>/gi;
const _BLOCK_CLOSE_RE = /<\/\s*(p|div|h[1-6]|ul|ol|tr|table)\s*>/gi;

function stripDescriptionHtml(text: string | null | undefined): string {
  if (!text) return "";
  if (!text.includes("<")) return text;
  return text
    .replace(_BR_RE, "\n")
    .replace(_LI_OPEN_RE, "\n• ")
    .replace(_BLOCK_CLOSE_RE, "\n")
    .replace(_HTML_TAG_RE, "")
    // Decode the few HTML entities a scraper might leave behind.
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'")
    // Collapse 3+ blank lines (the block-close → newline replacement
    // can create stacked blank lines for nested tags).
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

interface JobDetailBodyProps {
  job: Job;
  /** Optional callback for closing a drawer; absent on the standalone page. */
  onClose?: () => void;
  /** Whether to render the back-to-list affordance (true on standalone). */
  showBack?: boolean;
  /** Header text for the back affordance. */
  backLabel?: string;
  onBack?: () => void;
}

function formatRelativeTime(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return null;
  const diffMs = Date.now() - then;
  if (diffMs < 0) return null;
  const day = 24 * 60 * 60 * 1000;
  if (diffMs < day) return "today";
  if (diffMs < 2 * day) return "yesterday";
  const days = Math.floor(diffMs / day);
  if (days < 7) return `${days} days ago`;
  const weeks = Math.floor(days / 7);
  if (weeks < 5) return `${weeks}w ago`;
  return `${Math.floor(days / 30)}mo ago`;
}

function formatSalary(min?: number | null, max?: number | null): string | null {
  if (!min && !max) return null;
  const fmt = (ngwee: number) => {
    const kwacha = ngwee / 100;
    if (kwacha >= 1000)
      return `K${(kwacha / 1000).toFixed(kwacha % 1000 === 0 ? 0 : 1)}k`;
    return `K${kwacha.toFixed(0)}`;
  };
  if (min && max && min !== max) return `${fmt(min)}–${fmt(max)}`;
  return fmt(min ?? max ?? 0);
}

/**
 * Tries the employer's own apply page first; falls back to mailto;
 * returns null when neither is configured (button stays disabled).
 */
function buildApplyHref(job: Job): string | null {
  if (job.apply_url && /^https?:\/\//i.test(job.apply_url)) return job.apply_url;
  if (job.apply_email) {
    const subject = encodeURIComponent(`Application: ${job.title}`);
    const body = encodeURIComponent(
      `Hello${job.company ? ` ${job.company}` : ""},\n\nI'd like to apply for the ${job.title} role I saw on ZedApply.\n\n— Sent from zedapply.com`
    );
    return `mailto:${job.apply_email}?subject=${subject}&body=${body}`;
  }
  // Fall back to the scraper's source listing if everything else is missing —
  // at least gives the user somewhere to click rather than a dead button.
  if (job.source_url && /^https?:\/\//i.test(job.source_url)) return job.source_url;
  return null;
}

export function JobDetailBody({
  job,
  onClose,
  showBack = false,
  backLabel = "Back to jobs",
  onBack,
}: JobDetailBodyProps) {
  const postedRel = formatRelativeTime(job.posted_at);
  const salary = formatSalary(job.salary_min, job.salary_max);
  const applyHref = buildApplyHref(job);
  const closesIn = job.closing_date
    ? Math.ceil(
        (new Date(job.closing_date).getTime() - Date.now()) /
          (1000 * 60 * 60 * 24)
      )
    : null;

  return (
    <div className="p-6 md:p-8">
      {onClose && (
        <button onClick={onClose} className="btn btn-ghost btn-sm mb-6" type="button">
          <Icon name="x" size={16} /> Close
        </button>
      )}
      {showBack && onBack && (
        <button onClick={onBack} className="btn btn-ghost btn-sm mb-6" type="button">
          <Icon name="arrowLeft" size={14} /> {backLabel}
        </button>
      )}

      <div className="eyebrow mb-3">Job Details</div>

      <div className="flex items-start gap-4 mb-6">
        <Avatar name={job.company || "ZC"} size={48} />
        <div className="min-w-0 flex-1">
          <h1
            className="font-display text-3xl md:text-4xl mb-1"
            style={{ letterSpacing: "-0.015em", lineHeight: 1.1 }}
          >
            {job.title}
          </h1>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            {job.company || "Company not listed"}
            {job.location && <> &middot; {job.location}</>}
          </p>
        </div>
      </div>

      {/* Metadata strip */}
      <div
        className="flex flex-wrap gap-x-5 gap-y-2 mb-6 text-xs"
        style={{ color: "var(--muted)" }}
      >
        {postedRel && (
          <span className="flex items-center gap-1">
            <Icon name="clock" size={12} /> Posted {postedRel}
          </span>
        )}
        {salary && (
          <span
            className="flex items-center gap-1 font-mono"
            style={{ color: "var(--ink-2)" }}
          >
            {salary}/mo
          </span>
        )}
        {closesIn !== null && (
          <span
            className="flex items-center gap-1"
            style={{
              color: closesIn <= 3 ? "var(--danger)" : "var(--muted)",
              fontWeight: closesIn <= 3 ? 600 : 400,
            }}
          >
            <Icon name="clock" size={12} />
            {closesIn <= 0
              ? "Closed"
              : closesIn === 1
              ? "Closes tomorrow"
              : `Closes in ${closesIn} days`}
          </span>
        )}
        {job.source && job.source !== "manual" && job.source !== "partner" && (
          <span className="ml-auto text-[10px] opacity-60">
            Listed via {job.source}
          </span>
        )}
      </div>

      {/* Skills */}
      {job.skills.length > 0 && (
        <div className="mb-6">
          <div className="eyebrow mb-3">Required Skills</div>
          <div className="flex flex-wrap gap-1.5">
            {job.skills.map((s) => (
              <span key={s} className="tag tag-mono">
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Description — defensively stripped on the client in case a legacy
          row still carries HTML (the backend strip+backfill should have
          handled it, but stale rows + future scraper sources are real). */}
      {job.description && (() => {
        const cleaned = stripDescriptionHtml(job.description);
        if (!cleaned) return null;
        return (
          <div className="mb-8">
            <div className="eyebrow mb-3">Description</div>
            <p
              className="text-sm leading-relaxed whitespace-pre-wrap"
              style={{ color: "var(--ink-2)" }}
            >
              {cleaned}
            </p>
          </div>
        );
      })()}

      {/* Apply CTA — sticks to the bottom of the scrolling container.
          The mobile tab bar overlays the bottom 80px of the viewport,
          so we offset by that plus the iOS safe-area on mobile only.
          On desktop the offset collapses to zero. */}
      <div
        className="flex gap-3 sticky py-3"
        style={{
          background: "linear-gradient(to top, var(--surface) 70%, transparent)",
          bottom: "calc(var(--mobile-tabbar-offset, 0px))",
        }}
      >
        {applyHref ? (
          <a
            href={applyHref}
            target={applyHref.startsWith("mailto:") ? undefined : "_blank"}
            rel={applyHref.startsWith("mailto:") ? undefined : "noopener noreferrer"}
            className="btn btn-primary flex-1"
          >
            Apply Now <Icon name="external" size={14} />
          </a>
        ) : (
          <button
            className="btn btn-primary flex-1"
            disabled
            title="No application link provided"
            type="button"
          >
            Application link unavailable
          </button>
        )}
        <button
          className="btn btn-ghost"
          type="button"
          aria-label="Save job"
          title="Save this job (coming soon)"
        >
          <Icon name="bookmark" size={16} />
        </button>
      </div>
    </div>
  );
}
