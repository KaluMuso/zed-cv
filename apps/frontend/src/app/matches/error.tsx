"use client";

import { RouteSegmentError } from "@/components/RouteSegmentError";

export default function MatchesError({
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
      segment="matches"
      compact
      homeHref="/matches"
    />
  );
}
