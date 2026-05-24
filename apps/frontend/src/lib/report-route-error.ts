import * as Sentry from "@sentry/nextjs";

export type RouteErrorContext = {
  /** App Router segment id, e.g. "jobs" or "(app)/settings". */
  segment: string;
};

/**
 * Report a route-segment error to Sentry with digest + pathname context.
 * Next.js already attaches navigation breadcrumbs when the SDK is enabled;
 * we add segment tags so issues group by heavy route.
 */
export function reportRouteError(
  error: Error & { digest?: string },
  context: RouteErrorContext
): void {
  if (process.env.NODE_ENV === "development") {
    // eslint-disable-next-line no-console
    console.error(`[ZedApply] ${context.segment} error:`, error);
  }

  if (!process.env.NEXT_PUBLIC_SENTRY_DSN) return;

  const pathname =
    typeof window !== "undefined" ? window.location.pathname : undefined;

  Sentry.withScope((scope) => {
    scope.setTag("route_segment", context.segment);
    if (pathname) {
      scope.setTag("pathname", pathname);
      scope.setContext("route", { segment: context.segment, pathname });
    }
    if (error.digest) {
      scope.setExtra("next_digest", error.digest);
    }
    Sentry.captureException(error);
  });
}
