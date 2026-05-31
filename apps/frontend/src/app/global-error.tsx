"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Icon } from "@/components/ui/Icon";
import "./globals.css";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const [sentryEventId, setSentryEventId] = useState<string | null>(null);

  useEffect(() => {
    if (process.env.NODE_ENV === "development") {
      // eslint-disable-next-line no-console
      console.error(error);
    }
    const eventId = Sentry.captureException(error);
    if (eventId) setSentryEventId(eventId);
  }, [error]);

  const ref = sentryEventId ?? error.digest ?? "no-reference";

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(ref);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard may be unavailable on http previews; ref is still visible
    }
  };

  return (
    <html lang="en">
      <body className="bg-background text-foreground antialiased">
        <main
          className="max-w-[640px] mx-auto px-5 sm:px-6 py-16 sm:py-24 text-center"
          role="alert"
        >
          <div
            className="font-mono mb-4"
            style={{
              fontSize: 14,
              letterSpacing: "0.1em",
              color: "var(--danger)",
            }}
          >
            ERROR 500
          </div>
          <h1
            className="font-display mb-3"
            style={{
              fontSize: "clamp(40px, 7vw, 72px)",
              lineHeight: 1.05,
              letterSpacing: "-0.02em",
            }}
          >
            Something{" "}
            <span className="italic" style={{ color: "var(--copper-600)" }}>
              broke
            </span>
            .
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
            Sorry — that wasn&apos;t supposed to happen. Our team has been
            notified. You can try again, or send us this reference ID so we
            can dig into your specific case.
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
            <code
              aria-label="Error reference identifier"
              style={{ color: "var(--ink)" }}
            >
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

          <div className="flex flex-wrap gap-3 justify-center mb-8">
            <button
              type="button"
              onClick={reset}
              className="btn btn-primary btn-lg"
            >
              Try again <Icon name="arrowRight" size={16} />
            </button>
            <Link href="/jobs" className="btn btn-ghost btn-lg">
              Back to jobs
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
              Send us a message
            </Link>{" "}
            with the reference ID above and we&apos;ll take a look.
          </p>
        </main>
      </body>
    </html>
  );
}
