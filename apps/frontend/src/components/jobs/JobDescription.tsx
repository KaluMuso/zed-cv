"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { plainTextToMarkdown } from "@/lib/markdownNormalizer";
import { cn } from "@/lib/utils";

const MAIN_SUBTITLE_HEADINGS = new Set([
  "requirements",
  "location",
  "method of application",
  "how to apply",
  "qualifications",
  "key responsibilities",
  "job purpose",
]);

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
        "mt-6 mb-2 font-bold tracking-widest uppercase text-muted-foreground",
        main ? "text-xs" : "text-[11px] opacity-90",
      )}
    >
      {children}
    </h3>
  );
}

export function JobDescription({
  description,
  descriptionMarkdown,
}: {
  description: string | null | undefined;
  descriptionMarkdown?: string | null;
}) {
  const md =
    (descriptionMarkdown && descriptionMarkdown.trim()) ||
    plainTextToMarkdown(description || "");

  if (!md) {
    return (
      <p className="text-sm text-muted-foreground dark:text-muted-foreground">
        No description provided.
      </p>
    );
  }

  return (
    <div className="job-description-markdown prose prose-sm max-w-none text-sm text-foreground/90 dark:text-foreground/90 dark:prose-invert">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => <SectionHeading>{children}</SectionHeading>,
          h2: ({ children }) => <SectionHeading>{children}</SectionHeading>,
          h3: ({ children }) => <SectionHeading>{children}</SectionHeading>,
          a: ({ href, children }) => (
            <a
              href={href}
              target={href?.startsWith("http") ? "_blank" : undefined}
              rel={href?.startsWith("http") ? "noopener noreferrer" : undefined}
              className="underline text-primary dark:text-primary"
            >
              {children}
            </a>
          ),
          ul: ({ children }) => (
            <ul className="list-disc pl-5 space-y-1 my-2">{children}</ul>
          ),
          p: ({ children }) => <p className="my-2 leading-relaxed">{children}</p>,
        }}
      >
        {md}
      </ReactMarkdown>
    </div>
  );
}
