# MSW test handlers

The global `handlers` array in `handlers.ts` is intentionally empty.

## Why
`setupServer` is started with `onUnhandledRequest: "error"` in `src/test/setup.ts`.
Any fetch a test makes without a matching handler becomes a test failure
rather than a silent network attempt. This keeps test intent visible —
every mocked endpoint shows up next to the test that depends on it.

## How to declare handlers
Append them per-test (or per-`describe`) with `server.use(...)`:

```ts
import { http, HttpResponse } from "msw";
import { server } from "@/test/msw/server";

it("loads jobs", async () => {
  server.use(
    http.get("/api/jobs", () => HttpResponse.json({ jobs: [] })),
  );
  // ...
});
```

`server.resetHandlers()` runs in `afterEach`, so per-test handlers do not
leak into the next test.

## What not to do
- Do not add fixtures or "default" handlers to `handlers.ts`. Tests should
  fail loudly when they touch an undeclared endpoint.
- Do not call `server.listen()` or `server.close()` in individual tests —
  the lifecycle is owned by `src/test/setup.ts`.
