"use client";

import { RouteSegmentError } from "@/components/RouteSegmentError";

export default function SettingsError({
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
      segment="(app)/settings"
      compact
      homeHref="/settings"
    />
  );
}
