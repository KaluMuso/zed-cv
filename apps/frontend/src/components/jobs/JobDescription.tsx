"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { plainTextToMarkdown } from "@/lib/markdownNormalizer";
import { stripScraperMetadata } from "@/components/jobs/jobDetailHtml";
import { cn } from "@/lib/utils";

const MAIN_SUBTITLE_HEADINGS = new Set([
  "requirements",
  "location",
  "method of application",
  "how to apply",
  "qualifications",
  "key responsibilities",
  "job purpose",
  "duties",
  "responsibilities",
  "experience",
  "education",
  "competencies",
  "preferred qualifications",
  "secondary job functions",
  "compensation structure",
  "about the role",
  "about the company",
  "job summary",
  "essential functions",
  "minimum qualifications",
]);

const SECTION_HTML_META: {
  key: string;
  title: string;
  icon: string;
}[] = [
  { key: "responsibilities", title: "Responsibilities", icon: "📋" },
  { key: "requirements", title: "Requirements", icon: "✅" },
  { key: "benefits", title: "Benefits", icon: "🎁" },
  { key: "how_to_apply", title: "How to apply", icon: "📧" },
  { key: "about", title: "About", icon: "🏢" },
];

export type JobDescriptionSections = {
  section_responsibilities?: string | null;
  section_requirements?: string | null;
  section_benefits?: string | null;
  section_how_to_apply?: string | null;
  section_about?: string | null;
};

const proseClasses = cn(
  "job-description-markdown prose prose-zinc max-w-none text-sm",
  "dark:prose-invert",
  "prose-headings:mt-8 prose-headings:mb-3",
  "prose-p:my-4 prose-li:my-1",
  "prose-h2:text-base prose-h3:text-sm",
);

function headingText(children: React.ReactNode): string {
  if (typeof children === "string") return children.trim();
  if (Array.isArray(children)) {
    return children
      .map((c) => (typeof c === "string" ? c : ""))
      .join("")
      .trim();
  }
  return "";
}

function isMainSubtitle(text: string): boolean {
  const key = text.replace(/:$/, "").trim().toLowerCase();
  return MAIN_SUBTITLE_HEADINGS.has(key);
}

function SectionHeading({ children }: { children: React.ReactNode }) {
  const text = headingText(children);
  const main = isMainSubtitle(text);
  return (
    <h3
      className={cn(
        "job-description-heading font-bold tracking-widest uppercase text-muted-foreground",
        main ? "text-xs mt-8 mb-3 first:mt-0" : "text-[11px] mt-6 mb-2 opacity-90",
      )}
    >
      {children}
    </h3>
  );
}

const markdownComponents = {
  h1: ({ children }: { children?: React.ReactNode }) => (
    <SectionHeading>{children}</SectionHeading>
  ),
  h2: ({ children }: { children?: React.ReactNode }) => (
    <SectionHeading>{children}</SectionHeading>
  ),
  h3: ({ children }: { children?: React.ReactNode }) => (
    <SectionHeading>{children}</SectionHeading>
  ),
  a: ({ href, children }: { href?: string; children?: React.ReactNode }) => (
    <a
      href={href}
      target={href?.startsWith("http") ? "_blank" : undefined}
      rel={href?.startsWith("http") ? "noopener noreferrer" : undefined}
      className="underline text-primary dark:text-primary"
    >
      {children}
    </a>
  ),
  ul: ({ children }: { children?: React.ReactNode }) => (
    <ul className="list-disc pl-5 space-y-1 my-2">{children}</ul>
  ),
  ol: ({ children }: { children?: React.ReactNode }) => (
    <ol className="list-decimal pl-5 space-y-1 my-2">{children}</ol>
  ),
  li: ({ children }: { children?: React.ReactNode }) => (
    <li className="leading-relaxed">{children}</li>
  ),
  p: ({ children }: { children?: React.ReactNode }) => (
    <p className="my-2 leading-relaxed whitespace-pre-line">{children}</p>
  ),
  hr: () => <hr className="my-6 border-0 border-t border-[var(--line)]" />,
  blockquote: ({ children }: { children?: React.ReactNode }) => (
    <blockquote className="my-4 border-l-[3px] border-[var(--green-500)] bg-[var(--bg-2)] py-3 px-4 rounded-r-lg text-[var(--ink-2)]">
      {children}
    </blockquote>
  ),
  h4: ({ children }: { children?: React.ReactNode }) => (
    <SectionHeading>{children}</SectionHeading>
  ),
};

