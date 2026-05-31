"use client";

import { useState } from "react";
import { Icon } from "@/components/ui/Icon";
import { SaveJobButton } from "@/components/SaveJobButton";
import { Avatar } from "@/components/ui/Avatar";
import type { Job, MatchData } from "@/lib/api";
import { JobDescription } from "@/components/jobs/JobDescription";
import { DeadlineBadge } from "@/components/jobs/DeadlineBadge";
import { ApplyModal } from "@/components/jobs/ApplyModal";
import { JobDetailMatchPanel } from "@/components/jobs/JobDetailMatchPanel";
import { JobDetailSimilarMatches } from "@/components/jobs/JobDetailSimilarMatches";
import { CoverLetterModal } from "@/components/jobs/CoverLetterModal";
import { stripDescriptionHtml } from "@/components/jobs/jobDetailHtml";
import { SectionEyebrow } from "@/components/ui/SectionEyebrow";
import Link from "next/link";
import {
  EMPLOYMENT_TYPE_LABEL,
  WORK_ARRANGEMENT_LABEL,
  PAY_FREQUENCY_LABEL,
  formatSalary,
} from "@/components/jobs/jobDetailFormatters";
import {
  hasStructuredApplyContact,
  resolveApplyAction,
  resolveApplyContactMethods,
  type ApplyJobFields,
} from "@/lib/applyLink";
import { trackApplyClick } from "@/lib/trackApplyClick";
import { JobShareButtons } from "@/components/share/JobShareButtons";
import { isJobListingClosed } from "@/lib/isJobListingClosed";
import { cn } from "@/lib/utils";

interface JobDetailBodyProps {
  job: Job;
  onClose?: () => void;
  showBack?: boolean;
  backLabel?: string;
  onBack?: () => void;
  authToken?: string | null;
  jobSaved?: boolean;
  onSavedChange?: (nextSaved: boolean) => void;
  /** Personalised match for this job (signed-in users with CV). */
  match?: MatchData | null;
  /** Top matches used for the "Similar matches" grid at page bottom. */
  similarMatches?: MatchData[];
  viewerName?: string | null;
  subscriptionTier?: string | null;
}

function MetaPill({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-3 py-1 text-xs font-medium",
        "bg-muted/50 text-foreground/90 border border-border/60",
        className,
      )}
    >
      {children}
    </span>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <SectionEyebrow>{children}</SectionEyebrow>;
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <SectionTitle>{label}</SectionTitle>
      <p className="text-sm leading-relaxed whitespace-pre-wrap" style={{ color: "var(--ink-2)" }}>
        {value}
      </p>
    </div>
  );
}

