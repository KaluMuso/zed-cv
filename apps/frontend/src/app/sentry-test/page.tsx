import type { Metadata } from "next";

// Unlisted verification route — hitting /sentry-test should crash the
// server render so we can confirm Sentry is capturing exceptions from
// the Next.js runtime end-to-end. Delete in a follow-up commit once a
// real event has shown up in https://convergeo-w2.sentry.io/.
//
// force-dynamic skips static prerendering at build time; without it
// `next build` evaluates this page and the build itself fails. We
// only want the throw to fire when a user actually visits the URL.
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Sentry Test",
  robots: {
    index: false,
    follow: false,
    nocache: true,
    googleBot: { index: false, follow: false },
  },
};

export default function SentryTestPage(): never {
  // Heads-up paragraph never renders — this throw fires during the
  // server component render so the response is a 500. That's exactly
  // what we need: Sentry should capture the exception with a stack
  // trace, route, and (since source maps upload) symbolicated frames.
  throw new Error(
    "Intentional /sentry-test throw — verifying frontend Sentry capture.",
  );
}
