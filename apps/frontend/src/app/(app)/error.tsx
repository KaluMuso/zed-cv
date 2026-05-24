"use client";

import { RouteSegmentError } from "@/components/RouteSegmentError";

/** Catches errors in the (app) route group without tearing down the root shell. */
export default function AppGroupError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <RouteSegmentError error={error} reset={reset} segment="(app)" compact />
  );
}