export function JobDetailBody({
  job,
  onClose,
  showBack = false,
  backLabel = "Back to jobs",
  onBack,
  authToken,
  jobSaved = false,
  onSavedChange,
  match,
  similarMatches = [],
  viewerName,
  subscriptionTier,
}: JobDetailBodyProps) {
  const salary = formatSalary(job.salary_min, job.salary_max);
  const [applyOpen, setApplyOpen] = useState(false);
  const [coverOpen, setCoverOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);

  const listingClosed = isJobListingClosed(job);
  const applyFields = job as ApplyJobFields;
  const primaryApply = listingClosed ? null : resolveApplyAction(applyFields);
  const applyMethods = listingClosed ? [] : resolveApplyContactMethods(applyFields);
  const multipleApplyChannels = applyMethods.length > 1;

  const jobTypeLabel = job.employment_type
    ? EMPLOYMENT_TYPE_LABEL[job.employment_type] || job.employment_type
    : job.work_arrangement
      ? WORK_ARRANGEMENT_LABEL[job.work_arrangement] || job.work_arrangement
      : null;

  const payFreqSuffix =
    job.pay_frequency && PAY_FREQUENCY_LABEL[job.pay_frequency]
      ? PAY_FREQUENCY_LABEL[job.pay_frequency]
      : "/mo";

  const benefits = job.benefits ?? [];
  const tools = job.tools_tech_stack ?? [];
  const hasMoreSection = Boolean(
    job.reporting_structure ||
      job.manages_others != null ||
      job.interview_process ||
      job.success_metrics ||
      job.bonus_structure ||
      job.equity_offered != null,
  );

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

      {/* Header */}
      <header className="mb-6">
        <div className="flex items-start gap-4 mb-4">
          <Avatar name={job.company || "ZC"} size={56} />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium mb-1" style={{ color: "var(--muted)" }}>
              {job.company || "Company not listed"}
            </p>
            <h1
              className="font-display text-3xl md:text-4xl"
              style={{ letterSpacing: "-0.015em", lineHeight: 1.1 }}
            >
              {job.title}
            </h1>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {job.closing_date ? (
            <DeadlineBadge closingDate={job.closing_date} className="text-xs px-3 py-1" />
          ) : null}
          {salary && (
            <MetaPill>
              <span className="font-mono">
                {salary}
                {payFreqSuffix}
              </span>
              {job.currency && job.currency !== "ZMW" && (
                <span className="opacity-70 ml-1">{job.currency}</span>
              )}
            </MetaPill>
          )}
          {jobTypeLabel && <MetaPill>{jobTypeLabel}</MetaPill>}
          {job.work_arrangement && job.employment_type && (
            <MetaPill>
              {WORK_ARRANGEMENT_LABEL[job.work_arrangement] || job.work_arrangement}
              {job.work_arrangement === "hybrid" && job.hybrid_days_per_week && (
                <span className="opacity-80"> · {job.hybrid_days_per_week}d/wk</span>
              )}
            </MetaPill>
          )}
          {job.location && (
            <MetaPill>
              <Icon name="map" size={12} className="mr-1 opacity-70" />
              {job.location}
            </MetaPill>
          )}
        </div>
      </header>

      {listingClosed ? (
        <div
          className="mb-6 rounded-xl border px-4 py-3 text-sm"
          style={{
            borderColor: "var(--amber-500, #d97706)",
            background: "rgba(217, 119, 6, 0.08)",
            color: "var(--ink)",
          }}
          role="status"
        >
          <p className="font-medium">This role is no longer accepting applications</p>
          {job.closure_reason ? (
            <p className="mt-1 text-muted-foreground">{job.closure_reason}</p>
          ) : job.closing_date ? (
            <p className="mt-1 text-muted-foreground">Closed on {job.closing_date}</p>
          ) : job.deactivation_reason === "split_into_children" ? (
            <p className="mt-1 text-muted-foreground">
              Replaced by separate role listings — browse similar matches below.
            </p>
          ) : null}
        </div>
      ) : null}

      {/* Two-column: match panel stacks under header on mobile */}
      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(280px,320px)] gap-8 lg:gap-10">
        <aside className="order-1 lg:order-2 lg:sticky lg:top-6 lg:self-start">
          <JobDetailMatchPanel
            match={match}
            signedIn={Boolean(authToken)}
            viewerName={viewerName}
            subscriptionTier={subscriptionTier}
          />
        </aside>

        <div className="order-2 lg:order-1 min-w-0">
          {/* Action row */}
          <div className="flex flex-col sm:flex-row flex-wrap gap-3 mb-8">
            {primaryApply ? (
              multipleApplyChannels ? (
                <>
                  <button
                    type="button"
                    className="btn btn-primary flex-1 sm:flex-none sm:min-w-[200px] justify-center gap-2"
                    onClick={() => setApplyOpen(true)}
                    data-testid="job-detail-apply-open"
                  >
                    Apply now
                  </button>
                  <button
                    type="button"
                    className="btn btn-outline flex-1 sm:flex-none justify-center"
                    onClick={() => setApplyOpen(true)}
                  >
                    All apply options
                  </button>
                </>
              ) : (
                <a
                  href={primaryApply.href}
                  className="btn btn-primary flex-1 sm:flex-none sm:min-w-[200px] justify-center gap-2"
                  target={primaryApply.external ? "_blank" : undefined}
                  rel={primaryApply.external ? "noopener noreferrer" : undefined}
                  data-testid="job-detail-apply-primary"
                  onClick={() => {
                    if (authToken) {
                      trackApplyClick(authToken, job.id, primaryApply.applySource);
                    }
                  }}
                >
                  {primaryApply.label}
                  {primaryApply.external ? <Icon name="external" size={14} /> : null}
                </a>
              )
            ) : !listingClosed && hasStructuredApplyContact(applyFields) ? (
              <button
                type="button"
                className="btn btn-primary flex-1 sm:flex-none sm:min-w-[200px] justify-center"
                onClick={() => setApplyOpen(true)}
              >
                How to apply
              </button>
            ) : null}
            <SaveJobButton
              jobId={job.id}
              saved={jobSaved}
              token={authToken ?? null}
              showLabel
              saveLabel="Save"
              savedLabel="Saved"
              className="flex-1 sm:flex-none justify-center"
              onChange={(_id, next) => onSavedChange?.(next)}
            />
            <button
              type="button"
              className="btn btn-outline flex-1 sm:flex-none justify-center gap-1.5"
              onClick={() => setCoverOpen(true)}
            >
              <Icon name="sparkle" size={14} /> Generate cover letter
            </button>
            <Link
              href={`/profile/cv-builder?jobId=${encodeURIComponent(job.id)}&jobTitle=${encodeURIComponent(job.title)}&company=${encodeURIComponent(job.company || "")}`}
              className="btn btn-ghost flex-1 sm:flex-none justify-center gap-1.5"
            >
              <Icon name="file" size={14} /> Tailored CV
            </Link>
          </div>

          <section className="mb-8" aria-label="Share this job">
            <SectionTitle>Share</SectionTitle>
            <JobShareButtons
              job={{
                id: job.id,
                title: job.title,
                company: job.company,
                location: job.location,
              }}
            />
          </section>

          {job.reference_number && (
            <p className="text-xs font-mono mb-6" style={{ color: "var(--muted)" }}>
              Ref: {job.reference_number}
            </p>
          )}

          {job.skills.length > 0 && (
            <section className="mb-8">
              <SectionTitle>Required skills</SectionTitle>
              <div className="flex flex-wrap gap-1.5">
                {job.skills.map((s) => (
                  <span key={s} className="tag tag-mono">
                    {s}
                  </span>
                ))}
              </div>
            </section>
          )}

          {tools.length > 0 && (
            <section className="mb-8">
              <SectionTitle>Tools & tech</SectionTitle>
              <div className="flex flex-wrap gap-1.5">
                {tools.map((t) => (
                  <span key={t} className="tag tag-mono">
                    {t}
                  </span>
                ))}
              </div>
            </section>
          )}

          {benefits.length > 0 && (
            <section className="mb-8">
              <SectionTitle>Benefits</SectionTitle>
              <ul className="text-sm space-y-1" style={{ color: "var(--ink-2)" }}>
                {benefits.map((b, i) => (
                  <li key={i} className="flex gap-2">
                    <span style={{ color: "var(--green-700)" }}>•</span>
                    <span>{b}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {job.company_description && (
            <section className="mb-8">
              <SectionTitle>About the company</SectionTitle>
              <p className="text-sm leading-relaxed whitespace-pre-wrap" style={{ color: "var(--ink-2)" }}>
                {job.company_description}
              </p>
            </section>
          )}

          {(job.description || job.description_markdown) && (
            <section className="mb-8">
              <SectionTitle>About the role</SectionTitle>
              <JobDescription
                description={job.description ? stripDescriptionHtml(job.description) : null}
                descriptionMarkdown={job.description_markdown}
                descriptionHtml={job.description_html}
                sectionHtml={job.section_html}
                sections={{
                  section_responsibilities: job.section_responsibilities,
                  section_requirements: job.section_requirements,
                  section_benefits: job.section_benefits,
                  section_how_to_apply: job.section_how_to_apply,
                  section_about: job.section_about,
                }}
              />
            </section>
          )}

          {job.application_instructions && (
            <section
              className="mb-8 p-4 rounded-xl border"
              style={{ background: "var(--bg-2)", borderColor: "var(--line)" }}
            >
              <SectionTitle>How to apply</SectionTitle>
              <p className="text-sm leading-relaxed whitespace-pre-wrap" style={{ color: "var(--ink-2)" }}>
                {job.application_instructions}
              </p>
            </section>
          )}

          {hasMoreSection && (
            <section className="mb-8">
              <button
                type="button"
                onClick={() => setMoreOpen((v) => !v)}
                className="flex items-center gap-2 text-sm font-medium"
                style={{ color: "var(--ink-2)", background: "none", border: "none", padding: 0, cursor: "pointer" }}
              >
                <Icon name={moreOpen ? "chevronDown" : "chevronRight"} size={14} />
                More about this role
              </button>
              {moreOpen && (
                <div className="mt-4 space-y-6">
                  {job.reporting_structure && <Field label="Reports to" value={job.reporting_structure} />}
                  {job.manages_others != null && job.manages_others > 0 && (
                    <Field label="Direct reports" value={`${job.manages_others}`} />
                  )}
                  {job.interview_process && <Field label="Interview process" value={job.interview_process} />}
                  {job.success_metrics && <Field label="Success metrics" value={job.success_metrics} />}
                  {job.bonus_structure && <Field label="Bonus structure" value={job.bonus_structure} />}
                  {job.equity_offered != null && (
                    <Field label="Equity" value={job.equity_offered ? "Offered" : "Not offered"} />
                  )}
                </div>
              )}
            </section>
          )}

          <JobDetailSimilarMatches matches={similarMatches} currentJobId={job.id} />
        </div>
      </div>

      <ApplyModal job={job} open={applyOpen} onOpenChange={setApplyOpen} />
      <CoverLetterModal
        jobId={job.id}
        jobTitle={job.title}
        company={job.company}
        token={authToken ?? null}
        open={coverOpen}
        onOpenChange={setCoverOpen}
      />
    </div>
  );
}
