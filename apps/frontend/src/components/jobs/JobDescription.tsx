"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { plainTextToMarkdown } from "@/lib/markdownNormalizer";

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
      <p className="text-sm" style={{ color: "var(--muted)" }}>
        No description provided.
      </p>
    );
  }

  return (
    <div
      className="job-description-markdown prose prose-sm max-w-none text-sm"
      style={{ color: "var(--ink-2)" }}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h2: ({ children }) => (
            <h2
              className="font-display text-lg mt-6 mb-2"
              style={{ letterSpacing: "-0.01em", color: "var(--ink)" }}
            >
              {children}
            </h2>
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              target={href?.startsWith("http") ? "_blank" : undefined}
              rel={href?.startsWith("http") ? "noopener noreferrer" : undefined}
              className="underline"
              style={{ color: "var(--copper-600)" }}
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
