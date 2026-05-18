import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import SentryTestPage from "../page";

// Sanity check only. The page itself throws on render (that IS the
// behaviour) so this test deliberately does not invoke the component —
// it just verifies the module is on disk and exports a default
// function. If someone accidentally deletes /sentry-test before the
// Sentry capture has been verified in prod, this test fails loudly
// instead of silently disappearing.

describe("/sentry-test route", () => {
  it("has the page file on disk", () => {
    expect(existsSync(resolve(__dirname, "..", "page.tsx"))).toBe(true);
  });

  it("exports a default function", () => {
    expect(SentryTestPage).toBeDefined();
    expect(typeof SentryTestPage).toBe("function");
  });
});
