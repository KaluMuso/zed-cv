"use client";

import { useEffect } from "react";
import { ErrorFallback } from "@/components/ErrorFallback";
import { reportRouteError } from "@/lib/report-route-error";
import "./globals.css";

/**
 * Last-resort boundary when the root layout itself throws.
 * Must define its own <html> and <body> — parent layout is unavailable.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    reportRouteError(error, { segment: "global" });
  }, [error]);

  return (
    <html lang="en">
      <body className="min-h-screen font-sans bg-background text-foreground">
        <ErrorFallback error={error} reset={reset} segment="global" />
      </body>
    </html>
  );
}
