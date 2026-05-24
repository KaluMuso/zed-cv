"use client";

import { RouteSegmentError } from "@/components/RouteSegmentError";

export default function JobsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <RouteSegmentError
      error={error}
      reset={reset}
      segment="jobs"
      compact
      homeHref="/jobs"
    />
  );
}
