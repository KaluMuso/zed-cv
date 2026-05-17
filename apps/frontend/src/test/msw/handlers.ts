import type { HttpHandler } from "msw";

// Default handlers — empty so onUnhandledRequest: "error" forces every
// test to declare its own handlers explicitly. Keeps test intent visible.
export const handlers: HttpHandler[] = [];

// Test-local handlers should be appended via server.use(...) inside the
// test or a beforeEach. See src/test/msw/README.md.
