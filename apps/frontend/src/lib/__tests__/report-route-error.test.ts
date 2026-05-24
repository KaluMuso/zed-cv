import { describe, it, expect, vi, beforeEach } from "vitest";

const captureException = vi.fn();
const withScope = vi.fn((cb: (scope: { setTag: typeof vi.fn; setContext: typeof vi.fn; setExtra: typeof vi.fn }) => void) => {
  const scope = {
    setTag: vi.fn(),
    setContext: vi.fn(),
    setExtra: vi.fn(),
  };
  cb(scope);
  return scope;
});

vi.mock("@sentry/nextjs", () => ({
  withScope: (fn: (scope: unknown) => void) => withScope(fn),
  captureException,
}));

describe("reportRouteError", () => {
  beforeEach(() => {
    vi.resetModules();
    captureException.mockClear();
    withScope.mockClear();
    vi.stubEnv("NEXT_PUBLIC_SENTRY_DSN", "https://example@o0.ingest.sentry.io/0");
    vi.stubEnv("NODE_ENV", "test");
  });

  it("captures exception with segment tag and digest extra", async () => {
    const { reportRouteError } = await import("@/lib/report-route-error");
    const err = Object.assign(new Error("segment fail"), { digest: "digest-xyz" });

    reportRouteError(err, { segment: "matches" });

    expect(withScope).toHaveBeenCalled();
    expect(captureException).toHaveBeenCalledWith(err);
    const scope = withScope.mock.results[0]?.value as {
      setTag: ReturnType<typeof vi.fn>;
      setExtra: ReturnType<typeof vi.fn>;
    };
    expect(scope.setTag).toHaveBeenCalledWith("route_segment", "matches");
    expect(scope.setExtra).toHaveBeenCalledWith("next_digest", "digest-xyz");
  });

  it("skips Sentry when DSN is unset", async () => {
    vi.stubEnv("NEXT_PUBLIC_SENTRY_DSN", "");
    const { reportRouteError } = await import("@/lib/report-route-error");
    reportRouteError(new Error("no dsn"), { segment: "jobs" });
    expect(captureException).not.toHaveBeenCalled();
  });
});
