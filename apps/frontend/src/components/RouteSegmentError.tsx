"use client";

import { useEffect } from "react";
import { ErrorFallback } from "@/components/ErrorFallback";
import { reportRouteError } from "@/lib/report-route-error";

type RouteSegmentErrorProps = {
  error: Error & { digest?: string };
  reset: () => void;
  segment: string;
  compact?: boolean;
  homeHref?: string;
};

/** Thin wrapper: Sentry report + branded fallback for App Router error.tsx files. */
export function RouteSegmentError({
  error,
  reset,
  segment,
  compact = false,
  homeHref,
}: RouteSegmentErrorProps) {
  useEffect(() => {
    reportRouteError(error, { segment });
  }, [error, segment]);

  return (
    <ErrorFallback
      error={error}
      reset={reset}
      segment={segment}
      compact={compact}
      homeHref={homeHref}
    />
  );
}
