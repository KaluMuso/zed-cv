"use client";

import { useState } from "react";
import Link from "next/link";
import { Logo } from "@/components/ui/Logo";
import { Icon } from "@/components/ui/Icon";

export type ErrorFallbackProps = {
  error: Error & { digest?: string };
  reset: () => void;
  /** Shown in support ref copy; optional segment label for dev context. */
  segment?: string;
  homeHref?: string;
  compact?: boolean;
};

export function ErrorFallback({
  error,
  reset,
  segment,
  homeHref = "/",
  compact = false,
}: ErrorFallbackProps) {
  const [showDetails, setShowDetails] = useState(false);
  const [copied, setCopied] = useState(false);

  const ref = error.digest ?? "no-digest";
  const isDev = process.env.NODE_ENV === "development";

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(ref);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard may be unavailable on http previews
    }
  };

  return (
    <main
      className={
        compact
          ? "max-w-[560px] mx-auto px-4 py-10 sm:py-12 text-center"
          : "max-w-[640px] mx-auto px-5 sm:px-6 py-16 sm:py-24 text-center"
      }
      role="alert"
    >
      <div className="flex justify-center mb-6">
        <Logo size={compact ? 24 : 28} />
      </div>

      <h1
        className="font-display mb-3"
        style={{
          fontSize: compact ? "clamp(28px, 5vw, 40px)" : "clamp(32px, 6vw, 48px)",
          lineHeight: 1.1,
          letterSpacing: "-0.02em",
        }}
      >
        Something went wrong
      </h1>
      <p
        className="text-base sm:text-lg mb-6"
        style={{
          color: "var(--ink-2)",
          lineHeight: 1.7,
          maxWidth: 480,
          margin: "0 auto 24px",
        }}
      >
        Sorry — that wasn&apos;t supposed to happen. Try again, or go home and
        come back in a moment. If you contact support, include the reference
        below.
      </p>

      <div
        className="inline-flex items-center gap-2 px-4 py-2 mb-8 rounded-full"
        style={{
          background: "var(--bg-2)",
          border: "1px solid var(--line)",
          fontFamily: "var(--font-mono)",
          fontSize: 13,
          color: "var(--ink-2)",
        }}
      >
        <span style={{ color: "var(--muted)" }}>Ref:</span>
        <code aria-label="Error reference identifier" style={{ color: "var(--ink)" }}>
          {ref}
        </code>
        <button
          type="button"
          onClick={handleCopy}
          className="ml-1"
          style={{
            background: "none",
            border: "none",
            color: copied ? "var(--green-700)" : "var(--muted)",
            cursor: "pointer",
            fontSize: 12,
            padding: "2px 6px",
          }}
          aria-label="Copy reference ID"
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>

      <div className="flex flex-wrap gap-3 justify-center mb-6">
        <button type="button" onClick={reset} className="btn btn-primary btn-lg">
          Try again <Icon name="arrowRight" size={16} />
        </button>
        <Link href={homeHref} className="btn btn-ghost btn-lg">
          Go home
        </Link>
      </div>

      <p className="text-sm" style={{ color: "var(--muted)" }}>
        Still stuck?{" "}
        <Link
          href={`/contact?ref=${encodeURIComponent(ref)}`}
          style={{
            color: "var(--green-700)",
            textDecoration: "underline",
          }}
        >
          Contact support
        </Link>
        {segment ? (
          <>
            {" "}
            <span className="sr-only">Route segment: {segment}</span>
          </>
        ) : null}
      </p>

      {isDev ? (
        <div className="mt-8 text-left max-w-lg mx-auto">
          <button
            type="button"
            className="text-sm font-medium"
            style={{ color: "var(--green-700)" }}
            onClick={() => setShowDetails((v) => !v)}
            aria-expanded={showDetails}
          >
            {showDetails ? "Hide error details" : "Show error details"}
          </button>
          {showDetails ? (
            <pre
              className="mt-3 p-4 rounded-lg overflow-auto text-left text-xs"
              style={{
                background: "var(--bg-2)",
                border: "1px solid var(--line)",
                color: "var(--ink-2)",
                maxHeight: 240,
              }}
            >
              {error.message}
              {"\n\n"}
              {error.stack ?? "(no stack trace)"}
            </pre>
          ) : null}
        </div>
      ) : null}
    </main>
  );
}
