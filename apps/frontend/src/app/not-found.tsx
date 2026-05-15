import Link from "next/link";
import type { Metadata } from "next";
import { Icon } from "@/components/ui/Icon";

export const metadata: Metadata = {
  title: "Not found",
  description: "The page you were looking for doesn't exist.",
  robots: { index: false, follow: false },
};

export default function NotFound() {
  return (
    <main
      className="max-w-[640px] mx-auto px-5 sm:px-6 py-16 sm:py-24 text-center"
      role="region"
    >
      <div
        className="font-mono mb-4"
        style={{
          fontSize: 14,
          letterSpacing: "0.1em",
          color: "var(--copper-500)",
        }}
      >
        ERROR 404
      </div>
      <h1
        className="font-display mb-3"
        style={{
          fontSize: "clamp(40px, 7vw, 72px)",
          lineHeight: 1.05,
          letterSpacing: "-0.02em",
        }}
      >
        This page{" "}
        <span className="italic" style={{ color: "var(--copper-600)" }}>
          wandered off
        </span>
        .
      </h1>
      <p
        className="text-base sm:text-lg mb-8"
        style={{
          color: "var(--ink-2)",
          lineHeight: 1.7,
          maxWidth: 460,
          margin: "0 auto 32px",
        }}
      >
        We couldn&apos;t find what you were looking for. The link may be
        stale or the listing may have been closed.
      </p>
      <div className="flex flex-wrap gap-3 justify-center">
        <Link href="/jobs" className="btn btn-primary btn-lg">
          Back to jobs <Icon name="arrowRight" size={16} />
        </Link>
        <Link href="/" className="btn btn-ghost btn-lg">
          Home
        </Link>
      </div>
    </main>
  );
}
