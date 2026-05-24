"use client";

import { RouteSegmentError } from "@/components/RouteSegmentError";

export default function RootError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return <RouteSegmentError error={error} reset={reset} segment="root" />;
}