function MarkdownBlock({ md }: { md: string }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
      {md}
    </ReactMarkdown>
  );
}

function StructuredSectionCard({
  title,
  body,
  icon,
}: {
  title: string;
  body: string;
  icon?: string;
}) {
  return (
    <section
      className="rounded-xl border p-4 mb-4"
      style={{ borderColor: "var(--line)", background: "var(--bg-2)" }}
    >
      <h3 className="job-description-heading text-xs font-bold tracking-widest uppercase text-muted-foreground mb-3">
        {icon ? `${icon} ` : ""}
        {title}
      </h3>
      <MarkdownBlock md={body} />
    </section>
  );
}

function HtmlSectionCard({
  title,
  html,
  icon,
}: {
  title: string;
  html: string;
  icon: string;
}) {
  return (
    <section
      className="rounded-xl border p-4 mb-4"
      style={{ borderColor: "var(--line)", background: "var(--bg-2)" }}
    >
      <h3 className="job-description-heading text-xs font-bold tracking-widest uppercase text-muted-foreground mb-3">
        {icon} {title}
      </h3>
      <div
        className={proseClasses}
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </section>
  );
}

function hasStructuredSections(sections: JobDescriptionSections): boolean {
  return Boolean(
    sections.section_responsibilities?.trim() ||
      sections.section_requirements?.trim() ||
      sections.section_benefits?.trim() ||
      sections.section_how_to_apply?.trim() ||
      sections.section_about?.trim(),
  );
}

function hasSectionHtml(sectionHtml: Record<string, string> | null | undefined): boolean {
  if (!sectionHtml) return false;
  return Object.values(sectionHtml).some((v) => v && v.trim());
}

export function JobDescription({
  description,
  descriptionMarkdown,
  descriptionHtml,
  sectionHtml,
  sections,
}: {
  description: string | null | undefined;
  descriptionMarkdown?: string | null;
  descriptionHtml?: string | null;
  sectionHtml?: Record<string, string> | null;
  sections?: JobDescriptionSections;
}) {
  if (descriptionHtml?.trim()) {
    return (
      <article
        className={proseClasses}
        dangerouslySetInnerHTML={{ __html: descriptionHtml.trim() }}
      />
    );
  }

  if (hasSectionHtml(sectionHtml)) {
    return (
      <div className={proseClasses}>
        {SECTION_HTML_META.map(({ key, title, icon }) => {
          const html = sectionHtml?.[key];
          if (!html?.trim()) return null;
          return (
            <HtmlSectionCard key={key} title={title} html={html} icon={icon} />
          );
        })}
      </div>
    );
  }

  const structured = sections ?? {};
  if (hasStructuredSections(structured)) {
    const cards: { title: string; body: string }[] = [];
    if (structured.section_responsibilities?.trim()) {
      cards.push({
        title: "Responsibilities",
        body: structured.section_responsibilities.trim(),
      });
    }
    if (structured.section_requirements?.trim()) {
      cards.push({
        title: "Requirements",
        body: structured.section_requirements.trim(),
      });
    }
    if (structured.section_benefits?.trim()) {
      cards.push({
        title: "Benefits",
        body: structured.section_benefits.trim(),
      });
    }
    if (structured.section_how_to_apply?.trim()) {
      cards.push({
        title: "How to apply",
        body: structured.section_how_to_apply.trim(),
      });
    }
    if (structured.section_about?.trim()) {
      cards.push({ title: "About", body: structured.section_about.trim() });
    }
    return (
      <div className={proseClasses}>
        {cards.map((card) => (
          <StructuredSectionCard key={card.title} title={card.title} body={card.body} />
        ))}
      </div>
    );
  }

  const md = stripScraperMetadata(
    (descriptionMarkdown && descriptionMarkdown.trim()) ||
      plainTextToMarkdown(description || ""),
  );

  if (!md) {
    return (
      <p className="text-sm text-muted-foreground dark:text-muted-foreground">
        No description provided.
      </p>
    );
  }

  return (
    <div className={proseClasses}>
      <MarkdownBlock md={md} />
    </div>
  );
}
