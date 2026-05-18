"use client";

import { useState } from "react";
import { Icon } from "@/components/ui/Icon";
import { Avatar } from "@/components/ui/Avatar";
import type { Job } from "@/lib/api";
import { formatJobSource } from "@/lib/jobSource";
import { splitDescriptionChunks } from "@/lib/jobDescription";

// ── task #60: small formatters for structured field display ───────────
// Convert wire-format enum strings ("full_time", "on_site") into the
// human label we render in tags ("Full time", "On-site"). Falls back to
// the raw value if we don't recognise it so a future enum value still
// renders something, just less polished.
const EMPLOYMENT_TYPE_LABEL: Record<string, string> = {
  full_time: "Full time",
  part_time: "Part time",
  contract: "Contract",
  freelance: "Freelance",
  internship: "Internship",
  temporary: "Temporary",
};

const WORK_ARRANGEMENT_LABEL: Record<string, string> = {
  remote: "Remote",
  hybrid: "Hybrid",
  on_site: "On-site",
};

const PAY_FREQUENCY_LABEL: Record<string, string> = {
  monthly: "/mo",
  annual: "/yr",
  hourly: "/hr",
  daily: "/day",
};

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

  // task #60: "More about this role" collapses the long-form structured
  // fields (reporting structure, manages_others, interview process,
  // success metrics, bonus structure, equity) so the apply CTA stays
  // within reach on first paint. Collapsed by default.
  const [moreOpen, setMoreOpen] = useState(false);
  const benefits = job.benefits ?? [];
  const tools = job.tools_tech_stack ?? [];
  const hasMoreSection = Boolean(
    job.reporting_structure ||
      job.manages_others != null ||
      job.interview_process ||
      job.success_metrics ||
      job.bonus_structure ||
      job.equity_offered != null
  );
  const payFreqSuffix =
    job.pay_frequency && PAY_FREQUENCY_LABEL[job.pay_frequency]
      ? PAY_FREQUENCY_LABEL[job.pay_frequency]
      : "/mo";

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

      <div className="flex items-start gap-4 mb-4">
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

      {/* task #60: employment shape tags. Rendered as small inline tags
          near the title so the role's structure (remote / contract /
          etc.) is visible without scrolling. Hidden when the row has
          neither — legacy listings stay clean. */}
      {(job.employment_type || job.work_arrangement || job.reference_number) && (
        <div className="flex flex-wrap items-center gap-1.5 mb-6">
          {job.employment_type && (
            <span className="tag tag-mono">
              {EMPLOYMENT_TYPE_LABEL[job.employment_type] || job.employment_type}
            </span>
          )}
          {job.work_arrangement && (
            <span className="tag tag-mono">
              {WORK_ARRANGEMENT_LABEL[job.work_arrangement] || job.work_arrangement}
              {job.work_arrangement === "hybrid" && job.hybrid_days_per_week && (
                <> &middot; {job.hybrid_days_per_week}d/wk</>
              )}
            </span>
          )}
          {job.reference_number && (
            <span className="tag tag-mono" style={{ opacity: 0.7 }}>
              Ref: {job.reference_number}
            </span>
          )}
        </div>
      )}

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
            {salary}
            {payFreqSuffix}
            {job.currency && job.currency !== "ZMW" && (
              <span style={{ opacity: 0.7 }}> {job.currency}</span>
            )}
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
        <span className="ml-auto text-[10px] opacity-60">
          {formatJobSource(job.source, job.source_url)}
        </span>
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

      {/* task #60: tools / tech stack — rendered as a parallel chip row
          beneath Required Skills. Skills are abstract competencies
          ("project management"); tools are concrete named technologies
          ("postgres", "salesforce"). Worth surfacing both. */}
      {tools.length > 0 && (
        <div className="mb-6">
          <div className="eyebrow mb-3">Tools & tech</div>
          <div className="flex flex-wrap gap-1.5">
            {tools.map((t) => (
              <span key={t} className="tag tag-mono">
                {t}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* task #60: benefits — bullet list under its own eyebrow. Often
          the single biggest decision factor for a candidate. */}
      {benefits.length > 0 && (
        <div className="mb-6">
          <div className="eyebrow mb-3">Benefits</div>
          <ul className="text-sm space-y-1" style={{ color: "var(--ink-2)" }}>
            {benefits.map((b, i) => (
              <li key={i} className="flex gap-2">
                <span style={{ color: "var(--green-700)" }}>•</span>
                <span>{b}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* task #60: company description, surfaced before the role
          description because candidates often want to know who they'd
          be working for before reading the JD itself. */}
      {job.company_description && (
        <div className="mb-6">
          <div className="eyebrow mb-3">About the company</div>
          <p
            className="text-sm leading-relaxed whitespace-pre-wrap"
            style={{ color: "var(--ink-2)" }}
          >
            {job.company_description}
          </p>
        </div>
      )}

      {/* Description — HTML-stripped (legacy rows can still carry tags),
          then chunked into headings + paragraphs so section titles like
          "Job Purpose" / "Key Responsibilities" render as bold h3s
          instead of disappearing into the body text. */}
      {job.description && (() => {
        const cleaned = stripDescriptionHtml(job.description);
        if (!cleaned) return null;
        const chunks = splitDescriptionChunks(cleaned);
        return (
          <div className="mb-6">
            <div className="eyebrow mb-3">Description</div>
            {chunks.map((chunk, i) =>
              chunk.type === "heading" ? (
                <h3
                  key={i}
                  className="font-display text-base font-semibold mt-4 mb-2"
                  style={{ color: "var(--ink)" }}
                >
                  {chunk.text}
                </h3>
              ) : (
                <p
                  key={i}
                  className="text-sm leading-relaxed text-justify whitespace-pre-line mb-3"
                  style={{ color: "var(--ink-2)" }}
                >
                  {chunk.text}
                </p>
              ),
            )}
          </div>
        );
      })()}

      {/* task #60: application instructions — separate from Description
          because they're action-oriented; the candidate needs to find
          them quickly when deciding what to do next. */}
      {job.application_instructions && (
        <div
          className="mb-6 p-4 rounded-lg"
          style={{
            background: "var(--bg-2)",
            border: "1px solid var(--line)",
          }}
        >
          <div className="eyebrow mb-2">How to apply</div>
          <p
            className="text-sm leading-relaxed whitespace-pre-wrap"
            style={{ color: "var(--ink-2)" }}
          >
            {job.application_instructions}
          </p>
        </div>
      )}

      {/* task #60: collapsed "More about this role" section. Carries the
          interview-process / metrics / management-shape signals that
          matter to serious candidates but would otherwise push the
          apply CTA below the fold on mobile. */}
      {hasMoreSection && (
        <div className="mb-8">
          <button
            type="button"
            onClick={() => setMoreOpen((v) => !v)}
            className="flex items-center gap-2 text-sm font-medium"
            style={{
              color: "var(--ink-2)",
              background: "none",
              border: "none",
              padding: 0,
              cursor: "pointer",
            }}
          >
            <Icon
              name={moreOpen ? "chevronDown" : "chevronRight"}
              size={14}
            />
            More about this role
          </button>
          {moreOpen && (
            <div className="mt-4 space-y-4">
              {job.reporting_structure && (
                <Field label="Reports to" value={job.reporting_structure} />
              )}
              {job.manages_others != null && job.manages_others > 0 && (
                <Field
                  label="Direct reports"
                  value={`${job.manages_others}`}
                />
              )}
              {job.interview_process && (
                <Field label="Interview process" value={job.interview_process} />
              )}
              {job.success_metrics && (
                <Field label="Success metrics" value={job.success_metrics} />
              )}
              {job.bonus_structure && (
                <Field label="Bonus structure" value={job.bonus_structure} />
              )}
              {job.equity_offered != null && (
                <Field
                  label="Equity"
                  value={job.equity_offered ? "Offered" : "Not offered"}
                />
              )}
            </div>
          )}
        </div>
      )}

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

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div
        className="text-[11px] uppercase tracking-wider mb-1"
        style={{ color: "var(--muted)" }}
      >
        {label}
      </div>
      <p
        className="text-sm leading-relaxed whitespace-pre-wrap"
        style={{ color: "var(--ink-2)" }}
      >
        {value}
      </p>
    </div>
  );
}
