# Frontend testing

Unit + component tests for `apps/frontend/` run on **Vitest** + **React
Testing Library** + **MSW v2** (Node integration).

## Running

```bash
npm test              # one-shot run (CI mode)
npm run test:watch    # interactive watcher
npm run test:ui       # browser UI for debugging
npm run test:coverage # write coverage/ artefacts
```

## Where tests live

- **Co-locate** unit/component tests next to the file under test:
  `Foo.tsx` ↔ `Foo.test.tsx`, `useBar.ts` ↔ `useBar.test.ts`.
- Cross-cutting fixtures, the MSW server, and shared helpers live in
  `src/test/`.

Vitest picks up anything matching `src/**/*.{test,spec}.{ts,tsx}`.

## Naming

- `<component>.test.tsx` for React components.
- `<hook>.test.ts` for hooks (no JSX renderer needed).
- `<utility>.test.ts` for plain TS helpers.

## MSW discipline

The global handlers list (`src/test/msw/handlers.ts`) is empty by design.
`setupServer` runs with `onUnhandledRequest: "error"`, so a missing
handler fails the test instead of silently hitting the network. Declare
handlers per-test via `server.use(...)`. See
`src/test/msw/README.md` for examples.

## What not to do here

- **No real network.** Every outbound fetch must be intercepted.
- **No `localStorage`.** Next.js App Router rules apply in tests too —
  use the in-memory stores the app already uses.
- **No snapshot tests.** They rot quickly; prefer explicit assertions on
  the bits of the DOM you care about.
- **No retrofitted tests in this PR.** This bootstrap PR only ships
  infrastructure and two sentinel tests. Production code stays untouched.

## Cross-stack consistency

Backend tests live in `apps/backend/` and use `pytest`. The frontend
mirrors the same shape (co-located, opt-in fixtures, no shared global
state between tests). If you change one stack's conventions, update the
other.
